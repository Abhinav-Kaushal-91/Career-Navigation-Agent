"""Observed-market bridge-role assessment without invented titles or demand."""

import logging
from dataclasses import dataclass

from ai_career_navigator.domain import (
    BridgeOutcome,
    BridgeRoleAssessment,
    CandidateAccessibility,
    CandidateProfile,
    CareerGoal,
    ConfidenceLevel,
    GapCategory,
    GapItem,
    RoleAssessment,
)
from ai_career_navigator.market import MarketRequirementAnalysis

from .bridge_policy import MAX_BRIDGE_ROLES, bridge_evaluation_needed, material_gaps
from .comparison import normalize_capability
from .path_schemas import BridgeAnalysisResult, BridgeAnalysisStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Candidate:
    title: str
    strength_overlap: tuple[str, ...]
    reduced_gaps: tuple[GapItem, ...]
    capabilities: tuple[str, ...]
    posting_count: int


def _seniority_level(title: str) -> int:
    """Return a conservative title-seniority band for bridge-order validation."""

    normalized = f" {normalize_capability(title)} "
    if any(term in normalized for term in (" chief ", " vice president ", " vp ")):
        return 6
    if any(term in normalized for term in (" director ", " head ")):
        return 5
    if " senior manager " in normalized:
        return 4
    if any(
        term in normalized for term in (" senior ", " manager ", " principal ", " staff ", " lead ")
    ):
        return 3
    if any(term in normalized for term in (" associate ", " intermediate ")):
        return 2
    if any(term in normalized for term in (" junior ", " entry ", " intern ")):
        return 1
    return 2


def _observed_candidates(
    profile: CandidateProfile,
    role: RoleAssessment,
    analysis: MarketRequirementAnalysis,
    observed_titles: list[str],
    excluded_titles: set[str],
    target_title: str,
) -> list[_Candidate]:
    evidence = {
        normalize_capability(item.capability): item.capability
        for item in profile.approved_evidence_items
    }
    material = material_gaps(role.gaps)
    candidates: list[_Candidate] = []
    normalized_target = normalize_capability(target_title)
    target_seniority = _seniority_level(target_title)
    for title in dict.fromkeys(observed_titles):
        normalized_title = normalize_capability(title)
        if (
            normalized_title in excluded_titles
            or normalized_title == normalized_target
            or _seniority_level(title) > target_seniority
        ):
            continue
        posting_ids = {
            item.posting_id
            for item in analysis.postings
            if normalize_capability(item.normalized_title or item.original_title)
            == normalized_title
        }
        requirements = [item for item in analysis.requirements if item.posting_id in posting_ids]
        capabilities = {
            normalize_capability(
                item.normalized_capability or item.requirement_text
            ): item.normalized_capability or item.requirement_text
            for item in requirements
        }
        reduced = tuple(
            gap for gap in material if normalize_capability(gap.target_expectation) in capabilities
        )
        if not reduced:
            continue
        overlap = tuple(evidence[key] for key in capabilities if key in evidence)
        reduced_capability_keys = {normalize_capability(gap.target_expectation) for gap in reduced}
        candidates.append(
            _Candidate(
                title=title,
                strength_overlap=overlap,
                reduced_gaps=reduced,
                capabilities=tuple(
                    capabilities[key] for key in capabilities if key in reduced_capability_keys
                ),
                posting_count=len(posting_ids),
            )
        )
    return sorted(
        candidates,
        key=lambda item: (
            -len(item.reduced_gaps),
            -len(item.strength_overlap),
            -item.posting_count,
            item.title.casefold(),
        ),
    )[:MAX_BRIDGE_ROLES]


def _sentinel(
    role: RoleAssessment,
    outcome: BridgeOutcome,
    explanation: str,
    confidence: ConfidenceLevel,
    blockers: list[str] | None = None,
) -> BridgeRoleAssessment:
    return BridgeRoleAssessment(
        bridge_role=None,
        candidate_accessibility=role.candidate_accessibility,
        outcome=outcome,
        explanation=explanation,
        confidence=confidence,
        blockers=blockers or [],
    )


def assess_bridge_roles(
    profile: CandidateProfile,
    goal: CareerGoal,
    role: RoleAssessment,
    market_analysis: MarketRequirementAnalysis,
    observed_related_titles: list[str],
) -> BridgeAnalysisResult:
    """Evaluate only bridge titles already observed in retained market evidence."""

    if role.candidate_accessibility is CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE:
        assessment = _sentinel(
            role,
            BridgeOutcome.INSUFFICIENT_EVIDENCE,
            "Available evidence is insufficient to evaluate an intermediate role.",
            ConfidenceLevel.INSUFFICIENT,
        )
        return BridgeAnalysisResult(
            status=BridgeAnalysisStatus.INSUFFICIENT,
            outcome=BridgeOutcome.INSUFFICIENT_EVIDENCE,
            assessments=[assessment],
            limitations=["Bridge usefulness could not be assessed responsibly."],
        )
    if not bridge_evaluation_needed(role.candidate_accessibility, role.gaps):
        assessment = _sentinel(
            role,
            BridgeOutcome.NO_BRIDGE_REQUIRED,
            "Current accessibility and gap severity do not justify an intermediate role.",
            role.confidence,
        )
        return BridgeAnalysisResult(
            status=BridgeAnalysisStatus.NOT_REQUIRED,
            outcome=BridgeOutcome.NO_BRIDGE_REQUIRED,
            assessments=[assessment],
        )

    hard = [item for item in role.gaps if item.hard_blocker]
    excluded_titles = {normalize_capability(item) for item in goal.exclusions if item.strip()}
    candidates = _observed_candidates(
        profile,
        role,
        market_analysis,
        observed_related_titles,
        excluded_titles,
        goal.target_role or role.target_role,
    )
    bridge_would_help = bool(candidates)
    if hard:
        assessment = _sentinel(
            role,
            BridgeOutcome.NO_VALID_BRIDGE_ROLE,
            "An intermediate role does not resolve the confirmed non-substitutable prerequisite.",
            role.confidence,
            [str(item.gap_id) for item in hard],
        )
        return BridgeAnalysisResult(
            status=BridgeAnalysisStatus.LIMITED,
            outcome=BridgeOutcome.NO_VALID_BRIDGE_ROLE,
            assessments=[assessment],
            bridge_would_help=bridge_would_help,
            limitations=["A hard prerequisite must be resolved directly."],
        )
    if goal.bridge_role_willingness is False:
        assessment = _sentinel(
            role,
            BridgeOutcome.NO_VALID_BRIDGE_ROLE,
            "A bridge could improve readiness, but the user declined an intermediate role.",
            role.confidence,
        )
        return BridgeAnalysisResult(
            status=BridgeAnalysisStatus.LIMITED,
            outcome=BridgeOutcome.NO_VALID_BRIDGE_ROLE,
            assessments=[assessment],
            bridge_would_help=bridge_would_help,
            limitations=["Bridge-role willingness is set to no."],
        )
    if not candidates:
        assessment = _sentinel(
            role,
            BridgeOutcome.NO_VALID_BRIDGE_ROLE,
            "No observed related role was shown to reduce the material gap set.",
            ConfidenceLevel.LOW,
        )
        return BridgeAnalysisResult(
            status=BridgeAnalysisStatus.LIMITED,
            outcome=BridgeOutcome.NO_VALID_BRIDGE_ROLE,
            assessments=[assessment],
            limitations=["Observed related-role evidence did not support a useful bridge."],
        )

    outcome = (
        BridgeOutcome.RECOMMENDED_BRIDGE
        if len(candidates) == 1
        else BridgeOutcome.MULTIPLE_PLAUSIBLE_BRIDGES
    )
    assessments = []
    for candidate in candidates:
        gap_categories = {item.category for item in candidate.reduced_gaps}
        evidence_value = (
            "HIGH"
            if gap_categories & {GapCategory.EVIDENCE, GapCategory.EXPERIENCE}
            else "MODERATE"
        )
        leadership_gain = "HIGH" if GapCategory.LEADERSHIP_SCOPE in gap_categories else "LOW"
        assessments.append(
            BridgeRoleAssessment(
                bridge_role=candidate.title,
                current_strength_overlap=list(candidate.strength_overlap),
                gaps_reduced=[str(item.gap_id) for item in candidate.reduced_gaps],
                target_capabilities_gained=list(candidate.capabilities),
                market_availability_summary=(
                    f"Observed in {candidate.posting_count} validated related-title posting(s)."
                ),
                candidate_accessibility=(
                    CandidateAccessibility.APPLY_SELECTIVELY
                    if candidate.strength_overlap
                    else CandidateAccessibility.NEAR_TERM_TARGET
                ),
                evidence_building_value=evidence_value,
                leadership_scope_gain=leadership_gain,
                user_constraint_fit="MODERATE",
                outcome=outcome,
                explanation=(
                    f"Uses {len(candidate.strength_overlap)} confirmed strength(s) and may reduce "
                    f"{len(candidate.reduced_gaps)} material gap(s)."
                ),
                confidence=ConfidenceLevel.MODERATE,
            )
        )
    logger.info(
        "bridge_analysis_completed candidate_count=%d bridge_outcome=%s gap_reduction_count=%d",
        len(candidates),
        outcome,
        sum(len(item.gaps_reduced) for item in assessments),
    )
    return BridgeAnalysisResult(
        status=BridgeAnalysisStatus.SUCCEEDED,
        outcome=outcome,
        assessments=assessments,
        bridge_would_help=True,
    )
