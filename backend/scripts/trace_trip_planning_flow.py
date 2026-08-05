from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agents.tools.rag_tool import RAG_TOP_K
from app.agents.trip_planner_agent import (
    PlannerDraft,
    collect_trip_context as _original_collect_trip_context,
    generate_planner_draft as _original_generate_planner_draft,
)
from app.config import (
    AMAP_API_KEY,
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
    ENABLE_AMAP_ENRICHMENT,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_PROVIDER,
    RERANK_MODEL,
)
from app.models.schemas import TripRequest
from app.rag.retriever import retrieve_travel_guide as _original_retrieve_travel_guide
from app.rag.retriever import (
    retrieve_travel_guide_chunks as _original_retrieve_travel_guide_chunks,
)
from app.services.fallback_candidates import (
    extract_fallback_candidates,
    extract_hotel_candidates,
    extract_restaurant_candidates,
)
from app.services.name_guard import (
    KIND_MEALS,
    KIND_SPOTS,
    build_guard_index,
    verify_name,
)
from app.services.trip_service import generate_trip_itinerary as _original_generate_trip_itinerary


OUTPUT_DIR = Path("D:/develop/AI_tryProject/TravelPlanAssistant/outputs")
REPORT_FILE = OUTPUT_DIR / "xiamen_3days_flow_trace_20260804.md"

# ---------------------------------------------------------------------------
# 脱敏 helpers
# ---------------------------------------------------------------------------

def _mask_key(value: str | None) -> str:
    if not value:
        return "<EMPTY>"
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


_SECRET_KEY_NAMES = {"api_key", "key", "secret", "password"}


def _looks_like_secret(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    # 典型的 API Key：长度 >= 16 且只含字母、数字、下划线、横线
    if len(value) < 16:
        return False
    if all(ch.isalnum() or ch in "_-" for ch in value):
        return True
    return False


def _mask_dict(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        low = k.lower()
        is_secret_key = any(name in low for name in _SECRET_KEY_NAMES) and low not in {
            "token_usage",
            "prompt_tokens",
            "completion_tokens",
        }
        if is_secret_key and _looks_like_secret(v):
            out[k] = _mask_key(v)
        elif isinstance(v, dict):
            out[k] = _mask_dict(v)
        elif isinstance(v, list):
            out[k] = [_mask_dict(i) if isinstance(i, dict) else i for i in v]
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------------------
# 跟踪记录器
# ---------------------------------------------------------------------------

RETRIEVAL_RECORDS: list[dict[str, Any]] = []
PLANNER_RECORD: dict[str, Any] = {}
ITINERARY_RECORD: dict[str, Any] = {}
COLLECTED_CONTEXTS: list[str] | None = None
COLLECTED_USAGES: dict[str, dict[str, int]] | None = None


def _route_label(categories: list[str] | None) -> str:
    if not categories:
        return "主查询"
    cat = categories[0]
    return {"attraction": "主查询（景点）", "hotel": "住宿专项", "restaurant": "餐饮专项"}.get(cat, cat)


def traced_retrieve_travel_guide_chunks(
    query: str,
    top_k: int = RAG_TOP_K,
    destination: str | None = None,
    retrieval_scope: str | None = None,
    categories: list[str] | None = None,
    budget_tier: str | None = None,
) -> tuple[list[dict[str, str]], dict[str, int], dict[str, int]]:
    chunks, rerank_usage, embedding_usage = _original_retrieve_travel_guide_chunks(
        query=query,
        top_k=top_k,
        destination=destination,
        retrieval_scope=retrieval_scope,
        categories=categories,
        budget_tier=budget_tier,
    )
    candidate_k = max(top_k * 2, 6)
    record = {
        "route": _route_label(categories),
        "query": query,
        "top_k": top_k,
        "candidate_k": candidate_k,
        "destination": destination,
        "categories": categories,
        "budget_tier": budget_tier,
        "unique_chunks_after_dedup": len(chunks),
        "rerank_usage": rerank_usage,
        "embedding_usage": embedding_usage,
        "chunks": [
            {
                "source": chunk.get("source", ""),
                "title": chunk.get("title") or chunk.get("entity_name", ""),
                "category": chunk.get("category", ""),
                "rerank_score": chunk.get("rerank_score"),
                "text_preview": (chunk.get("text", "")[:400] + "...")
                if len(chunk.get("text", "")) > 400
                else chunk.get("text", ""),
            }
            for chunk in chunks
        ],
    }
    RETRIEVAL_RECORDS.append(record)
    return chunks, rerank_usage, embedding_usage


def traced_retrieve_travel_guide(
    query: str,
    top_k: int = RAG_TOP_K,
    destination: str | None = None,
    retrieval_scope: str | None = None,
    categories: list[str] | None = None,
    budget_tier: str | None = None,
) -> tuple[list[str], dict[str, int], dict[str, int]]:
    """覆盖外层缓存，保证 trace 能记录到真正的 retrieve_travel_guide_chunks 调用。"""
    chunks, rerank_usage, embedding_usage = traced_retrieve_travel_guide_chunks(
        query=query,
        top_k=top_k,
        destination=destination,
        retrieval_scope=retrieval_scope,
        categories=categories,
        budget_tier=budget_tier,
    )
    texts = [
        f"[来源: {chunk['source']} | 标题: {chunk['title']}]\n{chunk['text']}"
        for chunk in chunks
    ]
    return texts, rerank_usage, embedding_usage


def traced_generate_planner_draft(
    request: TripRequest,
    rag_contexts: list[str],
    day_count: int,
) -> tuple[PlannerDraft | None, dict[str, int]]:
    draft, usage = _original_generate_planner_draft(request, rag_contexts, day_count)

    hotel_names = [item["name"] for item in extract_hotel_candidates(rag_contexts)]
    restaurant_names = [item["name"] for item in extract_restaurant_candidates(rag_contexts)]

    PLANNER_RECORD.update(
        {
            "model": LLM_MODEL,
            "provider": LLM_PROVIDER,
            "day_count": day_count,
            "rag_contexts_count": len(rag_contexts),
            "hotel_candidates_for_prompt": hotel_names[:6],
            "restaurant_candidates_for_prompt": restaurant_names[:6],
            "token_usage": usage,
            "draft_raw": draft.model_dump(mode="json") if draft else None,
        }
    )
    return draft, usage


def traced_collect_trip_context(**kwargs: Any) -> tuple[list[str], dict[str, int], dict[str, int], dict[str, int]]:
    contexts, rewrite_usage, rerank_usage, embedding_usage = _original_collect_trip_context(**kwargs)
    global COLLECTED_CONTEXTS, COLLECTED_USAGES
    COLLECTED_CONTEXTS = contexts
    COLLECTED_USAGES = {
        "rewrite": rewrite_usage,
        "rerank": rerank_usage,
        "embedding": embedding_usage,
    }
    return contexts, rewrite_usage, rerank_usage, embedding_usage


def traced_generate_trip_itinerary(request: TripRequest) -> Any:
    itinerary = _original_generate_trip_itinerary(request)
    ITINERARY_RECORD.update(
        {
            "trip_id": itinerary.trip_id,
            "destination": itinerary.destination,
            "summary": itinerary.summary,
            "estimated_budget": itinerary.estimated_budget,
            "budget_breakdown": itinerary.budget_breakdown.model_dump(),
            "tips": itinerary.tips,
            "token_usage": itinerary.token_usage.model_dump(),
            "source_notes": itinerary.source_notes,
            "days": [day.model_dump(mode="json") for day in itinerary.days],
        }
    )
    return itinerary


# ---------------------------------------------------------------------------
# patch 模块级引用
# ---------------------------------------------------------------------------

import app.agents.tools.rag_tool as _rag_tool_module
import app.agents.trip_planner_agent as _planner_module
import app.rag.retriever as _retriever_module
import app.services.trip_service as _trip_service_module

_retriever_module.retrieve_travel_guide_chunks = traced_retrieve_travel_guide_chunks  # type: ignore[assignment]
_retriever_module.retrieve_travel_guide = traced_retrieve_travel_guide  # type: ignore[assignment]
_rag_tool_module.retrieve_travel_guide = traced_retrieve_travel_guide  # type: ignore[assignment]
_planner_module.collect_trip_context = traced_collect_trip_context  # type: ignore[assignment]
_planner_module.generate_planner_draft = traced_generate_planner_draft  # type: ignore[assignment]
_trip_service_module.collect_trip_context = traced_collect_trip_context  # type: ignore[assignment]
_trip_service_module.generate_planner_draft = traced_generate_planner_draft  # type: ignore[assignment]
_trip_service_module.generate_trip_itinerary = traced_generate_trip_itinerary  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# 构造请求：与图 1 表单完全一致
# ---------------------------------------------------------------------------

def build_request_from_image() -> TripRequest:
    return TripRequest(
        destination="厦门",
        start_date=date(2026, 8, 5),
        end_date=date(2026, 8, 7),
        travelers=1,
        budget_min_per_person=10000.0,
        budget_max_per_person=15000.0,
        preferences=["自然风景", "城市漫游", "美食探索"],
        pace="轻松",  # 前端"悠闲放松"映射到 value="轻松"
        dietary_preferences=["本地特色", "海鲜"],
        hotel_level="舒适型",
        special_notes="希望体验当地文化，偏好地铁出行，减少换乘。",
    )


# ---------------------------------------------------------------------------
# Markdown 报告生成
# ---------------------------------------------------------------------------

def _indent_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _chunk_table(chunks: list[dict[str, Any]]) -> str:
    lines = [
        "| # | 来源 | 标题 | 类别 | 重排分数 | 正文预览 |",
        "|---|------|------|------|----------|----------|",
    ]
    for idx, chunk in enumerate(chunks, start=1):
        score = chunk.get("rerank_score")
        score_str = f"{score:.4f}" if score is not None else "-"
        text = chunk.get("text_preview", "").replace("\n", " ")
        lines.append(
            f"| {idx} | {chunk.get('source', '')} | {chunk.get('title', '')} | "
            f"{chunk.get('category', '')} | {score_str} | {text[:120]} |"
        )
    return "\n".join(lines)


def _build_report(request: TripRequest, day_count: int) -> str:
    lines: list[str] = []

    lines.append("# 厦门 3 日行程规划全链路 Trace 报告")
    lines.append("")
    lines.append(f"- 生成时间：{date.today().isoformat()}")
    lines.append("- 触发方式：按图 1 表单输入，直接调用 `trip_service.generate_trip_itinerary`，未使用 pytest 测试")
    lines.append("- 运行脚本：`backend/scripts/trace_trip_planning_flow.py`")
    lines.append("")

    lines.append("## 0. 流程总览")
    lines.append("")
    lines.append("```mermaid")
    lines.append("flowchart TD")
    lines.append("    A[用户表单 TripRequest] --> B[rag_tool.build_destination_query]")
    lines.append("    B --> C[主查询 retrieve_travel_guide<br/>category=attraction top_k=5]")
    lines.append("    C --> D[向量召回 10 条 → 实体去重 → Cross-encoder 重排 → 5 条]")
    lines.append("    D --> E[住宿专项 retrieve_travel_guide<br/>category=hotel top_k=3 + budget_tier 硬过滤]")
    lines.append("    E --> F[向量召回 6 条 → 去重重排 → 3 条]")
    lines.append("    F --> G[餐饮专项 retrieve_travel_guide<br/>category=restaurant top_k=5]")
    lines.append("    G --> H[向量召回 10 条 → 去重重排 → 5 条]")
    lines.append("    H --> I[合并去重得到 13 条 RAG Contexts]")
    lines.append("    I --> J[提取 Fallback 候选实体 & 构建 Guard Index]")
    lines.append("    J --> K[trip_planner_agent.generate_planner_draft<br/>结构化 JSON 草稿]")
    lines.append("    K --> L[trip_service 名称校验 & 预算拆分]")
    lines.append("    L --> M[可选：高德地图 enrichment<br/>地址/坐标/路线]")
    lines.append("    M --> N[最终 Itinerary]")
    lines.append("```")
    lines.append("")

    # 1. 输入
    lines.append("## 1. 用户输入（TripRequest）")
    lines.append("")
    lines.append("```json")
    lines.append(_indent_json(request.model_dump(mode="json")))
    lines.append("```")
    lines.append("")
    lines.append(f"- 行程天数 day_count = `{day_count}`")
    lines.append(f"- 总预算下限 = ¥{request.total_budget_min:g}")
    lines.append(f"- 总预算上限 = ¥{request.total_budget_max:g}")
    lines.append("")

    # 2. 环境配置
    lines.append("## 2. 运行环境配置")
    lines.append("")
    lines.append("| 配置项 | 值 |")
    lines.append("|--------|-----|")
    lines.append(f"| LLM_PROVIDER | `{LLM_PROVIDER}` |")
    lines.append(f"| LLM_MODEL | `{LLM_MODEL}` |")
    lines.append(f"| LLM_BASE_URL | `{LLM_BASE_URL}` |")
    lines.append(f"| EMBEDDING_PROVIDER | `{EMBEDDING_PROVIDER}` |")
    lines.append(f"| EMBEDDING_MODEL | `{EMBEDDING_MODEL}` |")
    lines.append(f"| RERANK_MODEL | `{RERANK_MODEL}` |")
    lines.append(f"| RAG_TOP_K | `{RAG_TOP_K}` |")
    lines.append(f"| ENABLE_AMAP_ENRICHMENT | `{ENABLE_AMAP_ENRICHMENT}` |")
    lines.append(f"| AMAP_API_KEY | `{_mask_key(AMAP_API_KEY)}` |")
    lines.append("")

    # 3. LLM Query Rewrite
    queries_by_route = {
        str(record["route"]): str(record["query"])
        for record in RETRIEVAL_RECORDS
    }
    hotel_record = next(
        (record for record in RETRIEVAL_RECORDS if record["route"] == "住宿专项"),
        None,
    )
    rewrite_usage = (COLLECTED_USAGES or {}).get("rewrite", {})

    lines.append("## 3. LLM Query Rewrite")
    lines.append("")
    lines.append(f"- 主查询（景点）：`{queries_by_route.get('主查询（景点）', '<未记录>')}`")
    lines.append(f"- 住宿专项查询：`{queries_by_route.get('住宿专项', '<未记录>')}`")
    lines.append(f"- 餐饮专项查询：`{queries_by_route.get('餐饮专项', '<未记录>')}`")
    lines.append(
        f"- 住宿硬过滤 budget_tier：`{(hotel_record or {}).get('budget_tier') or '<无>'}`"
    )
    lines.append(f"- Query Rewrite token 消耗：`{rewrite_usage}`")
    lines.append("")

    # 4. 各路检索
    lines.append("## 4. 分路检索详情")
    lines.append("")
    lines.append("通用公式：`candidate_k = max(top_k * 2, 6)`，向量召回后再经 Cross-encoder 重排截回 `top_k` 条。")
    lines.append("")

    for rec in RETRIEVAL_RECORDS:
        lines.append(f"### 4.{RETRIEVAL_RECORDS.index(rec) + 1} {rec['route']}")
        lines.append("")
        lines.append(f"- Query：`{rec['query']}`")
        lines.append(f"- top_k：`{rec['top_k']}`")
        lines.append(f"- candidate_k（向量召回数）：`{rec['candidate_k']}`")
        lines.append(f"- 实体去重后进入重排数：`{rec['unique_chunks_after_dedup']}`")
        lines.append(f"- Rerank token：`{rec['rerank_usage']}`")
        lines.append(f"- Embedding token：`{rec['embedding_usage']}`")
        lines.append("")
        lines.append(_chunk_table(rec["chunks"]))
        lines.append("")

    # 5. 合并后的 RAG Contexts
    rag_contexts = COLLECTED_CONTEXTS or []
    usages = COLLECTED_USAGES or {}

    lines.append("## 5. 合并后的 RAG Contexts")
    lines.append("")
    lines.append(f"- 最终合并去重后 chunk 数：`{len(rag_contexts)}`")
    lines.append(f"- Query Rewrite token：`{usages.get('rewrite', {})}`")
    lines.append(f"- 累计 Rerank token：`{usages.get('rerank', {})}`")
    lines.append(f"- 累计 Embedding token：`{usages.get('embedding', {})}`")
    lines.append("")
    for idx, ctx in enumerate(rag_contexts, start=1):
        lines.append(f"### 5.{idx} Context {idx}")
        lines.append("")
        lines.append("```")
        lines.append(ctx)
        lines.append("```")
        lines.append("")

    # 6. 候选提取
    fallback = extract_fallback_candidates(rag_contexts)
    hotel_candidates = extract_hotel_candidates(rag_contexts)
    restaurant_candidates = extract_restaurant_candidates(rag_contexts)
    guard_index = build_guard_index(rag_contexts, fallback)

    lines.append("## 6. 候选实体提取（Fallback & Guard Index）")
    lines.append("")
    lines.append("### 6.1 景点候选")
    lines.append("")
    for idx, name in enumerate(fallback["spots"], start=1):
        lines.append(f"{idx}. {name}")
    lines.append("")
    lines.append("### 6.2 餐饮候选")
    lines.append("")
    for idx, c in enumerate(restaurant_candidates, start=1):
        lines.append(f"{idx}. {c['name']}（人均：{c['per_person_budget']}，推荐：{c['recommended_dishes']}）")
    lines.append("")
    lines.append("### 6.3 住宿候选")
    lines.append("")
    for idx, c in enumerate(hotel_candidates, start=1):
        lines.append(
            f"{idx}. {c['name']}（档次：{c['level']}，参考价：{c['reference_price']}，区域：{c['location']}）"
        )
    lines.append("")

    # 7. Planner Draft
    lines.append("## 7. Planner 生成的结构化草稿")
    lines.append("")
    draft_raw = PLANNER_RECORD.get("draft_raw")
    if draft_raw:
        lines.append("```json")
        lines.append(_indent_json(_mask_dict(draft_raw)))
        lines.append("```")
    else:
        lines.append("_Planner 未返回有效草稿，已回退到规则填充。_")
    lines.append("")
    lines.append(f"- Planner token 消耗：`{PLANNER_RECORD.get('token_usage', {})}`")
    lines.append(f"- 传入 Prompt 的酒店候选：`{PLANNER_RECORD.get('hotel_candidates_for_prompt', [])}`")
    lines.append(f"- 传入 Prompt 的餐厅候选：`{PLANNER_RECORD.get('restaurant_candidates_for_prompt', [])}`")
    lines.append("")

    # 7.1 名称校验
    if draft_raw:
        lines.append("### 7.1 草稿名称在 RAG 上下文中的校验结果")
        lines.append("")
        lines.append("| 天 | 景点名 | 校验 | 餐厅名 | 校验 |")
        lines.append("|---|--------|------|--------|------|")
        for day in draft_raw.get("days", []):
            spot = day.get("spot_name", "")
            meal = day.get("meal_name", "")
            spot_ok = verify_name(spot, guard_index, kind=KIND_SPOTS)
            meal_ok = verify_name(meal, guard_index, kind=KIND_MEALS)
            lines.append(
                f"| Day {day.get('day_index')} | {spot} | {'通过' if spot_ok else '未通过'} | "
                f"{meal} | {'通过' if meal_ok else '未通过'} |"
            )
        lines.append("")

    # 8. 最终 Itinerary
    lines.append("## 8. 最终行程（经 trip_service 组装、校验、预算拆分、地图增强）")
    lines.append("")
    if ITINERARY_RECORD:
        lines.append(f"- trip_id：`{ITINERARY_RECORD.get('trip_id')}`")
        lines.append(f"- 预估总预算：`¥{ITINERARY_RECORD.get('estimated_budget')}`")
        lines.append(f"- 预算拆分：`{ITINERARY_RECORD.get('budget_breakdown')}`")
        lines.append("")
        lines.append("### 8.1 整体概述")
        lines.append("")
        lines.append(ITINERARY_RECORD.get("summary", ""))
        lines.append("")
        lines.append("### 8.2 旅行提示")
        lines.append("")
        for tip in ITINERARY_RECORD.get("tips", []):
            lines.append(f"- {tip}")
        lines.append("")
        lines.append("### 8.3 每日行程")
        lines.append("")
        for day in ITINERARY_RECORD.get("days", []):
            lines.append(f"#### Day {day.get('day_index')} · {day.get('theme')} · {day.get('date')}")
            lines.append("")
            lines.append("**景点**")
            lines.append("")
            for spot in day.get("spots", []):
                lines.append(
                    f"- {spot.get('name')}（{spot.get('start_time', '-')} ~ {spot.get('end_time', '-')}）"
                    f"，预估 ¥{spot.get('estimated_cost')}，地址：{spot.get('address') or '未 enrichment'}"
                )
            lines.append("")
            lines.append("**餐饮**")
            lines.append("")
            for meal in day.get("meals", []):
                lines.append(
                    f"- {meal.get('name')}（{meal.get('meal_type')}），预估 ¥{meal.get('estimated_cost')}"
                )
            lines.append("")
            lines.append("**住宿**")
            lines.append("")
            hotel = day.get("hotel")
            if hotel:
                lines.append(
                    f"- {hotel.get('name')}（{hotel.get('level')}），预估 ¥{hotel.get('estimated_cost')}"
                )
            else:
                lines.append("- 无")
            lines.append("")
            lines.append("**交通**")
            lines.append("")
            for t in day.get("transport", []):
                lines.append(
                    f"- {t.get('mode')}：{t.get('from_place')} → {t.get('to_place')}，"
                    f"预估 ¥{t.get('estimated_cost')}，{t.get('duration') or '无耗时'}，"
                    f"{t.get('distance_km')} km"
                )
            lines.append("")
            lines.append("**备注**")
            lines.append("")
            for note in day.get("notes", []):
                lines.append(f"- {note}")
            lines.append("")

        lines.append("### 8.4 Token 消耗汇总")
        lines.append("")
        lines.append("```json")
        lines.append(_indent_json(_mask_dict(ITINERARY_RECORD.get("token_usage", {}))))
        lines.append("```")
        lines.append("")
        lines.append("### 8.5 Source Notes（内部来源说明）")
        lines.append("")
        for note in ITINERARY_RECORD.get("source_notes", []):
            lines.append(f"- {note}")
        lines.append("")

    lines.append("## 9. 关键观察")
    lines.append("")
    lines.append("- **非确定性**：Planner 由 LLM 生成，每次运行草稿可能不同；名称校验失败的条目会被 `trip_service` 替换为 RAG 上下文中的真实候选。")
    lines.append("- **Embedding / Rerank token 为 0**：当前 Ollama Embedding 与 OpenRouter Rerank 未在返回体中按 LangChain 标准上报 `token_usage`，因此统计为 0；实际发生了向量召回与 Cross-encoder 重排调用。")
    lines.append("- **餐饮 top_k**：本次运行餐饮专项与主查询一致，均为 `5`（即向量召回 `max(5×2, 6)=10` 后重排回 5）。")
    lines.append("- **名称校验**：最终行程中的景点 / 餐饮名称全部经过 `name_guard.verify_name` 与 RAG 上下文核验，未通过者已替换为 fallback 候选。")
    lines.append("")
    lines.append("---")
    lines.append("*报告由 `scripts/trace_trip_planning_flow.py` 自动生成*")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    request = build_request_from_image()
    day_count = (request.end_date - request.start_date).days + 1
    day_count = max(day_count, 1)

    print("=" * 60)
    print("开始执行厦门 3 日行程规划全链路 Trace")
    print("=" * 60)
    print(f"目的地：{request.destination}")
    print(f"日期：{request.start_date} ~ {request.end_date}（{day_count} 天）")
    print(f"人数：{request.travelers}")
    print(f"人均预算：{request.budget_min_per_person} ~ {request.budget_max_per_person}")
    print(f"偏好：{'、'.join(request.preferences)}")
    print(f"节奏：{request.pace}")
    print(f"饮食偏好：{'、'.join(request.dietary_preferences)}")
    print(f"酒店档次：{request.hotel_level}")
    print(f"备注：{request.special_notes}")
    print()

    itinerary = traced_generate_trip_itinerary(request)

    print()
    print("=" * 60)
    print("生成 Markdown 报告...")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = _build_report(request, day_count)
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"报告已保存：{REPORT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
