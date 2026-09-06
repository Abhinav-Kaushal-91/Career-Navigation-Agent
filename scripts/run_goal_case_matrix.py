"""Run the twelve goal-direction QA cases through the deterministic backend graph."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from ai_career_navigator.config import Settings
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
)
from ai_career_navigator.market import (
    FakeAdzunaMarketSearchClient,
    MarketSourceProvider,
    StructuredJobResult,
    StructuredJobSearchPage,
)
from ai_career_navigator.market.mcp.fake_client import FakeMarketSearchClient
from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.models.providers import FakeModelProvider
from ai_career_navigator.orchestration import (
    CareerWorkflowController,
    TransientMarketContentStore,
    WorkflowRuntimeContext,
    build_career_graph,
)

NOW = datetime(2026, 9, 4, 16, 0, tzinfo=UTC)


class MatrixModelProvider(FakeModelProvider):
    """Return grounded fixture output for each schema used by the full graph."""

    def generate_structured(self, *, request, model, output_schema, timeout_seconds):  # type: ignore[no-untyped-def]
        if request.response_schema_name == "TransferabilityAssessment":
            payload = json.loads(request.user_prompt.split("Assess this data:\n", 1)[1])
            requirement = payload["requirement"]
            candidate = payload["candidate_evidence"][0]
            self._outcomes.insert(  # noqa: SLF001
                0,
                json.dumps(
                    {
                        "requirement_id": requirement["requirement_id"],
                        "match_type": "PARTIAL_MATCH",
                        "supporting_evidence_ids": [candidate["evidence_id"]],
                        "candidate_maturity": candidate["maturity"],
                        "target_maturity": requirement["expected_maturity"],
                        "transferable_capability": candidate["capability"],
                        "remaining_difference": (
                            "The confirmed evidence is relevant but does not fully establish "
                            "the target capability."
                        ),
                        "confidence": "MODERATE",
                        "explanation": "The fixture records a bounded partial transfer.",
                    }
                ),
            )
        elif request.response_schema_name == "CareerPlanDraftOutput":
            self._outcomes.insert(0, request.user_prompt)  # noqa: SLF001
        return super().generate_structured(
            request=request,
            model=model,
            output_schema=output_schema,
            timeout_seconds=timeout_seconds,
        )


def stable_id(value: str):  # type: ignore[no-untyped-def]
    return uuid5(NAMESPACE_URL, f"career-navigator-case/{value}")


def evidence(case_set: str, capability: str, description: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=stable_id(f"{case_set}/{capability}"),
        evidence_type="skill",
        source_type="QA sample profile",
        source_reference=f"Sample profile {case_set}",
        capability=capability,
        description=description,
        maturity_level=EvidenceMaturity.PRODUCTION,
        confirmation_status=EvidenceConfirmationStatus.EXPLICIT,
        confidence=ConfidenceLevel.HIGH,
        approved_by_user=True,
        created_at=NOW,
    )


def profiles() -> dict[str, CandidateProfile]:
    return {
        "A": CandidateProfile(
            profile_id=stable_id("profile-a"),
            career_stage=CareerStage.SENIOR_INDIVIDUAL_CONTRIBUTOR,
            professional_summary=(
                "Senior automation developer with integration and cloud delivery experience."
            ),
            current_role="Senior Automation Developer",
            current_seniority="Senior",
            current_location="Toronto, Ontario",
            evidence_items=[
                evidence("A", "Python", "Built production Python automation services."),
                evidence("A", "REST APIs", "Designed production REST integrations."),
                evidence("A", "Cloud Architecture", "Designed cloud-hosted automation solutions."),
                evidence(
                    "A", "Stakeholder Leadership", "Led technical delivery with business owners."
                ),
            ],
            approval_status=ApprovalStatus.APPROVED,
            created_at=NOW,
            confirmed_at=NOW,
        ),
        "B": CandidateProfile(
            profile_id=stable_id("profile-b"),
            career_stage=CareerStage.MID_CAREER,
            professional_summary=(
                "Business systems analyst with data and requirements delivery experience."
            ),
            current_role="Business Systems Analyst",
            current_seniority="Intermediate",
            current_location="Calgary, Alberta",
            evidence_items=[
                evidence("B", "SQL", "Used SQL for production reporting and data validation."),
                evidence(
                    "B", "Requirements Analysis", "Led requirements discovery for system changes."
                ),
                evidence("B", "Process Design", "Mapped and redesigned operational processes."),
                evidence(
                    "B", "Stakeholder Facilitation", "Facilitated cross-functional workshops."
                ),
            ],
            approval_status=ApprovalStatus.APPROVED,
            created_at=NOW,
            confirmed_at=NOW,
        ),
    }


CASE_SPECS = (
    (GoalType.CURRENT_MARKET_ANALYSIS, "AI Solutions Architect", "Business Systems Analyst"),
    (GoalType.ROLE_TRANSITION, "AI Solutions Architect", "Technical Product Manager"),
    (GoalType.TARGET_CAREER_PATH, "Cloud Solutions Architect", "Data Engineer"),
    (GoalType.LEADERSHIP_PROGRESSION, "Engineering Manager", "Director of Automation"),
    (GoalType.CAREER_EXPLORATION, None, None),
    (GoalType.CAREER_REASSESSMENT, "AI Solutions Architect", "Technical Product Manager"),
)


def make_goal(goal_type: GoalType, target: str | None, set_id: str) -> CareerGoal:
    return CareerGoal(
        goal_id=stable_id(f"goal/{goal_type.value}/{set_id}"),
        goal_type=goal_type,
        target_role=target,
        target_seniority="Senior" if set_id == "A" else None,
        target_timeline_months=24 if goal_type is not GoalType.CAREER_EXPLORATION else None,
        target_location="Canada",
        target_industries=["Technology"] if set_id == "A" else ["Financial Services"],
        preferred_work_modes=["Hybrid"] if set_id == "A" else ["Remote"],
        geography_scopes=[GeographyScope.COUNTRY],
        bridge_role_willingness=(
            True
            if goal_type
            in {GoalType.ROLE_TRANSITION, GoalType.TARGET_CAREER_PATH, GoalType.CAREER_REASSESSMENT}
            else None
        ),
        search_expansion_permission=goal_type
        in {
            GoalType.ROLE_TRANSITION,
            GoalType.TARGET_CAREER_PATH,
            GoalType.LEADERSHIP_PROGRESSION,
            GoalType.CAREER_REASSESSMENT,
        },
        exploration_mode=goal_type is GoalType.CAREER_EXPLORATION,
        exclusions=["US-only roles"],
        approval_status=ApprovalStatus.APPROVED,
        created_at=NOW,
        approved_at=NOW,
    )


def requirement_payload(set_id: str) -> tuple[str, str]:
    requirements = (
        (
            ("Python", "Python required"),
            ("REST APIs", "REST API design required"),
            ("Architecture Ownership", "Architecture ownership required"),
        )
        if set_id == "A"
        else (
            ("SQL", "SQL required"),
            ("Requirements Analysis", "Requirements analysis required"),
            ("Stakeholder Leadership", "Stakeholder leadership required"),
        )
    )
    description = "Job description. " + " ".join(quote + "." for _, quote in requirements)
    description = (description + " Canada role with active employer application details. ") * 8
    payload = {
        "requirements": [
            {
                "source_quote": quote,
                "category": "LEADERSHIP"
                if "Leadership" in capability or "Ownership" in capability
                else "TECHNICAL",
                "normalized_capability": capability,
                "mandatory": True,
                "preferred": False,
                "years_required": None,
                "maturity_expected": "PRODUCTION",
                "confidence": "HIGH",
            }
            for capability, quote in requirements
        ],
        "limitations": [],
    }
    return description, json.dumps(payload)


def controller_for(target: str, set_id: str) -> tuple[CareerWorkflowController, FakeModelProvider]:
    description, model_output = requirement_payload(set_id)
    postings = [
        StructuredJobResult(
            provider=MarketSourceProvider.ADZUNA,
            provider_job_id=f"qa-{set_id}-{index}-{stable_id(target)}",
            title=target,
            url=f"https://example.invalid/jobs/{stable_id(target + set_id + str(index))}",
            description=description,
            company=f"QA Canada Employer {index}",
            location="Canada",
            created="2026-09-04",
        )
        for index in (1, 2)
    ]
    primary = FakeAdzunaMarketSearchClient(
        [
            StructuredJobSearchPage(
                provider=MarketSourceProvider.ADZUNA,
                page=1,
                total_available=2,
                results=postings,
            )
        ]
    )
    provider = MatrixModelProvider(outcomes=[model_output, model_output])
    gateway = ModelGateway(
        provider=provider,
        models={
            ModelRole.EXTRACTION: "fake-extraction",
            ModelRole.REASONING: "fake-reasoning",
            ModelRole.VALIDATION: "fake-validation",
        },
        timeout_seconds=10,
        max_retries=0,
        sleeper=lambda _: None,
    )
    context = WorkflowRuntimeContext(
        settings=Settings(max_retries=0),
        model_gateway=gateway,
        market_client_factory=FakeMarketSearchClient,
        structured_market_client_factory=lambda: primary,
        content_store=TransientMarketContentStore(),
        clock=lambda: NOW,
    )
    return CareerWorkflowController(build_career_graph(), context), provider


def display(value: object | None) -> str | None:
    if value is None:
        return None
    return str(getattr(value, "value", value)).replace("_", " ").title()


async def run_case(case_id: str, profile: CandidateProfile, goal: CareerGoal) -> dict[str, object]:
    if not goal.target_role:
        controller, provider = controller_for("Unspecified role", case_id[-1])
    else:
        controller, provider = controller_for(goal.target_role, case_id[-1])
    result = await controller.start(
        thread_id=f"qa-{case_id.lower()}",
        confirmed_profile=profile,
        confirmed_goal=goal,
        capability_inference_requested=False,
    )
    state = result.state
    snapshot = state.get("market_snapshot")
    summary = state.get("requirement_summary")
    role = state.get("role_assessment")
    plan = state.get("career_plan")
    status = display(state.get("workflow_status"))
    if plan:
        answer = (
            f"{display(role.candidate_accessibility) if role else 'No accessibility result'}; "
            f"{display(plan.path_type)} path with {len(plan.milestones)} milestone(s)."
        )
    elif (
        state.get("last_error") == "ROLE_DISCOVERY_REQUIRED" or status == "Role Discovery Required"
    ):
        answer = (
            "A named target role is required before the current V1 backend can search the market."
        )
    else:
        answer = "The backend stopped safely without producing a career plan."
    return {
        "case_id": case_id,
        "run_mode": "DETERMINISTIC_BACKEND",
        "goal_type": goal.goal_type.value,
        "profile_set": case_id[-1],
        "career_stage": profile.career_stage.value,
        "current_role": profile.current_role,
        "current_location": profile.current_location,
        "confirmed_capabilities": ", ".join(
            item.capability for item in profile.approved_evidence_items
        ),
        "target_role": goal.target_role,
        "target_seniority": goal.target_seniority,
        "timeline_months": goal.target_timeline_months,
        "target_location": goal.target_location,
        "work_modes": ", ".join(goal.preferred_work_modes),
        "industries": ", ".join(goal.target_industries),
        "geography_scope": ", ".join(scope.value for scope in goal.geography_scopes),
        "bridge_role_willingness": goal.bridge_role_willingness,
        "related_title_expansion": goal.search_expansion_permission,
        "exclusions": ", ".join(goal.exclusions),
        "workflow_status": status,
        "workflow_stage": display(state.get("current_stage")),
        "interrupted_for_review": result.interrupted,
        "validated_postings": getattr(snapshot, "validated_posting_count", None),
        "analyzed_postings": getattr(summary, "analyzed_posting_count", None),
        "opportunity_availability": display(getattr(snapshot, "opportunity_availability", None)),
        "market_confidence": display(getattr(snapshot, "evidence_confidence", None)),
        "candidate_accessibility": display(getattr(role, "candidate_accessibility", None)),
        "gap_count": len(role.gaps) if role else None,
        "bridge_outcome": display(state.get("bridge_outcome")),
        "timeline_assessment": display(
            getattr(state.get("timeline_assessment"), "classification", None)
        ),
        "plan_path": display(getattr(plan, "path_type", None)),
        "milestone_count": len(plan.milestones) if plan else None,
        "model_calls": len(provider.calls),
        "answer": answer,
        "limitations": " | ".join(state.get("limitations", [])),
        "last_error": state.get("last_error"),
    }


async def run_all(case_filter: str | None = None) -> list[dict[str, object]]:
    sample_profiles = profiles()
    results = []
    for index, (goal_type, target_a, target_b) in enumerate(CASE_SPECS, start=1):
        for set_id, target in (("A", target_a), ("B", target_b)):
            case_id = f"G{index}-{set_id}"
            if case_filter and case_id != case_filter:
                continue
            results.append(
                await run_case(
                    case_id, sample_profiles[set_id], make_goal(goal_type, target, set_id)
                )
            )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--case-id",
        choices=[f"G{i}-{set_id}" for i in range(1, 7) for set_id in "AB"],
    )
    args = parser.parse_args()
    results = asyncio.run(run_all(args.case_id))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps({"cases": len(results), "output": str(args.output)}))


if __name__ == "__main__":
    main()
