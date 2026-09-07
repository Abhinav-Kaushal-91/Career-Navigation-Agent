from pathlib import Path

from ai_career_navigator.domain import CandidateAccessibility
from ai_career_navigator.evaluation.pilot import (
    build_workflow_inputs,
    execution_payload,
    load_pilot_cases,
    map_accessibility_to_verdict,
)

WORKBOOK = Path(
    r"C:\Users\mkaus\Documents\Codex\2026-09-06"
    r"\referenced-chatgpt-conversation-this-is-an\outputs\career_navigator"
    r"\Career_Navigator_Evaluation.xlsx"
)


def test_reviewed_workbook_loads_ten_unique_cases() -> None:
    cases = load_pilot_cases(WORKBOOK)
    assert len(cases) == 10
    assert {case.execution.case_id for case in cases} == {
        f"CN-{index:03d}" for index in range(1, 11)
    }


def test_execution_payload_excludes_all_reference_fields() -> None:
    case = load_pilot_cases(WORKBOOK)[0]
    payload = execution_payload(case)
    assert set(payload) == {
        "case_id",
        "scenario_type",
        "candidate_profile",
        "career_goal",
        "target_role",
        "target_timeframe",
    }
    serialized = str(payload)
    assert case.reference.expected_career_verdict not in serialized
    assert case.reference.ground_truth_rationale not in serialized


def test_evaluation_verdict_mapping_is_explicit() -> None:
    assert map_accessibility_to_verdict(CandidateAccessibility.APPLY_NOW) == "ready_now"
    assert (
        map_accessibility_to_verdict(CandidateAccessibility.APPLY_SELECTIVELY)
        == "strong_fit_minor_gaps"
    )
    assert map_accessibility_to_verdict(CandidateAccessibility.NEAR_TERM_TARGET) == "adjacent_fit"
    assert (
        map_accessibility_to_verdict(CandidateAccessibility.ASPIRATIONAL)
        == "significant_upskilling"
    )
    assert map_accessibility_to_verdict(CandidateAccessibility.POOR_FIT) == "significant_upskilling"


def test_workflow_inputs_use_fixed_reviewed_evaluation_constraints() -> None:
    case = load_pilot_cases(WORKBOOK)[0]
    profile, goal = build_workflow_inputs(case)
    assert profile.professional_summary == case.execution.candidate_profile
    assert all(
        item.source_reference.endswith(":Candidate_Profile") for item in profile.evidence_items
    )
    assert goal.target_location == "Canada"
    assert goal.bridge_role_willingness is False
    assert goal.search_expansion_permission is False
