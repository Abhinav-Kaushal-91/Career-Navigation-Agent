"""Transparent path, milestone, timing, and confidence policies."""

from ai_career_navigator.domain import (
    BridgeOutcome,
    CandidateAccessibility,
    ConfidenceLevel,
    GapCategory,
    MilestoneType,
    PathType,
    RoleAssessment,
    TimelineAssessment,
    TimelineClassification,
)

_CONFIDENCE_ORDER = {
    ConfidenceLevel.INSUFFICIENT: 0,
    ConfidenceLevel.LOW: 1,
    ConfidenceLevel.MODERATE: 2,
    ConfidenceLevel.HIGH: 3,
}


def select_path_type(
    role: RoleAssessment,
    bridge_outcome: BridgeOutcome,
    timeline: TimelineAssessment,
) -> PathType:
    """Map approved upstream conclusions to one existing path type."""

    if role.candidate_accessibility is CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE:
        return PathType.EXPLORATION
    if role.candidate_accessibility in {
        CandidateAccessibility.APPLY_NOW,
        CandidateAccessibility.APPLY_SELECTIVELY,
    } and not any(item.hard_blocker for item in role.gaps):
        return PathType.DIRECT
    if bridge_outcome is BridgeOutcome.MULTIPLE_PLAUSIBLE_BRIDGES:
        return PathType.MULTIPLE_PATHS
    if bridge_outcome is BridgeOutcome.RECOMMENDED_BRIDGE:
        return PathType.BRIDGE
    if bridge_outcome is BridgeOutcome.NO_VALID_BRIDGE_ROLE and (
        any(item.hard_blocker for item in role.gaps)
        or role.candidate_accessibility is CandidateAccessibility.POOR_FIT
        or timeline.classification is TimelineClassification.UNLIKELY_WITHOUT_INTERMEDIATE_ROLE
    ):
        return PathType.NO_CREDIBLE_PATH
    if (
        role.candidate_accessibility is CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE
        or timeline.classification is TimelineClassification.UNSUPPORTED_INSUFFICIENT_EVIDENCE
    ):
        return PathType.EXPLORATION
    if role.candidate_accessibility is CandidateAccessibility.ASPIRATIONAL:
        return PathType.DEVELOPMENT
    return PathType.DIRECT


def milestone_type_for(category: GapCategory) -> MilestoneType:
    return {
        GapCategory.SKILL: MilestoneType.SKILL,
        GapCategory.EXPERIENCE: MilestoneType.EXPERIENCE,
        GapCategory.LEADERSHIP_SCOPE: MilestoneType.LEADERSHIP_SCOPE,
        GapCategory.EVIDENCE: MilestoneType.EVIDENCE,
        GapCategory.CREDENTIAL_PREREQUISITE: MilestoneType.EVIDENCE,
    }[category]


def phase_boundaries(months: int | None, path_type: PathType) -> tuple[int, int, int]:
    """Keep ordered steps until an evidence-based duration estimate exists.

    Requested months are a preference, not an estimate of how long actions need.
    Zero bounds are the existing storage representation for an untimed action;
    presentation must use ordinal steps, never display a zero-month forecast.
    """

    return 0, 0, 0


def lowest_confidence(*values: ConfidenceLevel | None) -> ConfidenceLevel:
    available = [item for item in values if item is not None]
    return min(available, key=_CONFIDENCE_ORDER.get) if available else ConfidenceLevel.INSUFFICIENT
