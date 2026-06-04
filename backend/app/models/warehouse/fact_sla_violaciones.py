from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String

from app.db.base import Base


class FactSlaViolacion(Base):
    __tablename__ = "fact_sla_violaciones"

    id = Column(Integer, primary_key=True, index=True)

    ticket_id = Column(String(50), nullable=False, index=True)
    cliente_identidad_id = Column(String(100), nullable=True)
    prioridad = Column(String(20), nullable=False, index=True)
    canal = Column(String(20), nullable=True)
    source_project = Column(String(50), nullable=True, index=True)

    sla_threshold_hours = Column(Float, nullable=False)
    elapsed_hours = Column(Float, nullable=False)
    breach_percentage = Column(Float, nullable=False)
    threshold_crossed = Column(Integer, nullable=False, index=True)  # 75|100|150

    escalation_required = Column(Boolean, nullable=False, default=False)
    escalado_hacia = Column(String(50), nullable=True)

    fecha_vencimiento_sla = Column(DateTime, nullable=True)
    violation_detected_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_fact_sla_violaciones_ticket_ts", "ticket_id", "violation_detected_at"),
        Index("idx_fact_sla_violaciones_threshold", "threshold_crossed", "prioridad"),
    )

    def __repr__(self) -> str:
        return (
            f"<FactSlaViolacion(ticket_id={self.ticket_id}, "
            f"breach_percentage={self.breach_percentage})>"
        )
