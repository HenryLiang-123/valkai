import logging
import time

from django.db import OperationalError

logger = logging.getLogger(__name__)

_DB_MAX_RETRIES = 5
_DB_BASE_DELAY = 0.05  # 50ms


def db_retry(fn, *args, **kwargs):
    """Execute a DB operation with exponential backoff for SQLite lock errors."""
    for attempt in range(_DB_MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except OperationalError as e:
            if "locked" not in str(e) or attempt == _DB_MAX_RETRIES - 1:
                raise
            delay = _DB_BASE_DELAY * (2 ** attempt)
            logger.warning("DB locked, retrying in %.2fs (attempt %d/%d)", delay, attempt + 1, _DB_MAX_RETRIES)
            time.sleep(delay)
