"""Opt-in Plan-stage replay of four saved GLM comparisons, not a full market run."""

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from check_glm_evidence_contract import save

from ai_career_navigator.career import (
    assess_bridge_roles,
    assess_candidate_accessibility,
    assess_timeline,
    synthesize_career_assessment,
)
from ai_career_navigator.career.plan import _apply_model_wording, generate_career_plan
from ai_career_navigator.domain import (
    CareerGoal,
    CareerPlan,
    ConfidenceLevel,
    CurrentMarketSnapshot,
    RequirementComparison,
    RoleAssessment,
    RoleRequirement,
)
from ai_career_navigator.market import (
    MarketRequirementAnalysis,
    MarketRequirementSummary,
    RequirementRunStatus,
)
from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.models.errors import ModelGatewayError, ModelProviderError
from ai_career_navigator.models.providers import FakeModelProvider
from ai_career_navigator.models.providers.fireworks import FireworksProvider
from ai_career_navigator.profile.service import build_candidate_profile
from ai_career_navigator.ui.demo_data import sample_profile_draft
from ai_career_navigator.ui.live_workflow import load_live_settings

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    "outputs/glm-contract-check/20260910T032403Z/results.json",
    "outputs/glm-contract-check/20260910T033132Z/results.json",
]
DEMO = "outputs/demo-profile-live/20260909T194458Z/results.json"


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def build_inputs():
    # Latest successful result per case; never retain the earlier failed Java result.
    cases = {}
    for source in SOURCES:
        for case in read(source)["cases"]:
            if case["result"]["status"] == "SUCCEEDED":
                cases[case["case"]] = {**case, "saved_source": source}
    assert len(cases) == 4
    profile = build_candidate_profile(sample_profile_draft(), approved=True)
    evidence = {item.evidence_id: item for item in profile.approved_evidence_items}
    requirements = [RoleRequirement.model_validate(c["requirement"]) for c in cases.values()]
    aliases = {}
    comparisons = []
    for case in cases.values():
        source = ROOT / case["saved_source"]
        request_data = next(
            data
            for path in source.parent.glob("*.request.json")
            if "Assess this data:\n"
            in (body := json.loads(path.read_text())["messages"][-1]["content"])
            for data in [json.loads(body.split("Assess this data:\n", 1)[1])]
            if data["requirement"]["requirement_id"] == case["requirement"]["requirement_id"]
        )
        mapping = {}
        for old in request_data["candidate_evidence"]:
            matches = [
                item
                for item in evidence.values()
                if (
                    item.capability == old["capability"]
                    and item.description == old["description"]
                    and (
                        "source_reference" not in old
                        or item.source_reference == old["source_reference"]
                    )
                    and item.maturity_level.value == old["maturity"]
                    and item.evidence_type == old["evidence_type"]
                )
            ]
            assert len(matches) == 1, "Saved evidence changed or is ambiguous"
            mapping[old["evidence_id"]] = str(matches[0].evidence_id)
        aliases[case["case"]] = mapping
        for saved in case["result"]["comparisons"]:
            row = json.loads(json.dumps(saved))
            for key in ["evidence_ids", "selected_evidence_ids", "omitted_evidence_ids"]:
                row[key] = [mapping[value] for value in row[key]]
            for quote in row["grounded_evidence_quotes"]:
                quote["evidence_id"] = mapping[quote["evidence_id"]]
            comparisons.append(RequirementComparison.model_validate(row))
    for comparison in comparisons:
        assert set(comparison.evidence_ids).issubset(evidence)
        for excerpt in comparison.grounded_evidence_quotes:
            evidence_id = UUID(str(excerpt["evidence_id"]))
            assert evidence_id in evidence
            item = evidence[evidence_id]
            assert any(
                " ".join(excerpt["quote"].split()).casefold() in " ".join(value.split()).casefold()
                for value in [item.description, item.context or "", item.outcome or ""]
            )
    demo = read(DEMO)
    goal = CareerGoal.model_validate(demo["goal"])
    assert goal.target_timeline_months is None
    snapshot = CurrentMarketSnapshot.model_validate(demo["graph_state"]["market_snapshot"])
    # This is a deliberately incomplete comparison contract slice, not a market estimate.
    snapshot = snapshot.model_copy(update={"evidence_confidence": ConfidenceLevel.LOW})
    count = len({r.posting_id for r in requirements})
    summary = MarketRequirementSummary(
        target_role=goal.target_role,
        geography=goal.target_location,
        source_page_count=count,
        identified_candidate_count=count,
        validated_in_scope_posting_count=count,
        analyzed_posting_count=count,
        exact_title_analyzed_count=count,
        related_title_analyzed_count=0,
        out_of_scope_count=0,
        unclear_geography_count=0,
        irrelevant_title_count=0,
        limitations=["Four saved comparison cases only; not a complete target-role sample."],
    )
    market = MarketRequirementAnalysis(
        status=RequirementRunStatus.SUCCEEDED, summary=summary, requirements=requirements
    )
    raw = assess_candidate_accessibility(profile, goal, snapshot, market, comparisons)
    synthesis = synthesize_career_assessment(profile, raw.role_assessment, market, None)
    role = raw.role_assessment.model_copy(
        update={
            "candidate_accessibility": synthesis.accessibility,
            "explanation": synthesis.accessibility_rationale,
            "confidence": ConfidenceLevel.LOW,
        }
    )
    bridges = assess_bridge_roles(profile, goal, role, market, [])
    timeline = assess_timeline(goal, role, bridges, snapshot)
    result = generate_career_plan(
        profile,
        goal,
        role,
        bridges.assessments,
        bridges.outcome,
        timeline.assessment,
        market_confidence=ConfidenceLevel.LOW,
    )
    return (
        role,
        result.plan,
        {
            "cases": list(cases),
            "goal": goal.model_dump(mode="json"),
            "evidence_id_aliases": aliases,
            "alias_rule": (
                "Exact unique capability + description + maturity + evidence type; "
                "source reference checked when supplied; no prefix matching"
            ),
            "requirements": [r.model_dump(mode="json") for r in requirements],
            "role": role.model_dump(mode="json"),
            "synthesis": synthesis.model_dump(mode="json"),
            "bridges": bridges.model_dump(mode="json"),
            "timeline": timeline.model_dump(mode="json"),
        },
    )


class PlanProvider(FireworksProvider):
    def __init__(self, key, output):
        super().__init__(key, streaming=True)
        self.output, self.calls = output, 0

    def _stream_response(self, payload, request, model, timeout_seconds):
        if self.calls:
            raise ModelProviderError("Plan diagnostic limited to one call")
        self.calls += 1
        payload = {**payload, "reasoning_effort": "high"}
        save(self.output / "request.json", payload)
        started = time.monotonic()
        try:
            response = super()._stream_response(payload, request, model, timeout_seconds)
        except ModelGatewayError as error:
            save(
                self.output / "provider-failure.json",
                {
                    "category": type(error).__name__,
                    "seconds": round(time.monotonic() - started, 2),
                },
            )
            raise
        (self.output / "response.txt").write_text(response.content, encoding="utf-8")
        metrics = {
            "seconds": round(time.monotonic() - started, 2),
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "finish_reason": response.finish_reason,
        }
        save(self.output / "metrics.json", metrics)
        print("RETURN " + json.dumps(metrics), flush=True)
        return response


def immutable_view(plan):
    value = plan.model_dump(mode="json")
    for milestone in value["milestones"]:
        milestone.pop("action")
        milestone.pop("measurable_outcome")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--replay-saved", type=Path)
    args = parser.parse_args()
    if args.replay_saved:
        source = args.replay_saved.resolve()
        plan = CareerPlan.model_validate_json((source / "baseline-plan.json").read_text())
        role = RoleAssessment.model_validate(
            json.loads((source / "inputs.json").read_text())["role"]
        )
        provider = FakeModelProvider(default_response=(source / "response.txt").read_text())
        gateway = ModelGateway(
            provider=provider,
            models={ModelRole.REASONING: "saved-glm-response"},
            max_retries=0,
            timeout_seconds=10,
        )
        rejections = []
        final = _apply_model_wording(plan, role, gateway, rejections=rejections)
        assert immutable_view(plan) == immutable_view(final)
        output = ROOT / "outputs/glm-plan-replay" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        output.mkdir(parents=True, exist_ok=False)
        changed = [
            f"milestone-{index}"
            for index, (old, new) in enumerate(zip(plan.milestones, final.milestones, strict=True))
            if (old.action, old.measurable_outcome) != (new.action, new.measurable_outcome)
        ]
        audit = {
            "mode": "OFFLINE_REPLAY_OF_SAVED_LIVE_RESPONSE",
            "source": str(source),
            "live_calls": 0,
            "accepted_changed_milestones": changed,
            "wording_rejections": [r.model_dump() for r in rejections],
            "immutable_fields_preserved": True,
        }
        save(output / "audit.json", audit)
        save(output / "final-plan.json", final.model_dump(mode="json"))
        print("REPLAY " + json.dumps(audit), flush=True)
        return
    role, plan, inputs = build_inputs()
    print(
        f"INPUT: four saved comparisons; {len(role.gaps)} gaps; "
        f"{len(plan.milestones)} milestones; {plan.path_type}",
        flush=True,
    )
    if not args.live:
        print("Dry run only; no API request.")
        return
    settings = load_live_settings().model_copy(update={"max_retries": 0})
    if settings.llm_provider != "fireworks" or "glm" not in settings.reasoning_model:
        raise ValueError("GLM Fireworks configuration required")
    output = ROOT / "outputs/glm-plan-check" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True, exist_ok=False)
    save(
        output / "manifest.json",
        {
            "mode": "LIVE_PLAN_WORDING_ON_SAVED_COMPARISON_SLICE",
            "sources": SOURCES,
            "demo": DEMO,
            "full_five_jd_workflow": False,
            "profile": "synthetic demo; confirmed evidence IDs and quotes checked",
            "upstream_synthesis": "deterministic fallback, not a new LLM assessment",
            "production_changed": False,
            "max_calls": 1,
            "max_retries": 0,
            "timeout_seconds": settings.model_timeout_seconds,
            "max_output_tokens": settings.model_max_output_tokens,
            "reasoning_effort": "high",
        },
    )
    save(output / "inputs.json", inputs)
    save(output / "baseline-plan.json", plan.model_dump(mode="json"))
    provider = PlanProvider(settings.fireworks_api_key, output)
    gateway = ModelGateway.from_settings(settings, providers={"fireworks": provider})
    print(f"START {output}", flush=True)
    final, accepted, failure = plan, False, None
    try:
        # Same refinement + semantic/lineage validator called by generate_career_plan.
        # Capture the precise rejection here instead of obscuring it behind fallback.
        rejections = []
        final = _apply_model_wording(plan, role, gateway, rejections=rejections)
        accepted = not rejections
        if rejections:
            failure = {"milestone_wording_rejections": [r.model_dump() for r in rejections]}
    except (ModelGatewayError, ValueError, TypeError) as error:
        failure = {"category": type(error).__name__}
        if isinstance(error, ValueError):
            failure["reason"] = str(error)
    unchanged = immutable_view(plan) == immutable_view(final)
    assert unchanged
    save(output / "final-plan.json", final.model_dump(mode="json"))
    result = {
        "model_wording_accepted": accepted,
        "deterministic_fallback_retained": not accepted,
        "failure": failure,
        "immutable_fields_preserved": unchanged,
        "live_calls": provider.calls,
        "milestones": len(final.milestones),
        "no_fixed_timeline_preserved": final.timeline_assessment.requested_months is None,
        "not_an_end_to_end_market_validation": True,
    }
    save(output / "audit.json", result)
    print("AUDIT " + json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
