"""Generic, dependency-free metric primitives shared across the eval suites.

Each function implements one row from the class metrics field guide (precision/
recall/F1, ranked-retrieval Recall@k/Precision@k/NDCG@k, and completeness). They
take plain Python collections in and return frozen Pydantic result models, so
every eval suite (retrieval, extraction, grounding, agent) reports numbers the
same shape without duplicating the arithmetic.
"""

import math
from collections.abc import Hashable, Iterable, Sequence

from pydantic import BaseModel, ConfigDict, Field


class PrecisionRecallF1(BaseModel):
    """Pooled (micro-averaged) precision/recall/F1 over a set of binary decisions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    true_positives: int = Field(ge=0)
    false_positives: int = Field(ge=0)
    false_negatives: int = Field(ge=0)
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)


def _safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def classification_metrics(
    predictions: Sequence[bool], labels: Sequence[bool]
) -> PrecisionRecallF1:
    """Precision/recall/F1 for a paired list of predicted vs. gold booleans.

    Used wherever an eval grades a yes/no decision per case: retrieval relevance,
    quote groundedness, schema validity, and similar binary gates.
    """

    if len(predictions) != len(labels):
        raise ValueError("predictions and labels must be the same length")
    true_positives = sum(1 for p, y in zip(predictions, labels) if p and y)
    false_positives = sum(1 for p, y in zip(predictions, labels) if p and not y)
    false_negatives = sum(1 for p, y in zip(predictions, labels) if not p and y)
    precision = _safe_divide(true_positives, true_positives + false_positives)
    recall = _safe_divide(true_positives, true_positives + false_negatives)
    return PrecisionRecallF1(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=_safe_divide(2 * precision * recall, precision + recall),
    )


def set_metrics(predicted: Iterable[Hashable], actual: Iterable[Hashable]) -> PrecisionRecallF1:
    """Precision/recall/F1 between a predicted set and a gold set (e.g. extracted capabilities)."""

    predicted_set = set(predicted)
    actual_set = set(actual)
    true_positives = len(predicted_set & actual_set)
    false_positives = len(predicted_set - actual_set)
    false_negatives = len(actual_set - predicted_set)
    precision = _safe_divide(true_positives, true_positives + false_positives)
    recall = _safe_divide(true_positives, true_positives + false_negatives)
    return PrecisionRecallF1(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=_safe_divide(2 * precision * recall, precision + recall),
    )


def pool_set_metrics(
    pairs: Iterable[tuple[Iterable[Hashable], Iterable[Hashable]]],
) -> PrecisionRecallF1:
    """Micro-averaged precision/recall/F1 across many (predicted, actual) set pairs.

    Pools true/false positive/negative counts before computing F1, matching the
    field guide's Micro F1 definition: "Pools all class decisions before computing F1."
    """

    true_positives = false_positives = false_negatives = 0
    for predicted, actual in pairs:
        result = set_metrics(predicted, actual)
        true_positives += result.true_positives
        false_positives += result.false_positives
        false_negatives += result.false_negatives
    precision = _safe_divide(true_positives, true_positives + false_positives)
    recall = _safe_divide(true_positives, true_positives + false_negatives)
    return PrecisionRecallF1(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=_safe_divide(2 * precision * recall, precision + recall),
    )


def exact_match_rate(predictions: Sequence[object], labels: Sequence[object]) -> float:
    """Fraction of predictions equal to the gold label (routing/classification accuracy)."""

    if len(predictions) != len(labels):
        raise ValueError("predictions and labels must be the same length")
    if not predictions:
        return 0.0
    return sum(1 for p, y in zip(predictions, labels) if p == y) / len(predictions)


def recall_at_k(ranked_ids: Sequence[Hashable], relevant_ids: Iterable[Hashable], k: int) -> float:
    """Recall@k: did the relevant items appear in the top k ranked results."""

    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    retrieved = set(ranked_ids[:k])
    return len(retrieved & relevant) / len(relevant)


def precision_at_k(
    ranked_ids: Sequence[Hashable], relevant_ids: Iterable[Hashable], k: int
) -> float:
    """Precision@k: what fraction of the top k ranked results are relevant."""

    if k <= 0:
        return 0.0
    relevant = set(relevant_ids)
    retrieved = ranked_ids[:k]
    return _safe_divide(sum(1 for item in retrieved if item in relevant), len(retrieved))


def dcg_at_k(graded_relevance: Sequence[float], k: int) -> float:
    """Discounted cumulative gain over the first k graded-relevance scores."""

    return sum(
        (2**relevance - 1) / math.log2(position + 2)
        for position, relevance in enumerate(graded_relevance[:k])
    )


def ndcg_at_k(ranked_relevance: Sequence[float], k: int) -> float:
    """Normalized DCG@k: DCG@k divided by the DCG of the ideal (sorted-descending) ordering."""

    ideal = dcg_at_k(sorted(ranked_relevance, reverse=True), k)
    return _safe_divide(dcg_at_k(ranked_relevance, k), ideal)


def completeness(produced_fields: Iterable[Hashable], required_fields: Iterable[Hashable]) -> float:
    """Filled required fields / total required fields (the field guide's Completeness formula)."""

    required = set(required_fields)
    if not required:
        return 1.0
    produced = set(produced_fields)
    return len(produced & required) / len(required)
