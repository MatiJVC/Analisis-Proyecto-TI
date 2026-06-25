from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, Numeric, String

from app.db.base import Base


class DimProduct(Base):
    """Catálogo de productos enriquecido desde eventos de inventario.

    Se popula vía upsert cuando los eventos de Inventario (Grupo 5) incluyen
    campos opcionales: product_name, category, unit, unit_price.
    """

    __tablename__ = "dim_products"

    sku_id = Column(String(100), primary_key=True)
    product_name = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)
    unit = Column(String(50), nullable=True)
    unit_price = Column(Numeric(14, 4), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_dim_products_category", "category"),
    )

    def __repr__(self) -> str:
        return (
            f"<DimProduct(sku_id={self.sku_id}, product_name={self.product_name}, "
            f"category={self.category}, unit_price={self.unit_price})>"
        )
