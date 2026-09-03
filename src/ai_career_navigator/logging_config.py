"""Standard-library logging configuration for the application."""

import logging
from typing import Final

from ai_career_navigator.config import Settings

LOG_FORMAT: Final = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(settings: Settings) -> None:
    """Configure process logging without emitting configuration or user data.

    Callers must log identifiers and safe metadata, never credentials, full resume
    content, or other sensitive payloads. A future observability adapter can replace
    handlers without changing application configuration access.
    """

    logging.basicConfig(
        level=settings.log_level,
        format=LOG_FORMAT,
        force=True,
    )
