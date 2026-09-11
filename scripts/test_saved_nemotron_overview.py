"""Bounded diagnostic of saved public JDs; never retrieves jobs or sends a resume."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import NAMESPACE_URL, uuid5

from ai_career_navigator.config import Settings
from ai_career_navigator.market.overview import synthesize_employer_overview
from ai_career_navigator.market.processing import assess_candidate
from ai_career_navigator.market.requirement_schemas import (
    MarketRequirementSummary,
    PostingCandidate,
    PostingGeographyStatus,
    PostingTitleMatch,
)
from ai_career_navigator.market.requirements import (
    _extraction_quality_counts,
    _quality_and_audit,
    extract_posting_requirements,
)
from ai_career_navigator.market.role_profile import build_canonical_target_role_profile
from ai_career_navigator.models import ModelGateway
from ai_career_navigator.models.providers.nvidia import NvidiaNimProvider


class DiagnosticGateway(ModelGateway):
    """Override the diagnostic budget before request inspection and provider dispatch."""

    output_token_limit = 4096

    def generate_structured(self, *, max_tokens=None, **kwargs):
        return super().generate_structured(max_tokens=self.output_token_limit, **kwargs)


class DiagnosticNvidiaProvider(NvidiaNimProvider):
    """Retain sanitized final content before schema checks, never private traces."""

    inspector = None

    def generate_structured(self, **kwargs):
        response = super().generate_structured(**kwargs)
        if self.inspector is not None:
            self.inspector.record(
                "provider_final_response",
                final_content=response.content,
                finish_reason=response.finish_reason,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
            )
        return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Send at most seven model calls")
    parser.add_argument("--posting-index", type=int, choices=range(1, 7))
    parser.add_argument("--timeout-seconds", type=int, choices=(90, 180, 600), default=90)
    parser.add_argument("--max-output-tokens", type=int, choices=(4096, 20000), default=4096)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root / "outputs/senior-java-basic-case/combined-job-and-jd-inventory.json"
    inventory = json.loads(source.read_text(encoding="utf-8"))["jd_inventory"]
    assert len(inventory) == 6, "This diagnostic is bounded to the reviewed six-document corpus"
    env = root / ".env"
    if not env.is_file():
        env = root / "src/ai_career_navigator/.env"
    configured = Settings(_env_file=env)
    assert configured.llm_provider == "nvidia", "Expected NVIDIA provider"
    assert all(
        "nemotron" in model.lower()
        for model in (
            configured.extraction_model,
            configured.reasoning_model,
        )
    ), "Expected Nemotron for both roles"
    settings = configured.model_copy(
        update={
            "max_retries": 0,
            "model_timeout_seconds": args.timeout_seconds,
            "model_inspector_enabled": True,
        }
    )
    assessments = []
    for jd in inventory:
        url = jd["source_url"]
        candidate = PostingCandidate(
            candidate_id=uuid5(NAMESPACE_URL, "live-review-candidate:" + url),
            posting_id=uuid5(NAMESPACE_URL, "live-review-posting:" + url),
            source_id=uuid5(NAMESPACE_URL, "live-review-source:" + url),
            source_reference=f"{jd['title']} > {jd['employer']}",
            source_reference_text=f"{jd['title']} {jd['employer']}",
            provider="YOU",
            provider_sources=["YOU"],
            source_url=url,
            source_provenance=[url],
            title=jd["title"],
            employer=jd["employer"],
            location=jd.get("location"),
            posting_text=jd["description_markdown"][:20000],
            extraction_confidence="MODERATE",
        )
        assessments.append(
            assess_candidate(
                candidate,
                target_role="Senior Java Developer",
                target_geography="Toronto, Canada",
            )
        )
    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "mode": "LIVE_MODEL_SAVED_PUBLIC_JDS" if args.live else "PREFLIGHT_NO_CALLS",
        "extraction_model": settings.extraction_model,
        "overview_model": settings.reasoning_model,
        "timeout_seconds": settings.model_timeout_seconds,
        "max_retries": settings.max_retries,
        "max_output_tokens": args.max_output_tokens,
        "single_posting_probe": args.posting_index,
        "configured_timeout_seconds": configured.model_timeout_seconds,
        "configured_max_retries": configured.max_retries,
        "limitations": [
            "Saved six-description diagnostic, not a replay of the current 27-posting portal run.",
            "No fresh retrieval, vacancy verification, candidate comparison or Plan call.",
            "Reconstructed source IDs; original metadata and source limitations retained below.",
            "Extraction tests selected saved inputs; single-posting probes do not build a profile.",
            "Atyeti is generic job-board wording; acceptance does not verify authenticity.",
            "Inspector retains sanitized provider final content, never private reasoning traces.",
        ],
        "postings": [],
    }
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "mode",
                    "extraction_model",
                    "overview_model",
                    "timeout_seconds",
                    "max_retries",
                    "max_output_tokens",
                )
            }
        ),
        flush=True,
    )
    for item in assessments:
        print(
            f"{item.candidate.employer}: {item.candidate.title} | "
            f"{item.title_match.value} | {item.geography_status.value}",
            flush=True,
        )
    if not args.live:
        return
    destination = (
        root / "outputs/nemotron-live-overview" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    )
    destination.mkdir(parents=True, exist_ok=False)
    provider = DiagnosticNvidiaProvider(settings.nvidia_api_key)
    gateway = DiagnosticGateway.from_settings(settings, providers={"nvidia": provider})
    gateway.output_token_limit = args.max_output_tokens
    provider.inspector = gateway.inspector

    def save():
        report["model_events"] = gateway.inspector.events
        (destination / "results.json").write_text(
            json.dumps(report, indent=2, default=str), encoding="utf-8"
        )

    save()
    extracted, qualities, audits, eligible = [], [], [], []
    for index, (jd, assessment) in enumerate(zip(inventory, assessments, strict=True), 1):
        if args.posting_index and index != args.posting_index:
            continue
        print(f"START {index}/6 {jd['employer']}", flush=True)
        started = perf_counter()
        outcome = extract_posting_requirements(assessment, gateway)
        quality, audit = _quality_and_audit(assessment, outcome, enrichment_used=False)
        is_eligible = (
            assessment.geography_status is PostingGeographyStatus.IN_SCOPE
            and assessment.title_match is not PostingTitleMatch.IRRELEVANT
        )
        report["postings"].append(
            {
                "employer": jd["employer"],
                "title": jd["title"],
                "source_url": jd["source_url"],
                "source_limitations": jd.get("limitations", []),
                "assessment": assessment.model_dump(mode="json"),
                "eligible_for_profile": is_eligible,
                "elapsed_seconds": round(perf_counter() - started, 2),
                "quality": quality.model_dump(mode="json"),
                "audit": audit.model_dump(mode="json"),
                "accepted_requirements": [
                    item.model_dump(mode="json") for item in outcome.requirements
                ],
            }
        )
        if is_eligible:
            eligible.append(assessment)
            qualities.append(quality)
            audits.append(audit)
            if not quality.failure_category:
                extracted.append((assessment, outcome.requirements))
        save()
        print(
            f"DONE {index}/6: raw={outcome.raw_count} accepted={len(outcome.requirements)} "
            f"unsupported={outcome.unsupported_count} failure={quality.failure_category} "
            f"seconds={report['postings'][-1]['elapsed_seconds']}",
            flush=True,
        )
    if args.posting_index:
        report["finished_at"] = datetime.now(UTC).isoformat()
        report["overview"] = {"method": "NOT_ATTEMPTED_SINGLE_POSTING_DIAGNOSTIC"}
        save()
        print(f"Results: {destination / 'results.json'}", flush=True)
        return
    summary = MarketRequirementSummary(
        **_extraction_quality_counts(extracted, qualities),
        target_role="Senior Java Developer",
        geography="Toronto, Canada",
        source_page_count=6,
        identified_candidate_count=6,
        validated_in_scope_posting_count=len(eligible),
        analyzed_posting_count=len(extracted),
        exact_title_analyzed_count=sum(
            a.title_match is PostingTitleMatch.EXACT_TARGET for a, _ in extracted
        ),
        target_variant_analyzed_count=sum(
            a.title_match is PostingTitleMatch.TARGET_VARIANT for a, _ in extracted
        ),
        related_title_analyzed_count=sum(
            a.title_match is PostingTitleMatch.RELATED_TITLE for a, _ in extracted
        ),
        out_of_scope_count=sum(
            a.geography_status is PostingGeographyStatus.OUT_OF_SCOPE for a in assessments
        ),
        unclear_geography_count=sum(
            a.geography_status is PostingGeographyStatus.UNCLEAR for a in assessments
        ),
        irrelevant_title_count=sum(
            a.title_match is PostingTitleMatch.IRRELEVANT for a in assessments
        ),
    )
    profile, canonical_audits = build_canonical_target_role_profile(
        target_role=summary.target_role,
        geography=summary.geography,
        requirements=[item for _, items in extracted for item in items],
        assessments=assessments,
        summary=summary,
        posting_audits=audits,
        generated_at=datetime.now(UTC),
    )
    report["summary"] = summary.model_dump(mode="json")
    report["canonical_profile"] = profile.model_dump(mode="json")
    report["canonical_audits"] = [item.model_dump(mode="json") for item in canonical_audits]
    save()
    print("START cross-posting overview (at most one call)", flush=True)
    report["overview"] = synthesize_employer_overview(profile, gateway).model_dump(mode="json")
    report["finished_at"] = datetime.now(UTC).isoformat()
    save()
    print(
        f"FINISHED profile={profile.profile_status.value} overview={report['overview']['method']}",
        flush=True,
    )
    print(f"Results: {destination / 'results.json'}", flush=True)


if __name__ == "__main__":
    main()
