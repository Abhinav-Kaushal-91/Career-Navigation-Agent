"""Run the bounded live AI Engineer/Canada calibration scenario."""

import asyncio
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ai_career_navigator.domain import (
    ApprovalStatus,
    CandidateProfile,
    CareerGoal,
    CareerStage,
    ConfidenceLevel,
    EvidenceConfirmationStatus,
    EvidenceItem,
    EvidenceMaturity,
    GeographyScope,
    GoalType,
    MilestoneType,
)
from ai_career_navigator.ui.live_workflow import (
    build_live_workflow_runtime,
    load_live_settings,
)


def _evidence(
    capability: str,
    description: str,
    *,
    evidence_type: str,
    maturity: EvidenceMaturity,
    source_reference: str,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_type=evidence_type,
        source_type="manual onboarding",
        source_reference=source_reference,
        capability=capability,
        description=description,
        maturity_level=maturity,
        confirmation_status=EvidenceConfirmationStatus.EXPLICIT,
        confidence=ConfidenceLevel.HIGH,
        approved_by_user=True,
    )


def _profile() -> CandidateProfile:
    role = "Intelligent Automation Consultant"
    project = "Agentic Career Intelligence System"
    professional = {
        "Enterprise Automation Architecture": (
            "Architected reusable enterprise automation frameworks and production solutions."
        ),
        "Real-time API Integration": (
            "Integrated enterprise systems through production REST APIs and real-time exchanges."
        ),
        "Solution Design": "Owned solution architecture and technical design decisions.",
        "Process Discovery": (
            "Led discovery, shadow sessions, problem definition, and requirements translation."
        ),
        "Stakeholder Leadership": (
            "Led cross-functional stakeholder alignment from discovery through delivery."
        ),
        "Production Automation Delivery": (
            "Delivered and supported automation solutions in professional production environments."
        ),
        "Copilot Studio Agent Development": (
            "Built an AI-assisted requirements agent that generated structured delivery artifacts."
        ),
    }
    technical = {
        "Python": "Implemented the portfolio system and supporting services in Python.",
        "MCP": "Implemented Model Context Protocol integrations in the portfolio system.",
        "Streamlit": "Built the interactive product interface in Streamlit.",
        "LangGraph": "Implemented bounded agent orchestration using LangGraph.",
        "LangChain": "Used LangChain components in retrieval and agent workflows.",
        "LangSmith": "Used LangSmith-compatible observability patterns for agent workflows.",
        "Structured Output and JSON Schema Design": (
            "Designed validated structured model contracts and JSON schemas."
        ),
        "RAG Pipeline Design": "Designed and implemented retrieval-augmented generation pipelines.",
        "Agentic AI System Design": (
            "Designed and implemented a multi-stage agentic career intelligence system."
        ),
        "Agent Orchestration": "Built controlled model and tool orchestration workflows.",
        "AI and Prompt Engineering": "Designed bounded prompts for extraction and reasoning tasks.",
        "LLM Prompt Architecture": "Implemented role-specific prompt and validation contracts.",
        "API Integration": "Integrated model, market, and application APIs.",
        "Reusable Framework Design": "Created reusable service and evaluation patterns.",
    }
    items = [
        *(
            _evidence(
                capability,
                description,
                evidence_type="employment",
                maturity=EvidenceMaturity.PRODUCTION,
                source_reference=role,
            )
            for capability, description in professional.items()
        ),
        *(
            _evidence(
                capability,
                description,
                evidence_type="project",
                maturity=EvidenceMaturity.DEMONSTRATED,
                source_reference=project,
            )
            for capability, description in technical.items()
        ),
    ]
    now = datetime.now(UTC)
    return CandidateProfile(
        career_stage=CareerStage.SENIOR_INDIVIDUAL_CONTRIBUTOR,
        professional_summary=(
            "Intelligent automation consultant with 12 years of experience spanning business "
            "discovery, solution architecture, production automation, API integration, and "
            "hands-on portfolio delivery of RAG and agentic AI systems."
        ),
        current_role=role,
        current_location="Toronto, Canada",
        evidence_items=items,
        approval_status=ApprovalStatus.APPROVED,
        created_at=now,
        confirmed_at=now,
    )


def _goal() -> CareerGoal:
    now = datetime.now(UTC)
    return CareerGoal(
        goal_type=GoalType.ROLE_TRANSITION,
        target_role="AI Engineer",
        target_location="Canada",
        geography_scopes=[GeographyScope.COUNTRY],
        bridge_role_willingness=False,
        search_expansion_permission=False,
        approval_status=ApprovalStatus.APPROVED,
        created_at=now,
        approved_at=now,
    )


def _value(value: object) -> object:
    return getattr(value, "value", value)


async def _run() -> None:
    runtime = build_live_workflow_runtime(load_live_settings())
    thread_id = f"ai-engineer-calibration-{uuid4()}"
    async for node in runtime.controller.stream_start(
        thread_id=thread_id,
        confirmed_profile=_profile(),
        confirmed_goal=_goal(),
        capability_inference_requested=False,
    ):
        print(f"completed_node={node}")

    result = runtime.controller.inspect(thread_id=thread_id)
    state = result.state
    profile = state.get("confirmed_profile")
    evidence = {item.evidence_id: item for item in profile.approved_evidence_items}
    canonical = state.get("canonical_target_role_profile")
    requirements = {
        item.canonical_requirement_id: item
        for item in [
            *getattr(canonical, "requirements", []),
            *getattr(canonical, "prerequisites", []),
        ]
    }
    comparisons = state.get("requirement_comparisons", [])
    rows = []
    for item in comparisons:
        target = requirements.get(item.requirement_id)
        rows.append(
            {
                "requirement": getattr(target, "display_name", str(item.requirement_id)),
                "candidate_evidence": [
                    evidence[evidence_id].capability
                    for evidence_id in item.evidence_ids
                    if evidence_id in evidence
                ],
                "candidate_maturity": _value(item.candidate_maturity),
                "target_maturity": _value(item.target_maturity),
                "functional_overlap": _value(item.functional_overlap),
                "ownership_alignment": _value(item.ownership_alignment),
                "scope_alignment": _value(item.scope_alignment),
                "production_context_difference": _value(item.production_context_difference),
                "match_type": _value(item.match_type),
                "partial_subtype": _value(item.partial_match_subtype),
                "residual_gap": item.remaining_difference,
            }
        )
    counts = Counter(_value(item.match_type) for item in comparisons)
    subtypes = Counter(_value(item.partial_match_subtype) for item in comparisons)
    synthesis = state.get("career_assessment_synthesis")
    assessment = state.get("role_assessment")
    plan = state.get("career_plan")
    provider_summary = state.get("market_provider_summary")
    retrieval_audits = state.get("market_posting_audits", [])
    retained_audits = [
        item
        for item in retrieval_audits
        if item.selected_for_primary_evidence and item.duplicate_of is None
    ]
    seniority_mix = Counter(item.seniority_classification.value for item in retained_audits)
    canonical_rows = [
        {
            "requirement": item.display_name,
            "employer_support": item.employer_support_count,
            "posting_support": item.posting_support_count,
            "adzuna_support": item.adzuna_support_count,
            "you_support": item.you_support_count,
            "source_agreement": item.source_agreement.value,
            "representative_quotes": item.representative_source_quotes,
        }
        for item in [
            *getattr(canonical, "requirements", []),
            *getattr(canonical, "prerequisites", []),
            *getattr(canonical, "optional_signals", []),
        ]
    ]
    report = {
        "thread_id": thread_id,
        "stage": _value(state.get("current_stage")),
        "workflow_status": _value(state.get("workflow_status")),
        "market": {
            "validated_postings": getattr(
                state.get("market_snapshot"), "validated_posting_count", 0
            ),
            "exact": getattr(state.get("market_snapshot"), "exact_title_count", 0),
            "variants": getattr(state.get("market_snapshot"), "target_variant_count", 0),
            "related": getattr(state.get("market_snapshot"), "related_title_count", 0),
            "analyzed": getattr(state.get("requirement_summary"), "analyzed_posting_count", 0),
            "source_discovery": {
                "adzuna_raw_results": getattr(provider_summary, "adzuna_raw_result_count", 0),
                "you_raw_results": getattr(provider_summary, "you_raw_result_count", 0),
                "usable_you_direct_postings": getattr(
                    provider_summary, "you_direct_posting_count", 0
                ),
                "cross_source_duplicates": getattr(
                    provider_summary, "cross_source_match_count", 0
                ),
                "rejected_you_context_or_aggregator": getattr(
                    provider_summary, "you_context_result_count", 0
                ),
                "you_rejected_results": getattr(
                    provider_summary, "you_rejected_result_count", 0
                ),
                "you_fallback_triggered": getattr(
                    provider_summary, "you_fallback_triggered", False
                ),
            },
            "final_primary_postings": {
                "total": len(retained_audits),
                "distinct_employers": len(
                    {item.employer.casefold() for item in retained_audits if item.employer}
                ),
                "adzuna_only": max(
                    0,
                    getattr(provider_summary, "adzuna_validated_count", 0)
                    - getattr(provider_summary, "cross_source_match_count", 0),
                ),
                "you_only": max(
                    0,
                    getattr(provider_summary, "you_validated_count", 0)
                    - getattr(provider_summary, "cross_source_match_count", 0),
                ),
                "cross_source": getattr(provider_summary, "cross_source_match_count", 0),
            },
            "seniority_mix": dict(seniority_mix),
        },
        "canonical_profile_status": _value(getattr(canonical, "profile_status", None)),
        "canonical_profile_confidence": _value(getattr(canonical, "confidence", None)),
        "canonical_requirement_support": canonical_rows,
        "canonical_requirements": rows,
        "counts": {
            "direct": counts["DIRECT_MATCH"],
            "transferable": counts["TRANSFERABLE_MATCH"],
            "partial_capability_present": subtypes["CAPABILITY_PRESENT_MATURITY_GAP"],
            "partial_adjacent": subtypes["ADJACENT_CAPABILITY_PARTIAL"],
            "partial_ownership_scope": subtypes["OWNERSHIP_OR_SCOPE_GAP"],
            "no_match": counts["NO_CONFIRMED_MATCH"],
        },
        "independent_severe_dimensions": [
            _value(item) for item in getattr(synthesis, "independent_severe_dimensions", [])
        ],
        "accessibility": _value(state.get("candidate_accessibility")),
        "confidence": _value(getattr(assessment, "confidence", None)),
        "grouped_career_gaps": [
            {
                "title": item.title,
                "severity": _value(item.severity),
                "underlying_requirements": item.underlying_requirement_names,
            }
            for item in getattr(synthesis, "grouped_gaps", [])
        ],
        "plan_route": _value(getattr(plan, "path_type", None)),
        "application_milestone_exists": any(
            item.milestone_type is MilestoneType.APPLICATION_READINESS
            for item in getattr(plan, "milestones", [])
        ),
        "audit_artifact_path": state.get("audit_artifact_path"),
        "nvidia_calls": runtime.model_usage.calls,
        "nvidia_failed_calls": runtime.model_usage.failed_calls,
    }
    destination = Path("outputs/ai-engineer-calibration-live-qa-2026-09-06.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(_run())
