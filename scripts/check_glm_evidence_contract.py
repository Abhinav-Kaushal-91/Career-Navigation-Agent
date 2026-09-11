"""Small opt-in GLM contract test using saved public JDs and a synthetic demo.

No retrieval, browser session changes, real candidate data or private model traces.
Uses the production provider, prompts, schema validation and comparison service.
Maximum five live requests, no retries, and a fifteen-minute total provider budget.
"""

import argparse
import hashlib
import json
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from ai_career_navigator.career.comparison import compare_candidate_to_requirements
from ai_career_navigator.career.comparison_prompts import PROMPT_VERSION as COMPARISON_VERSION
from ai_career_navigator.domain import ConfidenceLevel, RequirementCategory, RoleRequirement
from ai_career_navigator.market.requirement_prompts import PROMPT_VERSION as EXTRACTION_VERSION
from ai_career_navigator.market.requirement_schemas import (
    MarketRequirementAnalysis,
    MarketRequirementSummary,
    PostingCandidateAssessment,
    RequirementRunStatus,
)
from ai_career_navigator.market.requirements import extract_posting_requirements
from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.models.errors import ModelProviderError
from ai_career_navigator.models.inspection import LocalModelInspector
from ai_career_navigator.models.providers import FakeModelProvider, configured_provider
from ai_career_navigator.profile.service import build_candidate_profile
from ai_career_navigator.ui.demo_data import sample_profile_draft
from ai_career_navigator.ui.live_workflow import load_live_settings

ROOT = Path(__file__).resolve().parents[1]


def save(path, value):
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


class RecordedProvider:
    provider_name = "fireworks"

    def __init__(self, delegate, output):
        self.delegate = delegate
        self.output = output
        self.calls = 0
        self.deadline = time.monotonic() + 900

    def generate_structured(self, **kwargs):
        remaining = self.deadline - time.monotonic()
        if self.calls >= 5 or remaining <= 0:
            raise ModelProviderError("Diagnostic request/time budget exhausted; not sent")
        self.calls += 1
        kwargs["timeout_seconds"] = min(kwargs["timeout_seconds"], remaining)
        request = kwargs["request"]
        prefix = self.output / f"call-{self.calls:02d}"
        # Exact non-secret Fireworks body, matching the production adapter.
        save(
            prefix.with_suffix(".request.json"),
            {
                "model": kwargs["model"],
                "messages": [
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.user_prompt},
                ],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": True,
                "stream_options": {"include_usage": True},
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": request.response_schema_name,
                        "schema": kwargs["output_schema"],
                    },
                },
            },
        )
        print(f"CALL {self.calls} START {request.response_schema_name}", flush=True)
        started = time.monotonic()
        try:
            response = self.delegate.generate_structured(**kwargs)
        except Exception as error:
            save(
                prefix.with_suffix(".failure.json"),
                {
                    "category": type(error).__name__,
                    "seconds": time.monotonic() - started,
                },
            )
            print(f"CALL {self.calls} FAILED {type(error).__name__}", flush=True)
            raise
        # The production adapter removes reasoning before exposing ModelResponse.content.
        prefix.with_suffix(".response.txt").write_text(response.content, encoding="utf-8")
        metrics = {
            "seconds": round(time.monotonic() - started, 2),
            "finish_reason": response.finish_reason,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
        }
        save(prefix.with_suffix(".metrics.json"), metrics)
        print(f"CALL {self.calls} RETURN {json.dumps(metrics)}", flush=True)
        return response

    def generate_text(self, **kwargs):
        raise ModelProviderError("Text generation is outside this diagnostic")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--reuse-extraction", type=Path)
    parser.add_argument(
        "--only-case",
        choices=[
            "optional_mentoring",
            "cloud_alternatives",
            "java_experience",
            "unconfirmed_java8",
        ],
    )
    args = parser.parse_args()
    assert args.live
    settings = load_live_settings().model_copy(update={"max_retries": 0})
    if settings.llm_provider != "fireworks" or not settings.fireworks_streaming:
        raise ValueError("Expected configured streaming Fireworks; no provider override allowed")
    output = ROOT / "outputs/glm-contract-check" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True, exist_ok=False)
    recorded = RecordedProvider(configured_provider(settings), output)
    gateway = ModelGateway.from_settings(settings, providers={"fireworks": recorded})
    gateway.inspector = LocalModelInspector()
    saved = json.loads(
        (ROOT / "outputs/nemotron-live-overview/20260909T185859Z/results.json").read_text(
            encoding="utf-8"
        )
    )
    assessment = PostingCandidateAssessment.model_validate(saved["postings"][0]["assessment"])
    profile = build_candidate_profile(sample_profile_draft(), approved=True)
    summary = MarketRequirementSummary(
        target_role="Senior Java Developer",
        geography="Toronto, Canada",
        source_page_count=1,
        identified_candidate_count=1,
        validated_in_scope_posting_count=1,
        analyzed_posting_count=1,
        exact_title_analyzed_count=1,
        related_title_analyzed_count=0,
        out_of_scope_count=0,
        unclear_geography_count=0,
        irrelevant_title_count=0,
    )
    report = {
        "mode": "LIVE_PRODUCTION_GATEWAY_BOUNDED_DIAGNOSTIC",
        "model": settings.reasoning_model,
        "extraction_model": settings.extraction_model,
        "max_output_tokens": settings.model_max_output_tokens,
        "timeout_seconds": settings.model_timeout_seconds,
        "max_retries": 0,
        "prompt_versions": [EXTRACTION_VERSION, COMPARISON_VERSION],
        "source": "saved Cognizant JD; not a new vacancy/availability check",
        "source_sha256": hashlib.sha256(assessment.candidate.posting_text.encode()).hexdigest(),
        "profile": "synthetic demo; no inferred strengths automatically approved",
        "cases": [],
    }
    print(f"OUTPUT {output}", flush=True)
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "model",
                    "max_output_tokens",
                    "timeout_seconds",
                    "prompt_versions",
                )
            }
        ),
        flush=True,
    )
    save(output / "manifest.json", report)
    extraction_gateway = gateway
    if args.reuse_extraction:
        extraction_gateway = ModelGateway(
            provider=FakeModelProvider(
                default_response=args.reuse_extraction.read_text(encoding="utf-8")
            ),
            models={ModelRole.EXTRACTION: "saved-live-glm-response"},
            max_retries=0,
            timeout_seconds=10,
        )
        report["extraction_replayed_from"] = str(args.reuse_extraction.resolve())
    outcome = extract_posting_requirements(assessment, extraction_gateway)
    report["extraction"] = {
        "failure_category": outcome.failure_category,
        "raw_count": outcome.raw_count,
        "retained_count": len(outcome.requirements),
        "retained_types": dict(Counter(item.statement_type.value for item in outcome.requirements)),
        "limitations": outcome.limitations,
        "audit": [item.model_dump(mode="json") for item in outcome.audit_items],
    }
    save(output / "results.json", report)
    print(
        "EXTRACTION", outcome.raw_count, "raw;", len(outcome.requirements), "retained", flush=True
    )
    # These expectations are selected from the actual newly validated model output.
    predicates = [
        ("optional_mentoring", lambda r: "mentor" in (r.normalized_capability or "").lower()),
        (
            "cloud_alternatives",
            lambda r: r.relationship == "ANY_OF" and "aws" in r.requirement_text.lower(),
        ),
        (
            "java_experience",
            lambda r: r.years_required is not None and "java" in r.requirement_text.lower(),
        ),
    ]
    chosen = []
    for label, predicate in predicates:
        match = next((item for item in outcome.requirements if predicate(item)), None)
        if match is None:
            report["cases"].append({"case": label, "status": "NOT_EXTRACTED_OR_NOT_RETAINED"})
        else:
            chosen.append((label, match, assessment))
    # One saved version-specific quote tests the prior Java-only false-positive directly.
    audit = json.loads(
        (ROOT / "outputs/run-audits/250a5a5d-67ab-44af-9e48-190b91ee2d9e.json").read_text(
            encoding="utf-8"
        )
    )
    version_posting, version_row = next(
        (posting, row)
        for posting in audit["postings"]
        for row in posting["requirements"]
        if "java8" in row["source_quote"].lower()
    )
    version_source = assessment.model_copy(
        update={
            "candidate": assessment.candidate.model_copy(
                update={
                    "posting_id": UUID(version_posting["posting_id"]),
                    "title": version_posting["title"],
                    "employer": version_posting["employer"],
                    "source_reference": version_posting["source"],
                    "source_url": None,
                    "posting_text": version_row["source_quote"],
                    "retrieval_quality": "LOW",
                }
            )
        }
    )
    version_req = RoleRequirement(
        posting_id=version_source.candidate.posting_id,
        requirement_text=version_row["source_quote"],
        normalized_capability="Java",
        category=RequirementCategory.TECHNICAL,
        qualifier_quotes=["Java8"],
        mandatory=bool(version_row["mandatory"]),
        extraction_confidence=ConfidenceLevel.HIGH,
    )
    chosen.append(("unconfirmed_java8", version_req, version_source))
    for label, requirement, source in chosen:
        if args.only_case and label != args.only_case:
            continue
        market = MarketRequirementAnalysis(
            status=RequirementRunStatus.SUCCEEDED,
            summary=summary,
            assessments=[source],
            requirements=[requirement],
        )
        result = compare_candidate_to_requirements(profile, market, gateway)
        report["cases"].append(
            {
                "case": label,
                "requirement": requirement.model_dump(mode="json"),
                "result": result.model_dump(mode="json"),
            }
        )
        save(output / "results.json", report)
        save(output / "gateway-events.json", gateway.inspector.events)
        print(
            "CASE",
            label,
            result.status,
            [item.match_type for item in result.comparisons],
            flush=True,
        )
    report["live_calls"] = recorded.calls
    report["overall_accessibility"] = "NOT_ASSESSED: a small contract test is not a market sample"
    save(output / "results.json", report)
    save(output / "gateway-events.json", gateway.inspector.events)
    print("DONE", output, flush=True)


if __name__ == "__main__":
    main()
