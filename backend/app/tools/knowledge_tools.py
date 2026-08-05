"""本地旅行攻略检索工具：对话侧薄封装 + 对话版 query rewrite。

底层复用 retrieve_travel_guide（embedding / 召回 / 重排 / 缓存）。
不复用规划侧「主 query + 住宿 + 餐饮」多路编排。
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MAX_RETRIES,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_TIMEOUT_SECONDS,
    OPENCODE_API_KEY,
    OPENCODE_BASE_URL,
)
from app.llm import build_chat_llm
from app.rag.guide_catalog import known_destinations
from app.rag.retriever import retrieve_travel_guide
from app.tools.base import ToolResult


logger = logging.getLogger(__name__)

TOOL_NAME = "search_travel_guide"
CHAT_RAG_TOP_K = 3
MAX_SNIPPET_CHARS = 600
MAX_QUESTION_CHARS = 500


def _build_chat_llm():
    return build_chat_llm(
        provider=LLM_PROVIDER,
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        opencode_api_key=OPENCODE_API_KEY,
        opencode_base_url=OPENCODE_BASE_URL,
        temperature=0.2,
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=LLM_MAX_RETRIES,
    )


def _extract_response_text(response: Any) -> str:
    raw = getattr(response, "content", "")
    if isinstance(raw, list):
        return "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in raw
        ).strip()
    return str(raw or "").strip()


def resolve_destination(question: str, destination: str | None = None) -> str | None:
    """解析目的地：优先显式参数，其次从问句匹配已知攻略城市。"""
    explicit = (destination or "").strip()
    if explicit:
        # 兼容「大理市」「大理白族自治州」等：命中已知城市名则归一
        for city in sorted(known_destinations(), key=len, reverse=True):
            if city in explicit:
                return city
        return explicit

    text = (question or "").strip()
    if not text:
        return None
    for city in sorted(known_destinations(), key=len, reverse=True):
        if city in text:
            return city
    return None


def rewrite_chat_query(question: str, destination: str) -> tuple[str, str]:
    """必须通过 LLM 改写对话检索 Query；失败时中断检索。"""
    llm = _build_chat_llm()
    if llm is None:
        raise RuntimeError("LLM Query Rewrite is required but unavailable")

    system_prompt = (
        "你是旅行攻略向量检索的 query 改写器。"
        "把用户的一句话问题改写成适合本地攻略检索的关键词组合。"
        "要求："
        "1. 只输出空格分隔的关键词，不要解释、标点或句子"
        "2. 必须包含目的地城市名"
        "3. 保留问题主题（如日落、避坑、亲子、夜景、美食、节奏）"
        "4. 关键词要具体，可含景点名或场景特征"
        "5. 不要无故追加「景点 行程 攻略 推荐 餐饮 住宿」等泛化尾巴"
        "6. 不要扩展成住宿+餐饮多主题；只服务当前这一问"
    )
    human_prompt = f"目的地：{destination}\n用户问题：{question.strip()}"

    try:
        response = llm.invoke(
            [
                ("system", system_prompt),
                ("human", human_prompt),
            ]
        )
    except Exception as exc:
        raise RuntimeError("LLM Query Rewrite failed") from exc

    query = _extract_response_text(response)
    query = re.sub(r"[\"'`]+", "", query)
    query = " ".join(query.split())
    if not query:
        raise RuntimeError("LLM Query Rewrite returned an empty query")
    if destination not in query:
        raise RuntimeError("LLM Query Rewrite omitted the destination")

    logger.info(
        "chat rewrite: dest=%s question=%s -> %s",
        destination,
        question[:80],
        query,
    )
    return query, "llm"


def _truncate_snippet(text: str, limit: int = MAX_SNIPPET_CHARS) -> str:
    body = (text or "").strip()
    if len(body) <= limit:
        return body
    return body[:limit].rstrip() + "…"


def tool_search_travel_guide(
    question: str,
    destination: str | None = None,
) -> ToolResult:
    """检索本地旅行攻略知识库（固定 top_k=3）。"""
    q = (question or "").strip()
    if not q:
        return ToolResult(
            ok=False,
            name=TOOL_NAME,
            error="question 不能为空",
            summary="缺少检索问题",
            source="local_rag",
        )
    if len(q) > MAX_QUESTION_CHARS:
        q = q[:MAX_QUESTION_CHARS]

    dest = resolve_destination(q, destination)
    if not dest:
        return ToolResult(
            ok=False,
            name=TOOL_NAME,
            error="缺少目的地城市，无法检索本地攻略",
            summary="请先确认目的地城市后再查攻略",
            data={"need_destination": True},
            source="local_rag",
        )

    try:
        query, rewrite_source = rewrite_chat_query(q, dest)
    except RuntimeError as exc:
        logger.warning("search_travel_guide query rewrite failed: %s", exc)
        return ToolResult(
            ok=False,
            name=TOOL_NAME,
            error=str(exc),
            summary=f"本地攻略检索失败：{exc}",
            source="local_rag",
        )

    try:
        contexts, _rerank_usage, _embed_usage = retrieve_travel_guide(
            query=query,
            top_k=CHAT_RAG_TOP_K,
            destination=dest,
        )
    except Exception as exc:  # noqa: BLE001 - 工具边界
        logger.warning("search_travel_guide failed query=%s: %s", query, exc)
        return ToolResult(
            ok=False,
            name=TOOL_NAME,
            error=str(exc),
            summary=f"本地攻略检索失败：{exc}",
            source="local_rag",
        )

    snippets: list[dict[str, str]] = []
    for item in contexts:
        text = str(item)
        source = ""
        title = ""
        body = text
        # 解析 retrieve_travel_guide 格式: [来源: x | 标题: y]\nbody
        if text.startswith("[来源:"):
            header, _, rest = text.partition("]\n")
            body = rest if rest else text
            header_inner = header[len("[来源:") :].strip()
            if "| 标题:" in header_inner:
                src_part, _, title_part = header_inner.partition("| 标题:")
                source = src_part.strip()
                title = title_part.strip()
            else:
                source = header_inner
        snippets.append(
            {
                "source": source,
                "title": title,
                "text": _truncate_snippet(body),
            }
        )

    if not snippets:
        return ToolResult(
            ok=True,
            name=TOOL_NAME,
            data={
                "destination": dest,
                "question": q,
                "query": query,
                "rewrite_source": rewrite_source,
                "top_k": CHAT_RAG_TOP_K,
                "snippets": [],
            },
            summary=f"本地攻略暂无与「{dest} / {q[:40]}」直接相关的片段",
            source="local_rag",
        )

    titles = [s["title"] or s["source"] or "片段" for s in snippets[:3]]
    summary = f"已检索「{dest}」本地攻略 {len(snippets)} 条：{'、'.join(titles)}"
    return ToolResult(
        ok=True,
        name=TOOL_NAME,
        data={
            "destination": dest,
            "question": q,
            "query": query,
            "rewrite_source": rewrite_source,
            "top_k": CHAT_RAG_TOP_K,
            "snippets": snippets,
        },
        summary=summary,
        source="local_rag",
    )
