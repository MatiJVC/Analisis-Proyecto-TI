from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, Integer, Date, Numeric, DateTime, String, ForeignKey

from app.db.base import Base


class CierreDiario(Base):
    __tablename__ = "cierre_diario"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(Date, nullable=False, index=True)
    reported_total = Column(Numeric(18, 2), nullable=False)
    reported_count = Column(Integer, nullable=False)
    internal_total = Column(Numeric(18, 2), nullable=True)
    internal_count = Column(Integer, nullable=True)
    estado_id = Column(Integer, ForeignKey("dim_estados_conciliacion.id"), nullable=False)
    processed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    note = Column(String(1024), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<CierreDiario(fecha={self.fecha}, reported_total={self.reported_total}, "
            f"reported_count={self.reported_count}, estado_id={self.estado_id})>"
        )
