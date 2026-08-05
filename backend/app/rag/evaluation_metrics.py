from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence


TOP_K = 5
CANDIDATE_K = 20


def _validate_relevance_threshold(relevance_threshold: int) -> None:
    if relevance_threshold not in {1, 2, 3}:
        raise ValueError("relevance_threshold must be 1, 2, or 3")


def _relevant_keys(
    judgments: Mapping[str, int],
    relevance_threshold: int,
) -> set[str]:
    _validate_relevance_threshold(relevance_threshold)
    relevant = {
        str(chunk_key)
        for chunk_key, relevance in judgments.items()
        if int(relevance) >= relevance_threshold
    }
    if not relevant:
        raise ValueError("judgments have no relevance at or above threshold")
    return relevant


def _ranking_slots(ranked_keys: Sequence[str], k: int) -> list[str]:
    return [str(key) for key in ranked_keys[:k]]


def _unique_relevant_count(slots: Sequence[str], relevant_keys: set[str]) -> int:
    seen: set[str] = set()
    count = 0
    for key in slots:
        if not key or key in seen:
            continue
        seen.add(key)
        if key in relevant_keys:
            count += 1
    return count


def candidate_recall_at_20(
    ranked_keys: Sequence[str],
    judgments: Mapping[str, int],
    relevance_threshold: int = 2,
) -> float:
    """Fraction of the 20 candidate slots occupied by relevant chunks."""
    relevant_keys = _relevant_keys(judgments, relevance_threshold)
    retrieved = _unique_relevant_count(
        _ranking_slots(ranked_keys, CANDIDATE_K),
        relevant_keys,
    )
    return retrieved / CANDIDATE_K


def precision_at_5(
    ranked_keys: Sequence[str],
    judgments: Mapping[str, int],
    relevance_threshold: int = 2,
) -> float:
    """Fraction of the five final ranking slots occupied by relevant chunks."""
    relevant_keys = _relevant_keys(judgments, relevance_threshold)
    retrieved = _unique_relevant_count(
        _ranking_slots(ranked_keys, TOP_K),
        relevant_keys,
    )
    return retrieved / TOP_K


def ndcg_at_5(
    ranked_keys: Sequence[str],
    judgments: Mapping[str, int],
) -> float:
    """Graded ranking quality in the first five slots using 0-3 qrels."""
    slots = _ranking_slots(ranked_keys, TOP_K)
    seen: set[str] = set()
    dcg = 0.0
    for rank, key in enumerate(slots, start=1):
        if not key or key in seen:
            continue
        seen.add(key)
        relevance = max(0, int(judgments.get(key, 0)))
        dcg += (2**relevance - 1) / math.log2(rank + 1)

    ideal_relevances = sorted(
        (max(0, int(relevance)) for relevance in judgments.values()),
        reverse=True,
    )[:TOP_K]
    ideal_dcg = sum(
        (2**relevance - 1) / math.log2(rank + 1)
        for rank, relevance in enumerate(ideal_relevances, start=1)
    )
    return 0.0 if ideal_dcg == 0 else dcg / ideal_dcg


def validate_qrels(
    qrels: Mapping[str, Mapping[str, int]],
    case_ids: Iterable[str],
) -> None:
    """Validate one-to-one case coverage and 0-3 relevance grades."""
    normalized_case_ids = [str(case_id) for case_id in case_ids]
    if not all(normalized_case_ids):
        raise ValueError("Evaluation case ids must not be empty")
    if len(normalized_case_ids) != len(set(normalized_case_ids)):
        raise ValueError("Evaluation case ids must be unique")

    missing: list[str] = []
    without_positive: list[str] = []
    invalid_relevance: list[str] = []
    for case_id in normalized_case_ids:
        judgments = qrels.get(case_id)
        if judgments is None:
            missing.append(case_id)
            continue
        for chunk_key, relevance in judgments.items():
            if int(relevance) not in {0, 1, 2, 3}:
                invalid_relevance.append(f"{case_id}/{chunk_key}={relevance}")
        if not any(int(relevance) > 0 for relevance in judgments.values()):
            without_positive.append(case_id)

    unexpected = sorted(set(qrels) - set(normalized_case_ids))
    if missing or without_positive or invalid_relevance or unexpected:
        parts: list[str] = []
        if missing:
            parts.append(f"Missing qrels: {', '.join(missing)}")
        if without_positive:
            parts.append(f"No positive judgment: {', '.join(without_positive)}")
        if invalid_relevance:
            parts.append(f"Relevance must be 0-3: {', '.join(invalid_relevance)}")
        if unexpected:
            parts.append(f"Unexpected qrels: {', '.join(unexpected)}")
        raise ValueError("; ".join(parts))
