"""
Caché Redis para endpoints de KPIs.

Uso:
    from app.api.kpi_cache import get_kpi_cache, set_kpi_cache

    cached = get_kpi_cache(redis, "kpi:orders:30")
    if cached:
        return cached
    result = compute_kpis(...)
    set_kpi_cache(redis, "kpi:orders:30", result, ttl=60)
    return result

Si redis_client es None (entorno sin Redis), las funciones son no-ops y
el endpoint calcula siempre desde la base de datos.
"""
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_KPI_TTL_SECONDS = 60


def get_kpi_cache(redis_client, key: str) -> Optional[Any]:
    if redis_client is None:
        return None
    try:
        raw = redis_client.get(key)
        if raw:
            return json.loads(raw)
    except Exception:
        logger.warning("kpi_cache: fallo al leer clave %s", key, exc_info=True)
    return None


def set_kpi_cache(redis_client, key: str, value: Any, ttl: int = _KPI_TTL_SECONDS) -> None:
    if redis_client is None:
        return
    try:
        redis_client.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception:
        logger.warning("kpi_cache: fallo al escribir clave %s", key, exc_info=True)


def invalidate_kpi_cache(redis_client, prefix: str) -> None:
    """Elimina todas las claves de caché que empiecen con prefix (ej. 'kpi:orders:')."""
    if redis_client is None:
        return
    try:
        keys = redis_client.keys(f"{prefix}*")
        if keys:
            redis_client.delete(*keys)
    except Exception:
        logger.warning("kpi_cache: fallo al invalidar prefijo %s", prefix, exc_info=True)
