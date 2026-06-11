import os
import sys
import time
import uuid
from collections import defaultdict, deque
from threading import Lock

import redis as redis_lib
from fastapi import Depends, HTTPException, status

from app.auth import KeycloakUser, get_current_user

RATE_LIMIT = int(os.getenv("RATE_LIMIT", "100"))
WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
_ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Atomic sliding-window check-and-add via Lua script.
# Returns 1 if the request is allowed, 0 if the limit is exceeded.
_LUA_RATE_LIMIT = """
local key    = KEYS[1]
local now    = tonumber(ARGV[1])
local cutoff = tonumber(ARGV[2])
local limit  = tonumber(ARGV[3])
local member = ARGV[4]
local ttl    = tonumber(ARGV[5])
redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
local count = tonumber(redis.call('ZCARD', key))
if count >= limit then
    return 0
end
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, ttl)
return 1
"""

_redis: redis_lib.Redis | None = None
_lua_sha: str | None = None

try:
    _r = redis_lib.Redis.from_url(_REDIS_URL, decode_responses=True, socket_connect_timeout=2)
    _r.ping()
    _redis = _r
    _lua_sha = _r.script_load(_LUA_RATE_LIMIT)
except Exception:
    if _ENVIRONMENT != "development":
        print(
            f"FATAL: Redis no disponible en {_REDIS_URL}. "
            "El rate limiting multi-worker requiere Redis en producción.",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)

# In-memory fallback — válido solo para desarrollo con un único worker.
_registry_lock = Lock()
_per_user_locks: dict[str, Lock] = {}
_windows: dict[str, deque] = defaultdict(deque)


def _get_user_lock(user_sub: str) -> Lock:
    with _registry_lock:
        if user_sub not in _per_user_locks:
            _per_user_locks[user_sub] = Lock()
        return _per_user_locks[user_sub]


def require_rate_limit(user: KeycloakUser = Depends(get_current_user)) -> None:
    """Sliding-window rate limit: RATE_LIMIT requests per WINDOW_SECONDS per authenticated user.

    Production: Redis sorted-set + Lua script (atomic, shared across workers).
    Development fallback: in-memory deque (single-worker only).
    """
    if _redis is not None:
        now = time.time()
        allowed = _redis.evalsha(
            _lua_sha,
            1,
            f"rl:{user.sub}",
            str(now),
            str(now - WINDOW_SECONDS),
            str(RATE_LIMIT),
            str(uuid.uuid4()),
            str(WINDOW_SECONDS * 2),
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit excedido: máximo {RATE_LIMIT} requests por {WINDOW_SECONDS}s",
                headers={"Retry-After": str(WINDOW_SECONDS)},
            )
    else:
        now = time.time()
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
