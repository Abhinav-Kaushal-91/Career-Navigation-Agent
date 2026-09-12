import asyncio
import json
from pathlib import Path

from ai_career_navigator.config import Settings
from ai_career_navigator.domain import EvidenceConfirmationStatus
from ai_career_navigator.market import (
    FakeAdzunaMarketSearchClient,
    MarketContentError,
    MarketSearchResult,
    MarketSourceProvider,
    MarketTimeoutError,
    StructuredJobResult,
    StructuredJobSearchPage,
)
from ai_career_navigator.market.mcp.fake_client import FakeMarketSearchClient
from ai_career_navigator.market.schemas import MarketPageContent
from ai_career_navigator.models import ModelTimeoutError
from ai_career_navigator.models.providers import FakeModelProvider
from ai_career_navigator.orchestration import (
    MarketProcessingWorkflowStatus,
    MarketSearchWorkflowStatus,
    WorkflowStage,
    WorkflowStatus,
)
from ai_career_navigator.profile import InferenceDecision, apply_inference_decision

from .conftest import inference_json, make_controller, requirement_json


def market_fixture(
    *,
    title: str = "AI Solutions Architect",
    markdown: str = "Job description. Requirements: Python required. Apply now.",
    employer: str = "Example Canada",
    location: str = "Toronto, Canada",
    url: str = "https://example.com/jobs/ai-architect",
) -> tuple[MarketSearchResult, MarketPageContent]:
    result = MarketSearchResult(
        title=title,
        url=url,
        snippets=["Job description. Requirements. Apply now."],
    )
    page = MarketPageContent(
        url=url,
        title=title,
        markdown=markdown,
        employer=employer,
        location=location,
        active_status="ACTIVE",
    )
    return result, page


def test_fake_graph_interrupt_checkpoint_resume_reaches_market_ready(
    approved_profile, approved_goal, explicit_evidence, tmp_path
) -> None:
    search_result, page = market_fixture()
    second_result, second_page = market_fixture(
        employer="Second Canada",
        url="https://example.com/jobs/ai-architect-2",
    )
    market = FakeMarketSearchClient(
        search_outcomes=[[search_result, second_result]],
        content_outcomes={search_result.url: page, second_result.url: second_page},
    )
    provider = FakeModelProvider(
        outcomes=[
            inference_json(explicit_evidence.evidence_id),
            requirement_json(),
            requirement_json(),
        ]
    )
    controller, content_store = make_controller(
        provider,
        market,
        settings=Settings(max_retries=0, run_audit_directory=tmp_path / "run-audits"),
    )

    interrupted = asyncio.run(
        controller.start(
            thread_id="full-fake-flow",
            confirmed_profile=approved_profile,
            confirmed_goal=approved_goal,
        )
    )

    assert interrupted.interrupted
    assert interrupted.state["workflow_status"] is WorkflowStatus.WAITING_FOR_HUMAN
    assert len(provider.calls) == 1
    checkpoint = controller.inspect(thread_id="full-fake-flow")
    assert checkpoint.interrupted
    assert checkpoint.state["run_id"] == interrupted.state["run_id"]

    pending = interrupted.state["inferred_evidence"][0]
    reviewed = apply_inference_decision(
        interrupted.state["confirmed_profile"],
        pending.evidence_id,
        InferenceDecision.REJECT,
    )
    resumed = asyncio.run(
        controller.resume_inference_review(thread_id="full-fake-flow", reviewed_profile=reviewed)
    )

    assert resumed.interrupted
    assert resumed.state["current_stage"] is WorkflowStage.CAREER_PLAN_READY
    assert resumed.state["workflow_status"] is WorkflowStatus.WAITING_FOR_HUMAN
    assert resumed.state["market_snapshot"].validated_posting_count == 2
    assert resumed.state["requirement_summary"].analyzed_posting_count == 2
    assert resumed.state["requirement_summary"].exact_title_analyzed_count == 2
    assert resumed.state["career_assessment_synthesis"] is not None
    assert resumed.state["career_assessment_synthesis"].source_comparison_ids == [
        item.comparison_id for item in resumed.state["requirement_comparisons"]
    ]
    assert resumed.state["inferred_evidence"][0].confirmation_status is (
        EvidenceConfirmationStatus.REJECTED_INFERENCE
    )
    assert (
        len(provider.calls) == 5
    )  # identical atomic source conditions use deterministic comparison
    assert resumed.state["employer_overview"] is not None
    assert resumed.state["requirement_comparisons"][0].match_type.value == "DIRECT_MATCH"
    assert resumed.state["candidate_accessibility"].value == "INSUFFICIENT_CANDIDATE_EVIDENCE"
    assert resumed.state["role_assessment"].gaps == []
    assert (
        resumed.state["timeline_assessment"].classification.value
        == "UNSUPPORTED_INSUFFICIENT_EVIDENCE"
    )
    assert resumed.state["career_plan"].path_type.value == "EXPLORATION"
    assert resumed.state["career_plan"].plan_status.value == "DRAFT"
    assert content_store.get(resumed.state["run_id"])
    audit_path = Path(resumed.state["audit_artifact_path"])
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit_path.parent == tmp_path / "run-audits"
    assert audit["run_id"] == str(resumed.state["run_id"])
    assert audit["postings"][0]["requirements"][0]["source_quote"] == "Python required"
    assert audit["comparisons"][0]["selected_evidence"][0]["capability"] == "Python"
    assert "functional_overlap" in audit["comparisons"][0]
    assert audit["plan"]["path_type"] == "EXPLORATION"
    assert audit["schema_version"] == 2
    assert audit["pipeline_version"] == "grounded-evidence-tracks-v1"
    assert audit["prompt_versions"]["extraction"] == "market-requirements-v7"
    assert audit["prompt_versions"]["comparison"] == "candidate-comparison-v9"
    assert audit["prompt_versions"]["synthesis"] == "career-assessment-synthesis-v6-concise-v2"


def test_graph_stops_before_analysis_and_plan_when_target_profile_is_insufficient(
    approved_profile, approved_goal
) -> None:
    posting = StructuredJobResult(
        provider=MarketSourceProvider.ADZUNA,
        provider_job_id="adz-graph-1",
        title="AI Solutions Architect",
        url="https://employer.example/jobs/ai-architect",
        description=("Python required for production architecture delivery. " * 12),
        company="Example Canada",
        location="Toronto, Canada",
        created="2026-09-03",
    )
    primary = FakeAdzunaMarketSearchClient(
        [
            StructuredJobSearchPage(
                provider=MarketSourceProvider.ADZUNA,
                page=1,
                total_available=1,
                results=[posting],
            )
        ]
    )
    controller, content_store = make_controller(
        FakeModelProvider(outcomes=[requirement_json()]),
        FakeMarketSearchClient(),
        structured_market_client=primary,
    )

    result = asyncio.run(
        controller.start(
            thread_id="structured-adzuna-graph",
            confirmed_profile=approved_profile,
            confirmed_goal=approved_goal,
            capability_inference_requested=False,
        )
    )

    assert not result.interrupted
    assert result.state["current_stage"] is WorkflowStage.MARKET_READY
    assert result.state["workflow_status"] is WorkflowStatus.INSUFFICIENT_EVIDENCE
    assert result.state["requirement_summary"].analyzed_posting_count == 1
    assert result.state["canonical_target_role_profile"].profile_status.value == "INSUFFICIENT"
    assert result.state["role_assessment"] is None
    assert result.state["career_plan"] is None
    assert content_store.get_posting_evidence(result.state["run_id"])


def test_graph_continues_through_plan_with_validated_target_variants(
    approved_profile, approved_goal
) -> None:
    class VariantAwareProvider(FakeModelProvider):
        def generate_structured(  # type: ignore[no-untyped-def]
            self, *, request, model, output_schema, timeout_seconds
        ):
            if request.response_schema_name == "TargetVariantAssessmentResult":
                payload = json.loads(request.user_prompt)
                self._outcomes.insert(  # noqa: SLF001
                    0,
                    json.dumps(
                        {
                            "assessments": [
                                {
                                    "candidate_title": candidate["candidate_title"],
                                    "classification": "VALID_TARGET_VARIANT",
                                    "functional_overlap": 0.9,
                                    "ownership_overlap": 0.9,
                                    "scope_overlap": 0.9,
                                    "seniority_alignment": "ALIGNED",
                                    "outcome_overlap": 0.9,
                                    "core_requirement_overlap": 0.9,
                                    "evidence_confidence": "HIGH",
                                    "supporting_posting_ids": [
                                        item["posting_id"] for item in candidate["postings"]
                                    ],
                                    "reasoning_summary": (
                                        "Observed responsibilities and requirements align."
                                    ),
                                }
                                for candidate in payload["candidate_titles"]
                            ]
                        }
                    ),
                )
            return super().generate_structured(
                request=request,
                model=model,
                output_schema=output_schema,
                timeout_seconds=timeout_seconds,
            )

    description = ("Product strategy experience and Python required. " * 15).strip()
    postings = [
        StructuredJobResult(
            provider=MarketSourceProvider.ADZUNA,
            provider_job_id=f"variant-{index}",
            title=title,
            url=f"https://employer{index}.example/jobs/product-{index}",
            description=description,
            company=f"Employer {index}",
            location="Canada",
            created="2026-09-01",
        )
        for index, title in enumerate(
            ("Product Manager", "AI Product Manager", "Technical Product Manager"), start=1
        )
    ]
    primary = FakeAdzunaMarketSearchClient(
        [
            StructuredJobSearchPage(
                provider=MarketSourceProvider.ADZUNA,
                page=1,
                total_available=3,
                results=postings,
            )
        ]
    )
    provider = VariantAwareProvider(
        outcomes=[
            requirement_json("Python required"),
            requirement_json("Python required"),
            requirement_json("Python required"),
        ]
    )
    controller, _ = make_controller(
        provider,
        FakeMarketSearchClient(),
        structured_market_client=primary,
    )
    goal = approved_goal.model_copy(
        update={
            "target_role": "Product Manager",
            "target_location": "Canada",
            "search_expansion_permission": True,
        }
    )

    result = asyncio.run(
        controller.start(
            thread_id="validated-variant-graph",
            confirmed_profile=approved_profile,
            confirmed_goal=goal,
            capability_inference_requested=False,
        )
    )

    assert result.interrupted
    assert result.state["current_stage"] is WorkflowStage.CAREER_PLAN_READY
    profile = result.state["canonical_target_role_profile"]
    assert profile.profile_status.value == "PROVISIONAL"
    assert profile.exact_posting_count == 1
    assert profile.variant_posting_count == 2
    assert result.state["role_assessment"] is not None
    assert result.state["career_plan"] is not None


def test_partial_requirement_failure_reaches_market_ready_with_limitations(
    approved_profile, approved_goal
) -> None:
    markdown = """
## AI Solutions Architect — Exact Employer
Location: Toronto, Canada
Job description. Requirements: Python required. Apply now.

## AI Platform Architect — Related Employer
Location: Toronto, Canada
Job description. Requirements: Python required. Apply now.
"""
    search_result, page = market_fixture(
        title="AI Solutions Architect jobs in Canada",
        markdown=markdown,
        employer="",
    )
    market = FakeMarketSearchClient(
        search_outcomes=[[search_result]],
        content_outcomes={search_result.url: page},
    )
    provider = FakeModelProvider(
        outcomes=[requirement_json(), ModelTimeoutError("second posting failed")]
    )
    controller, _ = make_controller(provider, market)
    goal = approved_goal.model_copy(update={"search_expansion_permission": True})

    result = asyncio.run(
        controller.start(
            thread_id="partial-processing",
            confirmed_profile=approved_profile,
            confirmed_goal=goal,
            capability_inference_requested=False,
        )
    )

    assert result.state["current_stage"] is WorkflowStage.MARKET_READY
    assert not result.interrupted
    assert result.state["workflow_status"] is WorkflowStatus.INSUFFICIENT_EVIDENCE
    assert result.state["market_processing_status"] is MarketProcessingWorkflowStatus.LIMITED
    assert result.state["requirement_summary"].analyzed_posting_count == 1
    assert result.state["limitations"]
    assert result.state["market_snapshot"].exact_title_count == 1
    assert result.state["market_snapshot"].related_title_count == 1


def test_complete_requirement_processing_failure_safe_stops(
    approved_profile, approved_goal
) -> None:
    search_result, page = market_fixture()
    market = FakeMarketSearchClient(
        search_outcomes=[[search_result]],
        content_outcomes={search_result.url: page},
    )
    controller, _ = make_controller(
        FakeModelProvider(outcomes=[ModelTimeoutError("processing unavailable")]), market
    )

    result = asyncio.run(
        controller.start(
            thread_id="failed-processing",
            confirmed_profile=approved_profile,
            confirmed_goal=approved_goal,
            capability_inference_requested=False,
        )
    )

    assert result.state["workflow_status"] is WorkflowStatus.FAILED
    assert result.state["last_error"] == "MARKET_PROCESSING_FAILED"


def test_limited_market_retrieval_propagates_limitations_to_market_ready(
    approved_profile, approved_goal
) -> None:
    valid_result, valid_page = market_fixture()
    blocked_result, _ = market_fixture(
        url="https://example.com/jobs/blocked",
        employer="Blocked Employer",
    )
    market = FakeMarketSearchClient(
        search_outcomes=[[valid_result, blocked_result]],
        content_outcomes={
            valid_result.url: valid_page,
            blocked_result.url: MarketContentError("blocked"),
        },
    )
    controller, _ = make_controller(FakeModelProvider(outcomes=[requirement_json()]), market)

    result = asyncio.run(
        controller.start(
            thread_id="limited-retrieval",
            confirmed_profile=approved_profile,
            confirmed_goal=approved_goal,
            capability_inference_requested=False,
        )
    )

    assert result.state["current_stage"] is WorkflowStage.MARKET_READY
    assert not result.interrupted
    assert result.state["market_search_status"] is MarketSearchWorkflowStatus.LIMITED
    assert result.state["workflow_status"] is WorkflowStatus.INSUFFICIENT_EVIDENCE
    assert any("could not be retrieved" in item for item in result.state["limitations"])


def test_transient_market_error_is_retried_only_by_market_service(
    approved_profile, approved_goal
) -> None:
    search_result, page = market_fixture()
    market = FakeMarketSearchClient(
        search_outcomes=[MarketTimeoutError("temporary"), [search_result]],
        content_outcomes={search_result.url: page},
    )
    controller, _ = make_controller(
        FakeModelProvider(outcomes=[requirement_json()]),
        market,
        settings=Settings(max_retries=1),
    )

    result = asyncio.run(
        controller.start(
            thread_id="service-retry",
            confirmed_profile=approved_profile,
            confirmed_goal=approved_goal,
            capability_inference_requested=False,
        )
    )

    assert result.state["current_stage"] is WorkflowStage.MARKET_READY
    assert result.state["workflow_status"] is WorkflowStatus.INSUFFICIENT_EVIDENCE
    assert len(market.search_calls) == 13
    assert market.search_requests[0] == market.search_requests[1]
    assert market.search_requests[0].freshness.value == "month"
    assert result.state["retry_counts"] == {}
