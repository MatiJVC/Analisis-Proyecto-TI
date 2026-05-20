from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Index

from app.db.base import Base


class DimStatus(Base):
    __tablename__ = "dim_status"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_dim_status_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<DimStatus(id={self.id}, name={self.name})>"


DEFAULT_PAYMENT_STATUSES = [
    "aprobado",
    "esperando_revisión",
    "discrepancia_monto",
    "discrepancia_transacciones",
]
