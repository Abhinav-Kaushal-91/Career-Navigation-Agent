from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from streamlit.testing.v1 import AppTest

from ai_career_navigator.career.same_role import Competency
from ai_career_navigator.domain import GoalType
from ai_career_navigator.goal.configuration import VISIBLE_GOAL_TYPES, goal_intent_config
from ai_career_navigator.ui.components.career_story import journey_data
from ai_career_navigator.ui.components.career_visuals import (
    DIMENSIONS,
    build_coverage_radar,
    snapshot_data,
    unique_comparison_rows,
)


def test_destination_choice_is_merged_without_removing_legacy_intent():
    assert len(VISIBLE_GOAL_TYPES) == 5
    assert GoalType.ROLE_TRANSITION not in VISIBLE_GOAL_TYPES
    assert GoalType.TARGET_CAREER_PATH in VISIBLE_GOAL_TYPES
    for intent in (GoalType.ROLE_TRANSITION, GoalType.TARGET_CAREER_PATH):
        config = goal_intent_config(intent)
        assert config.requires_target and config.show_timeline
        assert config.show_bridge_willingness and config.show_search_expansion


def test_counts_are_same_rows_not_evidence_or_keywords_and_unknown_is_not_shortfall():
    statuses = [
        "Demonstrated",
        "Transferable",
        "Partially demonstrated",
        "Unconfirmed",
        "Needs development",
    ]
    rows = [{"Competency": str(i), "Your position": s} for i, s in enumerate(statuses)]
    rows.append(dict(rows[0]))
    original = [dict(row) for row in rows]
    counts, coverage = snapshot_data(rows, {"0": "TECHNICAL", "2": "TECHNICAL", "3": "DOMAIN"})
    assert sum(counts.values()) == len(unique_comparison_rows(rows)) == 5
    assert set(counts.values()) == {1}
    assert coverage == {"TECHNICAL": 0.5, "DOMAIN": 0.0}
    assert rows == original


def test_missing_group_data_is_not_invented():
    assert build_coverage_radar({}) is None
    assert build_coverage_radar({"TECHNICAL": 1, "DOMAIN": 0}) is None
    assert build_coverage_radar({"TECHNICAL": 1, "DOMAIN": None, "DESIGN": 0.5}) is None
    assert snapshot_data([])[1] == {}


def test_unconfirmed_groups_are_zero_coverage_and_do_not_hide_the_radar():
    rows = [
        {"Competency": key, "Your position": "Unconfirmed"}
        for key in ("TECHNICAL", "DESIGN", "DOMAIN")
    ]
    counts, coverage = snapshot_data(rows, {row["Competency"]: row["Competency"] for row in rows})
    assert counts["Unconfirmed"] == 3 and counts["Needs development"] == 0
    assert list(coverage.values()) == [0.0, 0.0, 0.0]
    assert build_coverage_radar(coverage) is not None
    assert all(row["Your position"] == "Unconfirmed" for row in rows)


def test_story_keeps_conditions_and_uses_existing_decision_step_only():
    milestones = [
        SimpleNamespace(
            basis="Relevant capability",
            milestone_type="PROJECT",
            action="Build only if needed.",
            measurable_outcome="A verified result.",
        ),
        SimpleNamespace(
            basis="Eligibility",
            milestone_type="APPLICATION_READINESS",
            action="Apply only if eligible; otherwise defer.",
            measurable_outcome="An apply-or-defer decision.",
        ),
    ]
    data = journey_data(SimpleNamespace(current_role="Plumber", target_role="Welder"), milestones)
    assert [s["label"] for s in data["stages"]] == [
        "Starting point",
        "Next milestone",
        "Decision point",
        "Target direction",
    ]
    assert data["stages"][2]["step"] == 1
    assert data["steps"][1]["action"] == milestones[1].action
    assert data["steps"][1]["done"] == milestones[1].measurable_outcome
    short = journey_data(SimpleNamespace(current_role="A", target_role=None), milestones[:1])
    assert len(short["steps"]) == 1
    assert not any(s["label"] in {"Target direction", "Decision point"} for s in short["stages"])


def test_story_uses_text_nodes_for_untrusted_model_and_profile_content():
    from ai_career_navigator.ui.components.career_story import JS

    assert "textContent=text" in JS
    assert "innerHTML" not in JS
    assert "setStateValue" not in JS  # selecting a detail never changes plan completion


@pytest.mark.parametrize("size", [3, 4, 5, 6])
def test_radar_axes_are_only_supplied_groups_and_centered_without_zero_label(size):
    keys = list(DIMENSIONS)[:size]
    chart = build_coverage_radar(dict.fromkeys(keys, 0.5))
    labels = chart.layout.annotations[:size]
    assert len(labels) == size
    assert all(a.align == "center" and a.xanchor == "center" for a in labels)
    assert {a.text for a in chart.layout.annotations[-2:]} == {"50%", "100%"}
    assert all(a.text != "0%" for a in chart.layout.annotations)
    assert len(chart.data[-1].x) == size + 1


def test_dimension_metadata_is_optional_and_not_a_new_skill_or_score():
    payload = dict(
        name="Welding",
        context="COMMON",
        expectation="QUALIFICATION",
        status="DEMONSTRATED",
        reason="Recorded practical work.",
        source_refs=["P1L1"],
    )
    old = Competency(**payload)
    new = Competency(**payload, display_dimension="TECHNICAL")
    assert old.display_dimension is None
    assert old.status == new.status
    with pytest.raises(ValidationError):
        Competency(**payload, display_dimension="Invented readiness score")


@pytest.mark.parametrize("count", [0, 1, 2, 5, 8])
def test_path_has_only_real_steps_without_invented_bridges_dates_or_success(count):
    milestones = [
        SimpleNamespace(
            milestone_type="EVIDENCE",
            phase=f"Step {i + 1}",
            action="Confirm experience before deciding.",
        )
        for i in range(count)
    ]
    data = journey_data(SimpleNamespace(current_role="Current", target_role="Target"), milestones)
    if not count:
        assert data["stages"] == []
    else:
        assert len(data["steps"]) == count
        assert [s["label"] for s in data["stages"]] == [
            "Starting point",
            "Next milestone",
            "Target direction",
        ]
        assert all(s["action"] == m.action for s, m in zip(data["steps"], milestones, strict=True))
        assert "months" not in str(data)
        assert "Ready" not in str(data)
        assert "bridge" not in str(data).lower()


def test_snapshot_and_table_use_identical_counts_and_processing_hides_chart():
    app = AppTest.from_string("""
import streamlit as st
from ai_career_navigator.ui.components.career_visuals import render_competency_snapshot
rows = [{"Competency": "A", "Your position": "Demonstrated"},
        {"Competency": "B", "Your position": "Transferable"},
        {"Competency": "C", "Your position": "Unconfirmed"}]
render_competency_snapshot(rows, {"A": "TECHNICAL", "B": "DESIGN", "C": "DOMAIN"},
                          processing_issue=True)
st.table(rows)
""").run()
    assert not app.exception
    assert sum(int(m.value) for m in app.metric) == len(app.table[0].value)
    assert not app.get("plotly_chart")


def test_processing_failure_does_not_get_path_and_no_target_is_invented():
    app = AppTest.from_string("""
from types import SimpleNamespace
from ai_career_navigator.ui.components.career_visuals import render_path_map
plan = SimpleNamespace(target_role=None, milestones=[SimpleNamespace(milestone_type="EVIDENCE")])
render_path_map(plan, processing_issue=True)
""").run()
    assert not app.exception and not app.get("plotly_chart")
