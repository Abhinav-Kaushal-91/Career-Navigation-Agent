"""The extraction handoff must not undo validated vacancy identity or ranking."""

from datetime import date
from uuid import uuid4

from ai_career_navigator.domain import ConfidenceLevel
from ai_career_navigator.market.requirement_schemas import (
    PostingCandidate,
    PostingCandidateAssessment,
    PostingGeographyStatus,
    PostingTitleMatch,
)
from ai_career_navigator.market.requirements import (
    _deduplicate_assessments,
    _select_employer_diverse,
)


def assessment(**changes):
    values = dict(
        source_id=uuid4(),
        source_reference="Synthetic posting",
        source_reference_text="Senior Financial Analyst at Employer in Toronto",
        title="Senior Financial Analyst",
        employer="Employer",
        location="Toronto",
        posting_text="Forecasting and reporting experience required. " * 5,
        extraction_confidence=ConfidenceLevel.HIGH,
        seniority_classification="SENIOR",
        retrieval_quality="HIGH",
    )
    values.update(changes)
    return PostingCandidateAssessment(
        candidate=PostingCandidate(**values),
        geography_status=PostingGeographyStatus.IN_SCOPE,
        title_match=PostingTitleMatch.TARGET_VARIANT,
    )


def test_distinct_requisitions_survive_extraction_dedup_even_with_identical_labels():
    first = assessment(requisition_id="REQ-A", canonical_job_url="https://example.com/jobs/shared")
    second = assessment(requisition_id="REQ-B", canonical_job_url="https://example.com/jobs/shared")
    retained = _deduplicate_assessments([first, second])
    assert {row.candidate.requisition_id for row in retained} == {"REQ-A", "REQ-B"}


def test_same_requisition_merges_provenance_without_adding_posting_support():
    first = assessment(
        requisition_id="REQ-A",
        provider_sources=["ADZUNA"],
        source_provenance=["https://adzuna.example/job/1"],
    )
    second = assessment(
        requisition_id="REQ-A",
        provider_sources=["YOU"],
        source_provenance=["https://employer.example/jobs/2"],
    )
    retained = _deduplicate_assessments([first, second])
    assert len(retained) == 1
    assert retained[0].candidate.provider_sources == ["ADZUNA", "YOU"]
    assert len(retained[0].candidate.source_provenance) == 2


def test_aggregator_segments_with_distinct_text_are_not_merged():
    first = assessment(
        source_url="https://example.com/jobs", posting_text="Forecasting experience required."
    )
    second = assessment(
        source_url="https://example.com/jobs", posting_text="Reporting experience required."
    )
    assert len(_deduplicate_assessments([first, second])) == 2


def test_explicit_seniority_survives_requirement_selection():
    senior = assessment()
    standard = assessment(title="Financial Analyst", seniority_classification="STANDARD")
    assert _select_employer_diverse([standard, senior], 1, "Senior Financial Analyst") == [senior]
    assert _select_employer_diverse([standard, senior], 1, "Financial Analyst", "Senior") == [
        senior
    ]
    assert _select_employer_diverse([senior, standard], 1, "Financial Analyst") == [standard]


def test_actual_age_not_date_presence_breaks_equal_quality_ties():
    old = assessment(posting_date=date(2026, 1, 1))
    recent = assessment(posting_date=date(2026, 9, 1))
    assert _select_employer_diverse([old, recent], 1, "Senior Financial Analyst") == [recent]
