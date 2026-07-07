import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Numeric, DateTime, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class FactPaymentsEvent(Base):
    __tablename__ = "fact_payments_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    order_id = Column(String(255), nullable=True, index=True)
    subscription_id = Column(String(255), nullable=True, index=True)
    amount = Column(Numeric(18, 2), nullable=False)
    token_transaccion = Column(String(255), nullable=False, index=True)
    codigo_error = Column(String(100), nullable=True)
    status = Column(String(100), nullable=False, index=True)
    timestamp_evento = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index("idx_fact_payments_events_tx_token_ts", "transaction_id", "token_transaccion", "timestamp_evento"),
        CheckConstraint(
            "status IN ('esperando_revisión', 'Aprobado', 'discrepancia_de_monto', 'discrepancia_de_transacciones', 'Rechazado')",
            name="ck_fact_payments_events_status",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            f"<FactPaymentsEvent(id={self.id}, transaction_id={self.transaction_id}, "
            f"status={self.status}, amount={self.amount})>"
        )
