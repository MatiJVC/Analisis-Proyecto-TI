from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class FactIncidente(Base):
    """
    Hechos: incidente (grano uno por incidente_id de negocio).
    FKs surrogate a sistemas y políticas SLA dimensionales.
    """

    __tablename__ = "fact_inc_incidentes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    sistema_dim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dim_inc_sistemas.id"),
        nullable=False,
        index=True,
    )
    politica_sla_dim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dim_inc_politicas_sla.id"),
        nullable=True,
        index=True,
    )

    incidente_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    titulo = Column(String(500), nullable=False)
    descripcion = Column(String(4000), nullable=True)
    estado = Column(String(80), nullable=False, index=True)
    creador_usuario_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    creado_en = Column(DateTime, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_fact_inc_inc_estado_creado", "estado", "creado_en"),
        Index("idx_fact_inc_inc_sistema_estado", "sistema_dim_id", "estado"),
    )

    def __repr__(self) -> str:
        return f"<FactIncidente(incidente_id={self.incidente_id}, estado={self.estado!r})>"

