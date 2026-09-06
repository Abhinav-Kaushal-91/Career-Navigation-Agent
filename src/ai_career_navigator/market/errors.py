"""Stable market-intelligence error categories."""


class MarketIntelligenceError(RuntimeError):
    """Base error exposed by the market integration boundary."""

    retryable = False


class MarketConfigurationError(MarketIntelligenceError):
    """Required market configuration is missing or invalid."""


class MarketAuthenticationError(MarketIntelligenceError):
    """The market provider rejected its credentials."""


class MarketTransportError(MarketIntelligenceError):
    """The market provider could not be reached."""

    retryable = True


class MarketTimeoutError(MarketTransportError):
    """A bounded market-provider operation timed out."""


class MarketRateLimitError(MarketTransportError):
    """The market provider asked the client to retry later."""


class MarketToolError(MarketIntelligenceError):
    """An approved MCP tool returned an error or malformed result."""

    retryable = True


class MarketContentError(MarketIntelligenceError):
    """A selected external page could not be retrieved or normalized."""

    retryable = True


class InsufficientMarketEvidenceError(MarketIntelligenceError):
    """No defensible market interpretation can be produced."""
