"""Host settings for extraction jobs."""

import logging
import os

logger = logging.getLogger(__name__)

MAX_CONCURRENT_ENV = "JARIT_MAX_CONCURRENT_EXTRACTIONS"
DEFAULT_MAX_CONCURRENT = 2


def max_concurrent_extractions() -> int:
    raw = os.getenv(MAX_CONCURRENT_ENV)
    if raw is None:
        return DEFAULT_MAX_CONCURRENT
    try:
        value = int(raw.strip())
    except ValueError:
        value = 0
    if value < 1:
        logger.warning(
            "%s=%r is not an integer >= 1; using %d",
            MAX_CONCURRENT_ENV,
            raw,
            DEFAULT_MAX_CONCURRENT,
        )
        return DEFAULT_MAX_CONCURRENT
    return value
