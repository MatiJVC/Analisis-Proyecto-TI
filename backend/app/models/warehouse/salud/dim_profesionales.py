from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class DimProfesionales(Base):
    __tablename__ = "dim_profesionales"
    
    # Primary Key (Surrogate)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Business Keys
    profesional_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    usuario_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Attributes
    nombres = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    profesion = Column(String(50), nullable=True)
    numero_registro = Column(String(50), nullable=True, index=True)
    
    # Status
    activo = Column(Boolean, default=True, index=True)
    
    # SCD Type 2 tracking
    fecha_inicio = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_fin = Column(DateTime, nullable=True)
    es_actual = Column(Boolean, default=True, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_dim_profesionales_activo", "activo"),
        Index("idx_dim_profesionales_profesion", "profesion"),
        Index("idx_dim_profesionales_usuario", "usuario_id"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<DimProfesionales(id={self.id}, profesional_id={self.profesional_id}, "
            f"profesion={self.profesion})>"
        )
