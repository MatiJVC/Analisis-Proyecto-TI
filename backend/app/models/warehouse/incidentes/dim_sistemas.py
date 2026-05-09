from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class DimIncSistema(Base):
    """Dimensión: sistemas de origen de incidentes."""

    __tablename__ = "dim_inc_sistemas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    sistema_id = Column(String(100), nullable=False, unique=True, index=True)

    nombre = Column(String(255), nullable=False, index=True)
    descripcion = Column(String(2000), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index("idx_dim_inc_sistemas_nombre", "nombre"),)

    def __repr__(self) -> str:
        return f"<DimIncSistema(id={self.id}, sistema_id={self.sistema_id!r}, nombre={self.nombre!r})>"

