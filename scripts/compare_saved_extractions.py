"""Offline comparison of two saved answers; never constructs a live API client."""

import argparse
import hashlib
import json
import logging
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

from ai_career_navigator.market.overview import build_overview_payload, source_overview
from ai_career_navigator.market.requirement_schemas import (
    MarketRequirementSummary,
    PostingCandidateAssessment,
    PostingRequirementResult,
)
from ai_career_navigator.market.requirements import (
    _contains_quote,
    _extraction_quality_counts,
    _quality_and_audit,
    extract_posting_requirements,
)
from ai_career_navigator.market.role_profile import build_canonical_target_role_profile
from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.models.inspection import LocalModelInspector
from ai_career_navigator.models.providers import FakeModelProvider
from ai_career_navigator.orchestration.nodes import market_ready

ROOT = Path(__file__).resolve().parents[1]
SAVED_RUN = ROOT / "outputs/nemotron-live-overview/20260909T185859Z/results.json"


def repair_known_escape(raw):
    """Diagnostic only: remove exactly two stray slashes on the known quote line."""
    lines = raw.splitlines(keepends=True)
    changed = []
    for index, line in enumerate(lines):
        if '"source_quote"' in line and "visa transfer or sponsorship" in line:
            if line.count("\\") != 2 or '"\\Please note' not in line:
                raise ValueError("Unexpected quote structure; do not perform broad repair")
            lines[index] = line.replace("\\", "")
            changed.append(index + 1)
    if len(changed) != 1:
        raise ValueError("Expected exactly one known malformed source-quote line")
    return "".join(lines), changed


def replay(label, raw, assessment, generated_at):
    inspector = LocalModelInspector()
    provider = FakeModelProvider(default_response=raw)
    gateway = ModelGateway(
        provider=provider,
        models={ModelRole.EXTRACTION: label},
        timeout_seconds=10,
        max_retries=0,
        inspector=inspector,
    )
    outcome = extract_posting_requirements(assessment, gateway)
    quality, audit = _quality_and_audit(assessment, outcome, enrichment_used=False)
    extracted = [] if quality.failure_category else [(assessment, outcome.requirements)]
    summary = MarketRequirementSummary(
        **_extraction_quality_counts(extracted, [quality]),
        target_role="Senior Java Developer",
        geography="Toronto, Canada",
        source_page_count=1,
        identified_candidate_count=1,
        validated_in_scope_posting_count=1,
        analyzed_posting_count=len(extracted),
        exact_title_analyzed_count=len(extracted),
        target_variant_analyzed_count=0,
        related_title_analyzed_count=0,
        out_of_scope_count=0,
        unclear_geography_count=0,
        irrelevant_title_count=0,
    )
    profile, canonical_audits = build_canonical_target_role_profile(
        target_role=summary.target_role,
        geography=summary.geography,
        requirements=outcome.requirements,
        assessments=[assessment],
        summary=summary,
        posting_audits=[audit],
        generated_at=generated_at,
    )
    gate = market_ready(
        {
            "run_id": uuid5(NAMESPACE_URL, "offline-extraction-comparison:" + label),
            "canonical_target_role_profile": profile,
            "limitations": profile.limitations,
            "completed_stages": [],
        },
        SimpleNamespace(
            context=SimpleNamespace(logger=logging.getLogger(__name__), clock=lambda: generated_at)
        ),
    )
    quote_counts = None
    if quality.schema_valid_response:
        parsed = PostingRequirementResult.model_validate_json(raw)
        quote_counts = {
            "checked": len(parsed.requirements),
            "passed": sum(
                _contains_quote(item.source_quote, assessment.candidate.posting_text)
                for item in parsed.requirements
            ),
            "raw_item_types": dict(Counter(item.item_type.value for item in parsed.requirements)),
        }
    return {
        "label": label,
        "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "external_calls": 0,
        "replay_calls": len(provider.calls),
        "quote_check": quote_counts,
        "quality": quality.model_dump(mode="json"),
        "accepted_counts": dict(Counter(x.statement_type.value for x in outcome.requirements)),
        "decision_counts": dict(Counter(x.final_classification for x in audit.items)),
        "accepted_requirements": [x.model_dump(mode="json") for x in outcome.requirements],
        "audit": audit.model_dump(mode="json"),
        "canonical_audit": [x.model_dump(mode="json") for x in canonical_audits],
        "canonical_profile": profile.model_dump(mode="json"),
        "market_summary": summary.model_dump(mode="json"),
        "source_grouping_not_model_output": source_overview(profile).model_dump(mode="json"),
        "next_overview_input_not_sent": build_overview_payload(profile),
        "market_gate": {k: str(v) if not isinstance(v, list) else v for k, v in gate.items()},
        "candidate_comparison": "NOT_RUN_INSUFFICIENT_SINGLE_EMPLOYER_CORPUS",
        "plan": "NOT_RUN",
        "validation_failures": [e for e in inspector.events if e["event"] == "rejected_response"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qwen-response", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    saved = json.loads(SAVED_RUN.read_text(encoding="utf-8"))
    request = next(e["payload"] for e in saved["model_events"] if e["event"] == "request")
    assessment = PostingCandidateAssessment.model_validate(saved["postings"][0]["assessment"])
    user_input = json.loads(next(m["content"] for m in request["messages"] if m["role"] == "user"))
    assert user_input["untrusted_bounded_posting_text"] == assessment.candidate.posting_text
    nemotron = next(
        e["final_content"] for e in saved["model_events"] if e["event"] == "provider_final_response"
    )
    qwen = args.qwen_response.read_text(encoding="utf-8-sig")
    repaired, changed_lines = repair_known_escape(qwen)
    now = datetime.now(UTC)
    cases = [
        replay("nemotron_original", nemotron, assessment, now),
        replay("qwen_original", qwen, assessment, now),
        replay("qwen_escape_repaired_DIAGNOSTIC_ONLY", repaired, assessment, now),
    ]
    report = {
        "mode": "OFFLINE_SAVED_EXTRACTION_COMPARISON",
        "created_at": now.isoformat(),
        "source_record": str(SAVED_RUN),
        "qwen_attachment": str(args.qwen_response),
        "source_input": user_input,
        "source_sha256": hashlib.sha256(assessment.candidate.posting_text.encode()).hexdigest(),
        "diagnostic_repair": {"changed_lines": changed_lines, "removed_backslashes": 2},
        "original_nemotron_usage": next(
            {k: v for k, v in e.items() if k not in {"final_content", "event"}}
            for e in saved["model_events"] if e["event"] == "provider_final_response"
        ),
        "qwen_usage": None,
        "limitations": [
            "One saved posting, one answer per model; not a multi-posting or multi-model live run.",
            "Qwen model/provider/settings are user-reported; no provider telemetry supplied.",
            "Instructions/data match the exported test; single-message Qwen transport differs.",
            "Repaired Qwen is a labelled counterfactual, not the original production outcome.",
            "Fake provider replay measures validation, not inference latency or cost.",
            "No private reasoning, credential access, external requests or approval changes.",
        ],
        "cases": cases,
    }
    assert cases[0]["quality"]["schema_valid_response"]
    assert not cases[1]["quality"]["schema_valid_response"]
    assert cases[2]["quality"]["schema_valid_response"]
    assert all(c["market_gate"]["workflow_status"] == "INSUFFICIENT_EVIDENCE" for c in cases)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for label, text in [("qwen-original", qwen), ("nemotron-original", nemotron),
                        ("qwen-escape-repaired-DIAGNOSTIC-ONLY", repaired)]:
        (args.output / f"{label}.txt").write_text(text, encoding="utf-8")
    for case in cases:
        print(json.dumps({
            "case": case["label"], "quality": case["quality"],
            "accepted_counts": case["accepted_counts"], "decisions": case["decision_counts"],
            "canonical_status": case["canonical_profile"]["profile_status"],
        }))


if __name__ == "__main__":
    main()
