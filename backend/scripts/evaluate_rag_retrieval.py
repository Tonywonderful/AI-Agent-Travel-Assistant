from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
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
from app.rag.retriever import _rerank_with_openrouter
from app.rag.vector_db import (
    RETRIEVAL_SCOPE_PLANNING,
    _search_guide_chunks_by_chroma,
)


DEFAULT_CASES_PATH = BACKEND_DIR / "eval" / "rag_eval_cases.json"
DEFAULT_QRELS_PATH = BACKEND_DIR / "eval" / "rag_qrels.json"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "outputs" / "evaluations"


def _load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("Evaluation cases must be a non-empty JSON list")

    required = {"id", "query", "destination", "top_k"}
    for index, case in enumerate(data, start=1):
        if not isinstance(case, dict):
            raise ValueError(f"Case {index} must be a JSON object")
        missing = required - set(case)
        if missing:
            raise ValueError(f"Case {index} is missing: {', '.join(sorted(missing))}")
        if not all(str(case[field]).strip() for field in required):
            raise ValueError(f"Case {index} contains an empty required field")
        if int(case["top_k"]) != TOP_K:
            raise ValueError(f"Case {case['id']} top_k must be {TOP_K}")
    return data


def _load_qrels(path: Path) -> dict[str, dict[str, int]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Qrels must be a JSON object")

    qrels: dict[str, dict[str, int]] = {}
    for case_id, judgments in data.items():
        if not isinstance(judgments, dict):
            raise ValueError(f"qrels[{case_id!r}] must be a JSON object")
        qrels[str(case_id)] = {
            str(chunk_key): int(relevance)
            for chunk_key, relevance in judgments.items()
        }
    return qrels


def _chunk_key(chunk: dict[str, Any]) -> str:
    existing = str(chunk.get("chunk_key", ""))
    if existing:
        return existing
    document_id = str(chunk.get("document_id") or chunk.get("source", ""))
    return f"{document_id}::{chunk.get('title', '')}"


def _final_ranking_result(
    chunks: list[dict[str, Any]],
    judgments: dict[str, int],
    relevance_threshold: int,
) -> dict[str, Any]:
    top_chunks = chunks[:TOP_K]
    chunk_keys = [_chunk_key(chunk) for chunk in top_chunks]
    return {
        "precision_at_5": precision_at_5(
            chunk_keys,
            judgments,
            relevance_threshold=relevance_threshold,
        ),
        "ndcg_at_5": ndcg_at_5(chunk_keys, judgments),
        "chunk_keys": chunk_keys,
        "titles": [str(chunk.get("title", "")) for chunk in top_chunks],
    }


def _model_rerank_only(
    query: str,
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int], list[float]]:
    scored, token_usage = _rerank_with_openrouter(
        query,
        candidates,
        TOP_K,
        filter_noise_titles=True,
    )
    if not scored:
        raise RuntimeError(
            "Model rerank failed; evaluation stopped without rule-based fallback"
        )

    reranked_chunks: list[dict[str, Any]] = []
    rerank_scores: list[float] = []
    for score, candidate_index in scored:
        if not 0 <= candidate_index < len(candidates):
            continue
        reranked_chunks.append(dict(candidates[candidate_index]))
        rerank_scores.append(float(score))

    if len(reranked_chunks) != TOP_K:
        raise RuntimeError(
            f"Model rerank returned {len(reranked_chunks)} valid results; "
            f"expected {TOP_K}. Evaluation stopped without rule-based fallback"
        )
    return reranked_chunks, token_usage, rerank_scores


def _aggregate_final(rows: list[dict[str, Any]]) -> dict[str, float]:
    if not rows:
        raise ValueError("Cannot aggregate an empty result set")
    total = len(rows)
    return {
        "precision_at_5": (
            sum(float(row["precision_at_5"]) for row in rows) / total
        ),
        "ndcg_at_5": sum(float(row["ndcg_at_5"]) for row in rows) / total,
    }


def _default_output_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return DEFAULT_OUTPUT_DIR / f"rag_retrieval_core_metrics_{timestamp}.json"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(
    cases_path: Path,
    qrels_path: Path,
    output_path: Path,
    relevance_threshold: int = 2,
) -> dict[str, Any]:
    cases = _load_cases(cases_path)
    qrels = _load_qrels(qrels_path)
    case_ids = [str(case["id"]) for case in cases]
    validate_qrels(qrels, case_ids)

    below_threshold = [
        case_id
        for case_id in case_ids
        if not any(
            int(relevance) >= relevance_threshold
            for relevance in qrels[case_id].values()
        )
    ]
    if below_threshold:
        raise ValueError(
            "No qrels at or above relevance threshold for: "
            + ", ".join(below_threshold)
        )

    recall_rows: list[float] = []
    top_five_rows: list[dict[str, Any]] = []
    case_results: list[dict[str, Any]] = []

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
            raise RuntimeError(
                f"Vector retrieval returned no candidates for {case_id}; "
                "the benchmark will not silently use keyword fallback"
            )

        candidate_keys = [_chunk_key(chunk) for chunk in candidates]
        recall_at_20 = candidate_recall_at_20(
            candidate_keys,
            judgments,
            relevance_threshold=relevance_threshold,
        )
        reranked_chunks, rerank_usage, rerank_scores = _model_rerank_only(
            query,
            candidates,
        )
        top_five_result = _final_ranking_result(
            reranked_chunks,
            judgments,
            relevance_threshold,
        )

        recall_rows.append(recall_at_20)
        top_five_rows.append(top_five_result)

        case_results.append(
            {
                "id": case_id,
                "query": query,
                "destination": destination,
                "recall_at_20": recall_at_20,
                "precision_at_5": top_five_result["precision_at_5"],
                "ndcg_at_5": top_five_result["ndcg_at_5"],
                "candidate_chunk_keys": candidate_keys[:CANDIDATE_K],
                "model_reranked_top_five_chunk_keys": top_five_result["chunk_keys"],
                "model_reranked_top_five_titles": top_five_result["titles"],
                "model_rerank_scores": rerank_scores,
                "model_rerank_token_usage": rerank_usage,
            }
        )
        print(f"[{index}/{len(cases)}] {case_id}", flush=True)

    result: dict[str, Any] = {
        "schema_version": 3,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "methodology": {
            "cases_path": str(cases_path),
            "qrels_path": str(qrels_path),
            "cases_sha256": _file_sha256(cases_path),
            "qrels_sha256": _file_sha256(qrels_path),
            "fixed_queries": True,
            "embedding_model": EMBEDDING_MODEL,
            "rerank_model": RERANK_MODEL,
            "collection": CHROMA_COLLECTION_NAME,
            "candidate_k": CANDIDATE_K,
            "top_k": TOP_K,
            "relevance_threshold": relevance_threshold,
            "recall_at_20_denominator": CANDIDATE_K,
            "candidate_order": "chroma_vector_similarity",
            "retrieval_scope": RETRIEVAL_SCOPE_PLANNING,
            "assistant_only_chunks_excluded": True,
            "top_five_order": "model_cross_encoder_rerank",
            "model_rerank_required": True,
            "no_rule_rerank_fallback": True,
            "fixed_noise_title_filter_enabled": True,
            "no_keyword_fallback": True,
        },
        "summary": {
            "recall_at_20": sum(recall_rows) / len(recall_rows),
            **_aggregate_final(top_five_rows),
        },
        "cases": case_results,
    }

    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite evaluation output: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate vector Recall@20 and model-reranked Precision@5/nDCG@5 "
            "without rule-based fallback."
        )
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--qrels", type=Path, default=DEFAULT_QRELS_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--relevance-threshold",
        type=int,
        choices=[1, 2, 3],
        default=2,
    )
    return parser


def _print_summary(result: dict[str, Any], output_path: Path) -> None:
    summary = result["summary"]
    print("=== RAG Core Metrics ===")
    print(f"Recall@20={summary['recall_at_20']:.3f}")
    print(f"Precision@5={summary['precision_at_5']:.3f}")
    print(f"nDCG@5={summary['ndcg_at_5']:.3f}")
    print(f"output: {output_path}")


def main() -> int:
    args = build_parser().parse_args()
    output_path = args.output or _default_output_path()
    result = run(
        cases_path=args.cases,
        qrels_path=args.qrels,
        output_path=output_path,
        relevance_threshold=args.relevance_threshold,
    )
    _print_summary(result, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
