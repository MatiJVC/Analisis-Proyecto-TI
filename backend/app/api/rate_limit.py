import os
import time
import uuid
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status

from app.auth import KeycloakUser, get_current_user
from app.redis_client import redis_client

RATE_LIMIT = int(os.getenv("RATE_LIMIT", "100"))
WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

# Lua script kept for when Redis is available in the future.
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


# DDL for the PostgreSQL-based rate limit table.
# Created automatically at startup (see main.py lifespan).
RATE_LIMIT_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS api_rate_limit (
    user_sub     VARCHAR(255)             NOT NULL,
    window_start TIMESTAMP WITH TIME ZONE NOT NULL,
    req_count    INTEGER                  NOT NULL DEFAULT 0,
    PRIMARY KEY (user_sub, window_start)
);
CREATE INDEX IF NOT EXISTS idx_rl_window_start ON api_rate_limit (window_start);
"""


def _pg_rate_limit(user_sub: str, limit: int, window_seconds: int) -> bool:
    """Fixed-window counter using PostgreSQL UPSERT.

    Uses its own session so the commit is isolated from the request's transaction.
    Returns True if the request is allowed, False if the limit is exceeded.
    Fails open (returns True) on any database error to avoid blocking legitimate traffic.
    """
    from app.db.session import SessionLocal
    from sqlalchemy import text

    # Align to fixed windows of `window_seconds` size.
    now_ts = int(datetime.now(tz=timezone.utc).timestamp())
    bucket = now_ts - (now_ts % window_seconds)
    window_start = datetime.fromtimestamp(bucket, tz=timezone.utc)

    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                INSERT INTO api_rate_limit (user_sub, window_start, req_count)
                VALUES (:sub, :ws, 1)
                ON CONFLICT (user_sub, window_start) DO UPDATE
                    SET req_count = api_rate_limit.req_count + 1
                RETURNING req_count
            """),
            {"sub": user_sub, "ws": window_start},
        ).scalar()
        db.commit()
        return result <= limit
    except Exception:
        db.rollback()
        return True  # fail open — DB error should not block traffic
    finally:
        db.close()


def require_rate_limit(user: KeycloakUser = Depends(get_current_user)) -> None:
    """Sliding-window rate limit per authenticated user.

    Production path: Redis sorted-set + Lua script (atomic, shared across workers).
    Fallback (no Redis): PostgreSQL fixed-window UPSERT (shared across workers via DB).
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
        if not _pg_rate_limit(user.sub, RATE_LIMIT, WINDOW_SECONDS):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit excedido: máximo {RATE_LIMIT} requests por {WINDOW_SECONDS}s",
                headers={"Retry-After": str(WINDOW_SECONDS)},
            )
