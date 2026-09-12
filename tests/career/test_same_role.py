"""Same-role contract, production routing, provenance and review regressions."""

import asyncio
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from ai_career_navigator.career.same_role import (
    AssessmentReply,
    assess_same_role,
    assessment_plan,
    build_inputs,
    is_same_role,
    reference_issues,
)
from ai_career_navigator.domain import CareerGoal
from ai_career_navigator.orchestration.approval import PlanReviewAction
from ai_career_navigator.orchestration.invalidation import revision_invalidation
from ai_career_navigator.profile.service import build_candidate_profile
from ai_career_navigator.ui.demo_data import sample_profile_draft

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from check_local_descriptions import load_descriptions, local_retrieval  # noqa: E402


@pytest.fixture
def inputs(tmp_path):
    (tmp_path / "Senior Software Engineer 3.txt").write_text(
        "Senior Java Developer\nMandatory Skills: Java\nBuild production Java services.",
        encoding="utf-8",
    )
    evidence, _ = load_descriptions(tmp_path, "Senior Java Developer")
    profile = build_candidate_profile(sample_profile_draft(), approved=True)
    goal = CareerGoal(
        goal_type="CURRENT_MARKET_ANALYSIS",
        target_role="Senior Java Developer",
        target_location="Toronto, Canada",
        approval_status="APPROVED",
        approved_at=profile.confirmed_at,
    )
    return profile, goal, evidence


def reply():
    return AssessmentReply(
        role_picture="Production Java backend delivery.",
        accessibility="APPLY_SELECTIVELY",
        rationale="Backend experience aligns; check each opening's depth.",
        confidence="MODERATE",
        competencies=[
            dict(
                name="Java backend development",
                context="COMMON",
                expectation="QUALIFICATION",
                status="DEMONSTRATED",
                reason="Employment describes production Java delivery.",
                source_refs=["P1L2"],
                candidate_refs=["E1"],
            )
        ],
        opportunities=[
            dict(
                posting_ref="P1",
                direction="Java backend",
                fit="CONSIDER",
                reason="Relevant core work.",
            )
        ],
        actions=[
            dict(
                action="Prepare a production backend delivery example.",
                basis_competencies=["Java backend development"],
                completion_check="An accurate example describes personal delivery.",
            )
        ],
    )


class Gateway:
    def __init__(self, responses):
        self.responses, self.requests = iter(responses), []

    def generate_structured(self, **request):
        self.requests.append(request)
        if request["metadata"]["task_type"] == "same_role_quality_review":
            return SimpleNamespace(
                structured_output={"corrections": [], "assessment": self.last.model_dump()}
            )
        self.last = next(self.responses)
        return SimpleNamespace(structured_output=self.last.model_dump())


def test_route_is_generic_and_does_not_capture_transition(inputs):
    profile, goal, _ = inputs
    assert is_same_role(profile, goal)
    assert is_same_role(
        profile.model_copy(update={"current_role": "Senior Accountant"}),
        goal.model_copy(update={"target_role": " senior ACCOUNTANT "}),
    )
    assert not is_same_role(profile, goal.model_copy(update={"target_role": "Engineering Manager"}))
    assert not is_same_role(profile, goal.model_copy(update={"goal_type": "CAREER_TRANSITION"}))


def test_short_references_full_text_and_deduplicated_candidate_records(inputs):
    profile, goal, evidence = inputs
    payload, sources, lines, candidates = build_inputs(*inputs)
    assert lines["P1L2"] == "Mandatory Skills: Java"
    assert len(candidates) == 4  # employment, one project, education, certification
    assert "evidence_id" not in json.dumps(payload)
    assert sources["P1"]["posting_id"] == str(evidence[0].posting.posting_id)
    assert payload["timeline_preference_months"] is None


def test_accepts_legitimate_mandatory_wording_without_lexical_gates(inputs):
    gateway = Gateway([reply()])
    result = assess_same_role(*inputs, gateway)
    assert not result.processing_issues
    assert len(gateway.requests) == 2
    assert result.accessibility == "APPLY_SELECTIVELY"
    plan = assessment_plan(result, *inputs[:2])
    assert plan.plan_status == "DRAFT"
    assert plan.source_assessment_id == result.assessment_id
    assert plan.milestones[0].supporting_evidence_ids == [inputs[0].evidence_items[0].evidence_id]
    assert "No fixed timeline" in plan.timing_basis
    assert plan.milestones[0].month_end == 0


def test_bad_reference_repairs_once_then_retains_independent_items(inputs):
    good = reply()
    broken = good.model_copy(
        update={
            "competencies": [
                good.competencies[0],
                good.competencies[0].model_copy(
                    update={
                        "name": "Messaging",
                        "candidate_refs": ["E999"],
                    }
                ),
            ]
        }
    )
    gateway = Gateway([broken, broken])
    result = assess_same_role(*inputs, gateway)
    assert len(gateway.requests) == 2
    assert len(result.competencies) == 1
    assert result.processing_issues
    assert assessment_plan(result, *inputs[:2]) is None
    assert "processing issue" in result.rationale


def test_correction_can_recover_and_plan_actions_need_real_basis(inputs):
    broken = reply().model_copy(
        update={
            "actions": [
                reply()
                .actions[0]
                .model_copy(update={"basis_competencies": ["Invented certification"]})
            ]
        }
    )
    gateway = Gateway([broken, reply()])
    result = assess_same_role(*inputs, gateway)
    assert not result.processing_issues
    assert len(gateway.requests) == 3


def test_insufficient_reply_has_no_plan(inputs):
    raw = reply().model_copy(
        update={
            "accessibility": "INSUFFICIENT_CANDIDATE_EVIDENCE",
            "confidence": "INSUFFICIENT",
            "actions": [],
        }
    )
    result = assess_same_role(*inputs, Gateway([raw]))
    assert assessment_plan(result, *inputs[:2]) is None


def test_no_input_does_not_call_model(inputs):
    gateway = Gateway([])
    with pytest.raises(ValueError):
        assess_same_role(*inputs[:2], [], gateway)
    assert not gateway.requests


def test_positive_verdict_without_demonstration_is_rejected(inputs):
    raw = reply().model_copy(update={"competencies": []})
    _, sources, lines, candidates = build_inputs(*inputs)
    assert any(
        "positive verdict" in issue for issue in reference_issues(raw, sources, lines, candidates)
    )


def test_one_employer_specialist_match_can_support_limited_fit_and_plan(inputs):
    proposal = reply().model_copy(
        update={
            "competencies": [reply().competencies[0].model_copy(update={"context": "SPECIALIST"})],
            "limitations": ["One reviewed role only; not a market-wide conclusion."],
        }
    )
    gateway = Gateway([proposal])
    result = assess_same_role(*inputs, gateway)
    assert len(result.posting_sources) == 1
    assert not result.processing_issues
    assert result.accessibility == "APPLY_SELECTIVELY"
    assert assessment_plan(result, *inputs[:2]) is not None
    assert len(gateway.requests) == 2


def test_reviewer_reclassifying_core_as_specialist_does_not_invalidate_fit(inputs):
    class ReviewerGateway(Gateway):
        def generate_structured(self, **request):
            response = super().generate_structured(**request)
            if request["metadata"]["task_type"] == "same_role_quality_review":
                response.structured_output["assessment"]["competencies"][0]["context"] = (
                    "SPECIALIST"
                )
            return response

    result = assess_same_role(*inputs, ReviewerGateway([reply()]))
    assert result.accessibility == "APPLY_SELECTIVELY"
    assert not result.processing_issues
    assert assessment_plan(result, *inputs[:2]) is not None


def test_processing_failure_withholds_verdict_instead_of_diagnosing_candidate(inputs):
    broken = reply().model_copy(
        update={
            "competencies": [
                reply().competencies[0].model_copy(update={"candidate_refs": ["E999"]})
            ]
        }
    )
    result = assess_same_role(*inputs, Gateway([broken, broken]))
    assert result.accessibility is None
    assert result.processing_issues == ["competencies[0]: unknown candidate reference"]
    assert assessment_plan(result, *inputs[:2]) is None
    assert "Assessment needs review" in result.rationale


def test_small_sample_does_not_automatically_upgrade_a_negative_verdict(inputs):
    from ai_career_navigator.domain import CandidateAccessibility

    cautious = reply().model_copy(update={"accessibility": CandidateAccessibility.ASPIRATIONAL})
    result = assess_same_role(*inputs, Gateway([cautious]))
    assert not result.processing_issues
    assert result.accessibility == "ASPIRATIONAL"


def test_fit_scope_prompt_keeps_factual_safeguards(inputs):
    from ai_career_navigator.career.same_role import SYSTEM_PROMPT

    assert "Employer count does not determine specialization" in SYSTEM_PROMPT
    assert "sample size alone" in SYSTEM_PROMPT
    assert "Projects are not production" in SYSTEM_PROMPT
    assert "Missing facts are not proven inability" in SYSTEM_PROMPT
    assert "No fixed timeline is a valid preference" in SYSTEM_PROMPT


def test_source_ids_are_not_plan_completion_checks(inputs):
    raw = reply().model_copy(
        update={"actions": [reply().actions[0].model_copy(update={"completion_check": "P1L2, E1"})]}
    )
    _, sources, lines, candidates = build_inputs(*inputs)
    assert any(
        "plain-language" in issue for issue in reference_issues(raw, sources, lines, candidates)
    )


def test_checkpoint_retains_only_cited_source_excerpts(inputs):
    result = assess_same_role(*inputs, Gateway([reply()]))
    assert set(result.source_lines) == {"P1L2"}


def test_analysis_and_plan_render_same_assessment(inputs):
    from streamlit.testing.v1 import AppTest

    assessment = assess_same_role(*inputs, Gateway([reply()]))
    plan = assessment_plan(assessment, *inputs[:2])
    # The complete typed saved state is covered by the live run. This focused UI
    # test uses already-validated domain objects without live calls.
    state = {"same_role_assessment": assessment, "career_plan": plan, "confirmed_goal": inputs[1]}

    def page():
        import streamlit as st

        from ai_career_navigator.ui.pages.assessment import render_assessment
        from ai_career_navigator.ui.pages.live_views import render_live_plan

        if st.session_state.get("page") == "plan":
            render_live_plan(st.session_state.result)
        else:
            render_assessment(st.session_state.result)

    app = AppTest.from_function(page)
    app.session_state.result = state
    app.run()
    assert not app.exception
    assert "Demonstrated" in str(app.table[0].value)
    app.session_state.page = "plan"
    app.run()
    assert not app.exception
    assert not any(button.label == "Approve Plan" for button in app.button)


def test_invalidation_clears_new_assessment():
    update = revision_invalidation({}, PlanReviewAction.EDIT_PROFILE_OR_PREFERENCES)
    assert "same_role_assessment" in update and update["same_role_assessment"] is None
    assert update["career_plan"] is None


def test_production_graph_bypasses_old_rules_and_preserves_exact_plan_review(inputs):
    from ai_career_navigator.config import Settings
    from ai_career_navigator.models.providers import FakeModelProvider
    from ai_career_navigator.ui.live_workflow import build_live_workflow_runtime

    runtime = build_live_workflow_runtime(Settings(), provider_override=FakeModelProvider())
    gateway = Gateway([reply()])

    async def retrieve(goal, _client, **kwargs):
        return local_retrieval(goal, inputs[2])

    def forbidden(*args, **kwargs):
        raise AssertionError("Legacy extraction/comparison must not run")

    runtime.controller._context = replace(
        runtime.controller._context,
        market_retrieval_service=retrieve,
        structured_market_client_factory=None,
        market_client_factory=lambda: None,
        model_gateway=gateway,
        market_processing_service=forbidden,
        candidate_comparison_service=forbidden,
        gap_analysis_service=forbidden,
        career_synthesis_service=forbidden,
    )
    thread = str(uuid4())
    result = asyncio.run(
        runtime.controller.start(
            thread_id=thread,
            confirmed_profile=inputs[0],
            confirmed_goal=inputs[1],
            capability_inference_requested=False,
        )
    )
    assert result.interrupted
    assert result.state["same_role_assessment"].accessibility == "APPLY_SELECTIVELY"
    assert result.state["canonical_target_role_profile"] is None
    plan = result.state["career_plan"]
    with pytest.raises(ValueError):
        asyncio.run(
            runtime.controller.submit_plan_action(
                thread_id=thread,
                plan_id=plan.plan_id,
                plan_version=plan.plan_version + 1,
                action=PlanReviewAction.APPROVE_AND_SAVE,
            )
        )
    approved = asyncio.run(
        runtime.controller.submit_plan_action(
            thread_id=thread,
            plan_id=plan.plan_id,
            plan_version=plan.plan_version,
            action=PlanReviewAction.APPROVE_AND_SAVE,
        )
    )
    assert approved.state["career_plan"].plan_status == "APPROVED"
    assert len(gateway.requests) == 2
