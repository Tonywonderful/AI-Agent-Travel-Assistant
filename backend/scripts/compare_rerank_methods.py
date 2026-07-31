from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agents.tools.rag_tool import build_destination_query
from app.config import CHROMA_COLLECTION_NAME, EMBEDDING_MODEL, RERANK_MODEL
from app.rag.retriever import _rerank_with_openrouter, _score_chunk_for_rerank
from app.rag.vector_db import search_guide_chunks_with_usage


DEFAULT_CASES_PATH = BACKEND_DIR / "eval" / "rag_eval_cases.json"
DEFAULT_OUTPUT_PATH = PROJECT_DIR / "outputs" / "rerank_comparison_results.json"


def _load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("Evaluation cases must be a non-empty JSON list.")
    return data


def _judge(case: dict[str, Any], chunks: list[dict[str, Any]]) -> dict[str, Any]:
    titles = [str(chunk.get("title", "")) for chunk in chunks]
    keywords = [str(value) for value in case.get("expected_title_keywords", [])]
    first_rank = next(
        (
            rank
            for rank, title in enumerate(titles, start=1)
            if any(keyword in title for keyword in keywords)
        ),
        None,
    )
    return {
        "top1_hit": first_rank == 1,
        "topk_hit": first_rank is not None,
        "rank": first_rank,
        "reciprocal_rank": 0.0 if first_rank is None else 1.0 / first_rank,
        "titles": titles,
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    top1_hits = sum(1 for row in rows if row["top1_hit"])
    topk_hits = sum(1 for row in rows if row["topk_hit"])
    return {
        "cases": total,
        "top1_hits": top1_hits,
        "top1_rate": top1_hits / total,
        "topk_hits": topk_hits,
        "topk_rate": topk_hits / total,
        "mrr": sum(float(row["reciprocal_rank"]) for row in rows) / total,
    }


def _rule_rerank(
    query: str,
    candidates: list[dict[str, Any]],
    top_k: int,
    destination: str,
) -> list[dict[str, Any]]:
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for index, candidate in enumerate(candidates):
        enriched = dict(candidate)
        score = _score_chunk_for_rerank(query, enriched, destination=destination)
        enriched["rerank_score"] = score
        scored.append((score, -index, enriched))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [chunk for _, _, chunk in scored[:top_k]]


def run(cases_path: Path, output_path: Path) -> dict[str, Any]:
    cases = _load_cases(cases_path)
    model_rows: list[dict[str, Any]] = []
    rule_rows: list[dict[str, Any]] = []
    model_failures: list[str] = []
    retrieval_latencies: list[float] = []
    model_latencies: list[float] = []
    rule_latencies: list[float] = []

    for index, case in enumerate(cases, start=1):
        case_id = str(case.get("id", f"case_{index}"))
        top_k = int(case.get("top_k", 5))
        destination = str(case["destination"])
        candidate_k = max(top_k * 2, 6)
        query, _ = build_destination_query(
            destination=destination,
            preferences=list(case.get("preferences", [])),
            pace=case.get("pace"),
            special_notes=case.get("special_notes"),
        )

        started = time.perf_counter()
        candidates, _ = search_guide_chunks_with_usage(
            query=query,
            top_k=candidate_k,
            destination=destination,
        )
        retrieval_latencies.append((time.perf_counter() - started) * 1000)

        started = time.perf_counter()
        model_scores, _ = _rerank_with_openrouter(query, candidates, top_k)
        model_latencies.append((time.perf_counter() - started) * 1000)
        if model_scores:
            model_chunks = [
                dict(candidates[candidate_index])
                for _, candidate_index in model_scores
                if 0 <= candidate_index < len(candidates)
            ][:top_k]
        else:
            model_chunks = []
            model_failures.append(case_id)

        started = time.perf_counter()
        rule_chunks = _rule_rerank(query, candidates, top_k, destination)
        rule_latencies.append((time.perf_counter() - started) * 1000)

        model_result = _judge(case, model_chunks)
        rule_result = _judge(case, rule_chunks)
        shared = {
            "id": case_id,
            "destination": destination,
            "candidate_count": len(candidates),
            "candidate_titles": [str(chunk.get("title", "")) for chunk in candidates],
        }
        model_rows.append({**shared, **model_result})
        rule_rows.append({**shared, **rule_result})
        print(
            f"[{index}/{len(cases)}] {case_id}: "
            f"model_rank={model_result['rank']} rule_rank={rule_result['rank']}",
            flush=True,
        )

    result = {
        "methodology": {
            "cases_path": str(cases_path),
            "embedding_model": EMBEDDING_MODEL,
            "collection": CHROMA_COLLECTION_NAME,
            "rerank_model": RERANK_MODEL,
            "candidate_k": "max(top_k * 2, 6)",
            "top_k": sorted({int(case.get("top_k", 5)) for case in cases}),
            "shared_candidates": True,
            "relevance_rule": "首个标题包含任一期望标题关键词即命中",
        },
        "model_rerank": _aggregate(model_rows),
        "rule_rerank": _aggregate(rule_rows),
        "model_failures": model_failures,
        "latency_ms": {
            "avg_vector_retrieval": sum(retrieval_latencies) / len(retrieval_latencies),
            "avg_model_rerank": sum(model_latencies) / len(model_latencies),
            "avg_rule_rerank": sum(rule_latencies) / len(rule_latencies),
        },
        "cases": {
            "model_rerank": model_rows,
            "rule_rerank": rule_rows,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare model rerank and rule rerank on the same vector candidates."
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run(args.cases, args.output)
    print("=== Comparison Summary ===")
    for label in ("model_rerank", "rule_rerank"):
        metrics = result[label]
        print(
            f"{label}: top1={metrics['top1_hits']}/{metrics['cases']} "
            f"({metrics['top1_rate']:.1%}), "
            f"topk={metrics['topk_hits']}/{metrics['cases']} "
            f"({metrics['topk_rate']:.1%}), MRR={metrics['mrr']:.3f}"
        )
    print(f"model_failures: {len(result['model_failures'])}")
    print(f"output: {args.output}")
    return 0 if not result["model_failures"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
