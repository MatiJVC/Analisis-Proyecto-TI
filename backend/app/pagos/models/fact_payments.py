import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class FactPayment(Base):
    __tablename__ = "fact_payments"

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    order_id = Column(Integer, ForeignKey("fact_orders.order_id"), nullable=True, index=True)
    subscription_id = Column(Integer, ForeignKey("fact_subscriptions.id"), nullable=True, index=True)
    amount = Column(Float, nullable=False, default=0.0)
    status_id = Column(Integer, ForeignKey("dim_status.id"), nullable=False, index=True)
    error_code = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("idx_fact_payments_order_timestamp", "order_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<FactPayment(transaction_id={self.transaction_id}, order_id={self.order_id}, "
            f"subscription_id={self.subscription_id}, amount={self.amount}, status_id={self.status_id})>"
        )
