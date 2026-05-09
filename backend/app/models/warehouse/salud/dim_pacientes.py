from datetime import datetime, date
from sqlalchemy import Column, String, Boolean, DateTime, Date, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class DimPacientes(Base):
    __tablename__ = "dim_pacientes"
    
    # Primary Key (Surrogate)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Business Keys
    paciente_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Attributes
    rut = Column(String(20), nullable=True, index=True)
    nombres = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    fecha_nacimiento = Column(Date, nullable=True)
    sexo = Column(String(20), nullable=True)
    telefono = Column(String(30), nullable=True)
    email = Column(String(150), nullable=True)
    direccion = Column(String(500), nullable=True)
    
    # SCD Type 2 tracking
    fecha_inicio = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_fin = Column(DateTime, nullable=True)
    es_actual = Column(Boolean, default=True, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_dim_pacientes_rut", "rut"),
        Index("idx_dim_pacientes_email", "email"),
        Index("idx_dim_pacientes_telefono", "telefono"),
        Index("idx_dim_pacientes_actual", "es_actual"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<DimPacientes(id={self.id}, paciente_id={self.paciente_id}, "
            f"nombres={self.nombres} {self.apellidos})>"
        )
