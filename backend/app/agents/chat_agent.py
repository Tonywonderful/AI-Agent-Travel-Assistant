"""对话 Agent：prompt 组装 + LLM Tool Calling 循环 + 最终流式输出。

通过模型原生 tool calling 决定是否调用工具。
工具实现见 app.tools；MCP 外壳见 app.mcp。
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from app.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MAX_RETRIES,
    LLM_MODEL,
    LLM_TIMEOUT_SECONDS,
)
from app.models.chat_schemas import ChatContext, ChatMessage
from app.tools.registry import execute_tool, get_tool_specs, parse_tool_arguments


logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 3

SYSTEM_PROMPT = """你是旅行对话助手，面向中文用户。

你可以使用工具查询信息：
- search_travel_guide：本地旅行攻略知识库（策展过的玩法、避坑、节奏、与产品口径一致的推荐说明）
- get_weather_forecast：天气预报
- geocode_place：地址/地点解析为坐标
- search_poi：搜索景点、餐厅、酒店等 POI（列表广度、周边检索）
- estimate_route：估算两地驾车距离与时间
- web_search：联网搜索（门票预约政策、开放时间变更、活动节庆、交通公告等时效信息）

工具分工：
- 怎么玩、避坑、节奏、和「本地攻略/行程」一致的建议 → 优先 search_travel_guide。
- 附近有什么酒店/餐厅/景点列表、距离远近 → 优先 search_poi / estimate_route；若攻略也有精选可再调 search_travel_guide 作补充，并区分「攻略精选」与「地图周边」。
- 门票预约、是否临时闭园、政策公告、近期活动等时效信息 → web_search。
- 冷不冷、宜不宜户外 → get_weather_forecast。
- 不要用 web_search 替代本地攻略库；不要用知识库冒充附近 POI 大全；不要用 web_search 替代天气/POI/路线工具。
- 纯行程解释、预算讨论等若上下文已足够，可不调用工具。
- 城市/地点未知时，优先从「当前只读上下文」中的目的地推断并传给工具；仍不足则先向用户确认，不要盲搜。
- 调用 search_travel_guide 时：question 写清用户意图；destination 尽量带上上下文中的城市。
- 不要编造工具未返回的营业时间、实时票价、精确路况；web_search 与攻略结果都要概括依据，勿捏造事实。
- 工具失败或攻略无结果时如实说明，可降级到其他工具或一般性建议。
- 你不能直接修改系统中的行程数据；若用户要改行程，先给可执行建议。

回答要求：
- 使用简洁中文，结构清晰，可分点；可用 Markdown。
- 若使用了工具，回答中简要体现依据（例如「根据本地攻略…」「地图检索显示…」「根据联网检索…」）。
- 拿到工具结果后，必须整理成对用户可读的中文回答（列表/要点），不要复述工具参数，不要输出 tool_call/function/parameter 等标签。
- 若上下文中有行程，优先结合行程并引用「第 N 天」。
- 不要暴露内部实现细节（模型名、密钥、代码路径、工具内部错误栈等）。
"""


def _build_chat_llm(*, streaming: bool):
    if not LLM_API_KEY:
        return None

    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        logger.warning("langchain_openai 未安装，无法启动对话")
        return None

    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=0.4,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL or None,
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=LLM_MAX_RETRIES,
        streaming=streaming,
    )


def _openai_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": spec["name"],
                "description": spec["description"],
                "parameters": spec["parameters"],
            },
        }
        for spec in get_tool_specs()
    ]


def _format_context_block(context: ChatContext) -> str:
    """把只读上下文格式化为 system 附加说明。"""
    lines: list[str] = [f"当前页面: {context.page}"]

    if context.planning is not None:
        planning = context.planning
        lines.append("规划表单草稿:")
        if planning.destination:
            lines.append(f"- 目的地: {planning.destination}")
        if planning.start_date or planning.end_date:
            lines.append(
                f"- 日期: {planning.start_date or '?'} ~ {planning.end_date or '?'}"
            )
        if planning.travelers is not None:
            lines.append(f"- 人数: {planning.travelers}")
        if planning.budget is not None:
            lines.append(f"- 预算: {planning.budget}")
        if planning.pace:
            lines.append(f"- 节奏: {planning.pace}")
        if planning.hotel_level:
            lines.append(f"- 住宿: {planning.hotel_level}")
        if planning.preferences:
            lines.append(f"- 偏好: {', '.join(planning.preferences)}")
        if planning.dietary_preferences:
            lines.append(f"- 饮食: {', '.join(planning.dietary_preferences)}")
        if planning.special_notes:
            lines.append(f"- 额外要求: {planning.special_notes}")

    if context.itinerary is not None:
        itinerary = context.itinerary
        lines.append("当前行程摘要:")
        if itinerary.trip_id:
            lines.append(f"- trip_id: {itinerary.trip_id}")
        if itinerary.destination:
            lines.append(f"- 目的地: {itinerary.destination}")
        if itinerary.day_count is not None:
            lines.append(f"- 天数: {itinerary.day_count}")
        if itinerary.estimated_budget is not None:
            lines.append(f"- 预估预算: {itinerary.estimated_budget}")
        if itinerary.summary:
            lines.append(f"- 概述: {itinerary.summary}")
        if itinerary.day_titles:
            lines.append("- 每日安排:")
            for title in itinerary.day_titles[:14]:
                lines.append(f"  - {title}")

    if context.extra:
        lines.append(f"其他上下文: {context.extra}")

    return "\n".join(lines)


def build_langchain_messages(
    messages: list[ChatMessage],
    context: ChatContext,
) -> list[Any]:
    """组装 LangChain 消息列表。"""
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    system_content = SYSTEM_PROMPT + "\n\n# 当前只读上下文\n" + _format_context_block(context)
    lc_messages: list[Any] = [SystemMessage(content=system_content)]

    for item in messages:
        text = item.content.strip()
        if not text:
            continue
        if item.role == "user":
            lc_messages.append(HumanMessage(content=text))
        elif item.role == "assistant":
            lc_messages.append(AIMessage(content=text))
        elif item.role == "system":
            lc_messages.append(SystemMessage(content=text))

    return lc_messages


def _extract_text_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return "".join(parts)
    return str(content)


def _normalize_tool_calls(ai_message: Any) -> list[dict[str, Any]]:
    """统一 tool_calls 结构为 {id, name, args}。"""
    raw_calls = getattr(ai_message, "tool_calls", None) or []
    normalized: list[dict[str, Any]] = []
    for index, call in enumerate(raw_calls):
        if isinstance(call, dict):
            name = call.get("name") or ""
            call_id = call.get("id") or f"call_{index}"
            args = parse_tool_arguments(call.get("args") or call.get("arguments"))
        else:
            name = getattr(call, "name", "") or ""
            call_id = getattr(call, "id", None) or f"call_{index}"
            args = parse_tool_arguments(getattr(call, "args", None))
        if not name:
            continue
        normalized.append({"id": call_id, "name": name, "args": args})
    return normalized


def _looks_like_raw_tool_call(text: str) -> bool:
    """识别模型把 tool call 泄漏成正文（如 <tool_call>/<function=...>）。"""
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    markers = (
        "<tool_call",
        "</tool_call>",
        "<function=",
        "</function>",
        "<parameter=",
        "tool_call>",
        "functioncall",
    )
    return any(marker in lowered for marker in markers)


def _fallback_answer_from_tool_summaries(summaries: list[str]) -> str:
    usable = [s.strip() for s in summaries if s and s.strip()]
    if not usable:
        return "我已完成检索，但没能整理出可读结果。请换个说法再试一次。"
    lines = ["根据刚刚的检索结果："]
    for item in usable[-3:]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("如需更具体的推荐（口味、预算、步行距离），可以继续告诉我。")
    return "\n".join(lines)


def _stream_final_answer(
    stream_llm: Any,
    lc_messages: list[Any],
    *,
    used_tools: bool,
    tool_summaries: list[str],
) -> Iterator[dict[str, Any]]:
    """无工具地生成最终回答；过滤 tool-call 泄漏，必要时回退到工具摘要。"""
    from langchain_core.messages import HumanMessage

    final_messages = list(lc_messages)
    if used_tools:
        final_messages.append(
            HumanMessage(
                content=(
                    "请仅基于上文工具返回结果，用简洁中文直接回答用户。"
                    "给出结构化要点即可；禁止再次调用任何工具；"
                    "禁止输出 <tool_call>、<function>、<parameter> 等标签或参数列表。"
                )
            )
        )

    parts: list[str] = []
    for chunk in stream_llm.stream(final_messages):
        text = _extract_text_content(getattr(chunk, "content", None))
        if text:
            parts.append(text)

    full = "".join(parts).strip()
    if not full or _looks_like_raw_tool_call(full):
        logger.warning(
            "final answer missing or leaked tool markup (len=%s), using tool summary fallback",
            len(full),
        )
        full = _fallback_answer_from_tool_summaries(tool_summaries)

    if full:
        yield {"type": "token", "text": full}


def iter_assistant_events(
    messages: list[ChatMessage],
    context: ChatContext,
) -> Iterator[dict[str, Any]]:
    """产出对话事件：tool_start / tool_result / token。

    调用约定：
    - tool_start: {"type":"tool_start","name":str,"args":dict}
    - tool_result: {"type":"tool_result","name":str,"ok":bool,"summary":str,"error":str|None}
    - token: {"type":"token","text":str}
    """
    from langchain_core.messages import ToolMessage

    llm = _build_chat_llm(streaming=False)
    stream_llm = _build_chat_llm(streaming=True)
    if llm is None or stream_llm is None:
        raise RuntimeError(
            "对话模型不可用：请检查 LLM_API_KEY / LLM_BASE_URL / langchain_openai 依赖。"
        )

    lc_messages = build_langchain_messages(messages, context)
    if len(lc_messages) < 2:
        raise ValueError("消息列表无效：至少需要一条用户消息。")

    tool_defs = _openai_tool_definitions()
    llm_with_tools = llm.bind_tools(tool_defs)
    tool_summaries: list[str] = []
    used_tools = False

    for round_index in range(MAX_TOOL_ROUNDS):
        ai_message = llm_with_tools.invoke(lc_messages)
        tool_calls = _normalize_tool_calls(ai_message)
        content_text = _extract_text_content(getattr(ai_message, "content", None)).strip()

        if not tool_calls:
            # 模型已给出最终文本（且不是 tool-call 泄漏）时直接使用，避免二次生成跑偏
            if content_text and not _looks_like_raw_tool_call(content_text):
                yield {"type": "token", "text": content_text}
                return

            yield from _stream_final_answer(
                stream_llm,
                lc_messages,
                used_tools=used_tools,
                tool_summaries=tool_summaries,
            )
            return

        logger.info(
            "chat tool round %s: %s",
            round_index + 1,
            [item["name"] for item in tool_calls],
        )
        used_tools = True
        lc_messages.append(ai_message)

        for call in tool_calls:
            yield {
                "type": "tool_start",
                "name": call["name"],
                "args": call["args"],
            }
            result = execute_tool(call["name"], call["args"])
            if result.summary:
                tool_summaries.append(result.summary)
            yield {
                "type": "tool_result",
                "name": result.name,
                "ok": result.ok,
                "summary": result.summary,
                "error": result.error,
            }
            lc_messages.append(
                ToolMessage(
                    content=result.to_llm_content(),
                    tool_call_id=call["id"],
                )
            )

    # 达到工具轮次上限后，强制无工具生成最终回答
    logger.warning("chat tool rounds exhausted, generating final answer without tools")
    yield from _stream_final_answer(
        stream_llm,
        lc_messages,
        used_tools=True,
        tool_summaries=tool_summaries,
    )


def stream_assistant_tokens(
    messages: list[ChatMessage],
    context: ChatContext,
) -> Iterator[str]:
    """仅产出文本 token（事件流的简化视图）。"""
    for event in iter_assistant_events(messages, context):
        if event.get("type") == "token":
            text = event.get("text")
            if text:
                yield str(text)
