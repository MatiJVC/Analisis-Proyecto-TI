from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class FactIncAccionPlaybook(Base):
    """Hechos: acciones de playbook ejecutadas sobre un incidente."""

    __tablename__ = "fact_inc_acciones_playbook"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    incidente_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fact_inc_incidentes.incidente_id"),
        nullable=False,
        index=True,
    )

    accion_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    tipo_accion = Column(String(120), nullable=False, index=True)
    ejecutado_por_usuario_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    ejecutado_en = Column(DateTime, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_fact_inc_play_inc_exec", "incidente_id", "ejecutado_en"),
        Index("idx_fact_inc_play_tipo", "tipo_accion"),
    )

    def __repr__(self) -> str:
        return f"<FactIncAccionPlaybook(accion_id={self.accion_id}, tipo_accion={self.tipo_accion!r})>"

