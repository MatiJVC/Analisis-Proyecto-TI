from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text

from app.db.base import Base


class FactInteraccion(Base):
    __tablename__ = "fact_interacciones"

    id = Column(Integer, primary_key=True, index=True)

    interaccion_id = Column(String(100), nullable=False, unique=True, index=True)
    ticket_id = Column(String(50), nullable=False, index=True)
    autor_tipo = Column(String(20), nullable=False, index=True)    # Cliente|Agente|Sistema
    autor_id = Column(String(100), nullable=True)
    contenido = Column(Text, nullable=True)
    es_nota_interna = Column(Boolean, nullable=False, default=False)

    creado_en = Column(DateTime, nullable=True, index=True)
    ingested_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_fact_interacciones_ticket_creado", "ticket_id", "creado_en"),
    )

    def __repr__(self) -> str:
        return (
            f"<FactInteraccion(interaccion_id={self.interaccion_id}, "
            f"ticket_id={self.ticket_id}, autor_tipo={self.autor_tipo})>"
        )
