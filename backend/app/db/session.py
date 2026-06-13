import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import find_dotenv, load_dotenv

# Searches for .env.local then .env walking up from CWD; Docker injects env vars directly.
_env = find_dotenv(".env.local", usecwd=True) or find_dotenv(usecwd=True)
if _env:
    load_dotenv(_env)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        f"DATABASE_URL environment variable is not set. "
        f"Checked {_env or '.env.local / .env'} and environment variables."
    )


engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "False").lower() == "true",
    pool_pre_ping=True,
    pool_size=5,   # 4 workers × 10 (size + overflow) = 40 conexiones máx → bajo el límite default de PG (100)
    max_overflow=5,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Session:  # ty:ignore[invalid-return-type]
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()  # no-op después de commit; descarta cambios sin commit en caso de excepción
        db.close()
