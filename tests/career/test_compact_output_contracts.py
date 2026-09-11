import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ai_career_navigator.career.comparison_schemas import TransferabilityAssessment
from ai_career_navigator.career.plan_schemas import CareerPlanDraftOutput
from ai_career_navigator.domain import BridgeOutcome, CandidateAccessibility
from ai_career_navigator.models.output_text import unique_statements
from tests.career.test_comparison import evidence, requirement, semantic_json
from tests.career.test_plan_generation import gateway, generate


def test_compact_comparison_binds_only_missing_metadata():
    req, item = requirement("Service Architecture"), evidence("Service Delivery")
    payload = json.loads(semantic_json(req, item))
    payload.pop("requirement_id")
    context = {"requirement_id": req.requirement_id}
    result = TransferabilityAssessment.model_validate(payload, context=context)
    assert result.requirement_id == req.requirement_id
    assert result.transferable_capability == item.capability
    wrong_id = uuid4()
    payload["requirement_id"] = wrong_id
    assert (
        TransferabilityAssessment.model_validate(payload, context=context).requirement_id
        == wrong_id
    )
    # Preserve wrong returned IDs so the service's identity check can reject them.


def test_wire_schemas_omit_reconstructable_metadata():
    comparison = TransferabilityAssessment.model_json_schema()
    assert "requirement_id" not in comparison["properties"]
    assert "transferable_capability" in comparison["properties"]
    assert "supporting_evidence_ids" in comparison["properties"]
    plan = CareerPlanDraftOutput.model_json_schema()
    assert set(plan["properties"]) == {"milestones"}
    assert set(plan["$defs"]["MilestoneDraftOutput"]["properties"]) == {
        "milestone_key",
        "action",
        "measurable_outcome",
    }


@pytest.mark.parametrize("overflow", ["explanation", "quote", "quote_count"])
def test_comparison_output_limits_reject_instead_of_truncating(overflow):
    req, item = requirement("Architecture"), evidence("Delivery")
    payload = json.loads(semantic_json(req, item))
    quote = {
        "evidence_id": str(item.evidence_id),
        "quote": "Used in production delivery.",
        "dimensions": ["function"],
    }
    payload["evidence_quotes"] = [quote]
    if overflow == "explanation":
        payload["explanation"] = "x" * 321
    elif overflow == "quote":
        quote["quote"] = "x" * 321
    else:
        payload["evidence_quotes"] = [quote] * 3
    with pytest.raises(ValidationError):
        TransferabilityAssessment.model_validate(payload)


@pytest.mark.parametrize("damage", [None, "missing_action", "unknown_key", "changed_phase"])
def test_compact_plan_runs_through_real_gateway_and_validation(damage):
    captured = {}

    def compact(payload):
        captured.update(json.loads(json.dumps(payload)))
        rows = [
            {key: row[key] for key in ("milestone_key", "action", "measurable_outcome")}
            for row in payload["milestones"]
        ]
        payload.clear()
        payload["milestones"] = rows
        if damage == "missing_action":
            rows[0].pop("action")
        elif damage == "unknown_key":
            rows[0]["milestone_key"] = "invented-slot"
        elif damage == "changed_phase":
            rows[0]["phase"] = "Invented phase"

    result = generate(
        CandidateAccessibility.APPLY_NOW,
        [],
        BridgeOutcome.NO_BRIDGE_REQUIRED,
        model_gateway=gateway(mutation=compact),
    )
    assert result.fallback_used is (damage is not None)
    assert result.plan.target_role == captured["target_role"]
    assert result.plan.risks == captured["risks"]
    assert result.plan.milestones[0].action == captured["milestones"][0]["action"]


def test_duplicate_limitations_keep_distinct_conditions():
    assert unique_statements(
        ["AWS unconfirmed.", " aws   UNCONFIRMED. ", "Azure unconfirmed.", ""]
    ) == ["AWS unconfirmed.", "Azure unconfirmed."]
