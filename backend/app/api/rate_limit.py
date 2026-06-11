from collections import defaultdict, deque
from datetime import datetime, timezone
from threading import Lock

from fastapi import Depends, HTTPException, status

from app.auth import KeycloakUser, get_current_user

# Protege _per_user_locks contra creación concurrente
_registry_lock = Lock()
_per_user_locks: dict[str, Lock] = {}
_windows: dict[str, deque] = defaultdict(deque)

RATE_LIMIT = 100
WINDOW_SECONDS = 60


def _get_user_lock(user_sub: str) -> Lock:
    """Devuelve el lock de sliding-window para un usuario, creándolo si no existe."""
    with _registry_lock:
        if user_sub not in _per_user_locks:
            _per_user_locks[user_sub] = Lock()
        return _per_user_locks[user_sub]


def require_rate_limit(user: KeycloakUser = Depends(get_current_user)) -> None:
    """Sliding-window rate limit: RATE_LIMIT requests per WINDOW_SECONDS per authenticated user.

    Nota: con múltiples workers (--workers N) cada proceso mantiene su propio estado.
    Para rate limiting compartido entre workers, migrar a Redis (fastapi-limiter).
    """
    now = datetime.now(tz=timezone.utc).timestamp()
    cutoff = now - WINDOW_SECONDS
    lock = _get_user_lock(user.sub)
    with lock:
        window = _windows[user.sub]
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= RATE_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit excedido: máximo {RATE_LIMIT} requests por {WINDOW_SECONDS}s",
                headers={"Retry-After": str(WINDOW_SECONDS)},
            )
        window.append(now)
