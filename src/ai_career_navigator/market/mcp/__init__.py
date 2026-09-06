"""Market MCP adapter exports."""

from ai_career_navigator.market.mcp.fake_client import FakeMarketSearchClient
from ai_career_navigator.market.mcp.protocol import MarketSearchClient, StructuredJobSearchClient
from ai_career_navigator.market.mcp.you_client import YouMcpMarketSearchClient

__all__ = [
    "FakeMarketSearchClient",
    "MarketSearchClient",
    "StructuredJobSearchClient",
    "YouMcpMarketSearchClient",
]
