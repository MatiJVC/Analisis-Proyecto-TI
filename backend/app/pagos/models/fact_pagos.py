import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Numeric, DateTime, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class FactPagos(Base):
    __tablename__ = "fact_pagos"

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    order_id = Column(String(255), nullable=True, index=True)
    subscription_id = Column(String(255), nullable=True, index=True)
    monto = Column(Numeric(18, 2), nullable=False)
    token_transaccion = Column(String(255), nullable=False, index=True)
    error_code_id = Column(Integer, ForeignKey("dim_error_codes.id"), nullable=True, index=True)
    timestamp_evento = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    estado_conciliacion_id = Column(Integer, ForeignKey("dim_estados_conciliacion.id"), nullable=False, index=True)

    __table_args__ = (
        Index("idx_fact_pagos_tx_order_ts", "transaction_id", "order_id", "timestamp_evento"),
    )

    def __repr__(self) -> str:
        return (
            f"<FactPagos(transaction_id={self.transaction_id}, order_id={self.order_id}, "
            f"monto={self.monto})>"
        )
