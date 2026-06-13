"""
Caché de KPIs con dos backends:

  1. Redis (cuando está disponible) — caché compartida entre todos los workers.
  2. TTLCache en-proceso (fallback) — caché local por worker, TTL idéntico.
     Con 4 workers, cada uno cachea de forma independiente; a lo sumo se
     calculan 4 veces el mismo KPI por minuto, lo cual es aceptable para
     analytics que corren queries pesados sobre PostgreSQL.

Uso (sin cambios en el código cliente):
    cached = get_kpi_cache(redis_client, "kpi:orders:30")
    if cached:
        return cached
    result = compute_kpis(...)
    set_kpi_cache(redis_client, "kpi:orders:30", result)
    return result
"""
import json
import logging
import threading
from typing import Any, Optional

from cachetools import TTLCache

logger = logging.getLogger(__name__)

_KPI_TTL_SECONDS = 60

# In-process cache: up to 500 entries, each expires after 60 seconds.
_local_cache: TTLCache = TTLCache(maxsize=500, ttl=_KPI_TTL_SECONDS)
_cache_lock = threading.Lock()


def get_kpi_cache(redis_client, key: str) -> Optional[Any]:
    if redis_client is not None:
        try:
            raw = redis_client.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            logger.warning("kpi_cache: fallo al leer clave %s de Redis", key, exc_info=True)
        return None

    with _cache_lock:
        return _local_cache.get(key)


def set_kpi_cache(redis_client, key: str, value: Any, ttl: int = _KPI_TTL_SECONDS) -> None:
    if redis_client is not None:
        try:
            redis_client.set(key, json.dumps(value, default=str), ex=ttl)
        except Exception:
            logger.warning("kpi_cache: fallo al escribir clave %s en Redis", key, exc_info=True)
        return

    with _cache_lock:
        _local_cache[key] = value


def invalidate_kpi_cache(redis_client, prefix: str) -> None:
    """Elimina todas las claves que empiecen con prefix (ej. 'kpi:orders:')."""
    if redis_client is not None:
        try:
            keys = redis_client.keys(f"{prefix}*")
            if keys:
                redis_client.delete(*keys)
        except Exception:
            logger.warning("kpi_cache: fallo al invalidar prefijo %s en Redis", prefix, exc_info=True)
        return

    with _cache_lock:
        to_remove = [k for k in list(_local_cache.keys()) if k.startswith(prefix)]
        for k in to_remove:
            _local_cache.pop(k, None)
