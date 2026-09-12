"""Transition contracts and real graph/UI wiring, with no external model calls."""

import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest

from ai_career_navigator.career.same_role import assessment_plan, build_inputs, is_same_role
from ai_career_navigator.career.transition import (
    REVIEW_INSTRUCTIONS,
    RULE_VERSION,
    SYSTEM_PROMPT,
    TransitionAssessment,
    TransitionReply,
    assess_career_transition,
    is_career_transition,
    transition_reference_issues,
    uses_consolidated_target_assessment,
)
from ai_career_navigator.domain import GoalType
from ai_career_navigator.orchestration.approval import PlanReviewAction
from ai_career_navigator.orchestration.invalidation import revision_invalidation
from tests.career.test_same_role import inputs as same_inputs  # noqa: F401
from tests.career.test_same_role import local_retrieval


@pytest.fixture
def inputs(request):
    profile, goal, evidence = request.getfixturevalue("same_inputs")
    title = "AI Engineer"
    body = (
        "AI Engineer\nBuild and evaluate AI services.\nBackend API integration experience required."
    )
    item = evidence[0]
    item = item.model_copy(
        update={
            "posting": item.posting.model_copy(update={"original_title": title}),
            "primary_source": item.primary_source.model_copy(update={"title": title}),
            "primary_content": item.primary_content.model_copy(
                update={"title": title, "markdown": body}
            ),
            "title_classification": "EXACT_TARGET",
        }
    )
    return (
        profile,
        goal.model_copy(update={"goal_type": GoalType.ROLE_TRANSITION, "target_role": title}),
        [item],
    )


def reply():
    return TransitionReply(
        role_picture="AI service integration with evaluation responsibility.",
        accessibility="NEAR_TERM_TARGET",
        confidence="LOW",
        rationale="Backend delivery transfers; AI evaluation experience needs clarification.",
        demonstrated_strengths=[
            dict(
                name="Backend service delivery",
                why_it_helps="Supports reliable service integration.",
                candidate_refs=["E1"],
            )
        ],
        competencies=[
            dict(
                name="AI service integration",
                context="COMMON",
                expectation="QUALIFICATION",
                status="TRANSFERABLE",
                reason="Production API work supports integration.",
                source_refs=["P1L3"],
                candidate_refs=["E1"],
                remaining_need="CLARIFY",
                transfer_explanation=(
                    "API delivery transfers; AI-specific evaluation is not established."
                ),
                development_focus="Confirm whether AI evaluation has been performed.",
            )
        ],
        opportunities=[
            dict(
                posting_ref="P1",
                direction="AI application engineering",
                fit="STRETCH",
                reason="AI-specific depth remains unconfirmed.",
            )
        ],
        actions=[
            dict(
                action="Document any AI evaluation work before choosing a learning project.",
                basis_competencies=["AI service integration"],
                action_type="EVIDENCE",
                completion_check="Existing evaluation experience or its absence is confirmed.",
            )
        ],
    )


class Gateway:
    def __init__(self, raw=None, reviewed=None):
        self.raw, self.reviewed, self.requests = raw or reply(), reviewed, []

    def generate_structured(self, **request):
        self.requests.append(request)
        if request["output_schema"].__name__.startswith("Leadership"):
            from tests.career.test_leadership import leadership_reply

            raw = leadership_reply(self.reviewed or self.raw).model_dump()
            return SimpleNamespace(structured_output={"corrections": [], "assessment": raw}
                                   if request["output_schema"].__name__ == "LeadershipReview"
                                   else raw)
        if request["metadata"]["task_type"] == "career_transition_quality_review":
            return SimpleNamespace(
                structured_output={
                    "corrections": [],
                    "assessment": (self.reviewed or self.raw).model_dump(),
                }
            )
        return SimpleNamespace(structured_output=self.raw.model_dump())


@pytest.mark.parametrize("target", ["AI Engineer", "Engineering Manager", "Accountant", "Welder"])
def test_transition_routing_is_generic_and_explicit(inputs, target):
    profile, goal, _ = inputs
    assert is_career_transition(profile, goal.model_copy(update={"target_role": target}))
    assert not is_same_role(profile, goal)
    assert not is_career_transition(
        profile, goal.model_copy(update={"goal_type": "TARGET_CAREER_PATH"})
    )
    assert uses_consolidated_target_assessment(
        profile, goal.model_copy(update={"goal_type": "TARGET_CAREER_PATH", "target_role": target})
    )
    assert uses_consolidated_target_assessment(
        profile,
        goal.model_copy(update={"goal_type": "LEADERSHIP_PROGRESSION", "target_role": target}),
    )
    assert not uses_consolidated_target_assessment(
        profile, goal.model_copy(update={"goal_type": "CAREER_EXPLORATION", "target_role": None})
    )


def test_shared_batch_preserves_transfer_and_strengths_and_plan_type(inputs):
    gateway = Gateway()
    result = assess_career_transition(*inputs, gateway)
    assert isinstance(result, TransitionAssessment)
    assert result.rule_version == RULE_VERSION
    assert not result.processing_issues
    assert result.competencies[0].status == "TRANSFERABLE"
    assert result.demonstrated_strengths[0].name == "Backend service delivery"
    assert [r["metadata"]["task_type"] for r in gateway.requests] == [
        "career_transition_assessment",
        "career_transition_quality_review",
    ]
    assert gateway.requests[0]["system_prompt"] == SYSTEM_PROMPT
    payload = json.loads(gateway.requests[0]["user_prompt"])
    assert payload["target_role"] == "AI Engineer"
    assert "target_seniority" in payload["goal_context"]
    assert "exclusions" in payload["goal_context"]
    assert "Personal portfolio" in str(payload["candidate"]["evidence"])
    plan = assessment_plan(result, *inputs[:2])
    assert plan.path_type == "DEVELOPMENT"
    assert plan.milestones[0].milestone_type == "EVIDENCE"
    assert plan.source_assessment_id == result.assessment_id
    assert "No fixed timeline" in plan.timing_basis
    assert plan.plan_status == "DRAFT"


def test_target_plan_selects_five_from_eight_related_descriptions_without_relabeling(inputs):
    profile, goal, evidence = inputs
    goal = goal.model_copy(
        update={
            "goal_type": GoalType.TARGET_CAREER_PATH,
            "search_expansion_permission": True,
        }
    )
    sources = [
        evidence[0].model_copy(
            update={
                "posting": evidence[0].posting.model_copy(
                    update={
                        "posting_id": uuid4(),
                        "employer": f"Employer {index}",
                    }
                ),
                "title_classification": "RELATED_TITLE",
            }
        )
        for index in range(8)
    ]
    _, selected, _, _ = build_inputs(profile, goal, sources)
    assert len(selected) == 5
    assert {item["scope"] for item in selected.values()} == {"RELATED_TITLE"}
    assert len({item["employer"] for item in selected.values()}) == 5
    # Explicitly disabling related-role expansion remains effective.
    _, excluded, _, _ = build_inputs(
        profile, goal.model_copy(update={"search_expansion_permission": False}), sources
    )
    assert not excluded


def test_leadership_cohort_prioritizes_target_discipline_and_level_before_length(inputs):
    from ai_career_navigator.market.schemas import PostingSeniority

    profile, goal, evidence = inputs
    goal = goal.model_copy(update={
        "goal_type": GoalType.LEADERSHIP_PROGRESSION,
        "target_role": "Software Engineering Manager",
        "search_expansion_permission": True,
    })
    items = []
    cases = [
        ("Manufacturing Engineering Manager", "Manage factory tooling. " * 150, "STANDARD"),
        ("Senior Software Delivery Manager", "Lead delivery across teams. " * 100, "SENIOR"),
        *[("Software Delivery Manager", "Lead delivery for a team.", "STANDARD")] * 5,
    ]
    for index, (title, body, level) in enumerate(cases):
        original = evidence[0]
        items.append(original.model_copy(update={
            "posting": original.posting.model_copy(update={
                "posting_id": uuid4(), "employer": f"Employer {index}", "original_title": title,
            }),
            "primary_content": original.primary_content.model_copy(
                update={"title": title, "markdown": body}
            ),
            "title_classification": "RELATED_TITLE",
            "seniority_classification": PostingSeniority(level),
        }))
    _, selected, _, _ = build_inputs(profile, goal, items)
    assert len(selected) == 5
    assert {item["title"] for item in selected.values()} == {"Software Delivery Manager"}
    assert len({item["employer"] for item in selected.values()}) == 5
    # Off-discipline/level results remain in discovery, not deleted to inflate fit.
    assert len(items) == 7


@pytest.mark.parametrize(
    "change,expected",
    [
        ({"candidate_refs": []}, "positive comparison"),
        ({"transfer_explanation": None}, "what transfers"),
        ({"development_focus": None}, "outstanding need"),
        ({"source_refs": ["P99L9"]}, "unknown source"),
    ],
)
def test_transfer_integrity_is_checked(inputs, change, expected):
    raw = reply()
    raw = raw.model_copy(update={"competencies": [raw.competencies[0].model_copy(update=change)]})
    _, sources, lines, candidates = build_inputs(*inputs)
    assert any(
        expected in issue for issue in transition_reference_issues(raw, sources, lines, candidates)
    )


def test_unresolved_strength_reference_stops_plan_and_removes_bad_strength(inputs):
    raw = reply()
    raw = raw.model_copy(
        update={
            "demonstrated_strengths": [
                raw.demonstrated_strengths[0].model_copy(update={"candidate_refs": ["E999"]}),
            ]
        }
    )
    gateway = Gateway(raw)
    result = assess_career_transition(*inputs, gateway)
    assert result.processing_issues
    assert result.demonstrated_strengths == []
    assert len(gateway.requests) == 2  # one bounded repair; not an endless retry loop
    assert assessment_plan(result, *inputs[:2]) is None


def test_final_review_is_revalidated(inputs):
    raw = reply()
    bad = raw.model_copy(
        update={
            "competencies": [
                raw.competencies[0].model_copy(update={"source_refs": ["P99L9"]}),
            ]
        }
    )
    result = assess_career_transition(*inputs, Gateway(reviewed=bad))
    assert result.processing_issues
    assert assessment_plan(result, *inputs[:2]) is None


def test_transition_prompt_distinguishes_unknowns_from_deficits():
    for phrase in [
        "Missing profile text alone calls for CLARIFY",
        "No fixed timeline is valid",
        "No invented certifications",
        "Projects,",
        "No EQ or personality",
        "do not automatically become years",
        "not automatically mean aspirational",
    ]:
        assert phrase in SYSTEM_PROMPT


@pytest.mark.parametrize("goal_type", [
    GoalType.ROLE_TRANSITION, GoalType.TARGET_CAREER_PATH, GoalType.LEADERSHIP_PROGRESSION,
])
@pytest.mark.parametrize("title_scope", ["EXACT_TARGET", "RELATED_TITLE"])
def test_transition_graph_plan_review_and_invalidation(inputs, tmp_path, goal_type, title_scope):
    from ai_career_navigator.config import Settings
    from ai_career_navigator.models.providers import FakeModelProvider
    from ai_career_navigator.ui.live_workflow import build_live_workflow_runtime

    runtime = build_live_workflow_runtime(
        Settings(run_audit_directory=tmp_path),
        provider_override=FakeModelProvider(),
    )
    gateway = Gateway()
    profile, goal, evidence = inputs
    goal = goal.model_copy(update={"goal_type": goal_type, "search_expansion_permission": True})
    evidence = [item.model_copy(update={"title_classification": title_scope}) for item in evidence]

    async def retrieve(goal, _client, **kwargs):
        return local_retrieval(goal, evidence)

    def forbidden(*args, **kwargs):
        raise AssertionError("Transition must not run legacy comparison/scoring")

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
            confirmed_profile=profile,
            confirmed_goal=goal,
            capability_inference_requested=False,
        )
    )
    assert result.interrupted
    assert result.state["transition_assessment"].accessibility == "NEAR_TERM_TARGET"
    assert result.state["same_role_assessment"] is None
    assert result.state["canonical_target_role_profile"] is None
    assert len(gateway.requests) == 2
    assert result.state["confirmed_goal"].goal_type == goal_type
    payload = json.loads(gateway.requests[0]["user_prompt"])
    assert payload["goal_context"]["goal_type"] == goal_type
    audit = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert audit["mode"] == "CAREER_TRANSITION"
    assert audit["goal_type"] == goal_type
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
    cleared = revision_invalidation(result.state, PlanReviewAction.REVISE_GOAL)
    assert cleared["transition_assessment"] is None and cleared["career_plan"] is None


def test_transition_analysis_and_plan_native_ui(inputs):
    from streamlit.testing.v1 import AppTest

    result = assess_career_transition(*inputs, Gateway())
    state = {
        "transition_assessment": result,
        "career_plan": assessment_plan(result, *inputs[:2]),
        "confirmed_goal": inputs[1],
    }

    def page():
        import streamlit as st

        from ai_career_navigator.ui.pages.assessment import render_assessment
        from ai_career_navigator.ui.pages.live_views import render_live_plan

        if st.session_state.get("plan"):
            render_live_plan(st.session_state.result)
        else:
            render_assessment(st.session_state.result)

    app = AppTest.from_function(page, default_timeout=15)
    app.session_state.result = state
    app.run()
    assert not app.exception
    assert "Transferable" in str(app.table[0].value)
    assert "Questions before deciding" in [item.value for item in app.subheader]
    assert any("Strengths you bring" in item.value for item in app.subheader)
    app.session_state.plan = True
    app.run()
    assert not app.exception
    assert any("No fixed timeline" in item.value for item in app.caption)


def test_transition_review_uses_specific_checks_without_old_bundle_fallback(inputs):
    gateway = Gateway()
    assess_career_transition(*inputs, gateway)
    prompt = gateway.requests[1]["system_prompt"]
    assert prompt == SYSTEM_PROMPT + REVIEW_INSTRUCTIONS
    for check in ["BASE VS SPECIALTY", "MIXED EVIDENCE", "UNKNOWN VS ABSENT", "ONE DIRECTION"]:
        assert check in prompt
    assert "split it or mark partial" not in prompt
    assert "forced positive verdict" in prompt


def test_leadership_contract_keeps_target_and_scope_without_promoting_mentoring(inputs):
    from ai_career_navigator.career.leadership import SYSTEM_PROMPT as leadership_prompt

    profile, goal, evidence = inputs
    goal = goal.model_copy(update={
        "goal_type": GoalType.LEADERSHIP_PROGRESSION,
        "target_role": "Software Engineering Manager",
    })
    gateway = Gateway()
    assess_career_transition(profile, goal, evidence, gateway)
    payload = json.loads(gateway.requests[0]["user_prompt"])
    assert payload["target_role"] == "Software Engineering Manager"
    assert payload["goal_context"]["goal_type"] == "LEADERSHIP_PROGRESSION"
    assert gateway.requests[0]["system_prompt"] == leadership_prompt
    for phrase in [
        "toward target_role", "Missing text never proves absence",
        "Only CORE postings define", "Do not default to coding",
        "No fixed timeline is", "Mentoring does not establish hiring",
    ]:
        assert phrase in gateway.requests[0]["system_prompt"]
    assert "Review contradictions" in gateway.requests[1]["system_prompt"]


def test_transition_v3_contract_separates_readiness_from_direction_and_safe_practice(inputs):
    gateway = Gateway()
    result = assess_career_transition(*inputs, gateway)
    assert result.rule_version == "career-transition-assessment-v5-concise-v3-fit-scope-all-directions"
    for request in gateway.requests:
        for phrase in [
            "TWO DISTINCT CONCLUSIONS",
            "readiness for the supplied opportunities NOW",
            "not a calendar estimate",
            "qualified supervision and practical assessment",
            "employer tests and optional credentials",
            "Only assert a legal requirement when authoritative information is supplied",
            "Generic employment wording must not inherit a tool",
        ]:
            assert phrase in request["system_prompt"]
    properties = TransitionReply.model_json_schema()["properties"]
    assert "Current readiness" in properties["rationale"]["description"]
    assert "distinct from readiness now" in properties["role_picture"]["description"]
    assert result.rationale == reply().rationale
    assert result.role_picture == reply().role_picture
    assert "SAFE PRACTICE" in gateway.requests[1]["system_prompt"]


def test_transition_v3_does_not_change_shared_call_bounds(inputs):
    gateway = Gateway()
    assess_career_transition(*inputs, gateway)
    assert len(gateway.requests) == 2
    assert all(r["max_tokens"] == 30000 and r["max_retries"] == 0 for r in gateway.requests)
    assert all(r["metadata"]["prompt_version"] == RULE_VERSION for r in gateway.requests)


def test_same_role_review_does_not_receive_transition_override(request):
    from ai_career_navigator.career.same_role import REVIEW_INSTRUCTIONS as default_review
    from ai_career_navigator.career.same_role import SYSTEM_PROMPT as same_prompt
    from ai_career_navigator.career.same_role import assess_same_role
    from tests.career.test_same_role import Gateway as SameGateway
    from tests.career.test_same_role import reply as same_reply

    gateway = SameGateway([same_reply()])
    assess_same_role(*request.getfixturevalue("same_inputs"), gateway)
    assert gateway.requests[1]["system_prompt"] == same_prompt + default_review
    assert "BASE VS SPECIALTY" not in gateway.requests[1]["system_prompt"]


def test_split_base_and_specialty_survive_review_and_keep_conditional_plan(inputs):
    raw = reply().model_dump()
    base = raw["competencies"][0]
    raw["competencies"] = [
        {
            **base,
            "name": "API development",
            "status": "DEMONSTRATED",
            "remaining_need": "NONE",
            "development_focus": None,
            "transfer_explanation": None,
        },
        {
            **base,
            "name": "Vendor API platform",
            "context": "SPECIALIST",
            "status": "NOT_ESTABLISHED",
            "candidate_refs": [],
            "transfer_explanation": None,
            "remaining_need": "CLARIFY",
            "development_focus": "Confirm prior platform use.",
        },
    ]
    raw["actions"] = [
        {
            "action": "If platform experience is absent, build a small integration.",
            "basis_competencies": ["Vendor API platform"],
            "action_type": "PROJECT",
            "completion_check": "Existing experience or a working integration is documented.",
        }
    ]
    raw = TransitionReply.model_validate(raw)
    result = assess_career_transition(*inputs, Gateway(raw))
    assert not result.processing_issues
    assert [c.status for c in result.competencies] == ["DEMONSTRATED", "NOT_ESTABLISHED"]
    plan = assessment_plan(result, *inputs[:2])
    assert plan.milestones[0].action.startswith("If platform experience is absent")
    assert plan.milestones[0].basis == "Vendor API platform"
    assert all(c.status != "TRANSFERABLE" for c in result.competencies)
