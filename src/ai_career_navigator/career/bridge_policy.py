"""Explainable bridge-role decision and ordering policy."""

from ai_career_navigator.domain import CandidateAccessibility, GapItem, GapSeverity

MAX_BRIDGE_ROLES = 3
MATERIAL_SEVERITIES = {GapSeverity.MODERATE, GapSeverity.HIGH, GapSeverity.BLOCKING}


def bridge_evaluation_needed(accessibility: CandidateAccessibility, gaps: list[GapItem]) -> bool:
    if accessibility is CandidateAccessibility.APPLY_NOW:
        return False
    if accessibility is CandidateAccessibility.APPLY_SELECTIVELY:
        return any(item.severity in {GapSeverity.HIGH, GapSeverity.BLOCKING} for item in gaps)
    return accessibility in {
        CandidateAccessibility.NEAR_TERM_TARGET,
        CandidateAccessibility.ASPIRATIONAL,
        CandidateAccessibility.POOR_FIT,
    }


def material_gaps(gaps: list[GapItem]) -> list[GapItem]:
    return [item for item in gaps if item.severity in MATERIAL_SEVERITIES]
