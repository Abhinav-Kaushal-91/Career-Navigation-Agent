import json

import pytest

from ai_career_navigator.career.plan import PlanSynthesisValidationError, _validate_wording
from ai_career_navigator.domain import (
    BridgeOutcome,
    CandidateAccessibility,
    GapCategory,
    TimelineClassification,
)
from tests.career.test_path_assessment import gap
from tests.career.test_plan_generation import gateway, generate, timeline


@pytest.mark.parametrize(
    ("original", "proposal"),
    [
        (
            "A confirmed answer resolves the uncertainty about Java.",
            "A confirmed answer removes the uncertainty regarding Java.",
        ),
        (
            "A refreshed assessment determines whether selective applications are supported.",
            "An updated assessment establishes whether selective applications are supported.",
        ),
        (
            "Demonstrate Data visualization in an applied solution.",
            "Show Data visualization in an applied solution.",
        ),
        ("Produce direct evidence of API design.", "Create direct evidence of API design."),
        (
            "During the 2018-present role, were services operated as part of a distributed system?",
            "In the 2018-present role, were services operated within a distributed system?",
        ),
        (
            "Reassess Platform Engineer readiness after building the required evidence.",
            "Reassess readiness for the Platform Engineer role "
            "once the required evidence has been built.",
        ),
    ],
)
def test_controlled_paraphrases(original, proposal):
    _validate_wording(original, proposal)


@pytest.mark.parametrize(
    ("original", "proposal", "reason"),
    [
        ("Confirm Java 8 experience.", "Confirm Java 17 experience.", "numeric"),
        ("Confirm 6+ years of experience.", "Confirm 6 years of experience.", "numeric"),
        ("Confirm C++ experience.", "Confirm C# experience.", "technical symbol"),
        ("Confirm Java is preferred.", "Confirm Java is required.", "obligation"),
        ("Confirm Java experience.", "Learn Java.", "content"),
        ("Confirm Java experience.", "Confirm Java experience within 6 months.", "numeric"),
        ("Demonstrate Java.", "Obtain a Java certification.", "content"),
        (
            "Confirm great working knowledge of Java.",
            "Confirm strong working knowledge of Java.",
            "qualifier",
        ),
        ("Check AWS or Azure.", "Check AWS and Azure.", "condition"),
        ("Do not learn Java; confirm AWS.", "Do learn Java; confirm not AWS.", "order"),
        ("Confirm Java and Java 8 experience.", "Confirm Java and 8 experience.", "content"),
        ("No fixed timeline.", "Missing timeline.", "polarity"),
        ("Confirm production Java experience.", "Confirm Java experience.", "content"),
        (
            "Reassess Platform Engineer readiness after building the required evidence.",
            "Reassess readiness for the Platform Engineer role "
            "before the required evidence has been built.",
            "condition",
        ),
    ],
)
def test_meaning_changes_fail_closed(original, proposal, reason):
    with pytest.raises(PlanSynthesisValidationError, match=reason):
        _validate_wording(original, proposal)


def run_mixed(mutate):
    return generate(
        CandidateAccessibility.NEAR_TERM_TARGET,
        [
            gap("Service design", category=GapCategory.SKILL),
            gap("API design", category=GapCategory.SKILL),
        ],
        BridgeOutcome.NO_BRIDGE_REQUIRED,
        timeline_assessment=timeline(None, TimelineClassification.NO_FIXED_TIMELINE),
        model_gateway=gateway(mutation=mutate),
    )


def test_per_milestone_fallback_preserves_valid_wording_and_records_field(caplog):
    captured = {}

    def mixed(payload):
        captured.update(json.loads(json.dumps(payload)))
        payload["milestones"][0]["action"] = payload["milestones"][0]["action"].replace(
            "Demonstrate", "Show"
        )
        payload["milestones"][1]["action"] += " Obtain a certification."
        payload["milestones"][1]["measurable_outcome"] = payload["milestones"][1][
            "measurable_outcome"
        ].replace("demonstrates", "shows")

    with caplog.at_level("INFO"):
        result = run_mixed(mixed)
    assert result.fallback_used
    assert result.plan.milestones[0].action.startswith("Show")
    # Action + outcome rollback together for the rejected slot.
    assert result.plan.milestones[1].action == captured["milestones"][1]["action"]
    assert (
        result.plan.milestones[1].measurable_outcome
        == (captured["milestones"][1]["measurable_outcome"])
    )
    assert {r.milestone_key for r in result.wording_rejections} == {"milestone-1"}
    assert {r.field for r in result.wording_rejections} == {"action"}
    assert "milestone_key=milestone-1 field=action" in caplog.text
    assert "Obtain a certification" not in caplog.text
    assert result.plan.timeline_assessment.requested_months is None
    assert not result.plan.bridge_roles
    for row, original in zip(result.plan.milestones, captured["milestones"], strict=True):
        assert row.phase == original["phase"]
        assert row.milestone_type.value == original["milestone_type"]
        assert [str(v) for v in row.linked_gap_ids] == original["linked_gap_ids"]
        assert row.evidence_to_create == original["evidence_to_create"]
        assert row.dependencies == original["dependencies"]


@pytest.mark.parametrize("damage", ["risks", "dependency", "duplicate_key"])
def test_global_damage_discards_even_valid_earlier_wording(damage):
    captured = {}

    def mixed(payload):
        captured.update(json.loads(json.dumps(payload)))
        payload["milestones"][0]["action"] = payload["milestones"][0]["action"].replace(
            "Demonstrate", "Show"
        )
        if damage == "risks":
            payload["risks"] = ["Invented risk"]
        elif damage == "dependency":
            payload["milestones"][1]["dependencies"] = ["invented"]
        else:
            payload["milestones"][1]["milestone_key"] = "milestone-0"

    result = run_mixed(mixed)
    assert result.fallback_used
    assert not result.wording_rejections
    assert result.plan.milestones[0].action == captured["milestones"][0]["action"]
    assert result.plan.risks == captured["risks"]
