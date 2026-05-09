from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class DimZonas(Base):
    __tablename__ = "dim_zonas"
    
    # Primary Key (Surrogate)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Business Keys
    zona_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Attributes
    nombre = Column(String(100), nullable=False, index=True)
    descripcion = Column(String(500), nullable=True)
    comuna = Column(String(100), nullable=True, index=True)
    region = Column(String(100), nullable=True, index=True)
    
    # Status
    activa = Column(Boolean, default=True, index=True)
    
    # SCD Type 2 tracking
    fecha_inicio = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_fin = Column(DateTime, nullable=True)
    es_actual = Column(Boolean, default=True, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_dim_zonas_activa", "activa"),
        Index("idx_dim_zonas_region_comuna", "region", "comuna"),
        Index("idx_dim_zonas_nombre", "nombre"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<DimZonas(id={self.id}, zona_id={self.zona_id}, "
            f"nombre={self.nombre}, region={self.region})>"
        )
