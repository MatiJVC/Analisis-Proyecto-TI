from sqlalchemy import Column, Integer, String

from app.db.base import Base


class DimEstadosConciliacion(Base):
    __tablename__ = "dim_estados_conciliacion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False, unique=True)

    def __repr__(self) -> str:
        return f"<DimEstadosConciliacion(id={self.id}, nombre={self.nombre})>"
