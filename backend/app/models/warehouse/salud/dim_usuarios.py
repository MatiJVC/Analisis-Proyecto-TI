from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class DimUsuarios(Base):
    __tablename__ = "dim_usuarios"
    
    # Primary Key (Surrogate)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Business Keys
    usuario_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Attributes
    rut = Column(String(20), nullable=True, index=True)
    nombres = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    email = Column(String(150), nullable=True)
    telefono = Column(String(30), nullable=True)
    
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
        Index("idx_dim_usuarios_activo", "activo"),
        Index("idx_dim_usuarios_actual", "es_actual"),
        Index("idx_dim_usuarios_email", "email"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<DimUsuarios(id={self.id}, usuario_id={self.usuario_id}, "
            f"nombres={self.nombres} {self.apellidos})>"
        )
