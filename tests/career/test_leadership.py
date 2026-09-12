"""Structured leadership decisions, repair and plan propagation without live calls."""

from types import SimpleNamespace

import pytest

from ai_career_navigator.career.leadership import (
    LeadershipAction,
    LeadershipAssessment,
    LeadershipReply,
    assess_leadership,
    leadership_issues,
)
from ai_career_navigator.career.same_role import assessment_plan, build_inputs
from ai_career_navigator.domain import CandidateAccessibility
from tests.career.test_transition import inputs as transition_inputs  # noqa: F401
from tests.career.test_transition import reply, same_inputs  # noqa: F401


@pytest.fixture
def inputs(request):
    return request.getfixturevalue("transition_inputs")


def leadership_reply(raw=None):
    data = (raw or reply()).model_dump()
    data.update(
        benchmark=[dict(posting_ref="P1", use="CORE", reason="Target work.")],
        current_readiness="UNCONFIRMED",
    )
    for item in data["competencies"]:
        item.update(
            applicability="TARGET",
            evidence_state="UNKNOWN",
            blocks_readiness=True,
            shortfall_quote=None,
        )
    for action in data["actions"]:
        action.update(purpose="CLARIFY", after_clarifying=[])
    return LeadershipReply.model_validate(data)


def check(inputs, draft):
    _, sources, lines, candidates = build_inputs(*inputs)
    return leadership_issues(draft, sources, lines, candidates)


def test_valid_unknown_does_not_become_shortfall(inputs):
    assert check(inputs, leadership_reply()) == []


def test_optional_repeated_focus_text_does_not_block_structured_unknown(inputs):
    draft = leadership_reply()
    draft = draft.model_copy(
        update={
            "competencies": [draft.competencies[0].model_copy(update={"development_focus": None})]
        }
    )
    assert check(inputs, draft) == []


@pytest.mark.parametrize(
    "changes,message",
    [
        ({"remaining_need": "BUILD_EXPERIENCE"}, "require clarification"),
        (
            {
                "evidence_state": "CONFIRMED_SHORTFALL",
                "remaining_need": "BUILD_EXPERIENCE",
                "shortfall_quote": "Has never managed people",
            },
            "exact candidate excerpt",
        ),
        ({"applicability": "CONTEXT"}, "context cannot become"),
    ],
)
def test_contradictory_comparisons_are_repaired_not_used(inputs, changes, message):
    draft = leadership_reply()
    draft = draft.model_copy(
        update={"competencies": [draft.competencies[0].model_copy(update=changes)]}
    )
    assert any(message in item for item in check(inputs, draft))


def test_unconfirmed_partial_cannot_claim_development_required(inputs):
    draft = leadership_reply().model_copy(update={"current_readiness": "DEVELOPMENT_REQUIRED"})
    assert any("confirmed material shortfall" in item for item in check(inputs, draft))


def test_context_posting_cannot_define_target_comparison(inputs):
    draft = leadership_reply()
    draft = draft.model_copy(
        update={"benchmark": [draft.benchmark[0].model_copy(update={"use": "CONTEXT"})]}
    )
    assert any("core benchmark support" in item for item in check(inputs, draft))


def development(draft, conditions=True):
    return LeadershipAction(
        action="Seek an authorized assignment to develop the missing responsibility.",
        action_type="EXPERIENCE",
        purpose="DEVELOP",
        basis_competencies=[draft.competencies[0].name],
        after_clarifying=[draft.competencies[0].name] if conditions else [],
        completion_check="An authorized assignment demonstrates the responsibility.",
    )


@pytest.mark.parametrize("prior,condition", [(False, True), (True, False)])
def test_unknown_development_needs_prior_clarification_and_explicit_condition(
    inputs, prior, condition
):
    draft = leadership_reply()
    draft = draft.model_copy(
        update={"actions": ([*draft.actions] if prior else []) + [development(draft, condition)]}
    )
    assert any("clarify unknown bases first" in issue for issue in check(inputs, draft))


def test_conditions_survive_into_action_completion_and_plan(inputs):
    draft = leadership_reply()
    apply = draft.actions[0].model_copy(update={
        "purpose": "APPLY", "action": "Apply after answering the questions.",
        "completion_check": "Applications submitted.",
    })
    draft = draft.model_copy(update={"actions": [*draft.actions, development(draft), apply]})
    requests = []

    class Gateway:
        def generate_structured(self, **request):
            requests.append(request)
            data = draft.model_dump()
            if request["metadata"]["task_type"].endswith("quality_review"):
                data = {"assessment": data, "corrections": []}
            return SimpleNamespace(structured_output=data)

    result = assess_leadership(*inputs, Gateway())
    assert not result.processing_issues
    assert [r["temperature"] for r in requests] == [0.1, 0]
    assert "before judging whether you should apply now" in result.rationale
    condition = "Only if your review confirms the relevant experience is missing"
    assert condition in result.actions[1].action
    assert condition in result.actions[1].completion_check
    plan = assessment_plan(result, *inputs[:2])
    assert condition in plan.milestones[1].action
    assert condition in plan.milestones[1].measurable_outcome
    assert "Only if a fresh readiness review confirms" in plan.milestones[2].action
    assert "Otherwise, defer" in plan.milestones[2].action
    assert "apply-or-defer" in plan.milestones[2].measurable_outcome
    assert "No fixed timeline" in plan.timing_basis
    assert LeadershipAssessment.model_validate(result.model_dump()) == result


def test_final_review_contradiction_withholds_plan(inputs):
    valid = leadership_reply()
    invalid = valid.model_copy(update={
        "current_readiness": "READY", "accessibility": CandidateAccessibility.APPLY_NOW,
    })

    class Gateway:
        def generate_structured(self, **request):
            if request["metadata"]["task_type"].endswith("quality_review"):
                return SimpleNamespace(
                    structured_output={
                        "assessment": invalid.model_dump(),
                        "corrections": [],
                    }
                )
            return SimpleNamespace(structured_output=valid.model_dump())

    result = assess_leadership(*inputs, Gateway())
    assert result.processing_issues
    assert result.accessibility is None
    assert assessment_plan(result, *inputs[:2]) is None


def test_invalid_semantics_trigger_bounded_repair_and_no_plan_if_unresolved(inputs):
    draft = leadership_reply().model_copy(update={"current_readiness": "DEVELOPMENT_REQUIRED"})
    requests = []

    class Gateway:
        def generate_structured(self, **request):
            requests.append(request)
            return SimpleNamespace(structured_output=draft.model_dump())

    result = assess_leadership(*inputs, Gateway())
    assert [r["temperature"] for r in requests] == [0.1, 0.0]
    assert result.processing_issues
    assert result.accessibility is None
    assert assessment_plan(result, *inputs[:2]) is None


@pytest.mark.parametrize("readiness", ["READY", "UNCONFIRMED", "DEVELOPMENT_REQUIRED"])
def test_apply_condition_and_defer_outcome_are_stored_in_exact_plan_version(readiness):
    from ai_career_navigator.career.leadership import finalize_leadership

    draft = leadership_reply()
    apply = draft.actions[0].model_copy(update={
        "purpose": "APPLY",
        "action": "Apply once management questions are answered.",
        "completion_check": "Applications are submitted.",
    })
    result = SimpleNamespace(
        processing_issues=[], current_readiness=readiness, actions=[apply], competencies=[],
        model_copy=lambda *, update: SimpleNamespace(**update),
    )
    finalized = finalize_leadership(result)
    action = finalized.actions[0]
    assert "Only if a fresh readiness review confirms" in action.action
    assert "employer's requirements" in action.action
    assert "Otherwise, defer" in action.action
    assert "apply-or-defer decision" in action.completion_check
    assert "Applications are submitted" not in action.completion_check


def test_leadership_prompt_preserves_formal_management_boundary_and_compact_copy():
    from ai_career_navigator.career.leadership import REVIEW_INSTRUCTIONS, SYSTEM_PROMPT

    assert "not formal people" in SYSTEM_PROMPT
    assert "at most three direct questions" in SYSTEM_PROMPT
    assert "not proof of readiness" in REVIEW_INSTRUCTIONS
    assert "employer inventory" in LeadershipReply.model_fields["role_picture"].description
