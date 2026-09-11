import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest

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
    GoalType,
)
from ai_career_navigator.market.mcp.fake_client import FakeMarketSearchClient
from ai_career_navigator.market.mcp.protocol import StructuredJobSearchClient
from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.models.providers import FakeModelProvider
from ai_career_navigator.orchestration import (
    CareerWorkflowController,
    TransientMarketContentStore,
    WorkflowRuntimeContext,
    build_career_graph,
)

NOW = datetime(2026, 9, 3, 16, 0, tzinfo=UTC)


@pytest.fixture
def explicit_evidence() -> EvidenceItem:
    return EvidenceItem(
        evidence_type="skill",
        source_type="manual onboarding",
        source_reference="Skills",
        capability="REST APIs",
        description="Built REST APIs for production automation.",
        maturity_level=EvidenceMaturity.PRODUCTION,
        confirmation_status=EvidenceConfirmationStatus.EXPLICIT,
        confidence=ConfidenceLevel.HIGH,
        approved_by_user=True,
        created_at=NOW,
    )


@pytest.fixture
def approved_profile(explicit_evidence: EvidenceItem) -> CandidateProfile:
    python_evidence = explicit_evidence.model_copy(
        update={
            "evidence_id": uuid4(),
            "capability": "Python",
            "description": "Used Python in production automation delivery.",
        }
    )
    return CandidateProfile(
        career_stage=CareerStage.MID_CAREER,
        current_role="Automation Developer",
        current_location="Toronto, Canada",
        evidence_items=[explicit_evidence, python_evidence],
        approval_status=ApprovalStatus.APPROVED,
        created_at=NOW,
        confirmed_at=NOW,
    )


@pytest.fixture
def approved_goal() -> CareerGoal:
    return CareerGoal(
        goal_type=GoalType.TARGET_CAREER_PATH,
        target_role="AI Solutions Architect",
        target_timeline_months=24,
        target_location="Toronto, Canada",
        approval_status=ApprovalStatus.APPROVED,
        created_at=NOW,
        approved_at=NOW,
    )


def inference_json(evidence_id: object) -> str:
    return json.dumps(
        {
            "inferred_capabilities": [
                {
                    "capability": "Enterprise Integration",
                    "description": "Integration capability.",
                    "supporting_evidence_ids": [str(evidence_id)],
                    "proposed_maturity": "PRODUCTION",
                    "confidence": "MODERATE",
                }
            ],
            "limitations": [],
            "unresolved_areas": [],
        }
    )


def empty_inference_json() -> str:
    return json.dumps({"inferred_capabilities": [], "limitations": [], "unresolved_areas": []})


def requirement_json(quote: str = "Python required") -> str:
    return json.dumps(
        {
            "requirements": [
                {
                    "source_quote": quote,
                    "category": "TECHNICAL",
                    "normalized_capability": "Python",
                    "mandatory": True,
                    "preferred": False,
                    "years_required": None,
                    "maturity_expected": "PRODUCTION",
                    "confidence": "HIGH",
                }
            ],
            "limitations": [],
        }
    )


def make_controller(
    provider: FakeModelProvider,
    market_client: FakeMarketSearchClient | None = None,
    *,
    settings: Settings | None = None,
    structured_market_client: StructuredJobSearchClient | None = None,
) -> tuple[CareerWorkflowController, TransientMarketContentStore]:
    model_gateway = ModelGateway(
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
    content_store = TransientMarketContentStore()
    context = WorkflowRuntimeContext(
        settings=settings or Settings(max_retries=0),
        model_gateway=model_gateway,
        market_client_factory=lambda: market_client or FakeMarketSearchClient(),
        structured_market_client_factory=(
            (lambda: structured_market_client) if structured_market_client else None
        ),
        content_store=content_store,
        clock=lambda: NOW,
    )
    return CareerWorkflowController(build_career_graph(), context), content_store
