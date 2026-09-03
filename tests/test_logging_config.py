import logging

from ai_career_navigator.config import Settings
from ai_career_navigator.logging_config import configure_logging


def test_configure_logging_respects_log_level() -> None:
    configure_logging(Settings(log_level="warning"))

    assert logging.getLogger().level == logging.WARNING
