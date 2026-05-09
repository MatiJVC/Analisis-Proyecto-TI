from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class DimIncReglaEscalamiento(Base):
    """Dimensión: reglas de escalamiento vinculadas a una política SLA."""

    __tablename__ = "dim_inc_reglas_escalamiento"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    regla_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    politica_sla_dim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dim_inc_politicas_sla.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tiempo_activacion_minutos = Column(Integer, nullable=False)
    notificar_a_usuario_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index("idx_dim_inc_regla_pol_tiempo", "politica_sla_dim_id", "tiempo_activacion_minutos"),)

    def __repr__(self) -> str:
        return (
            f"<DimIncReglaEscalamiento(id={self.id}, regla_id={self.regla_id}, "
            f"politica_sla_dim_id={self.politica_sla_dim_id})>"
        )

