from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class FactIncAuditoria(Base):
    """Hechos: entradas de auditoría ligadas al incidente."""

    __tablename__ = "fact_inc_auditoria"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    incidente_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fact_inc_incidentes.incidente_id"),
        nullable=False,
        index=True,
    )

    auditoria_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    accion_por_usuario_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    descripcion_accion = Column(String(2000), nullable=False)
    creado_en = Column(DateTime, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (Index("idx_fact_inc_aud_inc_creado", "incidente_id", "creado_en"),)

    def __repr__(self) -> str:
        return f"<FactIncAuditoria(auditoria_id={self.auditoria_id})>"

