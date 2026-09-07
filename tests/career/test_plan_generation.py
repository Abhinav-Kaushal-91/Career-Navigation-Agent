from datetime import date
from uuid import uuid4

import pytest

from ai_career_navigator.career import (
    PlanGenerationStatus,
    PlanSynthesisValidationError,
    generate_career_plan,
)
from ai_career_navigator.domain import (
    ApprovalStatus,
    BridgeOutcome,
    BridgeRoleAssessment,
    CandidateAccessibility,
    ConfidenceLevel,
    GapCategory,
    GapSeverity,
    MilestoneType,
    PathType,
    PlanStatus,
    TimelineAssessment,
    TimelineClassification,
)
from ai_career_navigator.models import (
    ModelGateway,
    ModelRequest,
    ModelResponse,
    ModelRole,
    ModelTimeoutError,
)
from tests.career.test_path_assessment import gap, goal, profile, role


def timeline(
    months=24,
    classification=TimelineClassification.AGGRESSIVE_BUT_PLAUSIBLE,
    *,
    confidence=ConfidenceLevel.MODERATE,
) -> TimelineAssessment:
    return TimelineAssessment(
        requested_months=months,
        classification=classification,
        assumptions=["The target requirement profile remains reasonably stable."],
        market_dependencies=["Continued availability of target-role openings."],
        confidence=confidence,
    )


def bridge(title: str, gap_ids: list[str]) -> BridgeRoleAssessment:
    return BridgeRoleAssessment(
        bridge_role=title,
        current_strength_overlap=["REST APIs"],
        gaps_reduced=gap_ids,
        target_capabilities_gained=["Production AI"],
        candidate_accessibility=CandidateAccessibility.NEAR_TERM_TARGET,
        evidence_building_value="HIGH",
        leadership_scope_gain="MODERATE",
        user_constraint_fit="MODERATE",
        outcome=BridgeOutcome.RECOMMENDED_BRIDGE,
        explanation="Uses confirmed strengths and builds target evidence.",
        confidence=ConfidenceLevel.MODERATE,
    )


class PlanProvider:
    provider_name = "plan-fake"

    def __init__(self, mutation=None, error=None):
        self.mutation = mutation
        self.error = error

    def generate_structured(self, *, request, model, output_schema, timeout_seconds):
        if self.error:
            raise self.error
        import json

        payload = json.loads(request.user_prompt)
        if self.mutation:
            self.mutation(payload)
        return ModelResponse(
            content=json.dumps(payload),
            provider=self.provider_name,
            model=model,
            role=request.role,
            finish_reason="stop",
            latency_ms=0,
        )

    def generate_text(
        self, *, request: ModelRequest, model: str, timeout_seconds: float
    ) -> ModelResponse:
        raise AssertionError("text generation is not used")


def gateway(*, mutation=None, error=None) -> ModelGateway:
    return ModelGateway(
        provider=PlanProvider(mutation=mutation, error=error),
        models={ModelRole.REASONING: "fake-reasoning"},
        timeout_seconds=10,
        max_retries=0,
        sleeper=lambda _: None,
    )


def generate(
    accessibility,
    gaps,
    outcome,
    bridges=None,
    timeline_assessment=None,
    model_gateway=None,
):
    return generate_career_plan(
        profile(),
        goal(months=(timeline_assessment.requested_months if timeline_assessment else 24)),
        role(accessibility, gaps),
        bridges or [],
        outcome,
        timeline_assessment or timeline(),
        model_gateway,
        market_confidence=ConfidenceLevel.HIGH,
        source_ids=[uuid4()],
    )


def test_direct_apply_now_plan_is_compact_and_draft() -> None:
    result = generate(
        CandidateAccessibility.APPLY_NOW,
        [],
        BridgeOutcome.NO_BRIDGE_REQUIRED,
        timeline_assessment=timeline(12, TimelineClassification.REALISTIC),
    )
    assert result.plan.path_type is PathType.DIRECT
    assert result.plan.plan_status is PlanStatus.DRAFT
    assert result.plan.approval_status is ApprovalStatus.DRAFT
    assert result.plan.bridge_roles == []
    assert len(result.plan.milestones) == 1
    assert result.plan.milestones[0].milestone_type is MilestoneType.APPLICATION_READINESS


def test_bridge_plan_has_current_bridge_target_structure_and_gap_links() -> None:
    target_gap = gap("Production AI")
    bridge_role = bridge("AI Automation Engineer", [str(target_gap.gap_id)])
    result = generate(
        CandidateAccessibility.ASPIRATIONAL,
        [target_gap],
        BridgeOutcome.RECOMMENDED_BRIDGE,
        [bridge_role],
    )
    assert result.plan.path_type is PathType.BRIDGE
    assert result.plan.bridge_roles == [bridge_role]
    assert any(target_gap.gap_id in item.linked_gap_ids for item in result.plan.milestones)
    assert result.plan.milestones[-1].milestone_type is MilestoneType.REASSESSMENT


def test_aspirational_plan_without_bridge_uses_development_and_no_application_milestone() -> None:
    target_gap = gap("Professional production maturity")

    result = generate(
        CandidateAccessibility.ASPIRATIONAL,
        [target_gap],
        BridgeOutcome.NO_BRIDGE_REQUIRED,
    )

    assert result.plan.path_type is PathType.DEVELOPMENT
    assert result.plan.milestones[-1].milestone_type is MilestoneType.REASSESSMENT
    assert all(
        item.milestone_type is not MilestoneType.APPLICATION_READINESS
        for item in result.plan.milestones
    )
    assert all("application" not in item.action.casefold() for item in result.plan.milestones)


def test_multiple_paths_share_foundation_and_bound_branches() -> None:
    first = gap("Production AI")
    second = gap("Cloud AI")
    result = generate(
        CandidateAccessibility.ASPIRATIONAL,
        [first, second],
        BridgeOutcome.MULTIPLE_PLAUSIBLE_BRIDGES,
        [
            bridge("AI Automation Engineer", [str(first.gap_id)]),
            bridge("AI Platform Engineer", [str(second.gap_id)]),
        ],
    )
    assert result.plan.path_type is PathType.MULTIPLE_PATHS
    phases = [item.phase for item in result.plan.milestones]
    assert phases.count("Common evidence foundation") == 2
    assert phases.count("Supported bridge options") == 2
    assert result.plan.target_role == "AI Solutions Architect"


def test_no_credible_path_contains_only_hard_prerequisite_resolution() -> None:
    blocker = gap(
        "CPA",
        category=GapCategory.CREDENTIAL_PREREQUISITE,
        severity=GapSeverity.BLOCKING,
        hard=True,
    )
    result = generate(
        CandidateAccessibility.POOR_FIT,
        [blocker],
        BridgeOutcome.NO_VALID_BRIDGE_ROLE,
    )
    assert result.plan.path_type is PathType.NO_CREDIBLE_PATH
    assert len(result.plan.milestones) == 1
    assert result.plan.milestones[0].linked_gap_ids == [blocker.gap_id]
    assert "CPA" in result.plan.milestones[0].action


def test_evidence_and_leadership_gaps_create_correct_applied_milestones() -> None:
    evidence_gap = gap("Architecture case study", category=GapCategory.EVIDENCE)
    leadership_gap = gap("Architecture ownership", category=GapCategory.LEADERSHIP_SCOPE)
    result = generate(
        CandidateAccessibility.NEAR_TERM_TARGET,
        [evidence_gap, leadership_gap],
        BridgeOutcome.NO_BRIDGE_REQUIRED,
        timeline_assessment=timeline(18, TimelineClassification.REALISTIC),
    )
    milestones = result.plan.milestones
    assert milestones[0].milestone_type is MilestoneType.EVIDENCE
    assert "Produce direct evidence" in milestones[0].action
    assert milestones[1].milestone_type is MilestoneType.LEADERSHIP_SCOPE
    assert "required personal ownership and scope" in milestones[1].action


def test_ranges_are_ordered_and_bounded_by_requested_timeline() -> None:
    target_gap = gap("Production AI")
    result = generate(
        CandidateAccessibility.ASPIRATIONAL,
        [target_gap],
        BridgeOutcome.RECOMMENDED_BRIDGE,
        [bridge("AI Automation Engineer", [str(target_gap.gap_id)])],
    )
    assert all(0 <= item.month_start <= item.month_end <= 24 for item in result.plan.milestones)
    assert not any("%" in item.action for item in result.plan.milestones)


def test_missing_timeline_does_not_invent_twenty_four_months() -> None:
    result = generate(
        CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE,
        [],
        BridgeOutcome.INSUFFICIENT_EVIDENCE,
        timeline_assessment=timeline(
            None,
            TimelineClassification.UNSUPPORTED_INSUFFICIENT_EVIDENCE,
            confidence=ConfidenceLevel.INSUFFICIENT,
        ),
    )
    assert result.plan.path_type is PathType.EXPLORATION
    assert result.plan.timeline_assessment.requested_months is None
    assert {(item.month_start, item.month_end) for item in result.plan.milestones} == {(0, 0)}


def test_no_fixed_timeline_produces_credible_untimed_plan() -> None:
    target_gap = gap("Product roadmap ownership")
    result = generate(
        CandidateAccessibility.APPLY_SELECTIVELY,
        [target_gap],
        BridgeOutcome.NO_BRIDGE_REQUIRED,
        timeline_assessment=timeline(
            None,
            TimelineClassification.NO_FIXED_TIMELINE,
            confidence=ConfidenceLevel.MODERATE,
        ),
    )

    assert result.plan.path_type is PathType.DIRECT
    assert result.plan.confidence is ConfidenceLevel.MODERATE
    assert result.plan.timeline_assessment.requested_months is None
    assert all(set(item.linked_gap_ids) <= {target_gap.gap_id} for item in result.plan.milestones)


def test_plan_current_role_falls_back_to_latest_active_employment_evidence() -> None:
    base_profile = profile()
    active_role = base_profile.evidence_items[0].model_copy(
        update={
            "evidence_type": "employment",
            "capability": "Senior Intelligent Automation Consultant",
            "start_date": date(2024, 1, 1),
            "end_date": None,
        }
    )
    result = generate_career_plan(
        base_profile.model_copy(update={"current_role": None, "evidence_items": [active_role]}),
        goal(months=12),
        role(CandidateAccessibility.APPLY_SELECTIVELY, []),
        [],
        BridgeOutcome.NO_BRIDGE_REQUIRED,
        timeline(12, TimelineClassification.REALISTIC),
    )

    assert result.plan.current_role == "Senior Intelligent Automation Consultant"


def test_plan_current_role_falls_back_to_latest_completed_employment() -> None:
    base_profile = profile()
    older = base_profile.evidence_items[0].model_copy(
        update={
            "evidence_type": "employment",
            "capability": "Automation Analyst",
            "start_date": date(2020, 1, 1),
            "end_date": date(2021, 12, 31),
        }
    )
    latest = older.model_copy(
        update={
            "capability": "Automation Consultant",
            "start_date": date(2022, 1, 1),
            "end_date": date(2024, 12, 31),
        }
    )

    result = generate_career_plan(
        base_profile.model_copy(update={"current_role": None, "evidence_items": [older, latest]}),
        goal(months=12),
        role(CandidateAccessibility.APPLY_SELECTIVELY, []),
        [],
        BridgeOutcome.NO_BRIDGE_REQUIRED,
        timeline(12, TimelineClassification.REALISTIC),
    )

    assert result.plan.current_role == "Automation Consultant"


def test_risks_and_assumptions_are_derived_from_supplied_analysis() -> None:
    target_gap = gap("Production AI")
    result = generate(
        CandidateAccessibility.ASPIRATIONAL,
        [target_gap],
        BridgeOutcome.RECOMMENDED_BRIDGE,
        [bridge("AI Automation Engineer", [str(target_gap.gap_id)])],
    )
    assert "Observed bridge-role availability may remain limited." in result.plan.risks
    assert "Market dependency: Continued availability of target-role openings." in (
        result.plan.risks
    )
    assert result.plan.assumptions == [
        "The target requirement profile remains reasonably stable.",
        "The target location remains Toronto.",
        "The user remains open to an intermediate role.",
    ]


def test_plan_confidence_uses_lowest_relevant_upstream_confidence() -> None:
    result = generate(
        CandidateAccessibility.APPLY_NOW,
        [],
        BridgeOutcome.NO_BRIDGE_REQUIRED,
        timeline_assessment=timeline(
            12, TimelineClassification.REALISTIC, confidence=ConfidenceLevel.LOW
        ),
    )
    assert result.plan.confidence is ConfidenceLevel.LOW


def test_refused_required_bridge_maps_to_no_credible_path() -> None:
    target_gap = gap("Production AI")
    result = generate_career_plan(
        profile(),
        goal(months=24, willingness=False),
        role(CandidateAccessibility.ASPIRATIONAL, [target_gap]),
        [],
        BridgeOutcome.NO_VALID_BRIDGE_ROLE,
        timeline(24, TimelineClassification.UNLIKELY_WITHOUT_INTERMEDIATE_ROLE),
    )
    assert result.plan.path_type is PathType.NO_CREDIBLE_PATH
    assert result.plan.milestones[0].linked_gap_ids == [target_gap.gap_id]


def test_unknown_bridge_gap_reference_is_rejected() -> None:
    target_gap = gap("Production AI")
    with pytest.raises(PlanSynthesisValidationError, match="unknown gap"):
        generate(
            CandidateAccessibility.ASPIRATIONAL,
            [target_gap],
            BridgeOutcome.RECOMMENDED_BRIDGE,
            [bridge("AI Automation Engineer", [str(uuid4())])],
        )


def test_valid_optional_model_wording_is_accepted() -> None:
    target_gap = gap("Production AI")
    result = generate(
        CandidateAccessibility.ASPIRATIONAL,
        [target_gap],
        BridgeOutcome.RECOMMENDED_BRIDGE,
        [bridge("AI Automation Engineer", [str(target_gap.gap_id)])],
        model_gateway=gateway(),
    )
    assert result.status is PlanGenerationStatus.SUCCEEDED
    assert not result.fallback_used


@pytest.mark.parametrize(
    ("mutation", "value"),
    [
        ("target_role", "Invented Target"),
        ("bridge_role", "Invented Bridge"),
        ("gap_id", str(uuid4())),
        ("phase", "Invented phase"),
        ("milestone_type", "SKILL"),
        ("dependency", "invented-dependency"),
        ("action", "Learn Kubernetes while demonstrating Production AI."),
        ("action", "Obtain certification for Production AI."),
    ],
)
def test_unsupported_model_content_uses_deterministic_fallback(mutation, value) -> None:
    target_gap = gap("Production AI")
    supported_bridge = bridge("AI Automation Engineer", [str(target_gap.gap_id)])

    def mutate(payload):
        if mutation == "target_role":
            payload["target_role"] = value
        elif mutation == "bridge_role":
            payload["bridge_roles"] = [value]
        elif mutation == "gap_id":
            payload["milestones"][0]["linked_gap_ids"] = [value]
        elif mutation == "phase":
            payload["milestones"][0]["phase"] = value
        elif mutation == "milestone_type":
            payload["milestones"][0]["milestone_type"] = value
        elif mutation == "dependency":
            payload["milestones"][0]["dependencies"] = [value]
        else:
            payload["milestones"][0]["action"] = value

    result = generate(
        CandidateAccessibility.ASPIRATIONAL,
        [target_gap],
        BridgeOutcome.RECOMMENDED_BRIDGE,
        [supported_bridge],
        model_gateway=gateway(mutation=mutate),
    )
    assert result.status is PlanGenerationStatus.SUCCEEDED_WITH_FALLBACK
    assert result.fallback_used
    assert "Kubernetes" not in result.plan.milestones[0].action
    assert "certification" not in result.plan.milestones[0].action


def test_model_failure_preserves_deterministic_plan() -> None:
    result = generate(
        CandidateAccessibility.APPLY_NOW,
        [],
        BridgeOutcome.NO_BRIDGE_REQUIRED,
        timeline_assessment=timeline(12, TimelineClassification.REALISTIC),
        model_gateway=gateway(error=ModelTimeoutError("unavailable")),
    )
    assert result.status is PlanGenerationStatus.SUCCEEDED_WITH_FALLBACK
    assert result.plan.path_type is PathType.DIRECT
    assert result.limitations


@pytest.mark.parametrize("months", [None, 6, 24])
def test_ready_candidate_has_no_invented_development_wait(months) -> None:
    result = generate(
        CandidateAccessibility.APPLY_NOW,
        [],
        BridgeOutcome.RECOMMENDED_BRIDGE,
        [bridge("Unneeded intermediate role", [])],
        timeline_assessment=timeline(
            months,
            TimelineClassification.REALISTIC
            if months
            else TimelineClassification.NO_FIXED_TIMELINE,
        ),
    )
    plan = result.plan
    assert plan.path_type is PathType.DIRECT
    assert not plan.bridge_roles
    assert len(plan.milestones) == 1
    action = plan.milestones[0]
    assert action.milestone_type is MilestoneType.APPLICATION_READINESS
    assert (action.month_start, action.month_end) == (0, 0)
    assert not action.linked_gap_ids
    assert plan.source_goal_id and plan.source_assessment_id
    assert action.basis


def test_all_material_gaps_reach_the_plan_without_a_silent_quota() -> None:
    gaps = [gap(f"Independent requirement {index}") for index in range(9)]
    result = generate(
        CandidateAccessibility.NEAR_TERM_TARGET, gaps, BridgeOutcome.NO_BRIDGE_REQUIRED
    )
    assert {value for item in result.plan.milestones for value in item.linked_gap_ids} == {
        item.gap_id for item in gaps
    }
    for item in result.plan.milestones[:-1]:
        assert item.linked_requirement_ids
        assert item.residual_difference


def test_harmless_wording_paraphrase_is_allowed_without_loss_of_conditions() -> None:
    def paraphrase(payload):
        item = payload["milestones"][0]
        item["action"] = item["action"].replace("Demonstrate", "Show")

    result = generate(
        CandidateAccessibility.NEAR_TERM_TARGET,
        [gap("Data visualization", category=GapCategory.SKILL)],
        BridgeOutcome.NO_BRIDGE_REQUIRED,
        model_gateway=gateway(mutation=paraphrase),
    )
    assert not result.fallback_used
    assert result.plan.milestones[0].action.startswith("Show")


def test_model_cannot_remove_the_practical_context_from_an_action() -> None:
    def remove_context(payload):
        payload["milestones"][0]["action"] = "Demonstrate Data visualization."

    result = generate(
        CandidateAccessibility.NEAR_TERM_TARGET,
        [gap("Data visualization", category=GapCategory.SKILL)],
        BridgeOutcome.NO_BRIDGE_REQUIRED,
        model_gateway=gateway(mutation=remove_context),
    )
    assert result.fallback_used
    assert "applied solution" in result.plan.milestones[0].action


def test_optional_employer_preference_is_a_check_not_forced_training() -> None:
    preference = gap("Cloud specialization").model_copy(update={"required_status": "PREFERRED"})
    result = generate(
        CandidateAccessibility.APPLY_SELECTIVELY,
        [preference],
        BridgeOutcome.NO_BRIDGE_REQUIRED,
    )
    action = result.plan.milestones[0]
    assert "each selected posting" in action.action
    assert "training" not in action.action
    assert action.linked_requirement_ids == [preference.requirement_id]


def test_employer_specific_prerequisite_is_an_eligibility_check_not_universal_training():
    prerequisite = gap(
        "Professional license", category=GapCategory.CREDENTIAL_PREREQUISITE
    ).model_copy(update={"required_status": "MANDATORY", "employer_specific": True})
    result = generate(
        CandidateAccessibility.APPLY_SELECTIVELY,
        [prerequisite],
        BridgeOutcome.NO_BRIDGE_REQUIRED,
    )
    action = result.plan.milestones[0]
    assert "employers that explicitly require" in action.action
    assert "obtain" not in action.action.casefold()
    assert action.linked_requirement_ids == [prerequisite.requirement_id]


def test_unknown_prerequisite_requests_the_specific_fact() -> None:
    prerequisite = gap(
        "Professional license", category=GapCategory.CREDENTIAL_PREREQUISITE
    ).model_copy(
        update={
            "evidence_status": "UNKNOWN",
            "clarification_needed": "Do you currently hold the required professional license?",
        }
    )
    result = generate(
        CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE,
        [prerequisite],
        BridgeOutcome.INSUFFICIENT_EVIDENCE,
    )
    assert len(result.plan.milestones) == 1
    assert prerequisite.clarification_needed in result.plan.milestones[0].action
    assert "obtain" not in result.plan.milestones[0].action.casefold()


def test_gap_action_keeps_confirmed_strengths_and_requirement_provenance() -> None:
    candidate = profile()
    evidence_id = candidate.approved_evidence_items[0].evidence_id
    residual = gap("API architecture ownership").model_copy(
        update={"current_evidence_ids": [evidence_id]}
    )
    result = generate_career_plan(
        candidate,
        goal(),
        role(CandidateAccessibility.NEAR_TERM_TARGET, [residual]),
        [],
        BridgeOutcome.NO_BRIDGE_REQUIRED,
        timeline(),
    )
    milestone = result.plan.milestones[0]
    assert milestone.supporting_evidence_ids == [evidence_id]
    assert milestone.demonstrated_strength == "REST APIs"
    assert milestone.residual_difference == residual.remaining_difference
    assert milestone.linked_requirement_ids == [residual.requirement_id]
