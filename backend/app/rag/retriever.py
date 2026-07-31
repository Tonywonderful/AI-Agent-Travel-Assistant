import hashlib
import json
import logging
import re

import httpx

from app.config import (
    RAG_TOP_K,
    REDIS_RAG_TTL_SECONDS,
    REDIS_RERANK_TTL_SECONDS,
    RERANK_API_KEY,
    RERANK_API_URL,
    RERANK_APP_TITLE,
    RERANK_HTTP_REFERER,
    RERANK_MODEL,
    RERANK_TIMEOUT_SECONDS,
)
from app.rag.vector_db import search_guide_chunks_with_usage
from app.services.cache_service import get_cached_json, set_cached_json


logger = logging.getLogger(__name__)


def _normalize_cache_text(value: str) -> str:
    """把检索 query 做简单标准化，避免大小写和空格造成重复 key。"""
    return " ".join(value.strip().lower().split())


def _extract_query_keywords(query: str) -> list[str]:
    """从 query 中切出用于轻量重排序的关键词。"""
    raw_parts = re.split(r"[\s,，。；;、]+", query)
    return [part.strip() for part in raw_parts if part.strip()]


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _score_chunk_for_rerank(
    query: str,
    chunk: dict[str, str],
    destination: str | None = None,
) -> int:
    """根据 query 关键词对召回片段做轻量打分。"""
    title = chunk.get("title", "")
    text = chunk.get("text", "")
    source = chunk.get("source", "")
    combined_text = f"{title}\n{text}"
    reasons: list[str] = []

    score = 0
    for keyword in _extract_query_keywords(query):
        if keyword in title:
            score += 3
            reasons.append(f"title+3:{keyword}")
        if keyword in text:
            score += 1
            reasons.append(f"text+1:{keyword}")

    # 文档开头通常是低信息量噪声片段。
    if title == "文档开头":
        score -= 8
        reasons.append("noise-8:文档开头")

    # 行程类片段更适合承接"景点 / 行程 / 推荐"类请求。
    if "行程" in title and "行程参考" not in title:
        score += 4
        reasons.append("domain+4:行程标题")

    # "经典行程参考"类片段内容过于全面，会霸占 Top1，对非行程查询做降权。
    if "行程参考" in title:
        score -= 4
        reasons.append("domain-4:行程参考降权")

    # "目的地简介"内容过于泛化，对具体查询（美食、亲子等）不是最优候选。
    if "目的地简介" in title:
        score -= 2
        reasons.append("domain-2:目的地简介降权")

    # 餐饮/预算类片段在"日落/拍照/轻松"这类主目标下通常不是最优候选。
    if _contains_any(title, ["餐饮", "预算"]) and not _contains_any(
        combined_text,
        ["日落", "傍晚", "拍照", "摄影", "出片", "洱海", "双廊", "慢节奏"],
    ):
        score -= 3
        reasons.append("domain-3:餐饮预算弱相关")

    # 目的地不匹配降权：优先使用 Chunk 元数据，兼容旧 Chunk 时才退回文本判断。
    if destination:
        chunk_destination = chunk.get("destination", "")
        if chunk_destination and chunk_destination != destination:
            score -= 5
            reasons.append(f"dest-5:metadata={chunk_destination}")
        elif not chunk_destination:
            chunk_lower = f"{source} {title} {text}".lower()
            if destination.lower() not in chunk_lower:
                score -= 5
                reasons.append(f"dest-5:缺失元数据且非{destination}片段")

    chunk["rerank_reasons"] = reasons
    return score


_NOISE_TITLES = {"文档开头"}


def _extract_rerank_token_usage(response_data: dict) -> tuple[dict[str, int], bool]:
    """只读取接口返回的官方 usage；没有 usage 时不做本地估算。"""
    usage = response_data.get("usage") or response_data.get("output", {}).get("usage") or {}
    prompt_tokens = (
        usage.get("prompt_tokens")
        or usage.get("input_tokens")
        or usage.get("input_token_count")
        or 0
    )
    completion_tokens = (
        usage.get("completion_tokens")
        or usage.get("output_tokens")
        or usage.get("output_token_count")
        or 0
    )
    total_tokens = usage.get("total_tokens") or usage.get("total_token_count") or 0

    if not prompt_tokens and not completion_tokens and total_tokens:
        prompt_tokens = total_tokens

    if prompt_tokens or completion_tokens:
        return {
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
        }, True

    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
    }, False


def _build_openrouter_headers() -> dict[str, str]:
    """构造 OpenRouter Rerank 请求头；站点信息为可选配置。"""
    headers = {
        "Authorization": f"Bearer {RERANK_API_KEY}",
        "Content-Type": "application/json",
    }
    if RERANK_HTTP_REFERER:
        headers["HTTP-Referer"] = RERANK_HTTP_REFERER
    if RERANK_APP_TITLE:
        headers["X-OpenRouter-Title"] = RERANK_APP_TITLE
    return headers


def _rerank_with_openrouter(
    query: str,
    chunks: list[dict[str, str]],
    top_k: int,
) -> tuple[list[tuple[float, int]] | None, dict[str, int]]:
    """调用 OpenRouter Rerank API 做语义重排序。返回 (scored, token_usage)。"""
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    if not RERANK_API_KEY or not RERANK_API_URL or not RERANK_MODEL or not chunks:
        logger.info("skip OpenRouter rerank: incomplete config or empty chunks")
        return None, empty_usage

    # 过滤已知噪声片段，避免浪费 rerank 名额。
    filtered = [
        (i, chunk) for i, chunk in enumerate(chunks)
        if chunk.get("title", "") not in _NOISE_TITLES
    ]
    if not filtered:
        logger.info("skip OpenRouter rerank: all chunks are noise")
        return None, empty_usage

    original_indices = [i for i, _ in filtered]
    clean_chunks = [chunk for _, chunk in filtered]
    documents = [
        {"text": f"{chunk.get('title', '')}\n{chunk.get('text', '')}"}
        for chunk in clean_chunks
    ]
    payload = {
        "model": RERANK_MODEL,
        "query": query,
        "documents": documents,
        "top_n": min(top_k, len(documents)),
    }

    try:
        logger.info(
            "calling OpenRouter rerank: model=%s candidates=%d top_k=%d",
            RERANK_MODEL,
            len(clean_chunks),
            top_k,
        )
        with httpx.Client(timeout=RERANK_TIMEOUT_SECONDS) as client:
            response = client.post(
                RERANK_API_URL,
                json=payload,
                headers=_build_openrouter_headers(),
            )
            if not response.is_success:
                logger.warning(
                    "OpenRouter rerank HTTP %d: %s",
                    response.status_code,
                    response.text[:500],
                )
                return None, empty_usage
            data = response.json()

        # 只提取接口返回的官方 token usage；没有 usage 时保持 0，不做估算。
        token_usage, has_official_usage = _extract_rerank_token_usage(data)
        if has_official_usage:
            logger.info(
                "OpenRouter rerank token: prompt=%d, completion=%d",
                token_usage["prompt_tokens"],
                token_usage["completion_tokens"],
            )

        results = data.get("results", [])
        if not results:
            logger.warning(
                "OpenRouter rerank empty results: %s",
                json.dumps(data, ensure_ascii=False)[:500],
            )
            return None, token_usage

        scored: list[tuple[float, int]] = []
        for item in results:
            index = item.get("index")
            if not isinstance(index, int) or not 0 <= index < len(original_indices):
                continue
            scored.append(
                (float(item.get("relevance_score", 0)), original_indices[index])
            )

        scored.sort(key=lambda item: item[0], reverse=True)
        if not scored:
            logger.warning("OpenRouter rerank returned no valid result indices")
            return None, token_usage

        logger.info("OpenRouter rerank success: results=%d", len(scored))
        return scored, token_usage

    except (httpx.HTTPError, json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning(
            "OpenRouter rerank failed: %s; falling back to rule-based",
            exc,
        )
        return None, empty_usage


def _build_rerank_cache_key(query: str, chunks: list[dict[str, str]]) -> str:
    """根据模型、query 与 chunk 指纹生成 rerank 缓存 key。"""
    normalized_query = _normalize_cache_text(query)
    content_fingerprint = "|".join(
        f"{c.get('source', '')}:{c.get('title', '')}" for c in chunks
    )
    model_hash = hashlib.md5(RERANK_MODEL.encode()).hexdigest()[:8]
    chunks_hash = hashlib.md5(content_fingerprint.encode()).hexdigest()[:12]
    return f"rerank:{model_hash}:{normalized_query}:{chunks_hash}"


def rerank_guide_chunks(
    query: str,
    matched_chunks: list[dict[str, str]],
    top_k: int,
    destination: str | None = None,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """对召回候选做重排序，优先 Cross-encoder，fallback 规则级。返回 (chunks, rerank_token_usage)。"""
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}

    # 尝试从缓存读取 rerank 结果
    cache_key = _build_rerank_cache_key(query, matched_chunks)
    cached = get_cached_json(cache_key)
    if cached is not None:
        logger.info("rerank cache hit: query=%s", query)
        reranked: list[dict[str, str]] = []
        for item in cached:
            idx = item["i"]
            if 0 <= idx < len(matched_chunks):
                enriched = dict(matched_chunks[idx])
                enriched["rerank_score"] = item["s"]
                enriched["rerank_reasons"] = [f"cross-encoder:{item['s']:.4f}"]
                reranked.append(enriched)
        return reranked[:top_k], empty_usage
    logger.info("rerank cache miss: query=%s", query)

    # 优先尝试 OpenRouter Cross-encoder Rerank。
    openrouter_results, rerank_token_usage = _rerank_with_openrouter(
        query,
        matched_chunks,
        top_k,
    )
    if openrouter_results:
        # 写入缓存：只存索引和分数，不重复存文本。
        cache_value = [
            {"i": idx, "s": round(score, 4)}
            for score, idx in openrouter_results
        ]
        set_cached_json(cache_key, cache_value, expire_seconds=REDIS_RERANK_TTL_SECONDS)

        reranked = []
        for score, original_index in openrouter_results:
            if 0 <= original_index < len(matched_chunks):
                enriched_chunk = dict(matched_chunks[original_index])
                enriched_chunk["rerank_score"] = round(score, 4)
                enriched_chunk["rerank_reasons"] = [f"cross-encoder:{score:.4f}"]
                reranked.append(enriched_chunk)
        return reranked[:top_k], rerank_token_usage

    # fallback 到规则级 Rerank。
    logger.info("OpenRouter rerank unavailable; using rule-based rerank")
    scored_chunks: list[tuple[int, int, dict[str, str]]] = []
    for index, chunk in enumerate(matched_chunks):
        enriched_chunk = dict(chunk)
        score = _score_chunk_for_rerank(query, enriched_chunk, destination=destination)
        enriched_chunk["rerank_score"] = score
        scored_chunks.append((score, -index, enriched_chunk))

    scored_chunks.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [chunk for _, _, chunk in scored_chunks[:top_k]], empty_usage


def retrieve_travel_guide_chunks(
    query: str, top_k: int = RAG_TOP_K, destination: str | None = None
) -> tuple[list[dict[str, str]], dict[str, int], dict[str, int]]:
    """返回带轻量 rerank 的原始攻略片段。返回 (chunks, rerank_usage, embedding_usage)。"""
    candidate_k = max(top_k * 2, 6)
    search_kwargs = {"query": query, "top_k": candidate_k}
    if destination:
        search_kwargs["destination"] = destination
    matched_chunks, embedding_usage = search_guide_chunks_with_usage(**search_kwargs)
    reranked_chunks, rerank_usage = rerank_guide_chunks(
        query=query, matched_chunks=matched_chunks, top_k=top_k, destination=destination
    )
    return reranked_chunks, rerank_usage, embedding_usage


def retrieve_travel_guide(
    query: str, top_k: int = RAG_TOP_K, destination: str | None = None
) -> tuple[list[str], dict[str, int], dict[str, int]]:
    """返回最相关的攻略片段。返回 (texts, rerank_usage, embedding_usage)。"""
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    cache_destination = destination or "all"
    model_hash = hashlib.md5(RERANK_MODEL.encode()).hexdigest()[:8]
    cache_key = (
        f"rag:guide:{model_hash}:{cache_destination}:"
        f"{_normalize_cache_text(query)}:{top_k}"
    )
    cached_value = get_cached_json(cache_key)
    if cached_value is not None:
        logger.info("rag cache hit: query=%s top_k=%s", query, top_k)
        return [str(item) for item in cached_value], empty_usage, empty_usage
    logger.info("rag cache miss: query=%s top_k=%s", query, top_k)

    matched_chunks, rerank_usage, embedding_usage = retrieve_travel_guide_chunks(
        query=query, top_k=top_k, destination=destination
    )

    results: list[str] = []
    for chunk in matched_chunks:
        results.append(
            f"[来源: {chunk['source']} | 标题: {chunk['title']}]\n{chunk['text']}"
        )

    set_cached_json(cache_key, results, expire_seconds=REDIS_RAG_TTL_SECONDS)
    return results, rerank_usage, embedding_usage
