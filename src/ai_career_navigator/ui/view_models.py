"""Presentation-only mappings from validated workflow objects to concise UI data."""

import re
from dataclasses import dataclass
from typing import Any

from ai_career_navigator.career.bridge_policy import material_gaps as policy_material_gaps
from ai_career_navigator.career.gap_policy import frequency_band
from ai_career_navigator.domain import (
    ConfidenceLevel,
    EmployerDiversity,
    EvidenceConfirmationStatus,
    GapSeverity,
    MarketConcentration,
    PathType,
    PlanStatus,
    TimelineClassification,
)

_LABELS = {
    "APPLY_NOW": "Apply now",
    "APPLY_SELECTIVELY": "Apply selectively",
    "NEAR_TERM_TARGET": "Near-term target",
    "ASPIRATIONAL": "Aspirational",
    "POOR_FIT": "Limited fit",
    "INSUFFICIENT_CANDIDATE_EVIDENCE": "Not enough candidate evidence",
    "INSUFFICIENT_EVIDENCE": "Not enough evidence",
    "AGGRESSIVE_BUT_PLAUSIBLE": "Aggressive but plausible",
    "NO_FIXED_TIMELINE": "No fixed timeline",
    "UNLIKELY_WITHOUT_INTERMEDIATE_ROLE": "Unlikely without an intermediate role",
    "UNSUPPORTED_INSUFFICIENT_EVIDENCE": "Timeline not yet supported",
    "DIRECT": "Direct selective transition",
    "BRIDGE": "Bridge route",
    "EXPLORATION": "Exploration",
    "MULTIPLE_PATHS": "Multiple supported paths",
    "NO_CREDIBLE_PATH": "No credible path yet",
    "LEADERSHIP_SCOPE": "Leadership scope",
    "CREDENTIAL_PREREQUISITE": "Credential prerequisite",
    "DIRECT_MATCH": "Direct match",
    "TRANSFERABLE_MATCH": "Transferable",
    "PARTIAL_MATCH": "Partial",
    "NO_CONFIRMED_MATCH": "No confirmed match",
}
_SENSITIVE_LIMITATION = re.compile(
    r"\b(salary|pay range|compensation|benefits?|bonus(?:es)?|stock|discount|purchase plan)\b",
    re.IGNORECASE,
)
_REJECTION_DIAGNOSTIC = re.compile(
    r"\brejected\s+\d+\s+.*(?:metadata|non-canonical|responsibilit)", re.IGNORECASE
)
_PROVIDER_DIAGNOSTIC = re.compile(
    r"\b(?:provider|schema|validation)\b.*\b(?:error|failed|invalid|missing field)\b",
    re.IGNORECASE,
)


def product_label(value: object) -> str:
    """Translate enum-backed implementation language into product language."""

    raw = str(getattr(value, "value", value))
    return _LABELS.get(raw, raw.replace("_", " ").capitalize())


def user_facing_limitations(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Remove source fragments and collapse internal diagnostics into useful statements."""

    retained: list[str] = []
    excluded_requirement_content = False
    excluded_provider_diagnostic = False
    for value in values:
        text = " ".join(str(value).split())
        if not text or _SENSITIVE_LIMITATION.search(text):
            continue
        if _REJECTION_DIAGNOSTIC.search(text):
            excluded_requirement_content = True
            continue
        if _PROVIDER_DIAGNOSTIC.search(text):
            excluded_provider_diagnostic = True
            continue
        if len(text) > 220:
            continue
        retained.append(text)
    if excluded_requirement_content:
        retained.append(
            "Some posting content was excluded because it did not describe candidate requirements."
        )
    if excluded_provider_diagnostic:
        retained.append("Some source records could not be validated for this bounded sample.")
    return tuple(dict.fromkeys(retained))


@dataclass(frozen=True)
class RequirementRow:
    name: str
    category: str
    frequency: float
    occurrences: int
    sample_size: int
    frequency_label: str


@dataclass(frozen=True)
class RequirementTheme:
    name: str
    requirements: tuple[str, ...]


@dataclass(frozen=True)
class MarketDimension:
    name: str
    value: str
    evidence: str


@dataclass(frozen=True)
class MarketViewModel:
    target_role: str
    geography: str
    search_date: str
    validated_postings: int
    exact_target_postings: int
    target_variant_postings: int
    related_title_postings: int
    expanded_market_postings: int
    distinct_employers: int
    availability: str
    availability_count: str
    confidence: str
    confidence_count: str
    requirements: tuple[RequirementRow, ...]
    analyzed_postings: int
    primary_analyzed_postings: int
    requirement_sample_confidence: str
    title_mix: tuple[tuple[str, int], ...]
    employer_counts: tuple[tuple[str, int], ...]
    known_employers: int
    top_three_share: float | None
    concentration: str
    concentration_interpretation: str
    related_titles: tuple[str, ...]
    target_variant_titles: tuple[str, ...]
    limitations: tuple[str, ...]
    dimensions: tuple[MarketDimension, ...]
    title_consistency: str
    title_conclusion: str
    employer_diversity: str
    employer_conclusion: str
    geography_spread: str
    geography_summary: str
    geography_counts: tuple[tuple[str, int], ...]
    canada_wide_postings: int
    remote_or_hybrid_postings: int
    requirement_themes: tuple[RequirementTheme, ...]
    market_takeaways: tuple[tuple[str, str], ...]
    what_this_means: str


def _title_consistency(exact: int, variants: int, related: int) -> tuple[str, str]:
    total = exact + variants + related
    if not total:
        return "Limited evidence", "There are no validated posting titles to interpret."
    exact_share = exact / total
    close_share = (exact + variants) / total
    if exact_share >= 0.70:
        return "High consistency", "Most validated postings use the exact target title."
    if close_share >= 0.50:
        return "Moderate variation", "The target title and close variants both appear regularly."
    return "Low consistency", "Most relevant postings use adjacent or alternative titles."


def _employer_diversity(snapshot: Any, top_share: float | None) -> tuple[str, str]:
    if (
        snapshot.employer_diversity is EmployerDiversity.INSUFFICIENT_EVIDENCE
        or snapshot.market_concentration is MarketConcentration.INSUFFICIENT_EVIDENCE
    ):
        return "Limited evidence", "There is not enough employer evidence to assess concentration."
    if (
        snapshot.employer_diversity is EmployerDiversity.HIGH
        and snapshot.market_concentration is MarketConcentration.LOW
    ):
        return (
            "Broadly distributed",
            "Observed hiring is not dominated by a small number of employers.",
        )
    if (
        snapshot.employer_diversity is EmployerDiversity.LOW
        or snapshot.market_concentration is MarketConcentration.HIGH
    ):
        return (
            "Concentrated",
            "A small number of employers account for most observed demand.",
        )
    percentage = round((top_share or 0) * 100)
    return (
        "Moderately concentrated",
        f"The top three employers account for {percentage}% of known-employer postings.",
    )


def _region(location: str) -> str:
    text = location.casefold()
    if "remote" in text:
        return "Remote"
    if text.strip() in {"canada", "canada-wide", "national", "nationwide"}:
        return "Canada-wide"
    regions = (
        ("Ontario", ("ontario", "toronto", "ottawa", "mississauga", "burlington", " on")),
        ("British Columbia", ("british columbia", "vancouver", "burnaby", " bc")),
        ("Alberta", ("alberta", "calgary", "edmonton", " ab")),
        ("Quebec", ("quebec", "québec", "montreal", " qc")),
        ("Manitoba", ("manitoba", "winnipeg", " mb")),
        ("Saskatchewan", ("saskatchewan", "regina", "saskatoon", " sk")),
        ("Atlantic Canada", ("nova scotia", "new brunswick", "newfoundland", "pei")),
    )
    padded = f" {text}"
    for name, markers in regions:
        if any(marker in padded for marker in markers):
            return name
    return location


def _geography_view(
    location_counts: dict[str, int],
) -> tuple[str, str, tuple[tuple[str, int], ...]]:
    grouped: dict[str, int] = {}
    for location, count in location_counts.items():
        region = _region(location)
        grouped[region] = grouped.get(region, 0) + count
    ranked = tuple(sorted(grouped.items(), key=lambda item: (-item[1], item[0])))
    total = sum(grouped.values())
    remote_share = grouped.get("Remote", 0) / total if total else 0
    physical = [name for name in grouped if name not in {"Remote", "Canada-wide"}]
    if not ranked:
        return "Limited evidence", "Validated posting locations were not available.", ()
    if remote_share >= 0.5:
        label = "Remote-heavy"
    elif len(physical) >= 3 or "Canada-wide" in grouped:
        label = "Canada-wide"
    elif len(physical) == 1 and "Remote" not in grouped:
        label = "Regionally concentrated"
    else:
        label = "Mixed"
    leaders = ", ".join(name for name, _ in ranked[:3])
    return label, f"Observed demand appears across {leaders}.", ranked


def _market_theme(category: str) -> str:
    return {
        "TECHNICAL": "Technical / functional capability",
        "DOMAIN": "Domain expertise",
        "EXPERIENCE": "Experience / maturity",
        "EDUCATION": "Credentials / prerequisites",
        "CREDENTIAL": "Credentials / prerequisites",
        "LEADERSHIP": "Ownership / leadership",
        "SCOPE": "Ownership / leadership",
        "COMMUNICATION": "Communication / collaboration",
        "LANGUAGE": "Communication / collaboration",
        "WORK_AUTHORIZATION": "Credentials / prerequisites",
        "LOCATION": "Work-location conditions",
        "OTHER": "Other role requirements",
    }.get(category, "Other role requirements")


def _requirement_themes(requirements: tuple[RequirementRow, ...]) -> tuple[RequirementTheme, ...]:
    grouped: dict[str, list[str]] = {}
    for item in requirements:
        grouped.setdefault(_market_theme(item.category), []).append(item.name)
    return tuple(
        RequirementTheme(name, tuple(dict.fromkeys(items))) for name, items in grouped.items()
    )


def market_view_model(state: dict[str, Any]) -> MarketViewModel:
    snapshot = state["market_snapshot"]
    summary = state.get("requirement_summary")
    analyzed = summary.analyzed_posting_count if summary else 0
    primary_analyzed = (
        summary.exact_title_analyzed_count + summary.target_variant_analyzed_count if summary else 0
    )
    requirements = tuple(
        RequirementRow(
            name=item.normalized_capability,
            category=str(getattr(item.category, "value", item.category)),
            frequency=item.exact_and_variant_frequency or 0,
            occurrences=(item.exact_title_occurrence_count + item.target_variant_occurrence_count),
            sample_size=primary_analyzed,
            frequency_label=product_label(frequency_band(item.exact_and_variant_frequency or 0)),
        )
        for item in (summary.capability_requirements if summary else ())
        if item.exact_title_occurrence_count + item.target_variant_occurrence_count > 0
    )
    known = snapshot.known_employer_posting_count
    top_share = snapshot.top_three_employer_posting_count / known if known else None
    title_consistency, title_conclusion = _title_consistency(
        snapshot.exact_title_count,
        snapshot.target_variant_count,
        snapshot.related_title_count,
    )
    employer_diversity, employer_conclusion = _employer_diversity(snapshot, top_share)
    geography_spread, geography_summary, geography_counts = _geography_view(
        snapshot.location_posting_counts
    )
    concentration = product_label(snapshot.market_concentration)
    concentration_interpretation = {
        "Low": "Observed demand is spread across employers.",
        "Moderate": "Observed demand has some employer concentration.",
        "High": "Observed demand is concentrated among a small number of employers.",
    }.get(concentration, "There is not enough evidence to interpret employer concentration.")
    limitations = [*snapshot.limitations]
    if summary:
        limitations.extend(summary.limitations)
    limitations.extend(state.get("limitations", []))
    requirement_themes = _requirement_themes(requirements)
    availability = {
        "STRONG": "Strong",
        "MODERATE": "Moderate",
        "LIMITED": "Limited",
        "SPARSE": "Sparse",
        "INSUFFICIENT_EVIDENCE": "Sparse",
    }[str(getattr(snapshot.opportunity_availability, "value", snapshot.opportunity_availability))]
    confidence = (
        "Limited"
        if snapshot.evidence_confidence in {ConfidenceLevel.LOW, ConfidenceLevel.INSUFFICIENT}
        else product_label(snapshot.evidence_confidence)
    )
    dominant_theme = requirement_themes[0].name if requirement_themes else "Not available"
    exact_count = snapshot.exact_title_count
    variant_count = snapshot.target_variant_count
    related_count = snapshot.related_title_count
    expanded_count = exact_count + variant_count + related_count
    expanded_scope = related_count > 0
    availability_scope = (
        f"{availability} signal across the expanded target and related-title market"
        if expanded_scope
        else f"{availability} signal across exact-target and target-variant evidence"
    )
    secondary_context = (
        "Related titles form part of the expanded evidence and remain secondary context for "
        "candidate analysis."
        if related_count
        else "The evidence is limited to the exact target and its close title variants."
    )
    what_this_means = (
        f"The bounded market signal is {availability.casefold()}, with "
        f"{title_consistency.casefold()} across posting titles. {secondary_context}"
        if requirement_themes
        else (
            f"The bounded market signal is {availability.casefold()}, but requirement evidence "
            f"is not sufficient to identify a consistent employer theme. {secondary_context}"
        )
    )
    dimensions = (
        MarketDimension(
            "Opportunity availability",
            availability,
            f"{availability_scope}; {expanded_count} validated postings in the bounded sample",
        ),
        MarketDimension(
            "Employer diversity",
            employer_diversity,
            f"{snapshot.distinct_employer_count} employers across "
            f"{snapshot.validated_posting_count} validated postings",
        ),
        MarketDimension(
            "Title consistency",
            title_consistency,
            f"{exact_count} exact · {variant_count} variants · {related_count} related",
        ),
        MarketDimension("Geographic spread", geography_spread, geography_summary),
        MarketDimension(
            "Evidence confidence",
            confidence,
            f"{analyzed} successfully analyzed postings",
        ),
    )
    return MarketViewModel(
        target_role=snapshot.target_role,
        geography=snapshot.geography,
        search_date=snapshot.search_date.isoformat(),
        validated_postings=snapshot.validated_posting_count,
        exact_target_postings=exact_count,
        target_variant_postings=variant_count,
        related_title_postings=related_count,
        expanded_market_postings=expanded_count,
        distinct_employers=snapshot.distinct_employer_count,
        availability=availability,
        availability_count=f"{snapshot.validated_posting_count} validated postings",
        confidence=confidence,
        confidence_count=(
            f"{analyzed} successfully analyzed postings"
            if analyzed
            else "No successfully analyzed postings"
        ),
        requirements=requirements,
        analyzed_postings=analyzed,
        primary_analyzed_postings=primary_analyzed,
        requirement_sample_confidence=(
            "Directional"
            if primary_analyzed < 8
            else "Moderate"
            if primary_analyzed < 12
            else "Strong"
        ),
        title_mix=tuple(
            (label, count)
            for label, count in (
                ("Exact target", snapshot.exact_title_count),
                ("Target variants", snapshot.target_variant_count),
                ("Related titles", snapshot.related_title_count),
            )
        ),
        employer_counts=tuple(
            sorted(snapshot.employer_posting_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
        known_employers=known,
        top_three_share=top_share,
        concentration=concentration,
        concentration_interpretation=concentration_interpretation,
        related_titles=tuple(snapshot.related_titles),
        target_variant_titles=tuple(snapshot.target_variant_titles),
        limitations=user_facing_limitations(limitations),
        dimensions=dimensions,
        title_consistency=title_consistency,
        title_conclusion=title_conclusion,
        employer_diversity=employer_diversity,
        employer_conclusion=employer_conclusion,
        geography_spread=geography_spread,
        geography_summary=geography_summary,
        geography_counts=geography_counts,
        canada_wide_postings=dict(geography_counts).get("Canada-wide", 0),
        remote_or_hybrid_postings=sum(
            count
            for location, count in snapshot.location_posting_counts.items()
            if "remote" in location.casefold() or "hybrid" in location.casefold()
        ),
        requirement_themes=requirement_themes,
        market_takeaways=(
            ("Availability", availability),
            ("Title landscape", title_consistency),
            ("Employer spread", employer_diversity),
            ("Geography", geography_spread),
            ("Leading requirement theme", dominant_theme),
        ),
        what_this_means=what_this_means,
    )


@dataclass(frozen=True)
class StrengthView:
    capability: str
    match_type: str
    explanation: str
    evidence_details: tuple[str, ...]
    maturity: str
    confidence: str
    target_requirements: tuple[str, ...]


@dataclass(frozen=True)
class TransferView:
    experience: str
    translation: str
    explanation: str


@dataclass(frozen=True)
class TargetAlignmentView:
    experience: str
    target_requirement: str
    alignment: str
    what_you_have: str
    still_missing: str | None


@dataclass(frozen=True)
class ReadinessView:
    dimension: str
    assessment: str
    basis: str


@dataclass(frozen=True)
class GapGroupView:
    gap: str
    gap_ids: tuple[object, ...]
    severity: str
    market_importance: str
    underlying_requirement_count: int
    severe_requirement_count: int
    mandatory_requirement_count: int
    preferred_requirement_count: int
    affected_dimensions: tuple[str, ...]
    underlying_requirements: tuple[str, ...]
    what_you_have: str
    still_missing: str
    evidence_to_build: str


@dataclass(frozen=True)
class AnalysisViewModel:
    target_role: str
    verdict: str
    accessibility: str
    confidence: str
    direct_count: int
    transferable_count: int
    partial_count: int
    no_match_count: int
    unassessed_count: int
    total_requirements: int
    material_gap_count: int
    strongest_matches: tuple[StrengthView, ...]
    transferable_strengths: tuple[TransferView, ...]
    target_alignments: tuple[TargetAlignmentView, ...]
    coverage: tuple[tuple[str, int], ...]
    readiness_dimensions: tuple[ReadinessView, ...]
    grouped_gaps: tuple[GapGroupView, ...]
    assessment_reason: str
    what_this_means: str
    limitations: tuple[str, ...]


_ANALYSIS_ACCESSIBILITY_LABELS = {
    "APPLY_NOW": "Apply now",
    "APPLY_SELECTIVELY": "Apply selectively",
    "NEAR_TERM_TARGET": "Near-term target",
    "ASPIRATIONAL": "Aspirational target",
    "POOR_FIT": "Poor fit",
    "INSUFFICIENT_CANDIDATE_EVIDENCE": "Insufficient evidence",
}
_ANALYSIS_DIMENSION_LABELS = {
    "FUNCTION": "Function",
    "OWNERSHIP": "Ownership",
    "SCOPE": "Scope",
    "MATURITY": "Maturity / production delivery",
    "TECHNICAL_DEPTH": "Technical depth",
    "DOMAIN_DEPTH": "Domain depth",
    "PEOPLE_LEADERSHIP": "People leadership",
    "STRATEGIC_RESPONSIBILITY": "Strategic responsibility",
    "LIFECYCLE_RESPONSIBILITY": "Lifecycle responsibility",
    "METRICS_OUTCOME_OWNERSHIP": "Metrics and outcome ownership",
    "PREREQUISITE": "Prerequisite",
}
_TARGET_ALIGNMENT_LABELS = {
    "DIRECTLY_ALIGNED": "Directly aligned",
    "TRANSFERABLE": "Transferable",
    "PARTIALLY_ALIGNED": "Partially aligned",
}


def _short(value: str | None, limit: int = 180) -> str:
    text = " ".join((value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _analysis_accessibility_label(value: object) -> str:
    raw = str(getattr(value, "value", value))
    return _ANALYSIS_ACCESSIBILITY_LABELS.get(raw, product_label(value))


def _dimension_label(value: object) -> str:
    raw = str(getattr(value, "value", value))
    return _ANALYSIS_DIMENSION_LABELS.get(raw, product_label(value))


def _target_alignment_label(value: object) -> str:
    raw = str(getattr(value, "value", value))
    return _TARGET_ALIGNMENT_LABELS.get(raw, product_label(value))


def _bounded_sentences(*values: str, maximum: int = 3) -> str:
    sentences: list[str] = []
    for value in values:
        for sentence in re.split(r"(?<=[.!?])\s+", " ".join(value.split())):
            normalized = sentence.strip()
            if normalized and normalized not in sentences:
                sentences.append(normalized)
            if len(sentences) == maximum:
                return " ".join(sentences)
    return " ".join(sentences)


def _analysis_conclusion(summary: str, rationale: str) -> str:
    """Present the synthesis career story without repeating its separate rationale."""

    del rationale
    return _bounded_sentences(summary, maximum=3)


def analysis_view_model(state: dict[str, Any]) -> AnalysisViewModel:
    """Map the validated career synthesis to presentation without reinterpreting it."""

    role = state["role_assessment"]
    synthesis = state.get("career_assessment_synthesis")
    if synthesis is None:
        raise ValueError("Career assessment synthesis is required for the Analysis view")
    profile = state.get("confirmed_profile")
    evidence = {item.evidence_id: item for item in getattr(profile, "approved_evidence_items", ())}
    strength_views = tuple(
        StrengthView(
            capability=item.title,
            match_type=_target_alignment_label(item.alignment_type),
            explanation=_short(item.summary, 300),
            evidence_details=tuple(
                f"{evidence[evidence_id].capability}: {_short(evidence[evidence_id].description)}"
                for evidence_id in item.supporting_evidence_ids
                if evidence_id in evidence
            ),
            maturity=product_label(item.maturity),
            confidence=product_label(item.confidence),
            target_requirements=tuple(item.target_requirements),
        )
        for item in synthesis.demonstrated_strengths
    )
    transfer_views = tuple(
        TransferView(
            experience=item.source_capability,
            translation=item.target_application,
            explanation=_short(item.explanation, 300),
        )
        for item in synthesis.transferable_strengths
    )
    target_alignment_views = tuple(
        TargetAlignmentView(
            experience=item.candidate_capability,
            target_requirement=item.target_requirement,
            alignment=_target_alignment_label(item.alignment_type),
            what_you_have=item.what_candidate_has,
            still_missing=item.what_is_still_missing,
        )
        for item in synthesis.target_alignments
    )
    gap_groups = tuple(
        GapGroupView(
            gap=item.display_title,
            gap_ids=tuple(item.underlying_gap_ids),
            severity=product_label(item.severity),
            market_importance=product_label(item.requirement_frequency),
            underlying_requirement_count=item.underlying_gap_count,
            severe_requirement_count=item.high_or_blocking_gap_count,
            mandatory_requirement_count=item.mandatory_requirement_count,
            preferred_requirement_count=item.preferred_requirement_count,
            affected_dimensions=tuple(
                _dimension_label(value) for value in item.affected_dimensions
            ),
            underlying_requirements=tuple(item.underlying_requirement_names),
            what_you_have=item.what_candidate_already_has,
            still_missing=item.what_is_missing,
            evidence_to_build=item.evidence_to_build,
        )
        for item in synthesis.grouped_gaps
    )

    dimension_groups: dict[str, list[object]] = {}
    for gap in synthesis.grouped_gaps:
        for dimension in gap.affected_dimensions:
            dimension_groups.setdefault(_dimension_label(dimension), []).append(gap)
    readiness = tuple(
        ReadinessView(
            dimension=dimension,
            assessment=(
                "Evidence required"
                if any(item.severity in {GapSeverity.HIGH, GapSeverity.BLOCKING} for item in gaps)
                else "Developing"
            ),
            basis=(
                f"{len(gaps)} synthesized career-gap theme(s); "
                f"{sum(item.high_or_blocking_gap_count for item in gaps)} high or blocking "
                "underlying requirement(s)."
            ),
        )
        for dimension, gaps in dimension_groups.items()
    )

    analyzed = getattr(state.get("requirement_summary"), "analyzed_posting_count", 0)
    limitation_parts: list[str] = [
        f"Assessment is based on {analyzed} successfully analyzed posting(s)."
        if analyzed
        else "The analyzed-posting sample size is unavailable."
    ]
    if synthesis.insufficient_comparison_count:
        limitation_parts.append(
            f"{synthesis.insufficient_comparison_count} requirement(s) could not be compared "
            "reliably."
        )
    if any(
        str(getattr(item.comparison_scope, "value", item.comparison_scope))
        in {"RELATED_TITLE", "COMBINED_RELATED"}
        for item in role.requirement_comparisons
    ):
        limitation_parts.append("Related-title evidence was used only as secondary context.")
    if synthesis.confidence is ConfidenceLevel.MODERATE:
        limitation_parts.append("Some assessment evidence has moderate confidence.")
    limitation_parts.extend(user_facing_limitations(tuple(synthesis.limitations)))

    direct_count = synthesis.direct_match_count
    transferable_count = synthesis.transferable_match_count
    partial_count = synthesis.partial_match_count
    no_match_count = synthesis.no_confirmed_match_count
    insufficient_count = synthesis.insufficient_comparison_count
    total = direct_count + transferable_count + partial_count + no_match_count + insufficient_count
    return AnalysisViewModel(
        target_role=synthesis.target_role,
        verdict=_bounded_sentences(synthesis.assessment_summary, maximum=3),
        accessibility=_analysis_accessibility_label(synthesis.accessibility),
        confidence=product_label(synthesis.confidence),
        direct_count=direct_count,
        transferable_count=transferable_count,
        partial_count=partial_count,
        no_match_count=no_match_count,
        unassessed_count=insufficient_count,
        total_requirements=total,
        material_gap_count=len(gap_groups),
        strongest_matches=strength_views,
        transferable_strengths=transfer_views,
        target_alignments=target_alignment_views,
        coverage=tuple(
            (label, count)
            for label, count in (
                ("Direct", direct_count),
                ("Transferable", transferable_count),
                ("Partial", partial_count),
                ("No confirmed match", no_match_count),
                ("Insufficient", insufficient_count),
            )
        ),
        readiness_dimensions=readiness,
        grouped_gaps=gap_groups,
        assessment_reason=_bounded_sentences(synthesis.accessibility_rationale, maximum=3),
        what_this_means=_analysis_conclusion(
            synthesis.assessment_summary, synthesis.accessibility_rationale
        ),
        limitations=tuple(dict.fromkeys(limitation_parts)),
    )


@dataclass(frozen=True)
class PlanOptionViewModel:
    option_id: str
    title: str
    route: str
    duration: str
    evidence_items: int
    effort: str
    risk: str
    trade_off: str
    evidence_needed: tuple[str, ...]
    recommended: bool


@dataclass(frozen=True)
class PlanActionViewModel:
    action: str
    why: str
    evidence: str
    career_gap: str
    gap_ids: tuple[object, ...]


@dataclass(frozen=True)
class PlanStrengthViewModel:
    title: str
    explanation: str


@dataclass(frozen=True)
class PlanViewModel:
    current_role: str
    target_role: str
    accessibility: str
    recommended_path: str
    confidence: str
    bridge_role: str | None
    untimed: bool
    route: tuple[tuple[str, str], ...]
    actions: tuple[PlanActionViewModel, ...]
    strengths: tuple[PlanStrengthViewModel, ...]
    why_this_path: str
    what_this_means: str


@dataclass(frozen=True)
class PlanEligibility:
    can_approve: bool
    missing_actions: tuple[str, ...]


def plan_eligibility(plan: Any, role: Any | None, synthesis: Any | None = None) -> PlanEligibility:
    missing: list[str] = []
    if plan is None:
        missing.append("Run career analysis to create a plan")
        return PlanEligibility(False, tuple(missing))
    if not plan.current_role:
        missing.append("Complete the current-role information")
    if not plan.target_role:
        missing.append("Add a target role")
    if role is None:
        missing.append("Complete the candidate-to-market comparison")
    if synthesis is None:
        missing.append("Complete the career assessment synthesis")
    elif synthesis.confidence is ConfidenceLevel.INSUFFICIENT:
        missing.append("Resolve the insufficient career-assessment evidence")
    if plan.timeline_assessment is None:
        missing.append("Add and assess a target timeline")
    elif (
        plan.timeline_assessment.classification
        is TimelineClassification.UNSUPPORTED_INSUFFICIENT_EVIDENCE
    ):
        missing.append("Add evidence needed to assess the timeline")
    if plan.path_type in {PathType.EXPLORATION, PathType.NO_CREDIBLE_PATH}:
        missing.append("Resolve the evidence needed for a credible path")
    if plan.confidence is ConfidenceLevel.INSUFFICIENT:
        missing.append("Review missing candidate or market evidence")
    if not plan.milestones:
        missing.append("Re-run analysis to build an evidence-linked roadmap")
    if role is not None:
        known_gap_ids = {item.gap_id for item in role.gaps}
        linked_gap_ids = {
            gap_id for milestone in plan.milestones for gap_id in milestone.linked_gap_ids
        }
        if not linked_gap_ids.issubset(known_gap_ids):
            missing.append("Regenerate the plan because milestone evidence links are invalid")
        material_gap_ids = {
            item.gap_id
            for item in policy_material_gaps(list(role.gaps))
            if not synthesis or item.gap_id in set(synthesis.source_gap_ids)
        }
        if material_gap_ids and not linked_gap_ids:
            missing.append("Regenerate the plan with evidence-linked milestones")
        if any(item.hard_blocker for item in role.gaps):
            missing.append("Resolve the blocking prerequisite before plan approval")
    can_approve = plan.plan_status is PlanStatus.DRAFT and not missing
    return PlanEligibility(can_approve, tuple(dict.fromkeys(missing)))


def plan_options(plan: Any) -> tuple[PlanOptionViewModel, ...]:
    months = getattr(getattr(plan, "timeline_assessment", None), "requested_months", None)
    duration = f"{months} months" if months else "No fixed timeline"
    risk_by_confidence = {
        "High": "Lower",
        "Moderate": "Moderate",
        "Low": "High",
        "Insufficient": "Not assessable",
    }
    if plan.path_type is PathType.DIRECT:
        return (
            PlanOptionViewModel(
                option_id="direct",
                title="Direct route",
                route=" → ".join(filter(None, (plan.current_role, plan.target_role))),
                duration=duration,
                evidence_items=sum(len(item.evidence_to_create) for item in plan.milestones),
                effort="Evidence closure",
                risk=risk_by_confidence.get(product_label(plan.confidence), "Not assessable"),
                trade_off="Build the required evidence before applying selectively.",
                evidence_needed=tuple(
                    dict.fromkeys(
                        evidence for item in plan.milestones for evidence in item.evidence_to_create
                    )
                ),
                recommended=True,
            ),
        )
    if plan.path_type in {PathType.BRIDGE, PathType.MULTIPLE_PATHS}:
        options: list[PlanOptionViewModel] = []
        for index, bridge in enumerate(plan.bridge_roles):
            if not bridge.bridge_role:
                continue
            relevant = [
                item
                for item in plan.milestones
                if item.phase != "Supported bridge options"
                or bridge.bridge_role.casefold() in item.action.casefold()
            ]
            options.append(
                PlanOptionViewModel(
                    option_id=str(bridge.bridge_assessment_id),
                    title=f"Bridge via {bridge.bridge_role}",
                    route=" → ".join(
                        filter(None, (plan.current_role, bridge.bridge_role, plan.target_role))
                    ),
                    duration=duration,
                    evidence_items=sum(len(item.evidence_to_create) for item in relevant),
                    effort=product_label(bridge.evidence_building_value or "Not assessed"),
                    risk=risk_by_confidence.get(product_label(bridge.confidence), "Not assessable"),
                    trade_off=bridge.explanation,
                    evidence_needed=tuple(
                        dict.fromkeys(
                            evidence for item in relevant for evidence in item.evidence_to_create
                        )
                    ),
                    recommended=index == 0,
                )
            )
        return tuple(options)
    return ()


def plan_view_model(plan: Any, role: Any | None, synthesis: Any | None = None) -> PlanViewModel:
    """Present a deterministic plan grounded in synthesis and raw gap provenance."""

    current = plan.current_role or "Current role not confirmed"
    target = plan.target_role or "Target role not confirmed"
    bridge = next(
        (item.bridge_role for item in plan.bridge_roles if item.bridge_role),
        None,
    )
    route_items = [("CURRENT ROLE", current)]
    if bridge:
        route_items.append(("NEXT STEP / BRIDGE", bridge))
    route_items.append(("TARGET ROLE", target))

    if synthesis is None:
        raise ValueError("Career assessment synthesis is required for the Plan view")
    gap_lookup = {item.gap_id: item for item in getattr(role, "gaps", ())}
    milestone_evidence: dict[object, list[str]] = {}
    for milestone in plan.milestones:
        for gap_id in milestone.linked_gap_ids:
            milestone_evidence.setdefault(gap_id, []).extend(milestone.evidence_to_create)

    severity_rank = {"BLOCKING": 4, "HIGH": 3, "MODERATE": 2, "LOW": 1}
    frequency_rank = {"COMMON": 4, "FREQUENT": 3, "OCCASIONAL": 2, "RARE": 1}

    def priority(group: Any) -> tuple[int, int, int, int, int]:
        dimensions = {str(getattr(item, "value", item)) for item in group.affected_dimensions}
        independent = {
            str(getattr(item, "value", item)) for item in synthesis.independent_severe_dimensions
        }
        return (
            severity_rank.get(str(getattr(group.severity, "value", group.severity)), 0),
            int(bool(dimensions & independent)),
            group.mandatory_requirement_count,
            frequency_rank.get(
                str(getattr(group.requirement_frequency, "value", group.requirement_frequency)), 0
            ),
            int("PREREQUISITE" in dimensions),
        )

    actions: list[PlanActionViewModel] = []
    for group in sorted(synthesis.grouped_gaps, key=priority, reverse=True)[:5]:
        gap_ids = tuple(gap_id for gap_id in group.underlying_gap_ids if gap_id in gap_lookup)
        if not gap_ids:
            continue
        artifacts = tuple(
            dict.fromkeys(
                artifact
                for gap_id in gap_ids
                for artifact in milestone_evidence.get(gap_id, ())
                if artifact
            )
        )
        actions.append(
            PlanActionViewModel(
                action=group.evidence_to_build,
                why=group.what_is_missing,
                evidence="; ".join(artifacts) or group.evidence_to_build,
                career_gap=group.title,
                gap_ids=gap_ids,
            )
        )

    underlying_count = sum(item.underlying_gap_count for item in synthesis.grouped_gaps)
    rationale_sentences = [
        item.strip()
        for item in re.split(r"(?<=[.!?])\s+", " ".join(synthesis.accessibility_rationale.split()))
        if item.strip()
    ]
    rationale_opening = rationale_sentences[0]
    rationale_conclusion = rationale_sentences[-1]
    why_this_path = _bounded_sentences(
        rationale_opening,
        (
            f"The recommended route addresses {len(synthesis.grouped_gaps)} career-level gap "
            f"theme(s) containing {underlying_count} underlying requirement(s)."
        ),
        rationale_conclusion,
        maximum=3,
    )
    focus = ", ".join(item.career_gap for item in actions[:2])
    if bridge:
        meaning = (
            f"Use the validated bridge route through {bridge} and focus next on "
            f"{focus or 'the documented career gaps'} before reassessing {target}."
        )
    elif plan.path_type is PathType.DIRECT:
        meaning = (
            f"Use the direct selective route toward {target} and focus next on "
            f"{focus or 'keeping your strongest evidence current'}."
        )
    else:
        meaning = (
            f"Use the longer development route toward {target} and focus next on "
            f"{focus or 'resolving the documented evidence barriers'}."
        )
    timeline = getattr(plan, "timeline_assessment", None)
    path_label = {
        PathType.DIRECT: "Direct selective transition",
        PathType.DEVELOPMENT: "Longer development route",
        PathType.BRIDGE: "Bridge route",
        PathType.MULTIPLE_PATHS: "Bridge route",
        PathType.EXPLORATION: "Longer development route",
        PathType.NO_CREDIBLE_PATH: "Longer development route",
    }[plan.path_type]
    return PlanViewModel(
        current_role=current,
        target_role=target,
        accessibility=_analysis_accessibility_label(synthesis.accessibility),
        recommended_path=path_label,
        confidence=product_label(plan.confidence),
        bridge_role=bridge,
        untimed=(
            timeline is not None
            and timeline.classification is TimelineClassification.NO_FIXED_TIMELINE
        ),
        route=tuple(route_items),
        actions=tuple(actions),
        strengths=tuple(
            PlanStrengthViewModel(item.title, _short(item.explanation, 220))
            for item in synthesis.strongest_advantages[:4]
        ),
        why_this_path=why_this_path,
        what_this_means=_bounded_sentences(
            rationale_opening, rationale_conclusion, meaning, maximum=3
        ),
    )


def untimed_roadmap_stages(view: PlanViewModel) -> tuple[tuple[str, str], ...]:
    """Create an ordinal roadmap without inventing month estimates."""

    strength_names = ", ".join(item.title for item in view.strengths[:2])
    next_action = (
        view.actions[0].action
        if view.actions
        else "Keep the confirmed target-role evidence current"
    )
    remaining = (
        view.actions[1].action
        if len(view.actions) > 1
        else "Accumulate direct evidence in the remaining priority dimensions"
    )
    return (
        (
            "NOW",
            f"Reframe and package confirmed evidence from {strength_names or view.current_role}",
        ),
        ("NEXT", next_action),
        ("BUILD / BRIDGE", view.bridge_role or remaining),
        (
            "TARGET",
            f"Reassess the evidence, then pursue {view.target_role} when it supports "
            f"{view.accessibility.casefold()}",
        ),
    )


def selected_plan_milestones(plan: Any, option_id: str) -> tuple[Any, ...]:
    """Filter only an actual selected bridge branch; retain shared roadmap phases."""

    if plan.path_type is not PathType.MULTIPLE_PATHS:
        return tuple(plan.milestones)
    selected = next(
        (item for item in plan.bridge_roles if str(item.bridge_assessment_id) == option_id), None
    )
    if selected is None or not selected.bridge_role:
        return tuple(plan.milestones)
    return tuple(
        item
        for item in plan.milestones
        if item.phase != "Supported bridge options"
        or selected.bridge_role.casefold() in item.action.casefold()
    )


def plan_limitations(state: dict[str, Any]) -> tuple[str, ...]:
    """Synthesize plan-level limitations without forwarding processing fragments."""

    summary = state.get("requirement_summary")
    limitations: list[str] = []
    if summary:
        limitations.append(
            "Market requirement analysis is based on "
            f"{summary.analyzed_posting_count} successfully analyzed posting(s)."
        )
    bridge_outcome = product_label(state.get("bridge_outcome", ""))
    if "insufficient" in bridge_outcome.casefold() or "not enough" in bridge_outcome.casefold():
        limitations.append("Bridge-role market evidence is limited.")
    return tuple(limitations)


def confirmed_evidence_detail(state: dict[str, Any]) -> dict[object, str]:
    profile = state.get("confirmed_profile")
    if profile is None:
        return {}
    return {
        item.evidence_id: f"{item.capability}: {item.description}"
        for item in profile.evidence_items
        if item.approved_by_user
        and item.confirmation_status
        in {
            EvidenceConfirmationStatus.EXPLICIT,
            EvidenceConfirmationStatus.CONFIRMED_INFERENCE,
        }
    }
