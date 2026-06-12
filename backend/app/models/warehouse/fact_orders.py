from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Index

from app.db.base import Base


class FactOrder(Base):

    __tablename__ = "fact_orders"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Business Keys
    order_id = Column(String(100), nullable=False, unique=True, index=True)
    customer_id = Column(String(100), nullable=False, index=True)

    # Dimensions
    sales_channel = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)

    # Metrics
    total_amount = Column(Numeric(18, 2), nullable=False, default=0)
    total_items = Column(Integer, nullable=False, default=0)

    # Fulfillment Flags
    payment_success = Column(Boolean, default=False, index=True)
    stock_reserved = Column(Boolean, default=False)
    delivery_completed = Column(Boolean, default=False, index=True)

    # Processing Metrics
    processing_time_seconds = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Composite Indexes
    __table_args__ = (
        Index("idx_fact_orders_customer_status", "customer_id", "status"),
        Index("idx_fact_orders_channel_date", "sales_channel", "created_at"),
        Index("idx_fact_orders_payment_delivery", "payment_success", "delivery_completed"),
    )

    def __repr__(self):
        return (
            f"<FactOrder(id={self.id}, order_id={self.order_id}, "
            f"customer_id={self.customer_id}, status={self.status}, "
            f"total_amount={self.total_amount})>"
        )
