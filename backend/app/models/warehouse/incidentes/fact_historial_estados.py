from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class FactIncHistorialEstado(Base):
    """Hechos: cada transición de estado de un incidente (timeline para SLA y MTTR)."""

    __tablename__ = "fact_inc_historial_estados"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    incidente_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fact_inc_incidentes.incidente_id"),
        nullable=False,
        index=True,
    )

    historial_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    estado_anterior = Column(String(120), nullable=True)
    estado_nuevo = Column(String(120), nullable=False, index=True)
    cambiado_por_usuario_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    cambiado_en = Column(DateTime, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (Index("idx_fact_inc_hist_inc_cambiado", "incidente_id", "cambiado_en"),)

    def __repr__(self) -> str:
        return (
            f"<FactIncHistorialEstado(historial_id={self.historial_id}, "
            f"{self.estado_anterior!r} -> {self.estado_nuevo!r})>"
        )

