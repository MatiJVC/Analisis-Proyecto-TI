from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Index
from app.db.base import Base


class FactSubscription(Base):
    __tablename__ = "fact_subscriptions"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Business Keys
    contract_id = Column(String(50), nullable=False, index=True, unique=True)
    user_id = Column(Integer, nullable=False)
    plan_id = Column(Integer, nullable=False)
    
    # Dimension Attributes
    status = Column(String(20), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    
    # Subscription Metrics
    renewed = Column(Boolean, default=False)
    auto_service = Column(Boolean, default=False)
    
    # Billing Metrics
    billing_success = Column(Boolean, default=False)
    billing_attempts = Column(Integer, default=0)
    billing_date = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_fact_subscriptions_user_status", "user_id", "status"),
        Index("idx_fact_subscriptions_plan_date", "plan_id", "start_date"),
        Index("idx_fact_subscriptions_contract", "contract_id"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<FactSubscription(id={self.id}, contract_id={self.contract_id}, "
            f"user_id={self.user_id}, status={self.status})>"
        )
