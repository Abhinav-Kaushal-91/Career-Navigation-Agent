from pathlib import Path
from uuid import uuid4

import pytest

from ai_career_navigator.evaluation.extraction_eval import (
    ExtractionCandidate,
    ExtractionGoldCase,
    evaluate_extraction,
    load_extraction_gold,
    summarize_extraction_quality,
)
from ai_career_navigator.market.requirement_schemas import PostingExtractionQuality

GOLD_PATH = Path(__file__).parents[1] / "fixtures" / "extraction_capability_gold.json"


def test_gold_set_loads_with_unique_posting_ids() -> None:
    cases = load_extraction_gold(GOLD_PATH)

    assert len(cases) == 4
    assert len({case.posting_id for case in cases}) == len(cases)


def test_perfect_extraction_scores_f1_of_one() -> None:
    gold = load_extraction_gold(GOLD_PATH)
    candidates = [
        ExtractionCandidate(
            posting_id=case.posting_id, extracted_capabilities=case.expected_capabilities
        )
        for case in gold
    ]

    result = evaluate_extraction(gold, candidates)

    assert result.f1 == 1.0


def test_partial_extraction_is_penalized_on_both_precision_and_recall() -> None:
    gold = [
        ExtractionGoldCase(
            posting_id="P-1",
            source_file="fixture",
            expected_capabilities=["python", "sql", "aws"],
        )
    ]
    candidates = [ExtractionCandidate(posting_id="P-1", extracted_capabilities=["python", "excel"])]

    result = evaluate_extraction(gold, candidates)

    assert result.true_positives == 1
    assert result.false_positives == 1
    assert result.false_negatives == 2


def test_missing_candidate_for_a_gold_posting_raises() -> None:
    gold = [
        ExtractionGoldCase(
            posting_id="P-1", source_file="fixture", expected_capabilities=["python"]
        )
    ]

    with pytest.raises(ValueError, match="P-1"):
        evaluate_extraction(gold, [])


def _quality(
    *,
    schema_valid: bool | None,
    raw_count: int,
    unsupported: int,
) -> PostingExtractionQuality:
    return PostingExtractionQuality(
        posting_id=uuid4(),
        source_id=uuid4(),
        title="Example Role",
        input_description_characters=500,
        schema_valid_response=schema_valid,
        raw_extracted_item_count=raw_count,
        accepted_capability_requirement_count=raw_count,
        prerequisite_condition_count=0,
        rejected_metadata_non_requirement_count=0,
        unsupported_grounding_count=unsupported,
    )


def test_extraction_quality_summary_surfaces_schema_validity_and_groundedness() -> None:
    records = [
        _quality(schema_valid=True, raw_count=4, unsupported=0),
        _quality(schema_valid=False, raw_count=2, unsupported=1),
    ]

    summary = summarize_extraction_quality(records)

    assert summary.posting_count == 2
    assert summary.schema_valid_rate == 0.5
    assert summary.groundedness_rate == 1 - (1 / 6)


def test_extraction_quality_summary_handles_empty_input() -> None:
    summary = summarize_extraction_quality([])

    assert summary.schema_valid_rate == 1.0
    assert summary.groundedness_rate == 1.0
