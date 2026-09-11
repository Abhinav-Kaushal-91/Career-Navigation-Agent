"""Public wording constraints must reach both initial and reviewer model calls."""

from ai_career_navigator.career import (
    plan_prompts,
    same_role,
    synthesis_prompts,
    transition_prompts,
)
from ai_career_navigator.career.presentation_prompts import (
    CONCISE_REVIEW_CHECK,
    CONCISE_REVIEW_STYLE,
)
from ai_career_navigator.career.transition import assess_career_transition
from tests.career.test_transition import Gateway, inputs, same_inputs  # noqa: F401


def test_public_style_is_attached_to_both_assessment_contracts():
    for contract in (same_role, transition_prompts):
        assert CONCISE_REVIEW_STYLE in contract.SYSTEM_PROMPT
        assert CONCISE_REVIEW_CHECK in contract.REVIEW_INSTRUCTIONS
        assert "-concise-v1" in contract.RULE_VERSION
    assert "never in public names or explanatory text" in synthesis_prompts.SYSTEM_PROMPT
    assert "Do not add inline source IDs" in plan_prompts.SYSTEM_PROMPT


def test_actual_gateway_requests_keep_style_references_and_call_bounds(request):
    gateway = Gateway()
    result = assess_career_transition(*request.getfixturevalue("inputs"), gateway)
    assert len(gateway.requests) == 2
    for request in gateway.requests:
        assert CONCISE_REVIEW_STYLE in request["system_prompt"]
        assert request["max_tokens"] == 30000
        assert request["max_retries"] == 0
        assert '"P1"' in request["user_prompt"]
    assert CONCISE_REVIEW_CHECK in gateway.requests[1]["system_prompt"]
    assert result.competencies[0].source_refs == ["P1L3"]
    assert result.competencies[0].candidate_refs == ["E1"]
    assert not result.processing_issues
