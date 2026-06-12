import os
import time
import uuid
from collections import OrderedDict, deque
from threading import Lock

from fastapi import Depends, HTTPException, status

from app.auth import KeycloakUser, get_current_user
from app.redis_client import redis_client

RATE_LIMIT = int(os.getenv("RATE_LIMIT", "100"))
WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

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

_lua_sha: str | None = None
if redis_client is not None:
    _lua_sha = redis_client.script_load(_LUA_RATE_LIMIT)

# In-memory fallback — válido solo para desarrollo con un único worker.
# OrderedDict + cap evita que _per_user_locks y _windows crezcan sin límite.
_MAX_TRACKED_USERS = 5_000
_registry_lock = Lock()
_per_user_locks: OrderedDict[str, Lock] = OrderedDict()
_windows: OrderedDict[str, deque] = OrderedDict()


def _get_user_lock(user_sub: str) -> Lock:
    with _registry_lock:
        if user_sub in _per_user_locks:
            _per_user_locks.move_to_end(user_sub)
        else:
            if len(_per_user_locks) >= _MAX_TRACKED_USERS:
                _oldest = next(iter(_per_user_locks))
                del _per_user_locks[_oldest]
                _windows.pop(_oldest, None)
            _per_user_locks[user_sub] = Lock()
        return _per_user_locks[user_sub]


def require_rate_limit(user: KeycloakUser = Depends(get_current_user)) -> None:
    """Sliding-window rate limit: RATE_LIMIT requests per WINDOW_SECONDS per authenticated user.

    Production: Redis sorted-set + Lua script (atomic, shared across workers).
    Development fallback: in-memory deque (single-worker only).
    """
    if redis_client is not None:
        now = time.time()
        allowed = redis_client.evalsha(
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
            window = _windows.setdefault(user.sub, deque())
            while window and window[0] < cutoff:
                window.popleft()
            if len(window) >= RATE_LIMIT:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit excedido: máximo {RATE_LIMIT} requests por {WINDOW_SECONDS}s",
                    headers={"Retry-After": str(WINDOW_SECONDS)},
                )
            window.append(now)
