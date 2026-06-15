"""
KPI cache — Single-Backend PostgreSQL architecture.

TTLCache (in-process) is the canonical caching mechanism.
With multiple workers each process caches independently; at most N workers
recompute the same KPI per TTL window, which is acceptable for analytics
queries against PostgreSQL.
"""
import logging
import threading
from typing import Any, Optional

from cachetools import TTLCache

logger = logging.getLogger(__name__)

_KPI_TTL_SECONDS = 60

# In-process cache: up to 500 entries, each expires after 60 seconds.
_local_cache: TTLCache = TTLCache(maxsize=500, ttl=_KPI_TTL_SECONDS)
_cache_lock = threading.Lock()


def get_kpi_cache(key: str) -> Optional[Any]:
    with _cache_lock:
        return _local_cache.get(key)


def set_kpi_cache(key: str, value: Any) -> None:
    with _cache_lock:
        _local_cache[key] = value


def invalidate_kpi_cache(prefix: str) -> None:
    """Remove all keys that start with prefix (e.g. 'kpi:orders:')."""
    with _cache_lock:
        to_remove = [k for k in list(_local_cache.keys()) if k.startswith(prefix)]
        for k in to_remove:
            _local_cache.pop(k, None)