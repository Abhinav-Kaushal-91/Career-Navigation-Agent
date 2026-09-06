from datetime import UTC, date, datetime
from pathlib import Path

from streamlit.testing.v1 import AppTest

from ai_career_navigator.domain import (
    ApprovalStatus,
    CandidateProfile,
    CareerStage,
    ConfidenceLevel,
    EvidenceConfirmationStatus,
    EvidenceItem,
    EvidenceMaturity,
)
from ai_career_navigator.profile import (
    ExperienceEntry,
    InferenceRunStatus,
    ProfileDraft,
    ProjectEntry,
    ProjectType,
    SkillCategory,
    SkillEntry,
    confirm_candidate_profile,
    finalize_strengths_profile,
)
from ai_career_navigator.ui.pages.profile import (
    PROFESSIONAL_SUMMARY_LABEL,
    _detected_skill_suggestions,
)


def test_literal_experience_skills_are_suggested_without_semantic_inference() -> None:
    draft = ProfileDraft(
        experiences=[
            ExperienceEntry(
                job_title="Developer",
                organization="Example",
                start_date=date(2024, 1, 1),
                current=True,
                accomplishments=["Built UiPath workflows and REST API integrations."],
            )
        ]
    )

    assert _detected_skill_suggestions(draft) == ("UiPath", "REST APIs")


def test_confirmed_skills_are_not_suggested_again() -> None:
    draft = ProfileDraft(
        experiences=[
            ExperienceEntry(
                job_title="Developer",
                organization="Example",
                start_date=date(2024, 1, 1),
                current=True,
                accomplishments=["Built Python services."],
            )
        ],
        skills=[
            SkillEntry(
                name="Python",
                category=SkillCategory.TECHNICAL,
                maturity=EvidenceMaturity.APPLIED,
            )
        ],
    )

    assert _detected_skill_suggestions(draft) == ()


def test_explicit_project_capabilities_are_suggested_verbatim() -> None:
    draft = ProfileDraft(
        projects=[
            ProjectEntry(
                name="Assistant",
                project_type=ProjectType.PERSONAL,
                context="Portfolio",
                contribution="Built an assistant.",
                capabilities_used=["Vector Search"],
                outcome="Working prototype.",
            )
        ]
    )

    assert _detected_skill_suggestions(draft) == ("Vector Search",)


def test_pasted_core_competencies_become_reviewable_suggestions() -> None:
    draft = ProfileDraft(
        core_competencies_text="UiPath, Insurance Operations\nStakeholder Management"
    )

    assert _detected_skill_suggestions(draft) == (
        "UiPath",
        "Stakeholder Management",
        "Insurance Operations",
    )


def test_professional_summary_appears_once_in_production_onboarding() -> None:
    app_path = Path(__file__).parents[2] / "src" / "ai_career_navigator" / "app.py"
    app = AppTest.from_file(app_path).run()
    app.session_state["current_step"] = "Profile"
    app.session_state["highest_reached_step"] = "Profile"
    app.session_state["profile_input_mode"] = "manual"
    app.session_state["capability_inference_status"] = InferenceRunStatus.EMPTY.value
    app.session_state["confirmed_profile"] = confirm_candidate_profile(ProfileDraft()).model_dump(
        mode="json"
    )

    summary_occurrences = 0
    for step in (
        "About You",
        "Professional Profile",
        "Portfolio Projects",
        "Education",
        "AI Strength Identification",
        "Review",
    ):
        app.session_state["current_profile_step"] = step
        app.session_state["highest_reached_profile_step"] = step
        app = app.run()
        summary_occurrences += sum(
            area.label == PROFESSIONAL_SUMMARY_LABEL for area in app.text_area
        )
        if step == "Professional Profile":
            headings = {item.value for item in app.subheader}
            assert {"Core Competencies", "Professional Experience"} <= headings

    assert summary_occurrences == 1


def test_profile_review_uses_user_facing_evidence_language() -> None:
    app_path = Path(__file__).parents[2] / "src" / "ai_career_navigator" / "app.py"
    app = AppTest.from_file(app_path).run()
    app.session_state["current_step"] = "Profile"
    app.session_state["highest_reached_step"] = "Profile"
    app.session_state["current_profile_step"] = "Review"
    app.session_state["highest_reached_profile_step"] = "Review"
    app.session_state["profile_input_mode"] = "manual"
    app.session_state["capability_inference_status"] = InferenceRunStatus.EMPTY.value
    app.session_state["confirmed_profile"] = confirm_candidate_profile(ProfileDraft()).model_dump(
        mode="json"
    )

    app = app.run()

    assert "What you've demonstrated" in {item.value for item in app.subheader}
    labels = {item.label for item in app.metric}
    assert {"User-entered evidence", "Confirmed evidence", "Portfolio projects"} <= labels
    assert "Evidence summary" not in {item.value for item in app.subheader}
    assert "Approved evidence" not in labels


def test_core_competency_prose_is_not_promoted_as_one_skill() -> None:
    draft = ProfileDraft(
        core_competencies_text=(
            "I have delivered complex automation programs across several business units "
            "while coordinating stakeholders."
        )
    )

    assert _detected_skill_suggestions(draft) == ()


def test_single_strengths_confirmation_confirms_retained_inference() -> None:
    now = datetime(2026, 9, 4, tzinfo=UTC)
    explicit = EvidenceItem(
        evidence_type="skill",
        source_type="manual onboarding",
        source_reference="Skills",
        capability="REST APIs",
        description="Built production REST integrations.",
        maturity_level=EvidenceMaturity.PRODUCTION,
        confirmation_status=EvidenceConfirmationStatus.EXPLICIT,
        confidence=ConfidenceLevel.HIGH,
        approved_by_user=True,
        created_at=now,
    )
    pending = EvidenceItem(
        evidence_type="inferred capability",
        source_type="AI capability inference",
        source_reference=f"Supporting evidence: {explicit.evidence_id} (Skills)",
        capability="Enterprise Integration",
        description="Supported by the confirmed integration evidence.",
        maturity_level=EvidenceMaturity.PRODUCTION,
        context="Production integration",
        confirmation_status=EvidenceConfirmationStatus.INFERRED_PENDING,
        confidence=ConfidenceLevel.MODERATE,
        approved_by_user=False,
        created_at=now,
    )
    profile = CandidateProfile(
        career_stage=CareerStage.MID_CAREER,
        evidence_items=[explicit, pending],
        approval_status=ApprovalStatus.APPROVED,
        created_at=now,
        confirmed_at=now,
    )
    updated = finalize_strengths_profile(
        ProfileDraft(), profile, ["Enterprise Integration"], now=now
    )
    confirmed = next(
        item for item in updated.evidence_items if item.evidence_id == pending.evidence_id
    )
    assert confirmed.approved_by_user
    assert confirmed.confirmation_status is EvidenceConfirmationStatus.CONFIRMED_INFERENCE


def test_removing_inferred_strength_preserves_rejected_provenance() -> None:
    now = datetime(2026, 9, 4, tzinfo=UTC)
    pending = EvidenceItem(
        evidence_type="inferred capability",
        source_type="AI capability inference",
        source_reference="Supporting evidence: retained-reference",
        capability="Enterprise Integration",
        description="Grounded inference.",
        maturity_level=EvidenceMaturity.APPLIED,
        confirmation_status=EvidenceConfirmationStatus.INFERRED_PENDING,
        confidence=ConfidenceLevel.MODERATE,
        approved_by_user=False,
        created_at=now,
    )
    profile = CandidateProfile(
        career_stage=CareerStage.MID_CAREER,
        evidence_items=[pending],
        approval_status=ApprovalStatus.APPROVED,
        created_at=now,
        confirmed_at=now,
    )

    updated = finalize_strengths_profile(ProfileDraft(), profile, [], now=now)
    rejected = updated.evidence_items[0]

    assert rejected.confirmation_status is EvidenceConfirmationStatus.REJECTED_INFERENCE
    assert not rejected.approved_by_user
    assert rejected.source_reference == pending.source_reference


def test_strengths_screen_replaces_manual_and_second_capability_steps() -> None:
    draft = ProfileDraft(
        experiences=[
            ExperienceEntry(
                job_title="Developer",
                organization="Example",
                start_date=date(2024, 1, 1),
                current=True,
                accomplishments=["Built Python services."],
            )
        ]
    )
    app_path = Path(__file__).parents[2] / "src" / "ai_career_navigator" / "app.py"
    app = AppTest.from_file(app_path).run()
    app.session_state["current_step"] = "Profile"
    app.session_state["highest_reached_step"] = "Profile"
    app.session_state["current_profile_step"] = "AI Strength Identification"
    app.session_state["highest_reached_profile_step"] = "AI Strength Identification"
    app.session_state["profile_input_mode"] = "manual"
    app.session_state["profile_draft"] = draft.model_dump(mode="json")
    app.session_state["confirmed_profile"] = confirm_candidate_profile(draft)
    app.session_state["capability_inference_status"] = InferenceRunStatus.EMPTY.value

    app = app.run()

    labels = {button.label for button in app.button}
    assert "Confirm my strengths" in labels
    assert "Identify additional capabilities" not in labels
    assert app.multiselect[0].value == ["Python"]

    app = (
        next(button for button in app.button if button.label == "Confirm my strengths")
        .click()
        .run()
    )
    confirmed = CandidateProfile.model_validate(app.session_state["confirmed_profile"])

    assert app.session_state["current_profile_step"] == "Review"
    assert app.session_state["profile_confirmed"]
    assert any(
        item.capability == "Python"
        and item.confirmation_status is EvidenceConfirmationStatus.EXPLICIT
        and item.approved_by_user
        for item in confirmed.evidence_items
    )

    app = next(button for button in app.button if button.label == "Continue to Goal").click().run()
    assert app.session_state["current_step"] == "Goal"
