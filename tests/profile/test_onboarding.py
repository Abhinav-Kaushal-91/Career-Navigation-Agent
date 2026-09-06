from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from ai_career_navigator.domain import (
    ApprovalStatus,
    CareerStage,
    EvidenceConfirmationStatus,
    EvidenceMaturity,
)
from ai_career_navigator.profile import (
    AboutYou,
    CertificationEntry,
    EducationEntry,
    ExperienceEntry,
    ProfileDraft,
    ProjectEntry,
    ProjectStage,
    ProjectType,
    SkillCategory,
    SkillEntry,
    build_candidate_profile,
    confirm_candidate_profile,
    maturity_from_label,
)


def student_draft() -> ProfileDraft:
    return ProfileDraft(
        about=AboutYou(
            current_role=None,
            years_professional_experience=0,
            current_location="Toronto, Canada",
            career_stage=CareerStage.STUDENT,
            career_summary="Computer science student building applied AI projects.",
        ),
        skills=[
            SkillEntry(
                name="Python",
                category=SkillCategory.TECHNICAL,
                maturity=EvidenceMaturity.DEMONSTRATED,
            )
        ],
        projects=[
            ProjectEntry(
                name="Campus accessibility assistant",
                project_type=ProjectType.ACADEMIC,
                context="Capstone project",
                contribution="Built the retrieval and evaluation pipeline.",
                capabilities_used=["Python", "Information Retrieval"],
                maturity=EvidenceMaturity.DEMONSTRATED,
                outcome="Produced a working demonstration for the capstone review.",
            )
        ],
        education=[
            EducationEntry(
                qualification="Bachelor of Computer Science",
                field_of_study="Computer Science",
                institution="Example University",
                completion_year=2027,
                expected=True,
            )
        ],
    )


def senior_professional_draft() -> ProfileDraft:
    return ProfileDraft(
        about=AboutYou(
            current_role="Senior RPA Developer",
            years_professional_experience=8,
            current_location="Toronto, Canada",
            career_stage=CareerStage.SENIOR_INDIVIDUAL_CONTRIBUTOR,
        ),
        experiences=[
            ExperienceEntry(
                job_title="Senior RPA Developer",
                organization="Example Cooperative",
                start_date=date(2022, 1, 1),
                current=True,
                accomplishments=["Built enterprise automations", "Integrated REST APIs"],
            )
        ],
        skills=[
            SkillEntry(
                name="UiPath",
                category=SkillCategory.TECHNICAL,
                maturity=EvidenceMaturity.PRODUCTION,
            )
        ],
        projects=[
            ProjectEntry(
                name="Claims automation platform",
                project_type=ProjectType.PROFESSIONAL,
                context="Insurance operations",
                contribution="Owned automation design and production delivery.",
                capabilities_used=["Automation Design", "Production Support"],
                maturity=EvidenceMaturity.PRODUCTION,
                outcome="Improved workflow reliability.",
            )
        ],
        education=[
            EducationEntry(
                qualification="Bachelor of Technology",
                field_of_study="Information Technology",
                institution="Example Institute",
                completion_year=2016,
            )
        ],
        certifications=[
            CertificationEntry(name="UiPath Advanced Developer", issuer="UiPath", year=2023)
        ],
    )


def test_student_with_no_role_no_employment_and_zero_years_is_valid() -> None:
    draft = student_draft()

    assert draft.about.current_role is None
    assert draft.about.years_professional_experience == 0
    assert draft.experiences == []


def test_profile_keeps_summary_and_core_competencies_as_separate_inputs() -> None:
    draft = student_draft().model_copy(
        update={"core_competencies_text": "Python; Information Retrieval"}
    )

    profile = build_candidate_profile(draft)

    assert profile.professional_summary == (
        "Computer science student building applied AI projects."
    )
    assert profile.core_competencies == "Python; Information Retrieval"


def test_negative_years_experience_fails() -> None:
    with pytest.raises(ValidationError):
        AboutYou(years_professional_experience=-1)


def test_current_experience_is_valid_without_end_date() -> None:
    entry = ExperienceEntry(
        job_title="Developer",
        organization="Example",
        start_date=date(2024, 1, 1),
        current=True,
    )

    assert entry.end_date is None


def test_current_role_falls_back_to_most_recent_active_experience() -> None:
    original = senior_professional_draft()
    draft = original.model_copy(
        update={
            "about": original.about.model_copy(update={"current_role": None}),
            "experiences": [
                ExperienceEntry(
                    job_title="Automation Consultant",
                    organization="Earlier employer",
                    start_date=date(2020, 1, 1),
                    current=True,
                ),
                ExperienceEntry(
                    job_title="Senior Intelligent Automation Consultant",
                    organization="Current employer",
                    start_date=date(2024, 1, 1),
                    current=True,
                ),
            ],
        }
    )

    profile = build_candidate_profile(draft)

    assert profile.current_role == "Senior Intelligent Automation Consultant"


@pytest.mark.parametrize("year", (1998, 2009))
def test_historical_experience_years_are_valid(year: int) -> None:
    entry = ExperienceEntry(
        job_title="Developer",
        organization="Example",
        start_date=date(year, 1, 1),
        end_date=date(year, 12, 1),
    )

    assert entry.start_date.year == year


def test_future_experience_start_fails() -> None:
    with pytest.raises(ValidationError, match="future"):
        ExperienceEntry(
            job_title="Developer",
            organization="Example",
            start_date=date(date.today().year + 1, 1, 1),
        )


def test_experience_end_before_start_fails() -> None:
    with pytest.raises(ValidationError, match="end date cannot precede"):
        ExperienceEntry(
            job_title="Developer",
            organization="Example",
            start_date=date(2025, 1, 1),
            end_date=date(2024, 1, 1),
        )


def test_empty_experience_is_not_valid() -> None:
    with pytest.raises(ValidationError):
        ExperienceEntry(
            job_title=" ",
            organization=" ",
            start_date=date(2025, 1, 1),
        )


def test_blank_skill_is_rejected_and_maturity_mapping_is_exact() -> None:
    with pytest.raises(ValidationError, match="skill name"):
        SkillEntry(
            name=" ",
            category=SkillCategory.TECHNICAL,
            maturity=EvidenceMaturity.EXPOSURE,
        )

    assert maturity_from_label("Used in Production") is EvidenceMaturity.PRODUCTION


def test_project_without_numeric_metric_and_personal_project_are_valid() -> None:
    project = ProjectEntry(
        name="Career planning prototype",
        project_type=ProjectType.PERSONAL,
        context="Independent portfolio project",
        contribution="Designed and built the application.",
        outcome="Improved the clarity of career research.",
    )

    assert project.measurable_impact is None
    assert project.delivery_stage is ProjectStage.PROTOTYPE


@pytest.mark.parametrize("stage", (ProjectStage.MVP, ProjectStage.PRODUCTION_GRADE))
def test_portfolio_project_supports_mvp_and_production_grade(stage: ProjectStage) -> None:
    project = ProjectEntry(
        name="Career Navigator",
        project_type=ProjectType.PERSONAL,
        delivery_stage=stage,
        context="Independent portfolio project",
        contribution="Designed and built the application.",
        outcome="Released a working system.",
    )

    assert project.delivery_stage is stage


def test_project_without_explicit_capabilities_is_preserved_without_inferred_evidence() -> None:
    project = ProjectEntry(
        name="Career planning prototype",
        project_type=ProjectType.PERSONAL,
        context="Independent portfolio project",
        contribution="Designed and built the application.",
        outcome="Produced a working prototype.",
    )
    draft = ProfileDraft(projects=[project])

    profile = build_candidate_profile(draft)

    assert profile.evidence_items == []
    assert draft.projects == [project]


def test_project_supports_qualitative_outcome_and_measurable_impact() -> None:
    project = ProjectEntry(
        name="Operations automation",
        project_type=ProjectType.PROFESSIONAL,
        context="Insurance operations",
        contribution="Automated transaction processing.",
        outcome="Improved reliability.",
        measurable_impact="Automated 5,000 transactions per month.",
    )

    assert project.outcome == "Improved reliability."
    assert project.measurable_impact is not None


def test_empty_project_is_not_valid() -> None:
    with pytest.raises(ValidationError):
        ProjectEntry(
            name=" ",
            project_type=ProjectType.OTHER,
            context=" ",
            contribution=" ",
            outcome=" ",
        )


def test_education_and_certifications_are_optional() -> None:
    assert ProfileDraft().education == []
    assert ProfileDraft().certifications == []


def test_historical_education_is_valid_without_a_2015_floor() -> None:
    education = EducationEntry(
        qualification="Bachelor's degree",
        institution="Example University",
        completion_year=1998,
    )

    assert education.completion_year == 1998


def test_future_education_requires_expected_status() -> None:
    with pytest.raises(ValidationError, match="expected"):
        EducationEntry(
            qualification="Master's degree",
            institution="Example University",
            completion_year=date.today().year + 1,
        )


def test_complete_profile_maps_only_explicit_approved_evidence() -> None:
    profile = build_candidate_profile(senior_professional_draft())

    assert profile.approval_status is ApprovalStatus.DRAFT
    assert profile.confirmed_at is None
    assert profile.evidence_items
    assert all(
        item.confirmation_status is EvidenceConfirmationStatus.EXPLICIT and item.approved_by_user
        for item in profile.evidence_items
    )
    skill_evidence = next(item for item in profile.evidence_items if item.evidence_type == "skill")
    assert skill_evidence.capability == "UiPath"
    assert skill_evidence.maturity_level is EvidenceMaturity.PRODUCTION


def test_confirmation_approves_profile_and_populates_timezone_aware_timestamp() -> None:
    timestamp = datetime(2026, 9, 2, 20, 0, tzinfo=UTC)

    profile = confirm_candidate_profile(student_draft(), now=timestamp)

    assert profile.approval_status is ApprovalStatus.APPROVED
    assert profile.confirmed_at == timestamp
    assert profile.confirmed_at.tzinfo is not None


def test_student_and_professional_drafts_round_trip_for_session_state() -> None:
    for draft in (student_draft(), senior_professional_draft()):
        restored = ProfileDraft.model_validate(draft.model_dump(mode="json"))

        assert restored == draft
