import logging

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MAX_RETRIES,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_TIMEOUT_SECONDS,
    OPENCODE_API_KEY,
    OPENCODE_BASE_URL,
    RAG_TOP_K,
)
from app.llm import build_chat_llm
from app.rag.retriever import retrieve_travel_guide
from app.rag.vector_db import RETRIEVAL_SCOPE_PLANNING


logger = logging.getLogger(__name__)
_HOTEL_TIER_BY_LEVEL = {
    "经济型": "经济型（200 元/晚以下）",
    "舒适型": "舒适型（200-500 元/晚）",
    "豪华型": "豪华型（500 元/晚以上）",
}


class PlanningQueries(BaseModel):
    """LLM 为三类规划检索生成的独立 Query。"""

    model_config = ConfigDict(extra="forbid")

    attraction: str = Field(..., min_length=1)
    hotel: str = Field(..., min_length=1)
    restaurant: str = Field(..., min_length=1)


def _normalize_hotel_tier(hotel_level: str | None) -> str | None:
    normalized = (hotel_level or "").strip()
    for level, budget_tier in _HOTEL_TIER_BY_LEVEL.items():
        if normalized.startswith(level):
            return budget_tier
    if "高端" in normalized or "高档" in normalized:
        return _HOTEL_TIER_BY_LEVEL["豪华型"]
    return None


def _build_query_llm():
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


def _extract_response_text(response) -> str:
    raw_text = getattr(response, "content", "")
    if isinstance(raw_text, list):
        raw_text = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in raw_text
        )
    return str(raw_text or "").strip()


def _extract_token_usage(response) -> dict[str, int]:
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    metadata = getattr(response, "response_metadata", None) or {}
    token_usage = metadata.get("token_usage", {})
    usage_metadata = getattr(response, "usage_metadata", None) or {}
    usage["prompt_tokens"] = int(
        token_usage.get("prompt_tokens", usage_metadata.get("input_tokens", 0)) or 0
    )
    usage["completion_tokens"] = int(
        token_usage.get("completion_tokens", usage_metadata.get("output_tokens", 0)) or 0
    )
    return usage


def _extract_json_object(raw_text: str) -> str:
    text = raw_text.strip()
    start_index = text.find("{")
    end_index = text.rfind("}")
    if start_index == -1 or end_index <= start_index:
        raise RuntimeError("LLM Query Rewrite returned invalid JSON")
    return text[start_index : end_index + 1]


def rewrite_planning_queries(
    destination: str,
    preferences: list[str] | None = None,
    pace: str | None = None,
    special_notes: str | None = None,
    dietary_preferences: list[str] | None = None,
    hotel_level: str | None = None,
    budget_min_per_person: float | None = None,
    budget_max_per_person: float | None = None,
    day_count: int = 1,
) -> tuple[PlanningQueries, dict[str, int]]:
    """必须由 LLM 生成规划侧三路 Query；失败时中断检索。"""
    llm = _build_query_llm()
    if llm is None:
        raise RuntimeError("LLM Query Rewrite is required but unavailable")

    system_prompt = (
        "你是旅行规划 RAG 的 Query Rewrite 模型。"
        "根据用户的完整条件生成景点、住宿、餐饮三条相互独立的向量检索 Query。"
        "只输出 JSON 对象，字段必须且只能为 attraction、hotel、restaurant。"
        "每个字段值必须是空格分隔的中文关键词，必须包含目的地。"
        "景点 Query 只表达景点、活动、节奏和用户明确提出的游玩诉求；"
        "住宿 Query 只表达住宿档次、预算和住宿诉求；"
        "餐饮 Query 只表达饮食偏好、预算和餐饮诉求。"
        "不要输出解释、Markdown 或代码块，不要虚构用户未提及的具体实体。"
    )
    human_prompt = (
        f"目的地：{destination}\n"
        f"行程天数：{day_count}\n"
        f"旅行偏好：{'、'.join(preferences or []) or '无'}\n"
        f"节奏：{pace or '无'}\n"
        f"饮食偏好：{'、'.join(dietary_preferences or []) or '无'}\n"
        f"酒店档次：{hotel_level or '无'}\n"
        f"人均预算：{budget_min_per_person if budget_min_per_person is not None else '无'}-"
        f"{budget_max_per_person if budget_max_per_person is not None else '无'} 元\n"
        f"额外备注：{special_notes or '无'}"
    )

    try:
        response = llm.invoke([("system", system_prompt), ("human", human_prompt)])
    except Exception as exc:
        raise RuntimeError("LLM Query Rewrite failed") from exc

    try:
        raw_text = _extract_response_text(response)
        queries = PlanningQueries.model_validate_json(_extract_json_object(raw_text))
    except RuntimeError:
        raise
    except (ValidationError, ValueError, TypeError) as exc:
        raise RuntimeError("LLM Query Rewrite returned invalid output") from exc

    normalized = PlanningQueries(
        **{
            field: " ".join(getattr(queries, field).split())
            for field in ("attraction", "hotel", "restaurant")
        }
    )
    missing_destination = [
        field
        for field in ("attraction", "hotel", "restaurant")
        if destination not in getattr(normalized, field)
    ]
    if missing_destination:
        raise RuntimeError(
            "LLM Query Rewrite omitted destination in: " + ", ".join(missing_destination)
        )

    logger.info("LLM planning query rewrite: %s -> %s", human_prompt, normalized.model_dump())
    return normalized, _extract_token_usage(response)


def build_destination_query(
    destination: str,
    preferences: list[str] | None = None,
    pace: str | None = None,
    special_notes: str | None = None,
) -> tuple[str, dict[str, int]]:
    """通过 LLM 改写景点 Query，供单路调试调用。"""
    queries, usage = rewrite_planning_queries(
        destination=destination,
        preferences=preferences,
        pace=pace,
        special_notes=special_notes,
    )
    return queries.attraction, usage


def get_destination_guide_context(
    destination: str,
    preferences: list[str] | None = None,
    pace: str | None = None,
    special_notes: str | None = None,
    top_k: int = RAG_TOP_K,
    dietary_preferences: list[str] | None = None,
    hotel_level: str | None = None,
    budget_min_per_person: float | None = None,
    budget_max_per_person: float | None = None,
    day_count: int = 1,
) -> tuple[list[str], dict[str, int], dict[str, int], dict[str, int]]:
    """根据目的地和偏好返回本地攻略片段。"""
    queries, rewrite_usage = rewrite_planning_queries(
        destination=destination,
        preferences=preferences,
        pace=pace,
        special_notes=special_notes,
        dietary_preferences=dietary_preferences,
        hotel_level=hotel_level,
        budget_min_per_person=budget_min_per_person,
        budget_max_per_person=budget_max_per_person,
        day_count=day_count,
    )
    contexts, rerank_usage, embedding_usage = retrieve_travel_guide(
        query=queries.attraction,
        top_k=top_k,
        destination=destination,
        retrieval_scope=RETRIEVAL_SCOPE_PLANNING,
        categories=["attraction"],
    )

    hotel_tier = _normalize_hotel_tier(hotel_level)
    hotel_tier_filter = hotel_tier or ("__unsupported__" if hotel_level else None)
    supplement_routes = [
        {
            "query": queries.hotel,
            "top_k": 3,
            "categories": ["hotel"],
            "budget_tier": hotel_tier_filter,
        },
        {
            "query": queries.restaurant,
            "top_k": top_k,
            "categories": ["restaurant"],
            "budget_tier": None,
        },
    ]

    existing_set = set(contexts)
    for route in supplement_routes:
        extra_contexts, extra_rerank, extra_embed = retrieve_travel_guide(
            query=str(route["query"]),
            top_k=int(route["top_k"]),
            destination=destination,
            retrieval_scope=RETRIEVAL_SCOPE_PLANNING,
            categories=route["categories"],
            budget_tier=route["budget_tier"],
        )
        for ctx in extra_contexts:
            if ctx not in existing_set:
                contexts.append(ctx)
                existing_set.add(ctx)
        rerank_usage["prompt_tokens"] += extra_rerank.get("prompt_tokens", 0)
        rerank_usage["completion_tokens"] += extra_rerank.get("completion_tokens", 0)
        embedding_usage["prompt_tokens"] += extra_embed.get("prompt_tokens", 0)
        embedding_usage["completion_tokens"] += extra_embed.get("completion_tokens", 0)

    return contexts, rewrite_usage, rerank_usage, embedding_usage
