from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, CheckConstraint, DateTime, Float, Index, Integer, String, Text

from app.db.base import Base


class FactTicket(Base):
    __tablename__ = "fact_tickets"

    id = Column(Integer, primary_key=True, index=True)

    ticket_id = Column(String(50), nullable=False, unique=True, index=True)
    asunto = Column(String(500), nullable=True)
    estado = Column(String(30), nullable=False, index=True)           # Abierto|Progreso|Resuelto|Cerrado
    prioridad = Column(String(20), nullable=False, index=True)        # Baja|Media|Alta|Crítica
    canal = Column(String(20), nullable=True, index=True)             # Chat|Email|Teléfono|App
    source_project = Column(String(50), nullable=True, index=True)    # orders|salud|subscriptions|...

    cliente_identidad_id = Column(String(100), nullable=True, index=True)
    agente_id = Column(String(100), nullable=True, index=True)

    pedido_id_ref = Column(String(100), nullable=True)
    suscripcion_id_red = Column(String(100), nullable=True)

    # Campos del TicketDto real del CRM externo sin equivalente previo.
    # Agregados vía backend/migrations/005_crm_ticket_new_fields.sql (no Alembic).
    cliente_id = Column(Integer, nullable=True)
    cliente_nombre = Column(String(255), nullable=True)
    pago_id_ref = Column(String(100), nullable=True)
    salud_ref = Column(String(100), nullable=True)
    resolucion = Column(Text, nullable=True)

    fecha_vencimiento_sla = Column(DateTime(timezone=True), nullable=True)
    resolution_time_hours = Column(Float, nullable=True)
    within_sla = Column(Boolean, nullable=True)
    csat_score = Column(Integer, nullable=True)                       # 1–5

    opened_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("estado IN ('Abierto', 'Progreso', 'Resuelto', 'Cerrado')", name="ck_fact_tickets_estado"),
        CheckConstraint("prioridad IN ('Baja', 'Media', 'Alta', 'Crítica')", name="ck_fact_tickets_prioridad"),
        CheckConstraint("canal IN ('Chat', 'Email', 'Teléfono', 'App') OR canal IS NULL", name="ck_fact_tickets_canal"),
        Index("idx_fact_tickets_estado_prioridad", "estado", "prioridad"),
        Index("idx_fact_tickets_source_opened", "source_project", "opened_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<FactTicket(ticket_id={self.ticket_id}, estado={self.estado}, "
            f"prioridad={self.prioridad})>"
        )
