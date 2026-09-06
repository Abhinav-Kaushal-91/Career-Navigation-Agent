"""Explicit, manual-only smoke test for configured capability inference."""

# ruff: noqa: E402 -- the local src path must be installed before project imports.

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from ai_career_navigator.config import Settings
from ai_career_navigator.domain import (
    ApprovalStatus,
    CandidateProfile,
    CareerStage,
    ConfidenceLevel,
    EvidenceConfirmationStatus,
    EvidenceItem,
    EvidenceMaturity,
)
from ai_career_navigator.models import ModelGateway
from ai_career_navigator.profile import infer_capabilities


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manual-only configured-provider capability-inference smoke validation."
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Local environment file read through Settings; secrets are never printed.",
    )
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    if args.env_file is not None and not args.env_file.is_file():
        raise SystemExit(f"Environment file not found: {args.env_file}")
    settings = Settings(_env_file=args.env_file)
    if settings.llm_provider not in {"fireworks", "nvidia"}:
        raise SystemExit("Set LLM_PROVIDER to fireworks or nvidia before running this smoke test.")
    if settings.llm_provider == "fireworks" and settings.fireworks_api_key is None:
        raise SystemExit("FIREWORKS_API_KEY is required. The key will not be printed.")
    if settings.llm_provider == "nvidia" and settings.nvidia_api_key is None:
        raise SystemExit("NVIDIA_API_KEY is required. The key will not be printed.")

    now = datetime.now(UTC)
    evidence = EvidenceItem(
        evidence_type="skill",
        source_type="manual smoke fixture",
        source_reference="Production automation project",
        capability="REST APIs",
        description="Integrated production automation workflows with REST APIs.",
        maturity_level=EvidenceMaturity.PRODUCTION,
        confirmation_status=EvidenceConfirmationStatus.EXPLICIT,
        confidence=ConfidenceLevel.HIGH,
        approved_by_user=True,
        created_at=now,
    )
    profile = CandidateProfile(
        career_stage=CareerStage.MID_CAREER,
        current_role="Automation Developer",
        evidence_items=[evidence],
        approval_status=ApprovalStatus.APPROVED,
        created_at=now,
        confirmed_at=now,
    )
    outcome = infer_capabilities(profile, ModelGateway.from_settings(settings))
    print(
        f"status={outcome.status.value} provider={outcome.provider} "
        f"model={outcome.model} inferred={len(outcome.inferred_evidence)}"
    )
    for item in outcome.inferred_evidence:
        print(
            f"capability={item.capability} maturity={item.maturity_level.value} "
            f"confidence={item.confidence.value}"
        )


if __name__ == "__main__":
    main()
