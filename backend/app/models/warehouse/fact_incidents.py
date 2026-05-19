from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String

from app.db.base import Base


class FactIncident(Base):
    __tablename__ = "fact_incidents"

    id = Column(Integer, primary_key=True, index=True)

    incident_id = Column(String(50), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False)
    severity = Column(String(20), nullable=False, index=True)
    status = Column(String(30), nullable=False, index=True)
    assignee = Column(String(100), nullable=True)

    opened_at = Column(DateTime, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    resolution_time_hours = Column(Float, nullable=True)
    sla_met = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_fact_incidents_status_severity", "status", "severity"),
        Index("idx_fact_incidents_opened_at", "opened_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<FactIncident(id={self.id}, incident_id={self.incident_id}, "
            f"status={self.status}, severity={self.severity})>"
        )
