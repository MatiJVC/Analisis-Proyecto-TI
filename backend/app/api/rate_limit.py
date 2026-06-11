import threading
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status

from app.auth import KeycloakUser, get_current_user

_lock = threading.Lock()
_windows: dict[str, deque] = defaultdict(deque)

RATE_LIMIT = 100
WINDOW_SECONDS = 60


def require_rate_limit(user: KeycloakUser = Depends(get_current_user)) -> None:
    """Sliding-window rate limit: RATE_LIMIT requests per WINDOW_SECONDS per authenticated user."""
    now = datetime.now(tz=timezone.utc).timestamp()
    cutoff = now - WINDOW_SECONDS
    with _lock:
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
