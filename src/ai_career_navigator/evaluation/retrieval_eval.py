"""Precision/recall against a hand-labeled search-result relevance gold set.

`is_promising_search_result` is the deterministic gate that decides whether a raw
market search hit is worth fetching and processing further (see
`ai_career_navigator.market.validation`). It has no notion of rank, so there is no
ranked list to compute Recall@k/NDCG@k against; the metric that matches what the
gate actually does is a binary-classification precision/recall/F1 over labeled
(search result, target title) pairs.
"""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ai_career_navigator.market.schemas import MarketSearchResult
from ai_career_navigator.market.validation import is_promising_search_result

from .metrics import PrecisionRecallF1, classification_metrics


class RetrievalGoldCase(BaseModel):
    """One hand-labeled (search result, target role) relevance judgment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str = Field(min_length=1)
    target_title: str = Field(min_length=1)
    result: MarketSearchResult
    expected_relevant: bool
    note: str = Field(default="", max_length=300)


def load_retrieval_gold(path: Path) -> list[RetrievalGoldCase]:
    """Load the hand-labeled relevance gold set from a JSON file."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = [RetrievalGoldCase.model_validate(item) for item in payload]
    if len({case.case_id for case in cases}) != len(cases):
        raise ValueError("retrieval gold set contains duplicate case IDs")
    return cases


def evaluate_retrieval_gold(cases: list[RetrievalGoldCase]) -> PrecisionRecallF1:
    """Score the deterministic relevance gate against the gold labels."""

    predictions = [is_promising_search_result(case.result, case.target_title) for case in cases]
    labels = [case.expected_relevant for case in cases]
    return classification_metrics(predictions, labels)
