"""Cross-posting organization may not strengthen or lose source evidence."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from ai_career_navigator.market.overview import (
    CapabilityDimension,
    ExpectationGroup,
    ModelEmployerOverview,
    build_overview_payload,
    source_overview,
    synthesize_employer_overview,
    validate_overview,
)
from ai_career_navigator.market.requirement_schemas import (
    CanonicalRoleRequirement,
    CanonicalTargetRoleProfile,
    PostingCandidate,
)
from ai_career_navigator.market.requirements import _is_concise_capability


def expectation(name="Mentoring", quote="Mentor junior engineers", **overrides):
    values = dict(
        display_name=name,
        category="LEADERSHIP",
        requirement_kind="CAPABILITY",
        frequency_band="COMMON",
        primary_support_ratio=0.5,
        employer_support_count=1,
        posting_support_count=1,
        exact_support_count=1,
        variant_support_count=0,
        related_support_count=0,
        supporting_requirement_ids=[uuid4()],
        supporting_posting_ids=[uuid4()],
        supporting_employers=["Employer A"],
        representative_source_quotes=[quote],
        confidence="MODERATE",
        requirement_scope="CORE",
    )
    values.update(overrides)
    return CanonicalRoleRequirement(**values)


def role_profile(*items):
    return CanonicalTargetRoleProfile(
        target_role="Generic role",
        geography="Toronto",
        profile_status="PROVISIONAL",
        confidence="MODERATE",
        exact_posting_count=2,
        variant_posting_count=0,
        related_posting_count=1,
        distinct_exact_employer_count=1,
        analyzed_exact_posting_count=2,
        analyzed_variant_posting_count=0,
        analyzed_related_posting_count=1,
        generated_at=datetime.now(UTC),
        requirements=list(items),
    )


def test_overview_payload_is_candidate_free_and_preserves_source_qualifiers():
    item = expectation(
        relationship="ANY_OF",
        capability_options=["Java", "Python"],
        preferred_signal=True,
        years_required=5,
    )
    payload = build_overview_payload(role_profile(item))
    row = payload["expectations"][0]
    assert row["alternatives"] == ["Java", "Python"]
    assert row["preferred"] and row["years"] == 5
    assert row["source_quotes"] == item.representative_source_quotes
    assert not any("candidate" in key or "profile_context" in key for key in payload)


@pytest.mark.parametrize("failure", ["unknown", "duplicate", "missing", "people"])
def test_invalid_model_organization_is_rejected(failure):
    item, another = expectation(), expectation("Communication", "Communicate technical designs")
    profile = role_profile(item, another)
    ids = [item.canonical_requirement_id, another.canonical_requirement_id]
    if failure == "unknown":
        ids[0] = uuid4()
    if failure == "duplicate":
        ids.append(ids[0])
    if failure == "missing":
        ids.pop()
    draft = ModelEmployerOverview(
        groups=[
            ExpectationGroup(
                dimension=CapabilityDimension.PEOPLE
                if failure == "people"
                else CapabilityDimension.LEADERSHIP,
                requirement_ids=ids,
            )
        ]
    )
    with pytest.raises(ValueError):
        validate_overview(draft, profile)


@pytest.mark.parametrize(
    "overrides",
    [
        {"requirement_kind": "PREFERENCE"},
        {"requirement_scope": "OPTIONAL"},
        {"requirement_kind": "ROLE_RESPONSIBILITY"},
        {"employer_specific": True},
    ],
)
def test_distinct_boundaries_cannot_be_blended(overrides):
    first, second = expectation(), expectation(**overrides)
    draft = ModelEmployerOverview(
        groups=[
            ExpectationGroup(
                dimension=CapabilityDimension.LEADERSHIP,
                requirement_ids=[first.canonical_requirement_id, second.canonical_requirement_id],
            )
        ]
    )
    with pytest.raises(ValueError, match="boundaries"):
        validate_overview(draft, role_profile(first, second))


def test_interpersonal_and_people_management_have_distinct_source_basis():
    mentor = expectation()
    manager = expectation(
        "People Management", "Manage direct reports and conduct performance reviews"
    )
    communication = expectation("Communication", "Explain decisions", category="COMMUNICATION")
    result = source_overview(role_profile(mentor, manager, communication))
    dimensions = {group.dimension: group.requirement_ids for group in result.groups}
    assert dimensions[CapabilityDimension.LEADERSHIP] == [mentor.canonical_requirement_id]
    assert dimensions[CapabilityDimension.PEOPLE] == [manager.canonical_requirement_id]
    assert dimensions[CapabilityDimension.INTERPERSONAL] == [communication.canonical_requirement_id]


def test_model_can_organize_but_not_rewrite_original_expectations():
    profile = role_profile(expectation())
    original = profile.model_dump()
    draft = ModelEmployerOverview(groups=source_overview(profile).groups)
    gateway = SimpleNamespace(
        generate_structured=lambda **kw: SimpleNamespace(
            structured_output=draft.model_dump(mode="json"),
        )
    )
    overview = synthesize_employer_overview(profile, gateway)
    assert overview.method == "MODEL_ORGANIZED_VALIDATED_EXTRACTS"
    assert profile.model_dump() == original


def test_invalid_model_output_preserves_all_source_expectations_with_limitation():
    profile = role_profile(expectation())
    gateway = SimpleNamespace(
        generate_structured=lambda **kw: SimpleNamespace(
            structured_output={"groups": [], "accessibility": "APPLY_NOW"},
        )
    )
    result = synthesize_employer_overview(profile, gateway)
    assert result.groups == source_overview(profile).groups
    assert result.method == "SOURCE_GROUPING" and result.limitations


def test_description_sections_and_noncanonical_heading_guard():
    text = "Responsibilities\nBuild APIs\n\nQualifications\nExperience building APIs required"
    candidate = PostingCandidate(
        source_id=uuid4(),
        source_reference="job",
        source_reference_text="job",
        title="Developer",
        posting_text=text,
        extraction_confidence="MODERATE",
    )
    assert candidate.posting_text == text
    assert not _is_concise_capability("Key Responsibilities D…")
    assert _is_concise_capability("Technical Communication")


def test_empty_evidence_never_invokes_model():
    gateway = SimpleNamespace(generate_structured=lambda **kw: pytest.fail("No data to organize"))
    assert not synthesize_employer_overview(None, gateway).groups


def test_profile_context_is_not_converted_into_new_evidence():
    import json

    from ai_career_navigator.career.comparison_prompts import build_transferability_prompt
    from ai_career_navigator.domain import RoleRequirement

    requirement = RoleRequirement(
        posting_id=uuid4(),
        category="LEADERSHIP",
        requirement_text="Manage direct reports",
        normalized_capability="People Management",
        extraction_confidence="MODERATE",
    )
    prompt = build_transferability_prompt(
        requirement,
        [],
        profile_context={
            "core_competencies": "Strong leadership",
            "professional_summary": "Team contributor",
        },
    )
    data = json.loads(prompt.split("Assess this data:\n", 1)[1])
    assert data["self_reported_profile_context"]["core_competencies"] == "Strong leadership"
    assert data["candidate_evidence"] == []
