import json
from uuid import uuid4

import pytest

from ai_career_navigator.orchestration.failure_diagnostics import (
    record_live_failure,
    safe_failure_code,
)


@pytest.mark.parametrize(
    "category,expected",
    [
        ("MARKETTIMEOUTERROR", "MARKET_TIMEOUT"),
        ("MarketRateLimitError", "MARKET_RATE_LIMIT"),
        ("MARKETCONTENTERROR", "MARKET_RESPONSE_INVALID"),
        ("ValidationError", "SCHEMA_VALIDATION_ERROR"),
        ("AttributeError", "INTERNAL_ATTRIBUTE_ERROR"),
        ("secret-key-and-private-error", "INTERNAL_ERROR"),
    ],
)
def test_codes_are_allowlisted(category, expected):
    assert safe_failure_code(category) == expected


def test_persists_only_safe_failure_fields(tmp_path, caplog):
    result = record_live_failure(
        "secret-key-and-profile",
        stage="private-profile",
        run_id="secret-key",
        elapsed_seconds=12.3456,
        directory=tmp_path,
    )
    saved = json.loads((tmp_path / f"{result['failure_id']}.json").read_text())
    assert saved["error_code"] == "INTERNAL_ERROR"
    assert saved["stage"] == "UNKNOWN"
    assert saved["run_id"] is None
    assert saved["elapsed_seconds"] == 12.346
    assert result["record_saved"]
    assert "secret-key" not in json.dumps(saved) + caplog.text
    assert "private-profile" not in json.dumps(saved) + caplog.text
    assert "live_analysis_failed" in caplog.text


def test_storage_failure_does_not_mask_original_failure(tmp_path, caplog):
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("occupied")
    result = record_live_failure(
        "MARKETTIMEOUTERROR",
        stage="MARKET_RETRIEVAL",
        elapsed_seconds=30,
        run_id=uuid4(),
        directory=blocked,
    )
    assert not result["record_saved"]
    assert result["error_code"] == "MARKET_TIMEOUT"
    assert "live_failure_record_not_saved" in caplog.text
