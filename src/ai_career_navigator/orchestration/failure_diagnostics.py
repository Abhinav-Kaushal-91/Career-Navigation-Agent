"""Allowlisted failure diagnostics: no exception text, payloads, credentials or traces."""

import json
import logging
import math
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from .state import WorkflowStage

logger = logging.getLogger(__name__)

_CODES = {
    "MARKETTIMEOUTERROR": "MARKET_TIMEOUT",
    "MARKET_TIMEOUT_ERROR": "MARKET_TIMEOUT",
    "MARKETRATELIMITERROR": "MARKET_RATE_LIMIT",
    "MARKET_RATE_LIMIT_ERROR": "MARKET_RATE_LIMIT",
    "MARKETCONTENTERROR": "MARKET_RESPONSE_INVALID",
    "MARKETTOOLERROR": "MARKET_RESPONSE_INVALID",
    "MARKETTRANSPORTERROR": "MARKET_TRANSPORT_ERROR",
    "MARKETAUTHENTICATIONERROR": "AUTHENTICATION_ERROR",
    "MARKETCONFIGURATIONERROR": "CONFIGURATION_ERROR",
    "VALIDATIONERROR": "SCHEMA_VALIDATION_ERROR",
    "MODELTIMEOUTERROR": "MODEL_TIMEOUT",
    "MODELPROVIDERERROR": "MODEL_PROVIDER_ERROR",
    "ATTRIBUTEERROR": "INTERNAL_ATTRIBUTE_ERROR",
    "TYPEERROR": "INTERNAL_TYPE_ERROR",
    "VALUEERROR": "INTERNAL_VALUE_ERROR",
    "KEYERROR": "INTERNAL_KEY_ERROR",
}
_SAFE_CODES = {
    *_CODES.values(),
    "ROLE_DISCOVERY_REQUIRED",
    "MARKET_PROCESSING_ERROR",
    "MARKET_PROCESSING_FAILED",
    "SAME_ROLE_ASSESSMENT_PROCESSING_FAILED",
    "TRANSITION_ASSESSMENT_PROCESSING_FAILED",
    "INTERRUPTED_RUN",
    "INVALID_CONFIRMED_PROFILE",
    "INVALID_CONFIRMED_GOAL",
    "CAREER_PLAN_UNAVAILABLE",
    "INTERNAL_ERROR",
}
_SAFE_STAGES = {stage.value for stage in WorkflowStage} | {
    "INITIALIZATION",
    "WORKFLOW_EXECUTION",
    "UNKNOWN",
}


def safe_failure_code(category: str | None) -> str:
    value = str(category or "").upper()
    code = _CODES.get(value, value)
    return code if code in _SAFE_CODES else "INTERNAL_ERROR"


def record_live_failure(
    category,
    *,
    stage,
    elapsed_seconds,
    run_id=None,
    market_result_preserved=False,
    last_checkpoint_stage=None,
    directory=Path("outputs/failed-runs"),
):
    """Return a small safe record even if local persistence fails; never raise for I/O."""
    try:
        verified_run_id = str(UUID(str(run_id))) if run_id else None
    except (ValueError, TypeError, AttributeError):
        verified_run_id = None
    stage_value = getattr(stage, "value", stage)
    checkpoint_stage = getattr(last_checkpoint_stage, "value", last_checkpoint_stage)
    elapsed = float(elapsed_seconds)
    record = {
        "schema_version": 1,
        "failure_id": str(uuid4()),
        "recorded_at": datetime.now(UTC).isoformat(),
        "run_id": verified_run_id,
        "error_code": safe_failure_code(category),
        "stage": stage_value if stage_value in _SAFE_STAGES else "UNKNOWN",
        "last_checkpoint_stage": checkpoint_stage if checkpoint_stage in _SAFE_STAGES else None,
        "elapsed_seconds": round(max(0, elapsed), 3) if math.isfinite(elapsed) else None,
        "market_result_preserved": bool(market_result_preserved),
    }
    # A warning is emitted even when INFO-level workflow logs are disabled.
    logger.warning(
        "live_analysis_failed failure_id=%s run_id=%s code=%s stage=%s elapsed_seconds=%s",
        record["failure_id"],
        record["run_id"],
        record["error_code"],
        record["stage"],
        record["elapsed_seconds"],
    )
    saved = False
    try:
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / f"{record['failure_id']}.json"
        destination.write_text(json.dumps(record, indent=2), encoding="utf-8")
        saved = True
    except OSError:
        logger.warning("live_failure_record_not_saved failure_id=%s", record["failure_id"])
    return {**record, "record_saved": saved}
