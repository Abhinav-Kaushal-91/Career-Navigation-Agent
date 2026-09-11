"""Qualitative timeline assessment without fake precision."""

import logging

from ai_career_navigator.domain import (
    ApprovalStatus,
    BridgeOutcome,
    CandidateAccessibility,
    CareerGoal,
    ConfidenceLevel,
    CurrentMarketSnapshot,
    GapSeverity,
    RoleAssessment,
    TimelineAssessment,
    TimelineClassification,
)

from .path_schemas import (
    BridgeAnalysisResult,
    TimelineAnalysisResult,
    TimelineAnalysisStatus,
)

logger = logging.getLogger(__name__)


def _unsupported(
    goal: CareerGoal,
    role: RoleAssessment,
    reason: str,
) -> TimelineAnalysisResult:
    assessment = TimelineAssessment(
        requested_months=goal.target_timeline_months,
        classification=TimelineClassification.UNSUPPORTED_INSUFFICIENT_EVIDENCE,
        blocking_gap_ids=[item.gap_id for item in role.gaps if item.hard_blocker],
        confidence=ConfidenceLevel.INSUFFICIENT,
        evidence_limitations=[reason],
    )
    return TimelineAnalysisResult(
        status=TimelineAnalysisStatus.INSUFFICIENT,
        assessment=assessment,
        limitations=[reason],
    )


def assess_timeline(
    goal: CareerGoal,
    role: RoleAssessment,
    bridge: BridgeAnalysisResult,
    snapshot: CurrentMarketSnapshot,
) -> TimelineAnalysisResult:
    """Classify a requested timeline from accessibility and path constraints."""

    months = goal.target_timeline_months
    if (
        months is not None
        and role.candidate_accessibility is CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE
    ):
        return _unsupported(goal, role, "Candidate evidence is insufficient for timeline analysis.")
    hard = [item for item in role.gaps if item.hard_blocker]
    if hard and months is not None:
        return _unsupported(
            goal,
            role,
            "A hard prerequisite has no evidence-supported completion duration.",
        )

    material = [
        item
        for item in role.gaps
        if item.severity in {GapSeverity.MODERATE, GapSeverity.HIGH, GapSeverity.BLOCKING}
    ]
    milestones = list(
        dict.fromkeys(
            item.evidence_needed or f"Resolve {item.target_expectation}" for item in material
        )
    )[:5]
    dependencies = ["Continued availability of relevant target-role openings."]
    if bridge.outcome in {
        BridgeOutcome.RECOMMENDED_BRIDGE,
        BridgeOutcome.MULTIPLE_PLAUSIBLE_BRIDGES,
    }:
        dependencies.append("Sufficient availability of the observed bridge role.")
    if goal.target_location or goal.preferred_work_modes:
        dependencies.append(
            "Openings compatible with the user's location and work-mode constraints."
        )
    dependencies.append("Target-role requirements remain materially similar to the current sample.")
    confidence = (
        ConfidenceLevel.MODERATE
        if role.confidence in {ConfidenceLevel.HIGH, ConfidenceLevel.MODERATE}
        and snapshot.evidence_confidence in {ConfidenceLevel.HIGH, ConfidenceLevel.MODERATE}
        else ConfidenceLevel.LOW
    )
    if months is None:
        if goal.approval_status is not ApprovalStatus.APPROVED:
            return _unsupported(goal, role, "The timeline preference has not been confirmed.")
        assessment = TimelineAssessment(
            requested_months=None,
            classification=TimelineClassification.NO_FIXED_TIMELINE,
            assumptions=[
                "The candidate can pursue the identified evidence outcomes without a deadline.",
                "No unconfirmed prerequisite is treated as resolved.",
            ],
            required_milestones=milestones,
            bridge_role_required=bridge.bridge_would_help,
            market_dependencies=dependencies,
            confidence=confidence,
        )
        logger.info(
            "timeline_analysis_completed requested_months=none classification=%s confidence=%s",
            assessment.classification,
            assessment.confidence,
        )
        return TimelineAnalysisResult(
            status=TimelineAnalysisStatus.SUCCEEDED,
            assessment=assessment,
        )

    accessibility = role.candidate_accessibility
    if accessibility in {
        CandidateAccessibility.APPLY_NOW,
        CandidateAccessibility.APPLY_SELECTIVELY,
    }:
        classification = TimelineClassification.REALISTIC
    elif bridge.bridge_would_help and goal.bridge_role_willingness is False:
        classification = TimelineClassification.UNLIKELY_WITHOUT_INTERMEDIATE_ROLE
    elif accessibility is CandidateAccessibility.NEAR_TERM_TARGET:
        classification = (
            TimelineClassification.REALISTIC
            if months >= 18
            else TimelineClassification.AGGRESSIVE_BUT_PLAUSIBLE
        )
    elif accessibility is CandidateAccessibility.ASPIRATIONAL:
        classification = (
            TimelineClassification.AGGRESSIVE_BUT_PLAUSIBLE
            if months >= 24
            and bridge.outcome
            in {
                BridgeOutcome.RECOMMENDED_BRIDGE,
                BridgeOutcome.MULTIPLE_PLAUSIBLE_BRIDGES,
            }
            else TimelineClassification.UNLIKELY_WITHOUT_INTERMEDIATE_ROLE
        )
    else:
        classification = (
            TimelineClassification.UNLIKELY_WITHOUT_INTERMEDIATE_ROLE
            if bridge.bridge_would_help
            else TimelineClassification.UNSUPPORTED_INSUFFICIENT_EVIDENCE
        )

    limitations = []
    if classification is TimelineClassification.UNSUPPORTED_INSUFFICIENT_EVIDENCE:
        limitations.append("The available path evidence cannot support timeline realism.")
        status = TimelineAnalysisStatus.INSUFFICIENT
        confidence = ConfidenceLevel.INSUFFICIENT
    else:
        status = TimelineAnalysisStatus.SUCCEEDED
    assessment = TimelineAssessment(
        requested_months=months,
        classification=classification,
        assumptions=[
            "The candidate can pursue the identified evidence outcomes.",
            "No unconfirmed prerequisite is treated as resolved.",
        ],
        blocking_gap_ids=[item.gap_id for item in hard],
        required_milestones=milestones,
        bridge_role_required=(
            classification is TimelineClassification.UNLIKELY_WITHOUT_INTERMEDIATE_ROLE
        ),
        market_dependencies=dependencies,
        confidence=confidence,
        evidence_limitations=limitations,
    )
    logger.info(
        "timeline_analysis_completed requested_months=%d classification=%s confidence=%s",
        months,
        classification,
        confidence,
    )
    return TimelineAnalysisResult(
        status=status,
        assessment=assessment,
        limitations=limitations,
    )
