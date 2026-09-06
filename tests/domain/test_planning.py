from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ai_career_navigator.domain import (
    ApprovalStatus,
    BridgeOutcome,
    BridgeRoleAssessment,
    CandidateAccessibility,
    CareerPlan,
    ConfidenceLevel,
    MilestoneType,
    PathType,
    PlanMilestone,
    PlanStatus,
)


def bridge_assessment() -> BridgeRoleAssessment:
    return BridgeRoleAssessment(
        bridge_role="AI Automation Engineer",
        candidate_accessibility=CandidateAccessibility.NEAR_TERM_TARGET,
        outcome=BridgeOutcome.RECOMMENDED_BRIDGE,
        explanation="Builds production AI delivery evidence.",
        confidence=ConfidenceLevel.MODERATE,
    )


def test_valid_direct_plan() -> None:
    plan = CareerPlan(
        path_type=PathType.DIRECT,
        current_role="Software Engineer",
        target_role="Senior Software Engineer",
        confidence=ConfidenceLevel.HIGH,
    )

    assert plan.bridge_roles == []


def test_valid_bridge_plan() -> None:
    plan = CareerPlan(
        path_type=PathType.BRIDGE,
        current_role="Senior UiPath Developer",
        target_role="AI Solutions Architect",
        bridge_roles=[bridge_assessment()],
        confidence=ConfidenceLevel.MODERATE,
    )

    restored = CareerPlan.model_validate_json(plan.model_dump_json())

    assert restored == plan


def test_bridge_plan_requires_bridge_assessment() -> None:
    with pytest.raises(ValidationError, match="bridge path"):
        CareerPlan(path_type=PathType.BRIDGE, confidence=ConfidenceLevel.LOW)


def test_approved_plan_requires_approved_at() -> None:
    with pytest.raises(ValidationError, match="approved_at"):
        CareerPlan(
            plan_status=PlanStatus.APPROVED,
            approval_status=ApprovalStatus.APPROVED,
            path_type=PathType.DIRECT,
            confidence=ConfidenceLevel.HIGH,
        )


def test_approved_plan_is_valid_with_timestamp() -> None:
    plan = CareerPlan(
        plan_status=PlanStatus.APPROVED,
        approval_status=ApprovalStatus.APPROVED,
        approved_at=datetime.now(UTC),
        path_type=PathType.DIRECT,
        confidence=ConfidenceLevel.HIGH,
    )

    assert plan.approved_at is not None


def test_milestone_end_cannot_precede_start() -> None:
    with pytest.raises(ValidationError, match="month_end"):
        PlanMilestone(
            phase="Foundation",
            month_start=6,
            month_end=3,
            milestone_type=MilestoneType.PROJECT,
            action="Build an AI system",
            measurable_outcome="Deployed production-style system",
        )


def test_no_credible_path_may_have_no_milestones() -> None:
    plan = CareerPlan(
        path_type=PathType.NO_CREDIBLE_PATH,
        confidence=ConfidenceLevel.INSUFFICIENT,
    )

    assert plan.milestones == []
