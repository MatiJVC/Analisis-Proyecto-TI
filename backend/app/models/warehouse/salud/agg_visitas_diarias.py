from datetime import datetime, date
from sqlalchemy import Column, String, DateTime, Date, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class AggVisitasDiarias(Base):
    __tablename__ = "agg_visitas_diarias"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Dimension Keys
    zona_dim_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    profesional_dim_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Time Dimension
    fecha = Column(Date, nullable=False, index=True)
    
    # Metrics
    total_visitas = Column(Integer, default=0)
    visitas_completadas = Column(Integer, default=0)
    visitas_incompletas = Column(Integer, default=0)
    visitas_puntales = Column(Integer, default=0)
    visitas_atrasadas = Column(Integer, default=0)
    
    # Rate Calculations
    tasa_completacion = Column(String(10), nullable=True)  # percentage as string
    tasa_puntualidad = Column(String(10), nullable=True)
    duracion_promedio_minutos = Column(String(10), nullable=True)
    
    # Timestamp for DWH tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_agg_visitas_diarias_fecha", "fecha"),
        Index("idx_agg_visitas_diarias_zona_fecha", "zona_dim_id", "fecha"),
        Index("idx_agg_visitas_diarias_profesional_fecha", "profesional_dim_id", "fecha"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<AggVisitasDiarias(id={self.id}, fecha={self.fecha}, "
            f"total_visitas={self.total_visitas})>"
        )
