from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class FactIncEvidencia(Base):
    """Hechos: evidencias archivadas contra un incidente."""

    __tablename__ = "fact_inc_evidencias"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    incidente_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fact_inc_incidentes.incidente_id"),
        nullable=False,
        index=True,
    )

    evidencia_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    url_archivo = Column(String(2048), nullable=False)
    descripcion = Column(String(2000), nullable=True)
    subido_en = Column(DateTime, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (Index("idx_fact_inc_evi_inc_subido", "incidente_id", "subido_en"),)

    def __repr__(self) -> str:
        return f"<FactIncEvidencia(evidencia_id={self.evidencia_id})>"

