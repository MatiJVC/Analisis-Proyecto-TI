from datetime import datetime, date
from sqlalchemy import Column, String, DateTime, Date, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class FactAlertas(Base):
    __tablename__ = "fact_alertas"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign Keys to dimensions
    paciente_dim_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    visita_dim_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Business Keys (to trace back to source)
    alerta_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Alert Attributes
    tipo = Column(String(50), nullable=False, index=True)
    mensaje = Column(String(500), nullable=True)
    prioridad = Column(String(20), nullable=False, index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    estado = Column(String(20), nullable=False, index=True)     # OPEN, RESOLVED, ACKNOWLEDGED
    
    # Metrics
    dias_abierta = Column(String(50), nullable=True)
    
    # Timestamp for DWH tracking
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_fact_alertas_paciente_tipo", "paciente_dim_id", "tipo"),
        Index("idx_fact_alertas_prioridad_estado", "prioridad", "estado"),
        Index("idx_fact_alertas_creacion", "created_at"),
        Index("idx_fact_alertas_tipo_prioridad", "tipo", "prioridad"),
        Index("idx_fact_alertas_estado", "estado"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<FactAlertas(id={self.id}, alerta_id={self.alerta_id}, "
            f"tipo={self.tipo}, prioridad={self.prioridad}, estado={self.estado})>"
        )
