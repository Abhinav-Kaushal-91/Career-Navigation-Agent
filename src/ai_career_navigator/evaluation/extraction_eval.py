"""Field accuracy, completeness, schema validity, and groundedness for requirement extraction.

`extract_posting_requirements` (ai_career_navigator.market.requirements) turns raw
posting text into `ExtractedRequirement` items via an LLM call, and already
computes per-posting `PostingExtractionQuality` counters (schema validity,
unsupported-grounding count) as production QA signal. This module adds the piece
that was missing: comparing the extracted capability set against a hand-labeled
gold set (field accuracy / completeness), and surfacing the existing quality
counters as eval-grade rates instead of leaving them as unread internals.
"""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ai_career_navigator.market.requirement_schemas import PostingExtractionQuality

from .metrics import PrecisionRecallF1, pool_set_metrics


def _normalize_capability(value: str) -> str:
    return " ".join(value.casefold().split())


class ExtractionGoldCase(BaseModel):
    """Hand-labeled expected capability set for one real job posting."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    posting_id: str = Field(min_length=1)
    source_file: str = Field(min_length=1)
    expected_capabilities: list[str] = Field(min_length=1)


class ExtractionCandidate(BaseModel):
    """The capability set a candidate extraction run produced for one posting."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    posting_id: str = Field(min_length=1)
    extracted_capabilities: list[str] = Field(default_factory=list)


def load_extraction_gold(path: Path) -> list[ExtractionGoldCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = [ExtractionGoldCase.model_validate(item) for item in payload]
    if len({case.posting_id for case in cases}) != len(cases):
        raise ValueError("extraction gold set contains duplicate posting IDs")
    return cases


def load_extraction_candidates(path: Path) -> list[ExtractionCandidate]:
    return [
        ExtractionCandidate.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def evaluate_extraction(
    gold: list[ExtractionGoldCase], candidates: list[ExtractionCandidate]
) -> PrecisionRecallF1:
    """Micro-averaged field accuracy: pooled capability precision/recall/F1 across all postings."""

    candidate_map = {item.posting_id: item.extracted_capabilities for item in candidates}
    missing = {case.posting_id for case in gold} - set(candidate_map)
    if missing:
        raise ValueError(f"no candidate extraction supplied for postings: {sorted(missing)}")
    pairs = (
        (
            [_normalize_capability(value) for value in candidate_map[case.posting_id]],
            [_normalize_capability(value) for value in case.expected_capabilities],
        )
        for case in gold
    )
    return pool_set_metrics(pairs)


class ExtractionQualitySummary(BaseModel):
    """Aggregated schema-validity and groundedness rates from production QA counters."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    posting_count: int = Field(ge=0)
    schema_valid_rate: float = Field(ge=0.0, le=1.0)
    groundedness_rate: float = Field(ge=0.0, le=1.0)


def summarize_extraction_quality(
    records: list[PostingExtractionQuality],
) -> ExtractionQualitySummary:
    """Surface `PostingExtractionQuality` counters as pass-rate metrics.

    `schema_valid_response` is `None` when validity was not assessed for that
    posting (e.g. an empty run); those records are excluded from the rate rather
    than counted as failures.
    """

    assessed = [item for item in records if item.schema_valid_response is not None]
    schema_valid_rate = (
        sum(1 for item in assessed if item.schema_valid_response) / len(assessed)
        if assessed
        else 1.0
    )
    total_items = sum(item.raw_extracted_item_count for item in records)
    unsupported_items = sum(item.unsupported_grounding_count for item in records)
    groundedness_rate = 1.0 - (unsupported_items / total_items if total_items else 0.0)
    return ExtractionQualitySummary(
        posting_count=len(records),
        schema_valid_rate=schema_valid_rate,
        groundedness_rate=groundedness_rate,
    )
