from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path
from typing import Any

import httpx
import uvicorn

BACKEND_DIR = Path(r"D:\develop\AI_tryProject\TravelPlanAssistant\backend")
OUTPUT_PATH = Path(r"D:\develop\AI_tryProject\TravelPlanAssistant\outputs\chengdu_user_flow_multiroute_trace_20260804.json")
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agents import trip_planner_agent
from app.agents.tools import rag_tool
from app.api.main import app
from app.rag import retriever, vector_db
from app.services import trip_service

trace: dict[str, Any] = {
    "trace_mode": {
        "entry": "real HTTP POST /trip/generate",
        "business_code_modified": False,
        "tests_or_test_scripts_used": False,
        "cache_policy": "diagnostic request forces cache misses so vector recall and cross-encoder rerank actually execute",
    },
    "request": {},
    "query_rewrite": {},
    "retrieval_routes": [],
    "fallback_candidates": {},
    "planner": {},
    "response": {},
}

# 仅在本次诊断进程中强制缓存未命中，确保能观察真实召回与重排阶段。
retriever.get_cached_json = lambda _key: None
retriever.set_cached_json = lambda *_args, **_kwargs: None

original_build_query = rag_tool.build_destination_query
original_search = retriever.search_guide_chunks_with_usage
original_rerank = retriever.rerank_guide_chunks
original_planner = trip_service.generate_planner_draft
original_extract_candidates = trip_service.extract_fallback_candidates

route_queue: list[dict[str, Any]] = []


def chunk_view(chunk: dict[str, Any], rank: int) -> dict[str, Any]:
    return {
        "rank": rank,
        "title": chunk.get("title", ""),
        "source": chunk.get("source", ""),
        "destination": chunk.get("destination", ""),
        "retrieval_scope": chunk.get("retrieval_scope", ""),
        "category": chunk.get("category", ""),
        "entity_name": chunk.get("entity_name", ""),
        "budget_tier": chunk.get("budget_tier", ""),
        "rerank_score": chunk.get("rerank_score"),
        "rerank_reasons": chunk.get("rerank_reasons", []),
        "text": chunk.get("text", ""),
    }


def traced_build_query(*args, **kwargs):
    query, usage = original_build_query(*args, **kwargs)
    trace["query_rewrite"] = {
        "input": {
            "destination": kwargs.get("destination", args[0] if args else None),
            "preferences": kwargs.get("preferences"),
            "pace": kwargs.get("pace"),
            "special_notes": kwargs.get("special_notes"),
        },
        "output_query": query,
        "usage": usage,
        "source": "llm" if usage.get("prompt_tokens", 0) or usage.get("completion_tokens", 0) else "rule_or_usage_unreported",
    }
    return query, usage


def mirrored_vector_scores(query: str, top_k: int, destination: str | None, retrieval_scope: str | None):
    try:
        collection = vector_db._get_chroma_collection()
        embedding, _usage = vector_db._embed_query_with_usage(query)
        if collection is None or embedding is None:
            return []
        query_args: dict[str, Any] = {
            "query_embeddings": [embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        where = vector_db._build_chroma_where(destination, retrieval_scope)
        if where:
            query_args["where"] = where
        result = collection.query(**query_args)
        rows = []
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for rank, (document, metadata, distance) in enumerate(zip(documents, metadatas, distances), start=1):
            rows.append({
                "rank": rank,
                "title": (metadata or {}).get("title", ""),
                "category": (metadata or {}).get("category", ""),
                "entity_name": (metadata or {}).get("entity_name", ""),
                "retrieval_scope": (metadata or {}).get("retrieval_scope", ""),
                "cosine_distance": distance,
                "cosine_similarity": 1 - distance if isinstance(distance, (int, float)) else None,
                "text": document.split("\n", 1)[1] if "\n" in document else document,
            })
        return rows
    except Exception as exc:
        return [{"diagnostic_error": f"{type(exc).__name__}: {exc}"}]


def traced_search(*args, **kwargs):
    query = kwargs.get("query", args[0] if args else "")
    top_k = kwargs.get("top_k", 5)
    destination = kwargs.get("destination")
    retrieval_scope = kwargs.get("retrieval_scope")
    chunks, usage = original_search(*args, **kwargs)
    route = {
        "route_index": len(trace["retrieval_routes"]) + 1,
        "query": query,
        "candidate_k": top_k,
        "destination_filter": destination,
        "retrieval_scope_filter": retrieval_scope,
        "embedding_usage": usage,
        "vector_candidates": [chunk_view(chunk, rank) for rank, chunk in enumerate(chunks, start=1)],
        "vector_scores_mirrored_with_same_query_filter_and_n": mirrored_vector_scores(
            query, top_k, destination, retrieval_scope
        ),
        "reranked_top": [],
    }
    trace["retrieval_routes"].append(route)
    route_queue.append(route)
    return chunks, usage


def traced_rerank(*args, **kwargs):
    chunks, usage = original_rerank(*args, **kwargs)
    if route_queue:
        route = route_queue.pop(0)
        route["requested_top_k"] = kwargs.get("top_k", args[2] if len(args) > 2 else None)
        route["rerank_usage"] = usage
        route["reranked_top"] = [chunk_view(chunk, rank) for rank, chunk in enumerate(chunks, start=1)]
        reasons = [reason for chunk in chunks for reason in chunk.get("rerank_reasons", [])]
        route["rerank_mode"] = "cross_encoder" if any(str(reason).startswith("cross-encoder:") for reason in reasons) else "rule_fallback"
    return chunks, usage


def traced_extract_candidates(contexts):
    result = original_extract_candidates(contexts)
    trace["fallback_candidates"] = result
    return result


def traced_planner(request, rag_contexts, day_count):
    draft, usage = original_planner(request, rag_contexts, day_count)
    trace["planner"] = {
        "model": trip_planner_agent.LLM_MODEL,
        "provider": trip_planner_agent.LLM_PROVIDER,
        "day_count": day_count,
        "rag_context_count": len(rag_contexts),
        "rag_contexts": rag_contexts,
        "usage": usage,
        "draft": draft.model_dump(mode="json") if draft is not None else None,
        "status": "structured_draft_ok" if draft is not None else "failed_or_invalid_then_service_fallback",
    }
    return draft, usage


rag_tool.build_destination_query = traced_build_query
retriever.search_guide_chunks_with_usage = traced_search
retriever.rerank_guide_chunks = traced_rerank
trip_service.extract_fallback_candidates = traced_extract_candidates
trip_service.generate_planner_draft = traced_planner

payload = {
    "destination": "成都",
    "start_date": "2026-08-11",
    "end_date": "2026-08-15",
    "travelers": 2,
    "budget": 8000,
    "preferences": ["自然风景", "城市漫游", "美食探索"],
    "pace": "轻松",
    "dietary_preferences": ["本地特色", "海鲜"],
    "hotel_level": "舒适型",
    "special_notes": "希望体验当地文化，安排一次温泉体验，偏好地铁出行，减少换乘。",
}
trace["request"] = payload

config = uvicorn.Config(app, host="127.0.0.1", port=8011, log_level="info")
server = uvicorn.Server(config)
thread = threading.Thread(target=server.run, daemon=True)
thread.start()

for _ in range(100):
    try:
        if httpx.get("http://127.0.0.1:8011/health", timeout=1).status_code == 200:
            break
    except Exception:
        time.sleep(0.1)
else:
    raise RuntimeError("diagnostic uvicorn failed to start")

try:
    with httpx.Client(timeout=6000) as client:
        response = client.post("http://127.0.0.1:8011/trip/generate", json=payload)
    trace["response"] = {
        "status_code": response.status_code,
        "json": response.json() if response.headers.get("content-type", "").startswith("application/json") else None,
        "text_preview": response.text[:1000],
    }
finally:
    server.should_exit = True
    thread.join(timeout=10)

OUTPUT_PATH.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
print(str(OUTPUT_PATH))
print(json.dumps({
    "status_code": trace["response"].get("status_code"),
    "rewrite": trace["query_rewrite"].get("output_query"),
    "routes": len(trace["retrieval_routes"]),
    "rerank_modes": [route.get("rerank_mode") for route in trace["retrieval_routes"]],
    "planner_status": trace["planner"].get("status"),
    "fallback_candidates": trace["fallback_candidates"],
}, ensure_ascii=False, indent=2))
