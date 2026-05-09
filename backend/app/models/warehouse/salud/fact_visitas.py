from datetime import datetime, date, time
from sqlalchemy import Column, Integer, String, DateTime, Date, Time, Index, ForeignKey, Interval
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class FactVisitas(Base):
    __tablename__ = "fact_visitas"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign Keys to dimensions
    paciente_dim_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    profesional_dim_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    zona_dim_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    usuario_creador_dim_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Business Keys (to trace back to source)
    visita_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Date Dimensions
    fecha_programada = Column(Date, nullable=False, index=True)
    hora_programada = Column(Time, nullable=True)
    fecha_inicio_real = Column(DateTime, nullable=True, index=True)
    fecha_fin_real = Column(DateTime, nullable=True)
    
    # Calculated Metrics
    duracion_minutos = Column(Integer, nullable=True)
    retraso_minutos = Column(Integer, nullable=True)
    
    # Status and Attributes
    estado = Column(String(30), nullable=False, index=True)
    completada = Column(Integer, default=0)  # 1 = completed, 0 = incomplete
    puntual = Column(Integer, default=0)      # 1 = on time, 0 = late
    
    # Timestamp for DWH tracking
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_fact_visitas_paciente_fecha", "paciente_dim_id", "fecha_programada"),
        Index("idx_fact_visitas_profesional_fecha", "profesional_dim_id", "fecha_programada"),
        Index("idx_fact_visitas_zona_estado", "zona_dim_id", "estado"),
        Index("idx_fact_visitas_estado_fecha", "estado", "fecha_programada"),
        Index("idx_fact_visitas_completada", "completada"),
        Index("idx_fact_visitas_puntual", "puntual"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<FactVisitas(id={self.id}, visita_id={self.visita_id}, "
            f"estado={self.estado}, fecha_programada={self.fecha_programada})>"
        )
