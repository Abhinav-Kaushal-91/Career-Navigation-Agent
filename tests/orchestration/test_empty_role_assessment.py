"""Empty retrieval must not masquerade as a model or candidate failure."""

import json
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from ai_career_navigator.config import Settings
from ai_career_navigator.domain import GoalType
from ai_career_navigator.market.schemas import MarketProviderSummary
from ai_career_navigator.orchestration.nodes import market_processing
from ai_career_navigator.orchestration.routing import route_after_market_processing
from ai_career_navigator.orchestration.state import WorkflowStatus
from tests.career.test_same_role import inputs as same_inputs  # noqa: F401


@pytest.fixture
def inputs(request):
    return request.getfixturevalue("same_inputs")


@pytest.mark.parametrize("transition", [False, True])
@pytest.mark.parametrize("raw_count", [0, 5])
def test_empty_sources_preserve_audit_and_stop_without_model(
    inputs, tmp_path, transition, raw_count
):
    profile, goal, _ = inputs
    if transition:
        goal = goal.model_copy(
            update={"goal_type": GoalType.ROLE_TRANSITION, "target_role": "AI Engineer"}
        )
    gateway = Mock()
    state = {
        "run_id": uuid4(),
        "confirmed_profile": profile,
        "confirmed_goal": goal,
        "limitations": ["Original retrieval limitation"],
        "market_provider_summary": MarketProviderSummary(raw_source_count=raw_count),
    }
    runtime = SimpleNamespace(
        context=SimpleNamespace(
            content_store=SimpleNamespace(get_processing_inputs=lambda _: []),
            model_gateway=gateway,
            legacy_target_plan_pipeline=False,
            settings=Settings(run_audit_directory=tmp_path),
            clock=lambda: profile.confirmed_at,
            logger=logging.getLogger(__name__),
        )
    )
    result = market_processing(state, runtime)
    assert result["workflow_status"] is WorkflowStatus.INSUFFICIENT_EVIDENCE
    assert result["last_error"] is None
    assert result["candidate_accessibility"] is None
    assert result["career_plan"] is None
    assert "Original retrieval limitation" in result["limitations"]
    assert route_after_market_processing(result) == "end"
    gateway.generate_structured.assert_not_called()
    saved = json.loads(Path(result["audit_artifact_path"]).read_text())
    assert saved["retrieval_summary"]["raw_source_count"] == raw_count
    assert "confirmed_profile" not in saved


def test_missing_transient_content_is_not_an_empty_provider_result(inputs, tmp_path):
    profile, goal, _ = inputs
    state = {
        "run_id": uuid4(),
        "confirmed_profile": profile,
        "confirmed_goal": goal,
        "market_source_ids": [uuid4()],
        "limitations": ["Retained search facts"],
    }
    gateway = Mock()
    runtime = SimpleNamespace(
        context=SimpleNamespace(
            content_store=SimpleNamespace(get_processing_inputs=lambda _: []),
            model_gateway=gateway,
            legacy_target_plan_pipeline=False,
            settings=Settings(run_audit_directory=tmp_path),
            clock=lambda: profile.confirmed_at,
            logger=logging.getLogger(__name__),
        )
    )
    result = market_processing(state, runtime)
    assert result["workflow_status"] is WorkflowStatus.FAILED
    assert "Retained search facts" in result["limitations"]
    gateway.generate_structured.assert_not_called()
