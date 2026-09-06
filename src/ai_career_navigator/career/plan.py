"""Evidence-grounded V1 career-plan generation."""

import logging
from collections.abc import Sequence
from uuid import UUID

from ai_career_navigator.domain import (
    ApprovalStatus,
    BridgeOutcome,
    BridgeRoleAssessment,
    CandidateProfile,
    CareerGoal,
    CareerPlan,
    ConfidenceLevel,
    GapCategory,
    GapItem,
    MilestoneType,
    PathType,
    PlanMilestone,
    PlanStatus,
    RoleAssessment,
    TimelineAssessment,
    TimelineClassification,
)
from ai_career_navigator.models import ModelGateway, ModelGatewayError, ModelRole

from .comparison import normalize_capability
from .plan_policy import (
    lowest_confidence,
    milestone_type_for,
    phase_boundaries,
    select_path_type,
)
from .plan_prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_plan_prompt
from .plan_schemas import (
    CareerPlanDraftOutput,
    CareerPlanGenerationResult,
    PlanGenerationStatus,
)
from .synthesis_schemas import CareerAssessmentSynthesis

logger = logging.getLogger(__name__)
_MATERIAL_GAP_LIMIT = 6
_SAFE_WORDING_TOKENS = {
    "a",
    "an",
    "and",
    "applied",
    "as",
    "build",
    "completed",
    "create",
    "created",
    "decision",
    "decisions",
    "deliver",
    "delivery",
    "demonstrate",
    "demonstrates",
    "document",
    "documented",
    "evidence",
    "for",
    "gain",
    "in",
    "one",
    "outcome",
    "produce",
    "project",
    "responsibility",
    "reviewable",
    "shows",
    "solution",
    "the",
    "through",
    "using",
    "with",
}


class PlanSynthesisValidationError(ValueError):
    """Raised when optional model wording changes the approved plan facts."""


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value.strip()))


def _current_role(profile: CandidateProfile) -> str | None:
    if profile.current_role:
        return profile.current_role
    employment = [
        item
        for item in profile.approved_evidence_items
        if item.evidence_type.casefold() == "employment"
    ]
    if not employment:
        return None
    active_employment = [item for item in employment if item.end_date is None]
    candidates = active_employment or employment
    latest = max(
        candidates,
        key=lambda item: item.start_date or item.end_date or item.created_at.date(),
    )
    return latest.capability


def _gap_action(gap: GapItem) -> tuple[str, str, list[str]]:
    target = gap.target_expectation
    evidence = gap.evidence_needed or f"Documented evidence of {target}"
    if gap.category is GapCategory.SKILL:
        return (
            f"Demonstrate {target} in an applied solution.",
            f"One working solution demonstrates {target} with documented design choices.",
            [evidence],
        )
    if gap.category is GapCategory.EXPERIENCE:
        return (
            f"Gain demonstrable practical experience in {target}.",
            f"One completed delivery shows applied responsibility for {target}.",
            [evidence],
        )
    if gap.category is GapCategory.LEADERSHIP_SCOPE:
        return (
            f"Own the relevant technical decisions and stakeholder alignment for {target}.",
            f"One delivery records decision ownership and cross-functional scope for {target}.",
            [evidence],
        )
    if gap.category is GapCategory.CREDENTIAL_PREREQUISITE:
        return (
            f"Resolve the confirmed prerequisite for {target}.",
            f"The required {target} prerequisite is verified with authoritative evidence.",
            [evidence],
        )
    return (
        f"Produce direct evidence of {target}.",
        f"One reviewable artifact demonstrates {target} and the resulting outcome.",
        [evidence],
    )


def _gap_milestones(gaps: Sequence[GapItem], *, phase: str, month_end: int) -> list[PlanMilestone]:
    milestones = []
    for gap in gaps[:_MATERIAL_GAP_LIMIT]:
        action, outcome, evidence = _gap_action(gap)
        milestones.append(
            PlanMilestone(
                phase=phase,
                month_start=0,
                month_end=month_end,
                milestone_type=milestone_type_for(gap.category),
                action=action,
                linked_gap_ids=[gap.gap_id],
                measurable_outcome=outcome,
                evidence_to_create=evidence,
            )
        )
    return milestones


def _bridge_gap_ids(assessment: BridgeRoleAssessment, allowed_gap_ids: set[UUID]) -> list[UUID]:
    try:
        gap_ids = [UUID(value) for value in assessment.gaps_reduced]
    except (TypeError, ValueError) as error:
        raise PlanSynthesisValidationError(
            "bridge assessment contains an invalid gap reference"
        ) from error
    if not set(gap_ids).issubset(allowed_gap_ids):
        raise PlanSynthesisValidationError("bridge assessment contains an unknown gap reference")
    return gap_ids


def _path_milestones(
    path_type: PathType,
    role: RoleAssessment,
    bridges: Sequence[BridgeRoleAssessment],
    timeline: TimelineAssessment,
) -> list[PlanMilestone]:
    foundation_end, bridge_end, total = phase_boundaries(timeline.requested_months, path_type)
    material = [item for item in role.gaps if item.severity.value != "LOW" or item.hard_blocker]
    if path_type is PathType.DIRECT:
        selected = material[:5]
        milestones = _gap_milestones(selected, phase="Evidence closure", month_end=foundation_end)
        dependencies = [str(item.milestone_id) for item in milestones]
        milestones.append(
            PlanMilestone(
                phase="Application readiness",
                month_start=foundation_end if dependencies else 0,
                month_end=total,
                milestone_type=MilestoneType.APPLICATION_READINESS,
                action=(
                    f"Begin selective applications for {role.target_role} using confirmed evidence."
                ),
                measurable_outcome=(
                    "A role-specific evidence package is used for selective applications."
                ),
                evidence_to_create=["Role-specific evidence summary"],
                dependencies=dependencies,
            )
        )
        return milestones
    if path_type is PathType.NO_CREDIBLE_PATH:
        prerequisites = [item for item in role.gaps if item.hard_blocker] or material
        return _gap_milestones(
            prerequisites,
            phase="Prerequisite resolution",
            month_end=total,
        )
    if path_type is PathType.EXPLORATION:
        return [
            PlanMilestone(
                phase="Evidence clarification",
                month_start=0,
                month_end=total,
                milestone_type=MilestoneType.REASSESSMENT,
                action="Gather the missing candidate or market evidence before selecting a path.",
                measurable_outcome=(
                    "The unresolved evidence areas are documented and the target path is "
                    "reassessed."
                ),
                evidence_to_create=["Updated evidence inventory", "Refreshed path assessment"],
            )
        ]

    if path_type is PathType.DEVELOPMENT:
        selected = material[:_MATERIAL_GAP_LIMIT]
        milestones = _gap_milestones(
            selected,
            phase="Capability and maturity development",
            month_end=foundation_end,
        )
        milestones.append(
            PlanMilestone(
                phase="Target-role reassessment",
                month_start=foundation_end,
                month_end=total,
                milestone_type=MilestoneType.REASSESSMENT,
                action=(
                    f"Reassess {role.target_role} readiness after building the required evidence."
                ),
                linked_gap_ids=[item.gap_id for item in selected],
                measurable_outcome=(
                    "A refreshed assessment determines whether selective applications are "
                    "supported."
                ),
                evidence_to_create=["Updated target-role readiness assessment"],
                dependencies=[str(item.milestone_id) for item in milestones],
            )
        )
        return milestones

    milestones = _gap_milestones(
        material, phase="Common evidence foundation", month_end=foundation_end
    )
    foundation_dependencies = [str(item.milestone_id) for item in milestones]
    allowed_gap_ids = {item.gap_id for item in role.gaps}
    selected_bridges = [item for item in bridges if item.bridge_role][:3]
    for assessment in selected_bridges:
        linked = _bridge_gap_ids(assessment, allowed_gap_ids)
        capabilities = ", ".join(assessment.target_capabilities_gained) or "target evidence"
        milestones.append(
            PlanMilestone(
                phase=(
                    "Bridge-role readiness"
                    if path_type is PathType.BRIDGE
                    else "Supported bridge options"
                ),
                month_start=foundation_end,
                month_end=bridge_end,
                milestone_type=MilestoneType.EXPERIENCE,
                action=(
                    f"Evaluate and selectively pursue the observed {assessment.bridge_role} path."
                ),
                linked_gap_ids=linked,
                measurable_outcome=(
                    f"Readiness evidence for {assessment.bridge_role} demonstrates {capabilities}."
                ),
                evidence_to_create=list(assessment.target_capabilities_gained),
                dependencies=foundation_dependencies,
            )
        )
    milestones.append(
        PlanMilestone(
            phase="Target-role readiness",
            month_start=bridge_end,
            month_end=total,
            milestone_type=MilestoneType.REASSESSMENT,
            action=(
                f"Reassess {role.target_role} readiness using the evidence created along the path."
            ),
            linked_gap_ids=[item.gap_id for item in material[:_MATERIAL_GAP_LIMIT]],
            measurable_outcome=(
                "A refreshed gap and market assessment supports the next application decision."
            ),
            evidence_to_create=["Updated target-role readiness assessment"],
            dependencies=[str(item.milestone_id) for item in milestones],
        )
    )
    return milestones


def _risks(
    role: RoleAssessment,
    bridge_outcome: BridgeOutcome,
    timeline: TimelineAssessment,
) -> list[str]:
    risks = [
        f"The prerequisite for {item.target_expectation} remains unresolved."
        for item in role.gaps
        if item.hard_blocker
    ]
    if bridge_outcome in {
        BridgeOutcome.RECOMMENDED_BRIDGE,
        BridgeOutcome.MULTIPLE_PLAUSIBLE_BRIDGES,
    }:
        risks.append("Observed bridge-role availability may remain limited.")
    if timeline.classification in {
        TimelineClassification.AGGRESSIVE_BUT_PLAUSIBLE,
        TimelineClassification.UNLIKELY_WITHOUT_INTERMEDIATE_ROLE,
    }:
        risks.append(
            "The requested timeline depends on producing the required evidence in sequence."
        )
    risks.extend(
        f"Evidence for {item.target_expectation} remains incomplete."
        for item in role.gaps
        if item.severity.value in {"HIGH", "BLOCKING"}
    )
    risks.extend(f"Market dependency: {item}" for item in timeline.market_dependencies)
    return _unique(risks)[:8]


def _assumptions(goal: CareerGoal, timeline: TimelineAssessment) -> list[str]:
    assumptions = list(timeline.assumptions)
    if goal.target_location:
        assumptions.append(f"The target location remains {goal.target_location}.")
    if goal.preferred_work_modes:
        assumptions.append(f"Work-mode preferences remain: {', '.join(goal.preferred_work_modes)}.")
    if goal.bridge_role_willingness is not None:
        willingness = "open to" if goal.bridge_role_willingness else "not pursuing"
        assumptions.append(f"The user remains {willingness} an intermediate role.")
    return _unique(assumptions)[:8]


def _validate_plan_traceability(plan: CareerPlan, role: RoleAssessment) -> None:
    gap_ids = {item.gap_id for item in role.gaps}
    milestone_ids = {str(item.milestone_id) for item in plan.milestones}
    for milestone in plan.milestones:
        if not set(milestone.linked_gap_ids).issubset(gap_ids):
            raise PlanSynthesisValidationError("milestone contains an unknown gap reference")
        if not set(milestone.dependencies).issubset(milestone_ids):
            raise PlanSynthesisValidationError("milestone contains an unknown dependency")
        if str(milestone.milestone_id) in milestone.dependencies:
            raise PlanSynthesisValidationError("milestone cannot depend on itself")
        if timeline := plan.timeline_assessment:
            if (
                timeline.requested_months is not None
                and milestone.month_end > timeline.requested_months
            ):
                raise PlanSynthesisValidationError("milestone exceeds the requested timeline")


def _apply_model_wording(
    plan: CareerPlan, role: RoleAssessment, gateway: ModelGateway
) -> CareerPlan:
    response = gateway.generate_structured(
        role=ModelRole.REASONING,
        output_schema=CareerPlanDraftOutput,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=build_plan_prompt(plan),
        temperature=0,
        max_tokens=2400,
        metadata={"task_type": "career_plan_wording", "prompt_version": PROMPT_VERSION},
    )
    draft = CareerPlanDraftOutput.model_validate(response.structured_output)
    expected_target = normalize_capability(plan.target_role or "")
    if normalize_capability(draft.target_role or "") != expected_target:
        raise PlanSynthesisValidationError("model changed the target role")
    expected_bridges = [item.bridge_role for item in plan.bridge_roles if item.bridge_role]
    if [normalize_capability(item) for item in draft.bridge_roles] != [
        normalize_capability(item) for item in expected_bridges
    ]:
        raise PlanSynthesisValidationError("model changed the supported bridge roles")
    if len(draft.milestones) != len(plan.milestones):
        raise PlanSynthesisValidationError("model changed the milestone count")

    by_key = {item.milestone_key: item for item in draft.milestones}
    expected_keys = {f"milestone-{index}" for index in range(len(plan.milestones))}
    if set(by_key) != expected_keys:
        raise PlanSynthesisValidationError("model changed milestone keys")
    gaps = {item.gap_id: item for item in role.gaps}
    updated = []
    credential_supported = any(
        item.category is GapCategory.CREDENTIAL_PREREQUISITE for item in role.gaps
    )
    for index, original in enumerate(plan.milestones):
        proposal = by_key[f"milestone-{index}"]
        if (
            proposal.phase != original.phase
            or proposal.milestone_type is not original.milestone_type
            or proposal.linked_gap_ids != original.linked_gap_ids
            or proposal.evidence_to_create != original.evidence_to_create
            or proposal.dependencies != original.dependencies
        ):
            raise PlanSynthesisValidationError("model changed milestone traceability")
        if (
            len(original.linked_gap_ids) == 1
            and original.milestone_type is not MilestoneType.REASSESSMENT
        ):
            anchor = normalize_capability(gaps[original.linked_gap_ids[0]].target_expectation)
            wording = normalize_capability(f"{proposal.action} {proposal.measurable_outcome}")
            if anchor not in wording:
                raise PlanSynthesisValidationError("model removed the supported capability anchor")
        original_tokens = set(
            normalize_capability(f"{original.action} {original.measurable_outcome}").split()
        )
        proposed_tokens = set(
            normalize_capability(f"{proposal.action} {proposal.measurable_outcome}").split()
        )
        if not proposed_tokens.issubset(original_tokens | _SAFE_WORDING_TOKENS):
            raise PlanSynthesisValidationError("model introduced unsupported plan content")
        credential_words = {"certification", "certificate", "credential"}
        if not credential_supported and credential_words & set(
            normalize_capability(proposal.action).split()
        ):
            raise PlanSynthesisValidationError("model introduced an unsupported credential")
        updated.append(
            original.model_copy(
                update={
                    "action": proposal.action,
                    "measurable_outcome": proposal.measurable_outcome,
                }
            )
        )
    if draft.risks != plan.risks or draft.assumptions != plan.assumptions:
        raise PlanSynthesisValidationError("model changed grounded risks or assumptions")
    return plan.model_copy(update={"milestones": updated})


def generate_career_plan(
    profile: CandidateProfile,
    goal: CareerGoal,
    role_assessment: RoleAssessment,
    bridge_assessments: list[BridgeRoleAssessment],
    bridge_outcome: BridgeOutcome,
    timeline_assessment: TimelineAssessment,
    model_gateway: ModelGateway | None = None,
    *,
    market_confidence: ConfidenceLevel | None = None,
    source_ids: list[UUID] | None = None,
    synthesis: CareerAssessmentSynthesis | None = None,
) -> CareerPlanGenerationResult:
    """Create a draft plan and optionally refine wording through the model gateway."""

    if synthesis is not None:
        gaps_by_id = {item.gap_id: item for item in role_assessment.gaps}
        ordered_gap_ids = [
            gap_id for group in synthesis.grouped_gaps for gap_id in group.underlying_gap_ids
        ]
        ordered_gaps = [gaps_by_id[value] for value in ordered_gap_ids if value in gaps_by_id]
        ordered_gaps.extend(
            item for item in role_assessment.gaps if item.gap_id not in set(ordered_gap_ids)
        )
        role_assessment = role_assessment.model_copy(
            update={
                "gaps": ordered_gaps,
                "candidate_accessibility": synthesis.accessibility,
                "explanation": synthesis.accessibility_rationale,
                "confidence": synthesis.confidence,
            }
        )

    logger.info(
        "plan_generation_started bridge_outcome=%s timeline_classification=%s model_role=%s",
        bridge_outcome,
        timeline_assessment.classification,
        ModelRole.REASONING.value if model_gateway else "none",
    )
    path_type = select_path_type(role_assessment, bridge_outcome, timeline_assessment)
    usable_bridges = [item for item in bridge_assessments if item.bridge_role]
    if path_type is PathType.BRIDGE and len(usable_bridges) != 1:
        raise PlanSynthesisValidationError("a bridge plan requires one supported bridge role")
    if path_type is PathType.MULTIPLE_PATHS and not 2 <= len(usable_bridges) <= 3:
        raise PlanSynthesisValidationError("multiple paths require two or three bridge roles")
    selected_bridges = (
        usable_bridges if path_type in {PathType.BRIDGE, PathType.MULTIPLE_PATHS} else []
    )
    bridge_confidence = (
        lowest_confidence(*(item.confidence for item in selected_bridges))
        if selected_bridges
        else None
    )
    confidence = lowest_confidence(
        role_assessment.confidence,
        timeline_assessment.confidence,
        bridge_confidence,
        market_confidence,
    )
    plan = CareerPlan(
        plan_version=1,
        plan_status=PlanStatus.DRAFT,
        path_type=path_type,
        current_role=_current_role(profile),
        target_role=goal.target_role or role_assessment.target_role,
        bridge_roles=selected_bridges,
        timeline_assessment=timeline_assessment,
        milestones=_path_milestones(
            path_type, role_assessment, selected_bridges, timeline_assessment
        ),
        risks=_risks(role_assessment, bridge_outcome, timeline_assessment),
        assumptions=_assumptions(goal, timeline_assessment),
        source_ids=list(dict.fromkeys([*role_assessment.source_ids, *(source_ids or [])])),
        confidence=confidence,
        approval_status=ApprovalStatus.DRAFT,
    )
    _validate_plan_traceability(plan, role_assessment)
    fallback_used = False
    limitations: list[str] = []
    if model_gateway is not None:
        try:
            plan = _apply_model_wording(plan, role_assessment, model_gateway)
        except (ModelGatewayError, PlanSynthesisValidationError, TypeError, ValueError):
            fallback_used = True
            limitations.append(
                "Optional wording synthesis was unavailable; the validated deterministic plan "
                "was retained."
            )
            confidence = lowest_confidence(plan.confidence, ConfidenceLevel.MODERATE)
            plan = plan.model_copy(update={"confidence": confidence})
    status = (
        PlanGenerationStatus.SUCCEEDED_WITH_FALLBACK
        if fallback_used
        else PlanGenerationStatus.SUCCEEDED
    )
    logger.info(
        "plan_generation_completed path_type=%s milestone_count=%d linked_gap_count=%d "
        "bridge_usage=%s fallback_used=%s confidence=%s",
        plan.path_type,
        len(plan.milestones),
        len({gap_id for item in plan.milestones for gap_id in item.linked_gap_ids}),
        bool(plan.bridge_roles),
        fallback_used,
        plan.confidence,
    )
    return CareerPlanGenerationResult(
        status=status,
        plan=plan,
        limitations=limitations,
        fallback_used=fallback_used,
    )
