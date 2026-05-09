from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class AuditPipeline(Base):
    __tablename__ = "audit_pipeline"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Pipeline Execution Information
    pipeline_name = Column(String(100), nullable=False, index=True)
    execution_id = Column(String(150), nullable=False, unique=True, index=True)
    
    # Source and Target Information
    source_system = Column(String(100), nullable=False, index=True)
    target_table = Column(String(100), nullable=False, index=True)
    
    # Execution Metrics
    estado = Column(String(20), nullable=False, index=True)  # SUCCESS, FAILED, PARTIAL
    registros_leidos = Column(String(20), default='0')
    registros_insertados = Column(String(20), default='0')
    registros_actualizados = Column(String(20), default='0')
    registros_rechazados = Column(String(20), default='0')
    
    # Errors and Warnings
    errores = Column(Text, nullable=True)
    advertencias = Column(Text, nullable=True)
    
    # Timestamp Information
    fecha_inicio = Column(DateTime, nullable=False)
    fecha_fin = Column(DateTime, nullable=True)
    duracion_segundos = Column(String(20), nullable=True)
    
    # Data Quality Information
    calidad_datos = Column(String(5), nullable=True)  # percentage
    trazabilidad_id = Column(String(100), nullable=True)
    
    # Timestamp for DWH tracking
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_audit_pipeline_executions", "execution_id"),
        Index("idx_audit_pipeline_source_target", "source_system", "target_table"),
        Index("idx_audit_pipeline_estado", "estado"),
        Index("idx_audit_pipeline_fecha", "fecha_inicio"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<AuditPipeline(id={self.id}, pipeline_name={self.pipeline_name}, "
            f"execution_id={self.execution_id}, estado={self.estado})>"
        )
