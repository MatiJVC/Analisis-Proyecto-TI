from datetime import datetime
from sqlalchemy import Column, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.db.base import Base


class FactIncEventoAlerta(Base):
    """Hechos: evento de alerta disparado (opcional vínculo a incidente abierto/creado)."""

    __tablename__ = "fact_inc_eventos_alerta"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    sistema_dim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dim_inc_sistemas.id"),
        nullable=False,
        index=True,
    )
    incidente_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fact_inc_incidentes.incidente_id"),
        nullable=True,
        index=True,
    )

    evento_alerta_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    payload = Column(JSONB, nullable=True)
    creado_en = Column(DateTime, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_fact_inc_ea_sistema_creado", "sistema_dim_id", "creado_en"),
        Index("idx_fact_inc_ea_incidente", "incidente_id"),
    )

    def __repr__(self) -> str:
        return f"<FactIncEventoAlerta(evento_alerta_id={self.evento_alerta_id})>"

