"""Production-graph replay contracts, not live-model accuracy measurements."""

import asyncio
import inspect
import json
from collections import Counter
from copy import deepcopy
from dataclasses import replace

import pytest
from pydantic import TypeAdapter

from ai_career_navigator.domain import GoalType
from ai_career_navigator.evaluation import v1_replay
from ai_career_navigator.evaluation.v1_replay import (
    RUN_MODE,
    build_inputs,
    evaluate_result,
    execute_case,
    lineage_checks,
    replay_cases,
    run_replays_sync,
)
from ai_career_navigator.orchestration.state import CareerGraphState


@pytest.fixture(scope="module")
def replay_report(tmp_path_factory):
    return run_replays_sync(audit_directory=tmp_path_factory.mktemp("v1-replay"))


@pytest.fixture(scope="module")
def rows(replay_report):
    return {item["case_id"]: item for item in replay_report["results"]}


def test_twelve_explicit_cases_cover_each_journey_twice():
    cases = replay_cases()
    assert len(cases) == 12
    assert len({item.case_id for item in cases}) == 12
    assert Counter(item.goal_type for item in cases) == {item: 2 for item in GoalType}
    assert len({item.stage for item in cases}) >= 4
    assert len({item.current_role for item in cases if item.current_role}) >= 8


@pytest.mark.parametrize("case", replay_cases(), ids=lambda item: item.case_id)
def test_structured_input_fidelity(case):
    profile, goal = build_inputs(case)
    assert profile.years_professional_experience == case.years
    assert profile.current_role == case.current_role
    assert profile.professional_summary == case.professional_summary
    assert profile.career_stage == case.stage
    assert profile.current_location == case.location
    assert goal.target_role == case.target_role
    assert goal.target_timeline_months == case.months
    assert goal.bridge_role_willingness == case.bridge_willingness
    assert goal.goal_type == case.goal_type
    assert goal.target_location == case.location
    assert goal.search_expansion_permission is False
    assert [item.capability for item in profile.evidence_items] == [
        item.capability for item in case.facts
    ]
    assert [item.maturity_level.value for item in profile.evidence_items] == [
        item.maturity for item in case.facts
    ]
    # Total years do not turn into a fabricated technology-specific history.
    assert [item.description for item in profile.evidence_items] == [
        item.description for item in case.facts
    ]
    assert all(item.approved_by_user for item in profile.evidence_items)


def test_run_artifacts_are_explicit_about_frozen_coverage(replay_report, rows):
    assert replay_report["run_mode"] == RUN_MODE
    assert replay_report["case_count"] == 12
    limits = " ".join(replay_report["coverage_limits"])
    assert "not live model semantic accuracy" in limits
    assert "Capability inference is opted out" in limits
    assert "plan model wording is disabled" in limits
    assert "100-case" in limits
    for row in rows.values():
        assert row["tokens"] is None
        assert row["cost"] is None
        assert row["graph_state"]["run_id"] == row["run_id"]
        assert row["graph_state"]["confirmed_profile"] == row["input"]["profile"]
        assert row["graph_state"]["confirmed_goal"] == row["input"]["goal"]
        assert row["effective_settings"]["market_analysis_posting_limit"] == 10
        restored = TypeAdapter(CareerGraphState).validate_python(row["graph_state"])
        assert str(restored["run_id"]) == row["run_id"]
        json.dumps(row)


@pytest.mark.parametrize("case_id", ["CURRENT-A", "CURRENT-B", "LEADERSHIP-B"])
def test_same_role_ready_plans_do_not_invent_bridge_or_waits(rows, case_id):
    row = rows[case_id]
    assert row["actual_accessibility"] == "APPLY_NOW"
    assert row["plan"]["path_type"] == "DIRECT"
    assert row["plan"]["bridge_roles"] == []
    assert len(row["plan"]["milestones"]) == 1
    action = row["plan"]["milestones"][0]
    assert action["milestone_type"] == "APPLICATION_READINESS"
    assert action["linked_gap_ids"] == []
    assert action["month_start"] == action["month_end"] == 0
    assert action["supporting_evidence_ids"]


def test_product_vision_ownership_remains_partial_while_discovery_transfers(rows):
    row = rows["TRANSITION-A"]
    by_label = {item["transferable_capability"]: item for item in row["comparisons"]}
    assert by_label["Process Discovery"]["match_type"] == "TRANSFERABLE_MATCH"
    assert by_label["Solution Roadmaps"]["match_type"] == "PARTIAL_MATCH"
    assert row["actual_accessibility"] == "NEAR_TERM_TARGET"
    assert row["gaps"]
    assert row["plan"]["milestones"][0]["linked_gap_ids"]


def test_project_evidence_is_not_promoted_to_production(rows):
    row = rows["TRANSITION-B"]
    assert row["input"]["goal"]["target_timeline_months"] is None
    assert row["plan"]["timeline_assessment"]["classification"] == "NO_FIXED_TIMELINE"
    assert sum(item["match_type"] == "PARTIAL_MATCH" for item in row["comparisons"]) == 2
    assert any(
        item["production_context_difference"] == "PROJECT_TO_PRODUCTION"
        for item in row["comparisons"]
    )


def test_provisional_variant_supported_target_reaches_analysis_and_plan(rows):
    row = rows["TARGET-A"]
    assert row["canonical_target_role_profile"]["profile_status"] == "PROVISIONAL"
    assert row["synthesis"] is not None
    assert row["plan"] is not None
    assert row["rubric_revision"]["original_expected"]["accessibility"] == [
        "APPLY_SELECTIVELY",
        "NEAR_TERM_TARGET",
    ]
    assert row["original_evaluation"]["passed"] is False
    assert row["evaluation"]["checks"]["provisional_confidence_qualified"]


def test_unsupported_title_descriptor_is_not_silently_accepted(tmp_path):
    case = next(item for item in replay_cases() if item.case_id == "TARGET-A")
    unsupported = replace(case, decorated_title="Sr. Python Developer – APIs")
    result = asyncio.run(execute_case(unsupported, audit_directory=tmp_path))
    assert result["canonical_target_role_profile"]["profile_status"] == "INSUFFICIENT"
    assert result["plan"] is None


@pytest.mark.parametrize("damage", ["missing", "unsupported"])
def test_positive_final_label_cannot_mask_missing_or_unsupported_comparison(rows, damage):
    row = deepcopy(rows["TARGET-A"])
    if damage == "missing":
        row["comparisons"].pop()
    else:
        row["comparisons"][0]["evidence_ids"] = []
        row["comparisons"][0]["grounded_evidence_quotes"] = []
        row["comparisons"][0]["evidence_status"] = "UNKNOWN"
    assert row["actual_accessibility"] == "APPLY_NOW"
    result = evaluate_result(row, row["rubric_revision"]["revised_expected"])
    assert not result["passed"]


def test_unknown_prerequisite_survives_extraction_without_becoming_confirmed_blocker(rows):
    row = rows["TARGET-B"]
    assert row["canonical_target_role_profile"]["prerequisites"]
    assert any(item["evidence_status"] == "UNKNOWN" for item in row["comparisons"])
    assert row["gaps"] and not any(item["hard_blocker"] for item in row["gaps"])
    assert row["actual_accessibility"] != "APPLY_NOW"


@pytest.mark.parametrize("case_id", ["EXPLORATION-A", "EXPLORATION-B"])
def test_targetless_exploration_requires_role_discovery_not_empty_search(rows, case_id):
    row = rows[case_id]
    assert row["workflow_status"] == "ROLE_DISCOVERY_REQUIRED"
    assert not any(row["requests"].values())
    assert row["synthesis"] is None
    assert row["plan"] is None


def test_insufficient_market_is_a_safe_stop_and_missing_candidate_is_unknown(rows):
    assert rows["REASSESS-A"]["market_snapshot"]["validated_posting_count"] == 0
    assert rows["REASSESS-A"]["plan"] is None
    assert rows["REASSESS-A"]["actual_accessibility"] is None
    candidate = rows["REASSESS-B"]
    assert candidate["actual_accessibility"] == "INSUFFICIENT_CANDIDATE_EVIDENCE"
    assert all(item["evidence_status"] == "UNKNOWN" for item in candidate["comparisons"])


def test_every_existing_result_preserves_end_to_end_lineage(rows):
    for row in rows.values():
        assert all(lineage_checks(row).values()), row["case_id"]


def test_evaluator_flags_changed_provenance_and_synthesis_verdict(rows):
    damaged = deepcopy(rows["TRANSITION-A"])
    damaged["comparisons"][0]["evidence_ids"] = ["invented"]
    damaged["plan"]["milestones"][0]["linked_gap_ids"] = ["invented"]
    damaged["actual_accessibility"] = "APPLY_NOW"
    checks = lineage_checks(damaged)
    assert not checks["comparison_evidence_ids_valid"]
    assert not checks["milestone_gap_ids_valid"]
    assert not checks["actual_accessibility_uses_synthesis"]


def test_actual_verdict_uses_synthesis_not_legacy_role_assessment(rows):
    row = deepcopy(rows["CURRENT-A"])
    row["raw_role_accessibility"] = "ASPIRATIONAL"
    assert row["actual_accessibility"] == row["synthesis"]["accessibility"] == "APPLY_NOW"
    assert evaluate_result(row, {"accessibility": ["APPLY_NOW"]})["passed"]


def test_expected_labels_are_not_part_of_execution_inputs(monkeypatch, tmp_path, rows):
    assert set(inspect.signature(execute_case).parameters) == {"case", "audit_directory"}
    sentinel = "DO_NOT_SEND_EXPECTED_ANSWER_TO_THE_MODEL"
    monkeypatch.setattr(v1_replay, "RUBRICS", {"CURRENT-A": {"accessibility": [sentinel]}})
    case = replay_cases()[0]
    output = asyncio.run(execute_case(case, audit_directory=tmp_path))
    assert output["actual_accessibility"] == rows["CURRENT-A"]["actual_accessibility"]
    assert sentinel not in json.dumps(output)
    assert "evaluation" not in output


def test_all_evaluator_rubrics_pass_on_production_outputs(replay_report):
    failures = {
        item["case_id"]: item["evaluation"]["failures"]
        for item in replay_report["results"]
        if not item["evaluation"]["passed"]
    }
    assert not failures
    assert replay_report["original_rubric_passed"] == 11
    assert replay_report["initial_review"]["passed"] == 11
