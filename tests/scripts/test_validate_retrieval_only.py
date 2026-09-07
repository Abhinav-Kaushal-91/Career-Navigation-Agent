import asyncio
import json
import sys

import pytest

from ai_career_navigator.config import Settings
from ai_career_navigator.market import FakeAdzunaMarketSearchClient
from ai_career_navigator.market.mcp.fake_client import FakeMarketSearchClient
from ai_career_navigator.market.schemas import StructuredJobSearchPage
from scripts import validate_retrieval_only as runner


def test_retrieval_runner_has_no_model_or_candidate_calls():
    primary = FakeAdzunaMarketSearchClient(
        [
            StructuredJobSearchPage(provider="ADZUNA", page=1, results=[]),
        ]
    )
    support = FakeMarketSearchClient()
    result = asyncio.run(
        runner.run_retrieval(
            Settings(_env_file=None, ydc_api_key="private-test-key"),
            role="Senior Java Developer",
            location="Toronto, Canada",
            primary=primary,
            support=support,
        )
    )
    assert result["failure"] is None
    assert result["candidate_data_sent"] is False
    assert result["nvidia_calls"] == 0
    assert result["limits"]["max_total_search_calls"] == 6
    assert result["limits"]["max_content_fetches"] == 12
    assert result["retrieval"]["snapshot"]["search_query_count"] <= 6
    assert "private-test-key" not in json.dumps(result)


def test_cli_requires_allow_live_before_reading_credentials(monkeypatch, tmp_path):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_retrieval_only.py",
            "--env-file",
            "not-read.env",
            "--role",
            "Test Role",
            "--location",
            "Toronto",
            "--output",
            str(tmp_path / "result.json"),
        ],
    )
    with pytest.raises(SystemExit) as error:
        runner.main()
    assert error.value.code == 2


def test_cli_preserves_previous_artifact(monkeypatch, tmp_path):
    output = tmp_path / "prior.json"
    output.write_text("prior result", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_retrieval_only.py",
            "--allow-live",
            "--env-file",
            "not-read.env",
            "--role",
            "Test Role",
            "--location",
            "Toronto",
            "--output",
            str(output),
        ],
    )
    with pytest.raises(SystemExit):
        runner.main()
    assert output.read_text(encoding="utf-8") == "prior result"
