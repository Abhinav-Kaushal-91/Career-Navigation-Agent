from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ai_career_navigator.domain import (
    ConfidenceLevel,
    CurrentMarketSnapshot,
    EmployerDiversity,
    JobPosting,
    MarketConcentration,
    OpportunityAvailability,
    RequirementCategory,
    RoleRequirement,
)


def test_posting_closing_date_cannot_precede_posting_date() -> None:
    with pytest.raises(ValidationError, match="closing_date"):
        JobPosting(
            source_id=uuid4(),
            original_title="AI Architect",
            posting_date=date(2026, 8, 10),
            closing_date=date(2026, 8, 1),
            extraction_confidence=ConfidenceLevel.HIGH,
        )


def test_requirement_cannot_be_mandatory_and_preferred() -> None:
    with pytest.raises(ValidationError, match="both mandatory and preferred"):
        RoleRequirement(
            posting_id=uuid4(),
            category=RequirementCategory.TECHNICAL,
            requirement_text="Python experience",
            mandatory=True,
            preferred=True,
            extraction_confidence=ConfidenceLevel.MODERATE,
        )


def test_negative_required_years_fails() -> None:
    with pytest.raises(ValidationError):
        RoleRequirement(
            posting_id=uuid4(),
            category=RequirementCategory.EXPERIENCE,
            requirement_text="Prior architecture experience",
            years_required=-1,
            extraction_confidence=ConfidenceLevel.MODERATE,
        )


def test_frequency_must_be_normalized() -> None:
    with pytest.raises(ValidationError):
        RoleRequirement(
            posting_id=uuid4(),
            category=RequirementCategory.DOMAIN,
            requirement_text="Financial services",
            frequency_within_sample=1.1,
            extraction_confidence=ConfidenceLevel.LOW,
        )


def test_current_market_snapshot_uses_separate_v1_market_signals() -> None:
    assert "market_breadth" not in CurrentMarketSnapshot.model_fields

    snapshot = CurrentMarketSnapshot(
        target_role="AI Solutions Architect",
        geography="Toronto, Canada",
        search_date=date(2026, 9, 2),
        exact_title_count=5,
        related_title_count=10,
        validated_posting_count=15,
        distinct_employer_count=11,
        opportunity_availability=OpportunityAvailability.MODERATE,
        employer_diversity=EmployerDiversity.HIGH,
        market_concentration=MarketConcentration.LOW,
        evidence_confidence=ConfidenceLevel.MODERATE,
        employer_posting_counts={
            "Employer A": 1,
            "Employer B": 1,
            "Employer C": 1,
            "Employer D": 1,
            "Employer E": 1,
            "Employer F": 1,
            "Employer G": 1,
            "Employer H": 1,
            "Employer I": 1,
            "Employer J": 1,
            "Employer K": 1,
        },
        known_employer_posting_count=11,
        largest_employer_posting_count=1,
        top_three_employer_posting_count=3,
    )

    restored = CurrentMarketSnapshot.model_validate_json(snapshot.model_dump_json())

    assert restored == snapshot
    assert snapshot.opportunity_availability is OpportunityAvailability.MODERATE
    assert snapshot.employer_diversity is EmployerDiversity.HIGH


def test_job_posting_json_serialization_handles_uuid_and_datetime() -> None:
    posting = JobPosting(
        source_id=uuid4(),
        original_title="GenAI Solutions Architect",
        retrieved_at=datetime.now(UTC),
        extraction_confidence=ConfidenceLevel.HIGH,
    )

    serialized = posting.model_dump(mode="json")

    assert isinstance(serialized["posting_id"], str)
    assert serialized["retrieved_at"].endswith("Z")


def test_snapshot_rejects_opaque_or_inconsistent_explainability_counts() -> None:
    with pytest.raises(ValidationError, match="known employer count"):
        CurrentMarketSnapshot(
            target_role="AI Architect",
            geography="Toronto",
            search_date=date(2026, 9, 3),
            exact_title_count=1,
            related_title_count=0,
            validated_posting_count=1,
            distinct_employer_count=1,
            opportunity_availability=OpportunityAvailability.SPARSE,
            employer_diversity=EmployerDiversity.LOW,
            market_concentration=MarketConcentration.INSUFFICIENT_EVIDENCE,
            evidence_confidence=ConfidenceLevel.HIGH,
            employer_posting_counts={"Employer": 1},
            known_employer_posting_count=0,
            largest_employer_posting_count=1,
            top_three_employer_posting_count=1,
        )
