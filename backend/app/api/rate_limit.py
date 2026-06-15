import os
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status

from app.auth import KeycloakUser, get_current_user

RATE_LIMIT = int(os.getenv("RATE_LIMIT", "100"))
WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

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


# Single-Backend PostgreSQL rate limiting via fixed-window UPSERT.
# Shared across all workers through the database; no in-memory state.
def require_rate_limit(user: KeycloakUser = Depends(get_current_user)) -> None:
    if not _pg_rate_limit(user.sub, RATE_LIMIT, WINDOW_SECONDS):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit excedido: máximo {RATE_LIMIT} requests por {WINDOW_SECONDS}s",
            headers={"Retry-After": str(WINDOW_SECONDS)},
        )