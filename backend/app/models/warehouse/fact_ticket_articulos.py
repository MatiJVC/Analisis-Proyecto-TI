from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String

from app.db.base import Base


class FactTicketArticulo(Base):
    """Mapea la entidad Ticket_articulo del MER — uso de KB por ticket."""

    __tablename__ = "fact_ticket_articulos"

    id = Column(Integer, primary_key=True, index=True)

    ticket_id = Column(String(50), nullable=False, index=True)
    articulo_id = Column(String(100), nullable=False, index=True)
    articulo_titulo = Column(String(500), nullable=True)
    articulo_categoria = Column(String(100), nullable=True)
    fue_enviado_al_cliente = Column(Boolean, nullable=False, default=False)
    agente_id = Column(String(100), nullable=True)

    vinculado_en = Column(DateTime, nullable=True, index=True)
    ingested_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_fact_ticket_articulos_ticket", "ticket_id"),
        Index("idx_fact_ticket_articulos_articulo", "articulo_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<FactTicketArticulo(ticket_id={self.ticket_id}, "
            f"articulo_id={self.articulo_id})>"
        )
