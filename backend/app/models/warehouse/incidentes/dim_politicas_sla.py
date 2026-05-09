from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class DimIncPoliticaSla(Base):
    """Dimensión: políticas de SLA aplicables a incidentes."""

    __tablename__ = "dim_inc_politicas_sla"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    politica_sla_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    nombre = Column(String(255), nullable=False, index=True)
    tiempo_maximo_resolucion_minutos = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index("idx_dim_inc_pol_sla_nombre", "nombre"),)

    def __repr__(self) -> str:
        return f"<DimIncPoliticaSla(id={self.id}, politica_sla_id={self.politica_sla_id}, nombre={self.nombre!r})>"

