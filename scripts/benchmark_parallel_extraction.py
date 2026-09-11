"""Opt-in four-posting, two-worker live extraction timing check; no website mutation."""

import argparse
import hashlib
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from check_glm_evidence_contract import RecordedProvider, save

from ai_career_navigator.market.requirement_prompts import PROMPT_VERSION
from ai_career_navigator.market.requirement_schemas import (
    PostingCandidate,
    PostingCandidateAssessment,
)
from ai_career_navigator.market.requirements import extract_posting_requirements
from ai_career_navigator.models import ModelGateway
from ai_career_navigator.models.providers import configured_provider
from ai_career_navigator.ui.live_workflow import load_live_settings

ROOT = Path(__file__).resolve().parents[1]


def load_cases():
    folder = ROOT / "outputs/fireworks-saved-market/20260909T221337Z"
    cases = []
    for name in ("call-01", "call-03", "call-05", "call-06"):
        path = folder / name / "request.json"
        body = json.loads(json.loads(path.read_text(encoding="utf-8"))["messages"][-1]["content"])
        candidate = PostingCandidate(
            candidate_id=body["posting_candidate_id"],
            source_id=body["source_id"],
            source_reference=body["source_reference"],
            source_reference_text=body["title"],
            title=body["title"],
            employer=body.get("employer"),
            location=body.get("location"),
            posting_text=body["untrusted_bounded_posting_text"],
            extraction_confidence="MODERATE",
            provider_sources=body.get("provider_provenance", []),
            source_type=body.get("source_type"),
            source_url=body.get("source_url"),
            source_provenance=body.get("source_provenance", []),
            title_classification=body.get("title_classification"),
        )
        cases.append(
            PostingCandidateAssessment(
                candidate=candidate,
                geography_status="IN_SCOPE",
                title_match=body.get("title_classification") or "EXACT_TARGET",
            )
        )
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    cases = load_cases()
    if not args.live:
        print(
            json.dumps(
                [
                    {"employer": c.candidate.employer, "characters": len(c.candidate.posting_text)}
                    for c in cases
                ]
            )
        )
        return
    settings = load_live_settings().model_copy(update={"max_retries": 0})
    if settings.llm_provider != "fireworks" or not settings.fireworks_streaming:
        raise ValueError("Requires configured streaming Fireworks; no provider override")
    output = ROOT / "outputs/parallel-extraction" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    deadline = started + 600
    report = {
        "model": settings.extraction_model,
        "prompt_version": PROMPT_VERSION,
        "workers": 2,
        "max_calls": 4,
        "max_retries": 0,
        "batch_deadline_seconds": 600,
        "max_output_tokens": settings.model_max_output_tokens,
        "source": (
            "Frozen public job texts, one full body and three short snippets; not fresh retrieval"
        ),
        "caveat": "Website may also be calling provider; no controlled serial baseline",
        "cases": [],
    }
    save(output / "manifest.json", report)
    print(f"OUTPUT {output}", flush=True)

    def run(index, assessment):
        begin = time.monotonic()
        row = {
            "index": index,
            "employer": assessment.candidate.employer,
            "title": assessment.candidate.title,
            "input_characters": len(assessment.candidate.posting_text),
            "input_sha256": hashlib.sha256(assessment.candidate.posting_text.encode()).hexdigest(),
            "started_after_seconds": round(begin - started, 2),
        }
        if begin >= deadline:
            return {**row, "status": "NOT_ATTEMPTED_BATCH_DEADLINE"}
        folder = output / f"posting-{index:02d}"
        folder.mkdir()
        provider = RecordedProvider(configured_provider(settings), folder)
        provider.deadline = deadline
        gateway = ModelGateway.from_settings(settings, providers={"fireworks": provider})
        print(
            f"POSTING {index} START {row['employer']} +{row['started_after_seconds']}s", flush=True
        )
        result = extract_posting_requirements(assessment, gateway)
        row.update(
            {
                "duration_seconds": round(time.monotonic() - begin, 2),
                "finished_after_seconds": round(time.monotonic() - started, 2),
                "failure_category": result.failure_category,
                "raw_count": result.raw_count,
                "retained_count": len(result.requirements),
                "rejected_count": result.rejected_count,
                "unsupported_count": result.unsupported_count,
                "retained_types": dict(
                    Counter(r.statement_type.value for r in result.requirements)
                ),
            }
        )
        save(
            folder / "validated.json",
            {
                "summary": row,
                "requirements": [r.model_dump(mode="json") for r in result.requirements],
                "audit": [r.model_dump(mode="json") for r in result.audit_items],
                "limitations": result.limitations,
            },
        )
        metrics_file = folder / "call-01.metrics.json"
        if metrics_file.exists():
            row["provider_metrics"] = json.loads(metrics_file.read_text(encoding="utf-8"))
        print("POSTING RETURN " + json.dumps(row), flush=True)
        return row

    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = [pool.submit(run, index, case) for index, case in enumerate(cases, 1)]
        for future in as_completed(pending):
            report["cases"].append(future.result())
            save(output / "results.json", report)
    report["wall_seconds"] = round(time.monotonic() - started, 2)
    report["sum_individual_seconds"] = round(
        sum(r.get("duration_seconds", 0) for r in report["cases"]), 2
    )
    report["cases"].sort(key=lambda r: r["index"])
    save(output / "results.json", report)
    print("COMPLETE " + json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
