"""Configuration-driven market provider construction."""

from ai_career_navigator.config import Settings
from ai_career_navigator.market.adzuna_client import AdzunaMarketSearchClient
from ai_career_navigator.market.errors import MarketConfigurationError
from ai_career_navigator.market.mcp.you_client import YouMcpMarketSearchClient


def build_primary_market_client(settings: Settings) -> AdzunaMarketSearchClient:
    if settings.market_primary_provider != "adzuna":
        raise MarketConfigurationError(
            f"Unsupported primary market provider: {settings.market_primary_provider}"
        )
    return AdzunaMarketSearchClient.from_settings(settings)


def build_enrichment_market_client(settings: Settings) -> YouMcpMarketSearchClient:
    if settings.market_enrichment_provider != "you":
        raise MarketConfigurationError(
            f"Unsupported enrichment market provider: {settings.market_enrichment_provider}"
        )
    return YouMcpMarketSearchClient.from_settings(settings)
