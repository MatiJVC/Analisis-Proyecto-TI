from datetime import datetime, date
from sqlalchemy import Column, String, DateTime, Date, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class AggAlertas(Base):
    __tablename__ = "agg_alertas"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Time Dimension
    fecha = Column(Date, nullable=False, index=True)
    
    # Alert Type Breakdown
    tipo_alerta = Column(String(50), nullable=True, index=True)
    
    # Priority Breakdown
    prioridad = Column(String(20), nullable=True, index=True)
    
    # Metrics
    total_alertas = Column(Integer, default=0)
    alertas_abiertas = Column(Integer, default=0)
    alertas_resueltas = Column(Integer, default=0)
    alertas_reconocidas = Column(Integer, default=0)
    
    # Status
    tiempo_promedio_resolucion_horas = Column(String(10), nullable=True)
    
    # Timestamp for DWH tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_agg_alertas_fecha", "fecha"),
        Index("idx_agg_alertas_tipo_fecha", "tipo_alerta", "fecha"),
        Index("idx_agg_alertas_prioridad_fecha", "prioridad", "fecha"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<AggAlertas(id={self.id}, fecha={self.fecha}, "
            f"tipo_alerta={self.tipo_alerta}, total_alertas={self.total_alertas})>"
        )
