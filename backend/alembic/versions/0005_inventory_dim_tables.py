"""inventory dim tables: dim_products, dim_locations

Crea las tablas de dimensión para el módulo de Inventario:
  - dim_products  — catálogo de SKUs con nombre, categoría, unidad y precio unitario
  - dim_locations — catálogo de ubicaciones físicas con nombre, tipo, ciudad y dirección

Estas tablas se populan vía upsert desde el inventory_processor cuando los
eventos de Inventario (Grupo 5) incluyen campos de metadata opcionales.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # ── dim_products ──────────────────────────────────────────────────────────
    if "dim_products" not in existing_tables:
        op.create_table(
            "dim_products",
            sa.Column("sku_id",       sa.String(100),       primary_key=True),
            sa.Column("product_name", sa.String(255),       nullable=True),
            sa.Column("category",     sa.String(100),       nullable=True),
            sa.Column("unit",         sa.String(50),        nullable=True),
            sa.Column("unit_price",   sa.Numeric(14, 4),    nullable=True),
            sa.Column("updated_at",   sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("NOW()")),
        )

    existing_indexes = (
        [idx["name"] for idx in inspector.get_indexes("dim_products")]
        if "dim_products" in existing_tables
        else []
    )
    if "idx_dim_products_category" not in existing_indexes:
        op.create_index("idx_dim_products_category", "dim_products", ["category"])

    # ── dim_locations ─────────────────────────────────────────────────────────
    if "dim_locations" not in existing_tables:
        op.create_table(
            "dim_locations",
            sa.Column("location_id",   sa.String(100),       primary_key=True),
            sa.Column("location_name", sa.String(255),       nullable=True),
            sa.Column("location_type", sa.String(50),        nullable=True),
            sa.Column("city",          sa.String(100),       nullable=True),
            sa.Column("address",       sa.String(255),       nullable=True),
            sa.Column("updated_at",    sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("NOW()")),
        )

    existing_indexes = (
        [idx["name"] for idx in inspector.get_indexes("dim_locations")]
        if "dim_locations" in existing_tables
        else []
    )
    if "idx_dim_locations_city" not in existing_indexes:
        op.create_index("idx_dim_locations_city", "dim_locations", ["city"])
    if "idx_dim_locations_type" not in existing_indexes:
        op.create_index("idx_dim_locations_type", "dim_locations", ["location_type"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "dim_locations" in existing_tables:
        op.drop_table("dim_locations")
    if "dim_products" in existing_tables:
        op.drop_table("dim_products")
