"""Description-supported specialties are generic variants, never invented exact titles."""

import pytest

from ai_career_navigator.market.combined_service import _identity_conflict
from ai_career_navigator.market.processing import assess_title
from ai_career_navigator.market.requirements import _assessment_from_evidence
from ai_career_navigator.market.schemas import MarketSearchResult
from ai_career_navigator.market.validation import (
    is_promising_search_result,
    title_equivalence_reason,
)
from tests.market.test_requirement_processing import structured_evidence


@pytest.mark.parametrize(
    "title,target,body",
    [
        (
            "Senior Software Engineer",
            "Senior Java Developer",
            "Qualifications\nProgramming (high proficiency in Java).",
        ),
        (
            "Senior Java Full Stack Developer",
            "Senior Java Developer",
            "Mandatory Skills: Java\nDevelop Java backend services.",
        ),
        (
            "Senior Software Engineer",
            "Senior Python Developer",
            "Requirements\nAdvanced expertise in Python or Java.",
        ),
        (
            "Senior Analyst",
            "Senior Financial Analyst",
            "Qualifications\nFinancial analysis experience is required.",
        ),
        (
            "Senior Software Engineer – Data Platform",
            "Senior Java Developer",
            "Required\nStrong programming ability in one or more languages:\nJava\nGo\nPython",
        ),
    ],
)
def test_body_can_establish_target_specialty(title, target, body):
    assert assess_title(title, target, body).value == "TARGET_VARIANT"
    assert title_equivalence_reason(title, target, body) == "DESCRIPTION_SUPPORTED_SPECIALTY"


@pytest.mark.parametrize(
    "title,body",
    [
        ("Senior Software Engineer", "Required: TypeScript and React experience."),
        ("Senior Software Engineer", "Preferred\nJava experience."),
        ("Senior Software Engineer", "Java is not required. We use TypeScript."),
        ("Senior Software Engineer", "About the company\nWe provide Java training courses."),
        ("Senior Software Engineer", "Java"),
        ("Junior Software Engineer", "Qualifications\nJava experience required."),
        ("Staff Software Engineer", "Qualifications\nJava experience required."),
        ("Senior Engineering Manager", "Qualifications\nJava experience required."),
        ("Senior Mechanical Engineer", "Qualifications\nJava experience required."),
    ],
)
def test_incidental_specialty_or_different_scope_not_promoted(title, body):
    assert assess_title(title, "Senior Java Developer", body).value != "TARGET_VARIANT"


def test_stale_title_only_classification_rechecked_after_full_text():
    item = structured_evidence(1, "Senior Software Engineer")
    item = item.model_copy(
        update={
            "title_classification": "IRRELEVANT",
            "primary_content": item.primary_content.model_copy(
                update={"markdown": "Qualifications\nStrong Java development experience required."}
            ),
        }
    )
    result = _assessment_from_evidence(item, target_role="Senior Java Developer")
    assert result.title_match.value == "TARGET_VARIANT"
    assert result.candidate.title == "Senior Software Engineer"
    assert result.candidate.title_classification == "TARGET_VARIANT"


def test_generic_heading_can_reach_bounded_content_fetch():
    candidate = MarketSearchResult(
        title="Senior Software Engineer", url="https://jobs.ashbyhq.com/example/4ad2f901-1234"
    )
    assert is_promising_search_result(candidate, "Senior Java Developer")


def test_body_supported_role_does_not_establish_same_vacancy():
    primary = structured_evidence(1, "Senior Java Developer")
    support = primary.primary_content.model_copy(
        update={
            "title": "Senior Software Engineer",
            "markdown": "Qualifications\nJava development experience is required.",
        }
    )
    assert (
        assess_title(support.title, "Senior Java Developer", support.markdown) == "TARGET_VARIANT"
    )
    assert _identity_conflict(primary, support) == "TITLE_NOT_GROUNDED"


def test_structured_discovery_snapshot_preserves_body_supported_variant():
    from tests.market.test_reliability_retrieval import retrieve, structured

    result = retrieve(
        structured(
            title="Senior Software Engineer",
            description="Qualifications\nHigh proficiency in Java programming is required.",
        )
    )
    assert result.snapshot.exact_title_count == 0
    assert result.snapshot.target_variant_count == 1
    assert result.snapshot.related_title_count == 0
    assert result.postings[0].original_title == "Senior Software Engineer"
    assert result.postings[0].title_match_kind == "DESCRIPTION_SUPPORTED_SPECIALTY"
