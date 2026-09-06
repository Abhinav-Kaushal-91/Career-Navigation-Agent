from uuid import uuid4

import pytest
from pydantic import ValidationError

from ai_career_navigator.domain import (
    ComparisonScope,
    ConfidenceLevel,
    GapCategory,
    MatchType,
    RequirementComparison,
    TimelineAssessment,
    TimelineClassification,
)


@pytest.mark.parametrize("match_type", list(MatchType))
def test_all_match_types_are_accepted(match_type: MatchType) -> None:
    comparison = RequirementComparison(
        requirement_id=uuid4(),
        posting_id=uuid4(),
        comparison_scope=ComparisonScope.EXACT_TARGET,
        match_type=match_type,
        confidence=ConfidenceLevel.MODERATE,
    )

    assert comparison.match_type is match_type


def test_gap_categories_match_the_five_v1_categories() -> None:
    assert {category.value for category in GapCategory} == {
        "SKILL",
        "EXPERIENCE",
        "LEADERSHIP_SCOPE",
        "EVIDENCE",
        "CREDENTIAL_PREREQUISITE",
    }


def test_timeline_requested_months_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        TimelineAssessment(
            requested_months=0,
            classification=TimelineClassification.REALISTIC,
            confidence=ConfidenceLevel.MODERATE,
        )
