"""The CLI configures logging; library imports have no logging side effect."""

import logging

from axiomeval.config import LOG_LEVELS
from axiomeval.errors import ConfigurationError


def configure_logging(level: str = "INFO") -> None:
    """Configure AxiomEval application logging."""
    if not isinstance(level, str) or level not in LOG_LEVELS:
        raise ConfigurationError("Invalid logging level")
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
