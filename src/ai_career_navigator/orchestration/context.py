"""Runtime dependency injection and transient content handoff for the graph."""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from ai_career_navigator.career import (
    BridgeAnalysisResult,
    CandidateComparisonResult,
    CareerAssessmentSynthesis,
    CareerPlanGenerationResult,
    GapAnalysisResult,
    TimelineAnalysisResult,
    assess_bridge_roles,
    assess_candidate_accessibility,
    assess_timeline,
    compare_candidate_to_requirements,
    generate_career_plan,
    synthesize_career_assessment,
)
from ai_career_navigator.config import Settings
from ai_career_navigator.domain import (
    CandidateProfile,
    CareerGoal,
    CurrentMarketSnapshot,
    RequirementComparison,
    RoleAssessment,
)
from ai_career_navigator.market import (
    MarketPostingEvidence,
    MarketRequirementAnalysis,
    MarketRetrievalResult,
    RetainedSourceContent,
    SearchLimits,
    analyze_market_requirements,
    limits_from_settings,
    retrieve_combined_market,
    retrieve_current_market,
)
from ai_career_navigator.market.mcp.protocol import MarketSearchClient, StructuredJobSearchClient
from ai_career_navigator.models import ModelGateway
from ai_career_navigator.profile import CapabilityInferenceOutcome, infer_capabilities

CapabilityInferenceService = Callable[[CandidateProfile, ModelGateway], CapabilityInferenceOutcome]
MarketRetrievalService = Callable[
    [CareerGoal, MarketSearchClient], Awaitable[MarketRetrievalResult]
]
MarketProcessingService = Callable[..., MarketRequirementAnalysis]
MarketClientFactory = Callable[[], MarketSearchClient]
StructuredMarketClientFactory = Callable[[], StructuredJobSearchClient]
CandidateComparisonService = Callable[
    [CandidateProfile, MarketRequirementAnalysis, ModelGateway], CandidateComparisonResult
]
GapAnalysisService = Callable[
    [
        CandidateProfile,
        CareerGoal,
        CurrentMarketSnapshot,
        MarketRequirementAnalysis,
        list[RequirementComparison],
    ],
    GapAnalysisResult,
]
BridgeAnalysisService = Callable[
    [CandidateProfile, CareerGoal, RoleAssessment, MarketRequirementAnalysis, list[str]],
    BridgeAnalysisResult,
]
TimelineAnalysisService = Callable[
    [CareerGoal, RoleAssessment, BridgeAnalysisResult, CurrentMarketSnapshot],
    TimelineAnalysisResult,
]
CareerPlanGenerationService = Callable[..., CareerPlanGenerationResult]
CareerSynthesisService = Callable[
    [CandidateProfile, RoleAssessment, MarketRequirementAnalysis, ModelGateway | None],
    CareerAssessmentSynthesis,
]


@dataclass
class TransientMarketContentStore:
    """Process-local raw-content buffer; never serialized into graph state."""

    _runs: dict[UUID, tuple[RetainedSourceContent, ...]] = field(default_factory=dict)
    _posting_evidence: dict[UUID, tuple[MarketPostingEvidence, ...]] = field(default_factory=dict)
    _analyses: dict[UUID, MarketRequirementAnalysis] = field(default_factory=dict)

    def put(self, run_id: UUID, content: list[RetainedSourceContent]) -> list[UUID]:
        self._runs[run_id] = tuple(content)
        return [item.source.source_id for item in content]

    def get(self, run_id: UUID) -> list[RetainedSourceContent]:
        return list(self._runs.get(run_id, ()))

    def put_posting_evidence(
        self, run_id: UUID, evidence: list[MarketPostingEvidence]
    ) -> list[UUID]:
        """Keep structured provider-neutral evidence outside checkpoint state."""

        self._posting_evidence[run_id] = tuple(evidence)
        return [item.primary_source.source_id for item in evidence]

    def get_posting_evidence(self, run_id: UUID) -> list[MarketPostingEvidence]:
        return list(self._posting_evidence.get(run_id, ()))

    def get_processing_inputs(
        self, run_id: UUID
    ) -> list[MarketPostingEvidence] | list[RetainedSourceContent]:
        """Prefer structured posting evidence and retain legacy web-source compatibility."""

        evidence = self.get_posting_evidence(run_id)
        return evidence if evidence else self.get(run_id)

    def put_analysis(self, run_id: UUID, analysis: MarketRequirementAnalysis) -> None:
        self._analyses[run_id] = analysis

    def get_analysis(self, run_id: UUID) -> MarketRequirementAnalysis | None:
        return self._analyses.get(run_id)


@dataclass(frozen=True)
class WorkflowRuntimeContext:
    """Non-serializable services supplied to nodes at invocation time."""

    settings: Settings
    model_gateway: ModelGateway
    market_client_factory: MarketClientFactory
    content_store: TransientMarketContentStore
    structured_market_client_factory: StructuredMarketClientFactory | None = None
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("ai_career_navigator.orchestration")
    )
    capability_inference_service: CapabilityInferenceService = infer_capabilities
    market_retrieval_service: MarketRetrievalService = retrieve_current_market
    market_processing_service: MarketProcessingService = analyze_market_requirements
    # Explicit historical replay only; production never falls back on assessment failure.
    legacy_target_plan_pipeline: bool = False
    candidate_comparison_service: CandidateComparisonService = compare_candidate_to_requirements
    gap_analysis_service: GapAnalysisService = assess_candidate_accessibility
    career_synthesis_service: CareerSynthesisService = synthesize_career_assessment
    bridge_analysis_service: BridgeAnalysisService = assess_bridge_roles
    timeline_analysis_service: TimelineAnalysisService = assess_timeline
    career_plan_generation_service: CareerPlanGenerationService = generate_career_plan
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)

    async def retrieve_market(
        self,
        goal: CareerGoal,
        *,
        limits: SearchLimits,
        now: datetime,
    ) -> MarketRetrievalResult:
        """Select providers inside the service boundary, never inside graph nodes."""

        if self.structured_market_client_factory is not None:
            client = self.structured_market_client_factory()
            if getattr(client, "provider", None) == "JSEARCH":
                from ai_career_navigator.market.jsearch_service import retrieve_jsearch_market

                return await retrieve_jsearch_market(goal, client, limits=limits, now=now)
            return await retrieve_combined_market(
                goal,
                client,
                enrichment_client=self.market_client_factory(),
                limits=limits,
                now=now,
            )
        return await self.market_retrieval_service(
            goal,
            self.market_client_factory(),
            limits=limits,
            now=now,
        )


def retrieval_limits(settings: Settings) -> SearchLimits:
    return limits_from_settings(settings)
