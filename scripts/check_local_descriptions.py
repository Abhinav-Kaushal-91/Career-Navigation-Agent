"""Run supplied local descriptions through the unchanged production graph.

No discovery calls, title overrides, fabricated URLs, or inference approvals.
Loopback source URLs identify local files, not verified public vacancies.
"""

import argparse
import asyncio
import hashlib
import json
import os
import time
from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from check_demo_to_analysis import BoundedRecorder
from pydantic_core import to_jsonable_python

from ai_career_navigator.domain import (
    ApprovalStatus,
    CareerGoal,
    CurrentMarketSnapshot,
    GeographyScope,
    GoalType,
    JobPosting,
    SourceRecord,
)
from ai_career_navigator.market.batch_profile import description_word_count
from ai_career_navigator.market.processing import assess_title, classify_seniority
from ai_career_navigator.market.schemas import (
    MarketPageContent,
    MarketPostingEvidence,
    MarketRetrievalResult,
    SearchPlan,
)
from ai_career_navigator.models.inspection import LocalModelInspector
from ai_career_navigator.models.providers import configured_provider
from ai_career_navigator.profile.service import build_candidate_profile
from ai_career_navigator.ui.demo_data import sample_profile_draft
from ai_career_navigator.ui.live_workflow import build_live_workflow_runtime, load_live_settings

ROOT = Path(__file__).resolve().parents[1]
# Source metadata transcribed from the supplied text. BMO's precise title is
# missing from its body, so its filename label is explicitly qualified below.
FILE_METADATA = {
    "Senior Software Engineer 3.txt": (
        "Senior Java Full Stack Developer",
        "LTIMindtree",
        "Mississauga, Ontario, Canada",
    ),
    "Senior Software Engineer 4.txt": (
        "Senior Software Engineer – Data Platform",
        "Kaseya",
        "Toronto, Ontario, Canada",
    ),
    "Senior Software Engineer 5.txt": (
        "Senior Software Engineer",
        "BMO",
        "Toronto, Ontario, Canada",
    ),
    "Senior Software Engineer.txt": (
        "Senior Software Engineer (Cloud, Data & APIs)",
        "Tactable",
        "Toronto, Ontario, Canada",
    ),
    "Software Developer.txt": (
        "Senior Full Stack Developer",
        "Impro.AI",
        "Toronto, Ontario, Canada",
    ),
}


def load_descriptions(folder, target, metadata=None):
    metadata = FILE_METADATA if metadata is None else metadata
    evidence, manifest = [], []
    now = datetime.now(UTC)
    for path in sorted(folder.glob("*.txt")):
        if path.name not in metadata:
            raise ValueError(f"Source metadata needs review for {path.name}")
        body = path.read_text(encoding="utf-8-sig").strip()
        if not body:
            raise ValueError(f"Empty description: {path.name}")
        title, employer, location = metadata[path.name]
        digest = hashlib.sha256(body.encode()).hexdigest()
        url = f"http://127.0.0.1/local-job-description/{digest}"
        notes = [
            "User-supplied text; public posting URL and active status not verified.",
            "Loopback source URL is a local provenance identifier, not an employer link.",
        ]
        if employer == "BMO":
            notes.append("Title taken from filename; city inferred from supplied street address.")
        if "not specified" in location.casefold():
            notes.append("City is not established by the supplied description; verify location.")
        classification = assess_title(title, target, posting_text=body)
        source = SourceRecord(
            source_type="USER_SUPPLIED_TEXT",
            title=path.name,
            url=url,
            employer=employer,
            geography=location,
            retrieval_date=now.date(),
            limitations=notes,
        )
        posting = JobPosting(
            source_id=source.source_id,
            original_title=title,
            employer=employer,
            location=location,
            location_evidence_text=location,
            requested_geography_scope=GeographyScope.METRO_AREA,
            matched_geography_scope=GeographyScope.METRO_AREA,
            retrieved_at=now,
            extraction_confidence="MODERATE",
            content_fingerprint=digest,
            currentness_basis="USER_SUPPLIED_NOT_VERIFIED",
        )
        evidence.append(
            MarketPostingEvidence(
                posting=posting,
                primary_source=source,
                primary_content=MarketPageContent(
                    url=url,
                    title=title,
                    employer=employer,
                    location=location,
                    markdown=body,
                    content_complete=None,
                ),
                source_type="INDIVIDUAL_JOB_BOARD_POSTING",
                retrieval_quality="MODERATE",
                title_classification=classification.value,
                seniority_classification=classify_seniority(title),
                limitations=notes,
            )
        )
        manifest.append(
            {
                "file": path.name,
                "sha256": digest,
                "title": title,
                "employer": employer,
                "location": location,
                "words": description_word_count(body),
                "characters": len(body),
                "classification": classification.value,
                "posting_id": str(posting.posting_id),
                "limitations": notes,
            }
        )
    if not evidence:
        raise ValueError("No text files found")
    return evidence, manifest


def local_retrieval(goal, evidence):
    # Keep every input in the audit; do not count irrelevant roles as validated leads.
    retained = [e for e in evidence if e.title_classification != "IRRELEVANT"]
    employer_counts = Counter(e.posting.employer for e in retained if e.posting.employer)
    counts = {
        kind: sum(e.title_classification == kind for e in retained)
        for kind in ("EXACT_TARGET", "TARGET_VARIANT", "RELATED_TITLE")
    }
    snapshot = CurrentMarketSnapshot(
        target_role=goal.target_role,
        geography=goal.target_location,
        search_date=datetime.now(UTC).date(),
        exact_title_count=counts["EXACT_TARGET"],
        target_variant_count=counts["TARGET_VARIANT"],
        related_title_count=counts["RELATED_TITLE"],
        validated_posting_count=len(retained),
        distinct_employer_count=len(employer_counts),
        employer_posting_counts=dict(employer_counts),
        known_employer_posting_count=sum(employer_counts.values()),
        largest_employer_posting_count=max(employer_counts.values(), default=0),
        top_three_employer_posting_count=sum(sorted(employer_counts.values(), reverse=True)[:3]),
        opportunity_availability="INSUFFICIENT_EVIDENCE",
        employer_diversity="INSUFFICIENT_EVIDENCE",
        market_concentration="INSUFFICIENT_EVIDENCE",
        evidence_confidence="LOW",
        source_ids=[e.primary_source.source_id for e in retained],
        limitations=[
            "User-selected local descriptions, not a live market search or vacancy count.",
            "Posting URLs and current availability are unverified; no availability inference.",
        ],
    )
    return MarketRetrievalResult(
        plan=SearchPlan(
            status="READY",
            goal_type=goal.goal_type,
            target_role=goal.target_role,
            geography=goal.target_location,
            expansion_permitted=True,
        ),
        snapshot=snapshot,
        sources=[e.primary_source for e in evidence],
        postings=[e.posting for e in retained],
        posting_evidence=evidence,
        source_coverage_reason="Local user-supplied descriptions; discovery bypassed.",
    )


async def run(args):
    metadata_path = getattr(args, "metadata", None)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path else None
    evidence, manifest = load_descriptions(args.folder, args.target, metadata)
    print(json.dumps(manifest, indent=2), flush=True)
    if not args.live:
        return
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    output = ROOT / "outputs/local-descriptions" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True, exist_ok=False)
    settings = load_live_settings().model_copy(
        update={
            "langsmith_tracing": False,
            "run_audit_directory": output / "run-audits",
        }
    )
    secrets = tuple(
        v.get_secret_value()
        for n in type(settings).model_fields
        if hasattr((v := getattr(settings, n)), "get_secret_value")
    )
    sanitizer = LocalModelInspector(secrets=secrets, max_events=1)
    recorder = BoundedRecorder(configured_provider(settings), output, sanitizer)
    runtime = build_live_workflow_runtime(settings, provider_override=recorder)
    profile = build_candidate_profile(sample_profile_draft(), approved=True)
    goal = CareerGoal(
        goal_type=GoalType(getattr(args, "goal_type", GoalType.CURRENT_MARKET_ANALYSIS)),
        target_role=args.target,
        target_location="Toronto, Canada",
        geography_scopes=[GeographyScope.METRO_AREA],
        target_timeline_months=None,
        search_expansion_permission=True,
        approval_status=ApprovalStatus.APPROVED,
        approved_at=datetime.now(UTC),
    )

    async def retrieve(_goal, _client, **_kwargs):
        return local_retrieval(_goal, evidence)

    # The sole injection is local text at the market-retrieval boundary.
    runtime.controller._context = replace(
        runtime.controller._context,
        structured_market_client_factory=None,
        market_client_factory=lambda: None,
        market_retrieval_service=retrieve,
    )
    run_id = uuid4()
    thread = f"local-description-{run_id}"
    report = {
        "mode": "USER_SUPPLIED_DESCRIPTIONS_LIVE_MODEL_SYNTHETIC_PROFILE",
        "run_id": str(run_id),
        "manifest": manifest,
        "target": args.target,
        "provider": settings.llm_provider,
        "model": settings.reasoning_model,
        "goal_type": goal.goal_type,
        "discovery_calls": 0,
        "title_overrides_used": False,
        "title_policy": "DESCRIPTION_SUPPORTED_SPECIALTY",
        "inferred_strengths_auto_approved": False,
        "steps": [],
    }
    started = previous = time.monotonic()

    def save():
        report["graph_state"] = runtime.controller.inspect(thread_id=thread).state
        report["total_seconds"] = round(time.monotonic() - started, 2)
        report["model_calls"] = recorder.calls
        sanitizer.record("report", data=to_jsonable_python(report))
        (output / "results.json").write_text(
            json.dumps(sanitizer.events[-1]["data"], indent=2), encoding="utf-8"
        )

    print(f"OUTPUT {output}", flush=True)
    try:
        async with asyncio.timeout(1800):
            async for node in runtime.controller.stream_start(
                thread_id=thread,
                confirmed_profile=profile,
                confirmed_goal=goal,
                capability_inference_requested=False,
                run_id=run_id,
            ):
                now = time.monotonic()
                report["steps"].append({"step": node, "seconds": round(now - previous, 2)})
                previous = now
                print(f"STEP {node} {report['steps'][-1]['seconds']}s", flush=True)
                save()
    except Exception as error:
        report["exception_category"] = type(error).__name__
    finally:
        report["market_analysis"] = runtime.controller._context.content_store.get_analysis(run_id)
        save()
        print(f"FINISHED {output / 'results.json'}", flush=True)
        print(
            json.dumps({k: report[k] for k in ("total_seconds", "model_calls", "steps")}),
            flush=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, default=ROOT / "job-descriptions")
    parser.add_argument("--target", default="Senior Java Developer")
    parser.add_argument(
        "--metadata", type=Path, help="Reviewed filename-to-title/employer/location JSON"
    )
    parser.add_argument(
        "--goal-type",
        choices=[g.value for g in GoalType],
        default=GoalType.CURRENT_MARKET_ANALYSIS.value,
    )
    parser.add_argument("--live", action="store_true")
    asyncio.run(run(parser.parse_args()))
