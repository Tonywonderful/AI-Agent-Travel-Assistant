import json
import math
from pathlib import Path
import sys

import pytest


CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag.evaluation_metrics import (  # noqa: E402
    CANDIDATE_K,
    TOP_K,
    candidate_recall_at_20,
    ndcg_at_5,
    precision_at_5,
    validate_qrels,
)
from scripts import evaluate_rag_retrieval  # noqa: E402


def test_core_metrics_for_multiple_relevant_chunks() -> None:
    ranked_keys = ["B", "A", "D", "C", "E"]
    judgments = {"A": 3, "C": 2, "F": 1}

    expected_dcg = 7 / math.log2(3) + 3 / math.log2(5)
    ideal_dcg = 7 + 3 / math.log2(3) + 1 / math.log2(4)

    assert TOP_K == 5
    assert CANDIDATE_K == 20
    assert candidate_recall_at_20(ranked_keys, judgments) == 0.1
    assert precision_at_5(ranked_keys, judgments) == 0.4
    assert ndcg_at_5(ranked_keys, judgments) == pytest.approx(
        expected_dcg / ideal_dcg
    )


def test_candidate_recall_uses_fixed_twenty_slot_denominator() -> None:
    relevant = [f"relevant-{index}" for index in range(53)]
    judgments = {key: 2 for key in relevant}
    ranked_keys = [*relevant[:19], "noise", relevant[19]]

    assert len(ranked_keys) == 21
    assert candidate_recall_at_20(ranked_keys, judgments) == 0.95
    assert candidate_recall_at_20(relevant[:20], judgments) == 1.0


def test_precision_uses_five_slots_and_penalizes_duplicates() -> None:
    ranked_keys = ["A", "A", "noise-1", "noise-2", "noise-3", "B"]
    judgments = {"A": 2, "B": 2}

    assert precision_at_5(ranked_keys, judgments) == 0.2
    assert precision_at_5(["A"], judgments) == 0.2


def test_ndcg_penalizes_duplicate_slots_without_shifting_later_results() -> None:
    ranked_keys = ["A", "A", "B"]
    judgments = {"A": 3, "B": 2}

    expected_dcg = 7 + 3 / math.log2(4)
    ideal_dcg = 7 + 3 / math.log2(3)
    assert ndcg_at_5(ranked_keys, judgments) == pytest.approx(
        expected_dcg / ideal_dcg
    )


def test_ndcg_reaches_one_when_top_five_is_the_ideal_graded_order() -> None:
    judgments = {"A": 3, "B": 3, "C": 2, "D": 2, "E": 1, "F": 1}

    assert ndcg_at_5(["A", "B", "C", "D", "E"], judgments) == 1.0


def test_binary_metrics_apply_relevance_threshold() -> None:
    ranked_keys = ["weak", "strict"]
    judgments = {"weak": 1, "strict": 2}

    assert candidate_recall_at_20(ranked_keys, judgments) == 0.05
    assert precision_at_5(ranked_keys, judgments) == 0.2
    assert candidate_recall_at_20(
        ranked_keys,
        judgments,
        relevance_threshold=1,
    ) == 0.1
    assert precision_at_5(
        ranked_keys,
        judgments,
        relevance_threshold=1,
    ) == 0.4


def test_binary_metrics_reject_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="relevance_threshold"):
        precision_at_5(["A"], {"A": 1}, relevance_threshold=0)

    with pytest.raises(ValueError, match="at or above threshold"):
        candidate_recall_at_20(["A"], {"A": 1}, relevance_threshold=2)


def test_validate_qrels_requires_exact_valid_case_coverage() -> None:
    with pytest.raises(ValueError, match="Missing qrels: q2"):
        validate_qrels({"q1": {"A": 1}}, ["q1", "q2"])

    with pytest.raises(ValueError, match="No positive judgment: q1"):
        validate_qrels({"q1": {"A": 0}}, ["q1"])

    with pytest.raises(ValueError, match="Relevance must be 0-3"):
        validate_qrels({"q1": {"A": 4}}, ["q1"])

    with pytest.raises(ValueError, match="Unexpected qrels: q2"):
        validate_qrels({"q1": {"A": 1}, "q2": {"B": 1}}, ["q1"])


def test_validate_qrels_rejects_empty_and_duplicate_case_ids() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        validate_qrels({"": {"A": 1}}, [""])

    with pytest.raises(ValueError, match="must be unique"):
        validate_qrels({"q1": {"A": 1}}, ["q1", "q1"])


def test_evaluation_aggregate_contains_only_final_ranking_metrics() -> None:
    rows = [
        {"precision_at_5": 1.0, "ndcg_at_5": 0.8},
        {"precision_at_5": 0.2, "ndcg_at_5": 0.4},
    ]

    assert evaluate_rag_retrieval._aggregate_final(rows) == {
        "precision_at_5": 0.6,
        "ndcg_at_5": pytest.approx(0.6),
    }


def test_evaluation_uses_model_rerank_scores_and_original_indices(monkeypatch) -> None:
    candidates = [{"title": f"chunk-{index}"} for index in range(6)]
    captured_kwargs = {}

    def fake_rerank(query, chunks, top_k, **kwargs):
        captured_kwargs.update(kwargs)
        return (
            [(0.9, 4), (0.8, 1), (0.7, 5), (0.6, 0), (0.5, 3)],
            {"prompt_tokens": 12, "completion_tokens": 0},
        )

    monkeypatch.setattr(
        evaluate_rag_retrieval,
        "_rerank_with_openrouter",
        fake_rerank,
    )

    reranked, usage, scores = evaluate_rag_retrieval._model_rerank_only(
        "query",
        candidates,
    )

    assert [chunk["title"] for chunk in reranked] == [
        "chunk-4",
        "chunk-1",
        "chunk-5",
        "chunk-0",
        "chunk-3",
    ]
    assert usage == {"prompt_tokens": 12, "completion_tokens": 0}
    assert scores == [0.9, 0.8, 0.7, 0.6, 0.5]
    assert captured_kwargs == {"filter_noise_titles": True}


def test_evaluation_run_uses_planning_scope(monkeypatch, tmp_path) -> None:
    cases_path = tmp_path / "cases.json"
    qrels_path = tmp_path / "qrels.json"
    output_path = tmp_path / "result.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "id": "case-1",
                    "query": "厦门 海边骑行",
                    "destination": "厦门",
                    "top_k": 5,
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    qrels_path.write_text(
        json.dumps({"case-1": {"xiamen_guide.md::景点1": 3}}, ensure_ascii=False),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}
    candidates = [
        {
            "title": f"景点{index}",
            "document_id": "xiamen_guide.md",
            "retrieval_scope": "planning",
        }
        for index in range(1, 21)
    ]

    def fake_search(**kwargs):
        captured.update(kwargs)
        return candidates, {"prompt_tokens": 0, "completion_tokens": 0}

    monkeypatch.setattr(evaluate_rag_retrieval, "_search_guide_chunks_by_chroma", fake_search)
    monkeypatch.setattr(
        evaluate_rag_retrieval,
        "_model_rerank_only",
        lambda query, chunks: (
            chunks[:5],
            {"prompt_tokens": 0, "completion_tokens": 0},
            [1.0, 0.9, 0.8, 0.7, 0.6],
        ),
    )

    result = evaluate_rag_retrieval.run(cases_path, qrels_path, output_path)

    assert captured["retrieval_scope"] == "planning"
    assert result["methodology"]["retrieval_scope"] == "planning"
    assert result["methodology"]["assistant_only_chunks_excluded"] is True


def test_evaluation_stops_when_model_rerank_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        evaluate_rag_retrieval,
        "_rerank_with_openrouter",
        lambda query, chunks, top_k, **kwargs: (
            None,
            {"prompt_tokens": 0, "completion_tokens": 0},
        ),
    )

    with pytest.raises(RuntimeError, match="without rule-based fallback"):
        evaluate_rag_retrieval._model_rerank_only("query", [{"title": "chunk"}])
