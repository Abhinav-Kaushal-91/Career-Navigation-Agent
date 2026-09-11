"""Opt-in production extraction check: saved public JDs, no candidate or fresh search."""

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from check_glm_evidence_contract import RecordedProvider, save

from ai_career_navigator.market.batch_profile import analyze_five_postings
from ai_career_navigator.market.schemas import MarketPostingEvidence
from ai_career_navigator.models import ModelGateway
from ai_career_navigator.models.providers import configured_provider
from ai_career_navigator.ui.live_workflow import load_live_settings

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    args = parser.parse_args()
    assert args.live
    settings = load_live_settings().model_copy(update={"max_retries": 0})
    if settings.llm_provider != "fireworks":
        raise ValueError("This check expects the configured Fireworks provider")
    saved = json.loads(
        (ROOT / "outputs/demo-profile-live/20260909T194458Z/results.json").read_text(
            encoding="utf-8"
        )
    )
    sources = [
        MarketPostingEvidence.model_validate(row) for row in saved["retained_posting_evidence"]
    ]
    output = ROOT / "outputs/five-posting-recovery" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True, exist_ok=False)
    recorded = RecordedProvider(configured_provider(settings), output)
    send_stream = recorded.delegate._stream_response

    def audited_stream(payload, request, model, timeout_seconds):
        # Actual adapter body, including deployment-specific reasoning controls;
        # credentials are sent separately by the adapter, never in this artifact.
        save(output / f"wire-{recorded.calls:02d}.json", payload)
        return send_stream(payload, request, model, timeout_seconds)

    recorded.delegate._stream_response = audited_stream
    recorded.deadline = time.monotonic() + 600
    gateway = ModelGateway.from_settings(settings, providers={"fireworks": recorded})
    print(f"OUTPUT {output}", flush=True)
    started = time.monotonic()
    analysis = analyze_five_postings(
        sources,
        target_role="Senior Java Developer",
        geography="Toronto, Canada",
        model_gateway=gateway,
    )
    save(output / "validated-analysis.json", analysis.model_dump(mode="json"))
    canonical = analysis.canonical_profile
    report = {
        "mode": "LIVE_MODEL_SAVED_PUBLIC_SOURCES_NOT_A_FRESH_MARKET_OR_CANDIDATE_RUN",
        "seconds": round(time.monotonic() - started, 2),
        "model_calls": recorded.calls,
        "selected_descriptions": len(canonical.selected_posting_ids),
        "processing_status": canonical.extraction_processing_status,
        "requirements": [item.display_name for item in canonical.requirements],
        "duties": [item.display_name for item in canonical.responsibilities],
        "preferences": [item.display_name for item in canonical.preferences],
        "profile_status": canonical.profile_status,
        "coverage_limitations": canonical.coverage_limitations,
        "limitations": canonical.limitations,
    }
    save(output / "report.json", report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
