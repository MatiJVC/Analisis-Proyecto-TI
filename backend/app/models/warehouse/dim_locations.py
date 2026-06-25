from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, String

from app.db.base import Base


class DimLocation(Base):
    """Catálogo de ubicaciones físicas enriquecido desde eventos de inventario.

    Se popula vía upsert cuando los eventos critical_threshold_reached de
    Inventario (Grupo 5) incluyen campos opcionales: location_name,
    location_type, city, address.
    """

    __tablename__ = "dim_locations"

    location_id = Column(String(100), primary_key=True)
    location_name = Column(String(255), nullable=True)
    location_type = Column(String(50), nullable=True)
    city = Column(String(100), nullable=True)
    address = Column(String(255), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_dim_locations_city", "city"),
        Index("idx_dim_locations_type", "location_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<DimLocation(location_id={self.location_id}, "
            f"location_name={self.location_name}, city={self.city})>"
        )
