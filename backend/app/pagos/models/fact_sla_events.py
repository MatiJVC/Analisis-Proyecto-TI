from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, CheckConstraint, Index

from app.db.base import Base


class FactSlaEvent(Base):
    __tablename__ = "fact_sla_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # timestamp_fin NULL significa que el evento sigue activo
    timestamp_inicio = Column(DateTime(timezone=True), nullable=False, index=True)
    timestamp_fin = Column(DateTime(timezone=True), nullable=True, index=True)
    tipo = Column(String(20), nullable=False)       # 'downtime' | 'degraded'
    duracion_segundos = Column(Integer, nullable=True)  # calculado al cerrar el evento
    descripcion = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("tipo IN ('downtime', 'degraded')", name="ck_sla_event_tipo"),
        Index("idx_sla_events_inicio_fin", "timestamp_inicio", "timestamp_fin"),
    )

    def __repr__(self) -> str:
        return (
            f"<FactSlaEvent(id={self.id}, tipo={self.tipo}, "
            f"inicio={self.timestamp_inicio}, fin={self.timestamp_fin})>"
        )
