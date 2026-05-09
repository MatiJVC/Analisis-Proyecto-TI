from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.db.base import Base


class FactFichasClinicas(Base):
    __tablename__ = "fact_fichas_clinicas"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign Keys to dimensions
    visita_dim_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    usuario_creador_dim_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    usuario_actualizador_dim_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Business Keys (to trace back to source)
    ficha_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Ficha Attributes
    estado = Column(String(30), nullable=False, index=True)  # DRAFT, COMPLETED, ARCHIVED
    contenido = Column(JSONB, nullable=True)
    
    # Content Metadata
    tiene_adjuntos = Column(String(1), default='0')  # 1 = yes, 0 = no
    cantidad_adjuntos = Column(String(10), default='0')
    
    # Timestamp for DWH tracking
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_fact_fichas_visita_estado", "visita_dim_id", "estado"),
        Index("idx_fact_fichas_creador", "usuario_creador_dim_id"),
        Index("idx_fact_fichas_estado", "estado"),
        Index("idx_fact_fichas_creacion", "created_at"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<FactFichasClinicas(id={self.id}, ficha_id={self.ficha_id}, "
            f"estado={self.estado})>"
        )
