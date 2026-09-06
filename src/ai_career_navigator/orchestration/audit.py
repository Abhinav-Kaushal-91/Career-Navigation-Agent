"""Bounded, chain-of-thought-free audit artifacts for live-run QA."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from ai_career_navigator.market import MarketRequirementAnalysis

from .state import CareerGraphState


def persist_run_audit(
    state: CareerGraphState | dict[str, Any],
    analysis: MarketRequirementAnalysis,
    *,
    directory: Path,
) -> Path:
    """Persist bounded posting, requirement, comparison, and plan provenance."""

    run_id = UUID(str(state["run_id"]))
    profile = state.get("confirmed_profile")
    evidence = {item.evidence_id: item for item in getattr(profile, "approved_evidence_items", ())}
    canonical_profile = state.get("canonical_target_role_profile")
    canonical_items = list(
        {
            item.canonical_requirement_id: item
            for item in [
                *getattr(canonical_profile, "requirements", ()),
                *getattr(canonical_profile, "responsibilities", ()),
                *getattr(canonical_profile, "prerequisites", ()),
                *getattr(canonical_profile, "preferences", ()),
                *getattr(canonical_profile, "optional_signals", ()),
                *getattr(canonical_profile, "related_context", ()),
            ]
        }.values()
    )
    canonical_by_id = {item.canonical_requirement_id: item for item in canonical_items}
    raw_by_id = {item.requirement_id: item for item in analysis.raw_requirements}

    postings = []
    for audit in state.get("posting_requirement_audits", []):
        requirement_rows = []
        for item in audit.items:
            raw = raw_by_id.get(item.source_requirement_id)
            canonical = canonical_by_id.get(item.canonical_requirement_id)
            requirement_rows.append(
                {
                    "source_requirement_id": (
                        str(item.source_requirement_id) if item.source_requirement_id else None
                    ),
                    "source_quote": item.source_quote,
                    "normalized_requirement": item.normalized_capability,
                    "category": item.category.value,
                    "item_type": item.item_type.value,
                    "accepted": item.accepted,
                    "final_classification": item.final_classification,
                    "canonical_requirement_id": (
                        str(item.canonical_requirement_id)
                        if item.canonical_requirement_id
                        else None
                    ),
                    "canonical_requirement": getattr(canonical, "display_name", None),
                    "mandatory": getattr(raw, "mandatory", None),
                    "preferred": getattr(raw, "preferred", None),
                    "target_maturity": (
                        canonical.expected_maturity.value
                        if canonical and canonical.expected_maturity
                        else None
                    ),
                    "rejection_or_override_reason": item.rejection_or_override_reason,
                }
            )
        postings.append(
            {
                "posting_id": str(audit.posting_id),
                "title": audit.title,
                "employer": audit.employer,
                "location": audit.location,
                "source": audit.source_reference,
                "provider": audit.provider,
                "title_classification": audit.title_classification.value,
                "extraction_status": audit.extraction_status.value,
                "requirements": requirement_rows,
            }
        )

    retrieval_postings = [
        {
            "posting_id": audit.posting_id,
            "provider": audit.provider.value,
            "source_url": audit.source_url,
            "source_type": audit.source_type.value,
            "title": audit.title,
            "employer": audit.employer,
            "location": audit.location,
            "title_classification": audit.title_classification,
            "seniority_classification": audit.seniority_classification.value,
            "duplicate_of": audit.duplicate_of,
            "selected_content_source": (
                audit.selected_content_source.value if audit.selected_content_source else None
            ),
            "selected_for_primary_evidence": audit.selected_for_primary_evidence,
            "rejection_reason": audit.rejection_reason,
        }
        for audit in state.get("market_posting_audits", [])
    ]

    comparisons = []
    for item in state.get("requirement_comparisons", []):
        comparisons.append(
            {
                "comparison_id": str(item.comparison_id),
                "requirement_id": str(item.requirement_id),
                "selected_evidence": [
                    {
                        "evidence_id": str(evidence_id),
                        "capability": getattr(evidence.get(evidence_id), "capability", None),
                    }
                    for evidence_id in item.evidence_ids
                ],
                "candidate_maturity": (
                    item.candidate_maturity.value if item.candidate_maturity else None
                ),
                "target_maturity": item.target_maturity.value if item.target_maturity else None,
                "functional_overlap": item.functional_overlap.value,
                "ownership_alignment": item.ownership_alignment.value,
                "scope_alignment": item.scope_alignment.value,
                "maturity_alignment": item.maturity_alignment.value,
                "production_context_difference": item.production_context_difference.value,
                "match_type": item.match_type.value if item.match_type else None,
                "partial_match_subtype": (
                    item.partial_match_subtype.value if item.partial_match_subtype else None
                ),
                "residual_difference": item.remaining_difference,
                "confidence": item.confidence.value,
            }
        )

    plan = state.get("career_plan")
    payload = {
        "schema_version": 1,
        "run_id": str(run_id),
        "generated_at": datetime.now(UTC).isoformat(),
        "target_role": getattr(canonical_profile, "target_role", None),
        "postings": postings,
        "retrieval_postings": retrieval_postings,
        "canonical_requirements": [
            {
                "canonical_requirement_id": str(item.canonical_requirement_id),
                "display_name": item.display_name,
                "employer_support_count": item.employer_support_count,
                "posting_support_count": item.posting_support_count,
                "responsibility_support_count": item.responsibility_support_count,
                "qualification_support_count": item.qualification_support_count,
                "adzuna_support_count": item.adzuna_support_count,
                "you_support_count": item.you_support_count,
                "provider_sources": [value.value for value in item.provider_sources],
                "source_provenance": item.source_provenance,
                "statement_types": [value.value for value in item.statement_types],
                "responsibility_requirement_ids": [
                    str(value) for value in item.responsibility_requirement_ids
                ],
                "qualification_requirement_ids": [
                    str(value) for value in item.qualification_requirement_ids
                ],
                "source_agreement": item.source_agreement.value,
                "representative_source_quotes": item.representative_source_quotes,
            }
            for item in canonical_items
        ],
        "comparisons": comparisons,
        "accessibility": getattr(state.get("candidate_accessibility"), "value", None),
        "plan": (
            {
                "path_type": plan.path_type.value,
                "milestones": [
                    {
                        "phase": item.phase,
                        "action": item.action,
                        "linked_gap_ids": [str(value) for value in item.linked_gap_ids],
                    }
                    for item in plan.milestones
                ],
            }
            if plan
            else None
        ),
    }
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{run_id}.json"
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(destination)
    return destination
