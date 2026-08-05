from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import CHROMA_COLLECTION_NAME, EMBEDDING_MODEL, RERANK_MODEL
from app.rag.evaluation_metrics import (
    CANDIDATE_K,
    TOP_K,
    candidate_recall_at_20,
    ndcg_at_5,
    precision_at_5,
    validate_qrels,
)
from app.rag.retriever import _rerank_with_openrouter, _score_chunk_for_rerank
from app.rag.vector_db import (
    RETRIEVAL_SCOPE_PLANNING,
    _search_guide_chunks_by_chroma,
)


DEFAULT_CASES_PATH = BACKEND_DIR / "eval" / "rag_eval_cases.json"
DEFAULT_QRELS_PATH = BACKEND_DIR / "eval" / "rag_qrels.json"
DEFAULT_OUTPUT_PATH = PROJECT_DIR / "outputs" / "rerank_comparison_results.json"


def _load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("Evaluation cases must be a non-empty JSON list.")
    for case in data:
        if int(case.get("top_k", 0)) != TOP_K:
            raise ValueError(f"Case {case.get('id')} top_k must be {TOP_K}")
    return data


def _load_qrels(path: Path) -> dict[str, dict[str, int]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Evaluation qrels must be a JSON object.")
    return {
        str(case_id): {
            str(chunk_key): int(relevance)
            for chunk_key, relevance in judgments.items()
        }
        for case_id, judgments in data.items()
    }


def _chunk_key(chunk: dict[str, Any]) -> str:
    existing = str(chunk.get("chunk_key", ""))
    if existing:
        return existing
    document_id = str(chunk.get("document_id") or chunk.get("source", ""))
    return f"{document_id}::{chunk.get('title', '')}"


def _judge(
    chunks: list[dict[str, Any]],
    judgments: dict[str, int],
    relevance_threshold: int = 2,
) -> dict[str, Any]:
    chunk_keys = [_chunk_key(chunk) for chunk in chunks[:TOP_K]]
    return {
        "precision_at_5": precision_at_5(
            chunk_keys,
            judgments,
            relevance_threshold=relevance_threshold,
        ),
        "ndcg_at_5": ndcg_at_5(chunk_keys, judgments),
        "chunk_keys": chunk_keys,
        "titles": [str(chunk.get("title", "")) for chunk in chunks[:TOP_K]],
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, float]:
    if not rows:
        raise ValueError("Cannot aggregate an empty result set.")
    total = len(rows)
    return {
        "precision_at_5": (
            sum(float(row["precision_at_5"]) for row in rows) / total
        ),
        "ndcg_at_5": sum(float(row["ndcg_at_5"]) for row in rows) / total,
    }


def _rule_rerank(
    query: str,
    candidates: list[dict[str, Any]],
    destination: str,
) -> list[dict[str, Any]]:
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for index, candidate in enumerate(candidates):
        enriched = dict(candidate)
        score = _score_chunk_for_rerank(query, enriched, destination=destination)
        scored.append((score, -index, enriched))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [chunk for _, _, chunk in scored[:TOP_K]]


def _model_rerank(
    query: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    scores, _ = _rerank_with_openrouter(query, candidates, TOP_K)
    if not scores:
        raise RuntimeError("Model rerank failed; comparison stopped")
    return [
        dict(candidates[index])
        for _, index in scores
        if 0 <= index < len(candidates)
    ][:TOP_K]


def run(
    cases_path: Path,
    qrels_path: Path,
    output_path: Path,
    relevance_threshold: int = 2,
) -> dict[str, Any]:
    cases = _load_cases(cases_path)
    qrels = _load_qrels(qrels_path)
    validate_qrels(qrels, [str(case["id"]) for case in cases])

    model_rows: list[dict[str, Any]] = []
    rule_rows: list[dict[str, Any]] = []
    candidate_recall_rows: list[float] = []
    case_rows: list[dict[str, Any]] = []

    for index, case in enumerate(cases, start=1):
        case_id = str(case["id"])
        query = str(case["query"]).strip()
        destination = str(case["destination"])
        judgments = qrels[case_id]
        candidates, _ = _search_guide_chunks_by_chroma(
            query=query,
            top_k=CANDIDATE_K,
            destination=destination,
            retrieval_scope=RETRIEVAL_SCOPE_PLANNING,
        )
        if not candidates:
            raise RuntimeError(f"Vector retrieval returned no candidates for {case_id}")

        candidate_recall_rows.append(
            candidate_recall_at_20(
                [_chunk_key(chunk) for chunk in candidates],
                judgments,
                relevance_threshold=relevance_threshold,
            )
        )
        model_result = _judge(
            _model_rerank(query, candidates),
            judgments,
            relevance_threshold,
        )
        rule_result = _judge(
            _rule_rerank(query, candidates, destination),
            judgments,
            relevance_threshold,
        )
        model_rows.append(model_result)
        rule_rows.append(rule_result)
        case_rows.append(
            {
                "id": case_id,
                "query": query,
                "destination": destination,
                "model_rerank": model_result,
                "rule_rerank": rule_result,
            }
        )
        print(f"[{index}/{len(cases)}] {case_id}", flush=True)

    result = {
        "schema_version": 3,
        "methodology": {
            "cases_path": str(cases_path),
            "qrels_path": str(qrels_path),
            "fixed_queries": True,
            "embedding_model": EMBEDDING_MODEL,
            "collection": CHROMA_COLLECTION_NAME,
            "rerank_model": RERANK_MODEL,
            "candidate_k": CANDIDATE_K,
            "top_k": TOP_K,
            "relevance_threshold": relevance_threshold,
            "retrieval_scope": RETRIEVAL_SCOPE_PLANNING,
            "assistant_only_chunks_excluded": True,
            "no_keyword_fallback": True,
            "shared_candidates": True,
        },
        "candidate_recall_at_20": (
            sum(candidate_recall_rows) / len(candidate_recall_rows)
        ),
        "model_rerank": _aggregate(model_rows),
        "rule_rerank": _aggregate(rule_rows),
        "cases": case_rows,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare rerank methods by Precision@5 and nDCG@5."
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--qrels", type=Path, default=DEFAULT_QRELS_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--relevance-threshold",
        type=int,
        choices=[1, 2, 3],
        default=2,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run(
        args.cases,
        args.qrels,
        args.output,
        relevance_threshold=args.relevance_threshold,
    )
    print("=== Rerank Comparison ===")
    print(f"Candidate Recall@20={result['candidate_recall_at_20']:.3f}")
    for label in ("model_rerank", "rule_rerank"):
        metrics = result[label]
        print(
            f"{label}: Precision@5={metrics['precision_at_5']:.3f}, "
            f"nDCG@5={metrics['ndcg_at_5']:.3f}"
        )
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
