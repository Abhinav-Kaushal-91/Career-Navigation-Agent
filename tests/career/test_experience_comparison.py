import json
from datetime import date

import pytest

from ai_career_navigator.career import compare_candidate_to_requirements
from ai_career_navigator.career.comparison_prompts import build_transferability_prompt
from ai_career_navigator.domain import MatchType
from ai_career_navigator.profile.experience import calculate_professional_experience
from tests.career.test_comparison import (
    analysis,
    evidence,
    gateway,
    profile,
    requirement,
    semantic_json,
)


def test_prompt_includes_calculated_tenure_and_retains_unknown_technology_duration():
    item = evidence("Developer", description="Developed backend services.").model_copy(
        update={"evidence_type": "employment", "start_date": date(2018, 9, 1), "is_current": True}
    )
    calculated = calculate_professional_experience([item], as_of=date(2026, 9, 10))
    prompt = build_transferability_prompt(
        requirement("Service development", years=6), [item], calculated_experience=calculated
    )
    payload = json.loads(prompt.split("Assess this data:\n", 1)[1])
    assert payload["calculated_experience"]["approximate_professional_years"] == 8.02
    assert (
        payload["calculated_experience"]["employment_periods"][0]["technology_specific_years"]
        is None
    )
    assert payload["candidate_evidence"][0]["is_current"] is True


@pytest.mark.parametrize("status", ["UNKNOWN", "SUPPORTED"])
def test_unresolved_duration_is_a_question_not_a_partial_deficit(status):
    item = evidence("Service development", description="Developed backend services.")
    req = requirement("Distributed systems", years=6)
    payload = json.loads(semantic_json(req, item))
    payload.update(
        {
            "match_type": "PARTIAL_MATCH",
            "evidence_status": status,
            "partial_match_subtype": "ADJACENT_CAPABILITY_PARTIAL",
            "clarification_needed": (
                "During which employment periods did you use distributed systems?"
            ),
        }
    )
    model, provider = gateway(json.dumps(payload))
    result = compare_candidate_to_requirements(profile([item]), analysis([req]), model)
    comp = result.comparisons[0]
    assert comp.match_type is None
    assert comp.evidence_status == "UNKNOWN"
    assert comp.clarification_needed == payload["clarification_needed"]
    assert comp.evidence_ids == [item.evidence_id]
    sent = json.loads(provider.calls[0].request.user_prompt.split("Assess this data:\n", 1)[1])
    assert "calculated_experience" in sent


def test_confirmed_shortfall_without_unanswered_question_remains_partial():
    req = requirement("Python", years=5)
    item = evidence("Python", description="3 years of confirmed Python usage.")
    model, _ = gateway()
    result = compare_candidate_to_requirements(profile([item]), analysis([req]), model)
    assert result.comparisons[0].match_type is MatchType.PARTIAL_MATCH


def test_unanswered_experience_questions_do_not_make_a_distant_transition():
    from ai_career_navigator.career import synthesize_career_assessment
    from ai_career_navigator.domain import CandidateAccessibility, GapSeverity
    from tests.career.test_synthesis import Finding, SynthesisScenario, build_scenario

    candidate, role, market = build_scenario(
        SynthesisScenario(
            "unresolved_duration",
            "Specialist",
            "Specialist",
            (
                Finding("Platform experience", "Platform delivery", MatchType.PARTIAL_MATCH),
                Finding("Service experience", "Service delivery", MatchType.PARTIAL_MATCH),
            ),
            frozenset(),
        )
    )
    role = role.model_copy(
        update={
            "gaps": [
                item.model_copy(
                    update={
                        "severity": GapSeverity.INSUFFICIENT_EVIDENCE,
                        "clarification_needed": "Which employment dates cover this work?",
                    }
                )
                for item in role.gaps
            ]
        }
    )
    result = synthesize_career_assessment(candidate, role, market, None)
    assert result.accessibility is CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE
    assert "Aspirational target" not in result.accessibility_rationale
    assert (
        "missing information is not a demonstrated capability deficit"
        in result.accessibility_rationale
    )
