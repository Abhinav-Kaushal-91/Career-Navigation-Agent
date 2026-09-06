import asyncio
from pathlib import Path

import pytest

from ai_career_navigator.config import Settings
from ai_career_navigator.market import MarketSearchResult
from ai_career_navigator.market.schemas import MarketPageContent
from scripts.smoke_test_you_market import _load_settings, _parse_args, run


class FakeSmokeClient:
    def __init__(self) -> None:
        self.result = MarketSearchResult(
            title="AI Solutions Architect",
            url="https://example.com/jobs/architect",
            snippets=["Safe snippet"],
            source_domain="example.com",
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        del exc_type, exc_value, traceback

    async def search(self, request) -> list[MarketSearchResult]:  # type: ignore[no-untyped-def]
        assert request.query == '"AI Solutions Architect" jobs Toronto Canada'
        return [self.result]

    async def fetch_content(self, url: str) -> MarketPageContent:
        assert url == self.result.url
        return MarketPageContent(
            url=url,
            title=self.result.title,
            markdown="Bounded content",
        )


def test_env_file_argument_is_accepted() -> None:
    args = _parse_args(["--env-file", "local.env", "--fetch-first"])

    assert args.env_file == Path("local.env")
    assert args.fetch_first is True


def test_missing_env_file_fails_clearly(tmp_path: Path) -> None:
    missing = tmp_path / "missing.env"

    with pytest.raises(SystemExit, match="Environment file not found"):
        _load_settings(missing)


def test_missing_you_key_fails_before_client_creation() -> None:
    factory_called = False

    def client_factory(settings: Settings):
        nonlocal factory_called
        del settings
        factory_called = True
        return FakeSmokeClient()

    with pytest.raises(SystemExit, match="YDC_API_KEY is required"):
        asyncio.run(
            run(
                settings=Settings(ydc_api_key=None),
                fetch_first=False,
                client_factory=client_factory,
            )
        )

    assert factory_called is False


def test_output_contains_only_safe_metadata_and_never_secrets(capsys) -> None:
    secrets = (
        "private-you-secret",
        "private-nvidia-secret",
        "private-fireworks-secret",
    )
    settings = Settings(
        ydc_api_key=secrets[0],
        nvidia_api_key=secrets[1],
        fireworks_api_key=secrets[2],
    )

    asyncio.run(
        run(
            settings=settings,
            fetch_first=True,
            client_factory=lambda _: FakeSmokeClient(),
        )
    )
    output = capsys.readouterr().out

    assert "mcp_connection=connected" in output
    assert "allowed_tools=you-contents,you-search" in output
    assert "discovered_tools=you-contents,you-search" in output
    assert "search_result_count=1" in output
    assert "first_content_retrieval=succeeded" in output
    assert "example.com" in output
    for secret in secrets:
        assert secret not in output
