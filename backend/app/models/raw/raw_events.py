import uuid
from sqlalchemy import Column, String, Boolean, Integer, Index, JSON
from sqlalchemy import DateTime as SADateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.db.base import Base


class RawEvent(Base):
    """Bronze layer — maps to fact_raw_events in the Data Warehouse."""

    __tablename__ = "fact_raw_events"

    # UUID PK — generated server-side, never from the client
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Audit timestamp (set by the ingestion backend, not derived from payload)
    ingested_at = Column(SADateTime(timezone=True), nullable=False, index=True)

    source     = Column(String(50),  nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    payload    = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict)

    # ETL orchestration — set to TRUE once event is promoted to Silver/Gold
    processed   = Column(Boolean, nullable=False, default=False)
    # Retry tracking — incremented on each failed ETL attempt; failed=True
    # permanently removes the event from the retry queue after MAX_ETL_RETRIES.
    retry_count = Column(Integer, nullable=False, default=0)
    failed      = Column(Boolean, nullable=False, default=False)


    __table_args__ = (
        # Composite used by Power BI views (source filter + time range)
        Index("idx_fre_source_ingested", "source", "ingested_at"),
        # idx_fre_pending is intentionally omitted here — it is a partial index
        # (WHERE processed = FALSE AND failed = FALSE) managed by ETL_RETRY_DDL
        # in api/routes/events.py, which runs at startup via CREATE INDEX IF NOT EXISTS.
        # Defining it here too would be misleading: SQLAlchemy's ORM dialect cannot
        # express the raw SQL WHERE clause reliably, and the DDL version takes precedence.
    )

    def __repr__(self) -> str:
        return (
            f"<RawEvent(event_id={self.event_id}, source={self.source}, "
            f"event_type={self.event_type}, processed={self.processed}, "
            f"retry_count={self.retry_count}, failed={self.failed})>"
        )
