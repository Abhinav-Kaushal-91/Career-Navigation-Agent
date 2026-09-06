from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from ai_career_navigator.domain import (
    ApprovalStatus,
    CandidateProfile,
    CareerGoal,
    CareerStage,
    ConfidenceLevel,
    EvidenceConfirmationStatus,
    EvidenceItem,
    EvidenceMaturity,
    GeographyScope,
    GoalType,
)


def evidence_item(**overrides: object) -> EvidenceItem:
    values: dict[str, object] = {
        "evidence_type": "project",
        "source_type": "manual",
        "source_reference": "project-1",
        "capability": "Python",
        "description": "Built a Python application",
        "maturity_level": EvidenceMaturity.DEMONSTRATED,
        "confirmation_status": EvidenceConfirmationStatus.EXPLICIT,
        "confidence": ConfidenceLevel.HIGH,
    }
    values.update(overrides)
    return EvidenceItem(**values)


def test_student_profile_without_employment_history_is_valid() -> None:
    profile = CandidateProfile(
        career_stage=CareerStage.STUDENT,
        evidence_items=[evidence_item()],
    )

    assert profile.current_role is None
    assert profile.evidence_items[0].maturity_level is EvidenceMaturity.DEMONSTRATED


def test_approved_profile_requires_confirmed_at() -> None:
    with pytest.raises(ValidationError, match="confirmed_at"):
        CandidateProfile(
            career_stage=CareerStage.MID_CAREER,
            approval_status=ApprovalStatus.APPROVED,
        )


def test_rejected_inference_cannot_be_approved() -> None:
    with pytest.raises(ValidationError, match="rejected inference"):
        evidence_item(
            confirmation_status=EvidenceConfirmationStatus.REJECTED_INFERENCE,
            approved_by_user=True,
        )


def test_rejected_and_pending_inferences_are_not_approved_evidence() -> None:
    accepted = evidence_item(approved_by_user=True)
    rejected = evidence_item(
        capability="Unconfirmed leadership",
        confirmation_status=EvidenceConfirmationStatus.REJECTED_INFERENCE,
    )
    pending = evidence_item(
        capability="Possible architecture",
        confirmation_status=EvidenceConfirmationStatus.INFERRED_PENDING,
    )
    profile = CandidateProfile(
        career_stage=CareerStage.EARLY_CAREER,
        evidence_items=[accepted, rejected, pending],
    )

    assert profile.approved_evidence_items == (accepted,)


def test_evidence_end_date_cannot_precede_start_date() -> None:
    with pytest.raises(ValidationError, match="end_date"):
        evidence_item(start_date=date(2025, 1, 1), end_date=date(2024, 1, 1))


def test_open_exploration_without_target_role_is_valid() -> None:
    goal = CareerGoal(goal_type=GoalType.CAREER_EXPLORATION, exploration_mode=True)

    assert goal.target_role is None


def test_negative_goal_timeline_fails() -> None:
    with pytest.raises(ValidationError):
        CareerGoal(
            goal_type=GoalType.TARGET_CAREER_PATH,
            target_role="AI Solutions Architect",
            target_timeline_months=-1,
        )


def test_approved_goal_requires_approved_at() -> None:
    with pytest.raises(ValidationError, match="approved_at"):
        CareerGoal(
            goal_type=GoalType.ROLE_TRANSITION,
            target_role="Product Owner",
            approval_status=ApprovalStatus.APPROVED,
        )


def test_country_remote_scope_requires_remote_work_mode() -> None:
    with pytest.raises(ValidationError, match="COUNTRY_REMOTE requires Remote"):
        CareerGoal(
            goal_type=GoalType.TARGET_CAREER_PATH,
            target_role="AI Solutions Architect",
            geography_scopes=[GeographyScope.COUNTRY_REMOTE],
            preferred_work_modes=["Hybrid"],
        )


def test_candidate_profile_json_round_trip() -> None:
    profile = CandidateProfile(
        career_stage=CareerStage.STUDENT,
        portfolio_links=["https://example.com/portfolio"],
        evidence_items=[evidence_item(created_at=datetime.now(UTC))],
    )

    restored = CandidateProfile.model_validate_json(profile.model_dump_json())

    assert restored == profile
