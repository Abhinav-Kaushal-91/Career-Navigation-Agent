"""Shared guardrails: usable individual matches do not establish whole-role readiness."""

from ai_career_navigator.domain import ConfidenceLevel, RequirementStatementType


def is_hiring_expectation(requirement):
    return (
        requirement.statement_type
        in {RequirementStatementType.HIRING_CAPABILITY, RequirementStatementType.PREREQUISITE}
        and not requirement.preferred
        and requirement.role_importance not in {"ADDITIONAL", "SPECIALIST"}
    )


def comparison_is_resolved(item):
    """An unknown answer or failed operation is not evidence of a candidate deficit."""
    return (
        item.match_type is not None
        and item.confidence not in {ConfidenceLevel.LOW, ConfidenceLevel.INSUFFICIENT}
        and item.evidence_status not in {"UNKNOWN", "OPERATION_FAILED"}
        and not item.clarification_needed
    )


def unresolved_hiring_requirements(analysis, comparisons):
    canonical = analysis.canonical_profile
    if canonical is None:
        return ()
    completed = {item.requirement_id for item in comparisons if comparison_is_resolved(item)}
    return tuple(
        item
        for item in canonical.comparison_requirements
        if item.canonical_requirement_id not in completed
    )


def readiness_coverage_notes(analysis, comparisons):
    """Keep specific questions visible even when a bounded verdict is possible."""
    unresolved = unresolved_hiring_requirements(analysis, comparisons)
    if not unresolved:
        return []
    failed = {
        item.requirement_id for item in comparisons if item.evidence_status == "OPERATION_FAILED"
    }
    notes = []
    for label, selected in (
        (
            "Processing incomplete; retry comparison",
            [item for item in unresolved if item.canonical_requirement_id in failed],
        ),
        (
            "Candidate evidence to clarify",
            [
                item
                for item in unresolved
                if item.canonical_requirement_id not in failed and not item.employer_specific
            ],
        ),
        (
            "Employer-specific conditions to verify",
            [
                item
                for item in unresolved
                if item.canonical_requirement_id not in failed and item.employer_specific
            ],
        ),
    ):
        if selected:
            notes.append(f"{label}: " + ", ".join(item.display_name for item in selected) + ".")
    return notes


def readiness_coverage_issue(analysis, comparisons):
    canonical = analysis.canonical_profile
    if canonical is None:
        return None  # Legacy noncanonical callers retain their existing policy.
    hiring = tuple(item for item in canonical.comparison_requirements if not item.employer_specific)
    if len(hiring) < 2:
        return (
            "Limited market coverage: usable hiring evidence covers fewer than two distinct "
            "baseline expectations. Individual "
            "matches remain valid, but overall role readiness is not established."
        )
    if canonical.coverage_limitations:
        return " ".join(canonical.coverage_limitations)
    if canonical.profile_status == "INSUFFICIENT":
        return "Limited market coverage: insufficient independent target-role hiring evidence."
    completed = {item.requirement_id for item in comparisons if comparison_is_resolved(item)}
    unresolved = [item for item in hiring if item.canonical_requirement_id not in completed]
    core = [item for item in hiring if item.role_importance == "CORE"]
    if core and sum(item.canonical_requirement_id in completed for item in core) * 2 <= len(core):
        return (
            "Core comparison incomplete: more than half of the role's core capabilities "
            "must be resolved. Supporting matches do not replace core coverage."
        )
    prerequisites = [
        item
        for item in unresolved
        if item.requirement_kind == "PREREQUISITE" and item.mandatory_signal
    ]
    if prerequisites:
        return (
            "Required baseline eligibility remains unverified: "
            + ", ".join(item.display_name for item in prerequisites)
            + ". This is an unanswered question, not a confirmed disqualification."
        )
    resolved_count = len(hiring) - len(unresolved)
    if resolved_count < 2 or resolved_count * 2 <= len(hiring):
        return (
            f"Core comparison incomplete: {resolved_count} of {len(hiring)} baseline hiring "
            "expectations are resolved. At least two and more than half must be resolved; "
            "completed matches remain valid."
        )
    return None
