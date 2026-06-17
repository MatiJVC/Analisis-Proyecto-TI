"""fix fact_orders column types: order_id/customer_id String, total_amount Numeric

Revision ID: 0001
Revises:
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    has_fact_payments = "fact_payments" in tables

    # fact_payments tiene FK sobre fact_orders.order_id; hay que quitarla antes
    # de cambiar el tipo y volver a crearla después.
    if has_fact_payments:
        op.drop_constraint("fact_payments_order_id_fkey", "fact_payments", type_="foreignkey")

    op.alter_column(
        "fact_orders",
        "order_id",
        type_=sa.String(100),
        existing_type=sa.Integer(),
        existing_nullable=False,
        postgresql_using="order_id::varchar(100)",
    )
    op.alter_column(
        "fact_orders",
        "customer_id",
        type_=sa.String(100),
        existing_type=sa.Integer(),
        existing_nullable=False,
        postgresql_using="customer_id::varchar(100)",
    )
    op.alter_column(
        "fact_orders",
        "total_amount",
        type_=sa.Numeric(18, 2),
        existing_type=sa.Float(),
        existing_nullable=False,
        postgresql_using="total_amount::numeric(18,2)",
    )

    # Actualizar fact_payments.order_id al mismo tipo para mantener la FK
    if has_fact_payments:
        op.alter_column(
            "fact_payments",
            "order_id",
            type_=sa.String(100),
            existing_type=sa.Integer(),
            existing_nullable=True,
            postgresql_using="order_id::varchar(100)",
        )
        op.create_foreign_key(
            "fact_payments_order_id_fkey",
            "fact_payments",
            "fact_orders",
            ["order_id"],
            ["order_id"],
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    has_fact_payments = "fact_payments" in tables

    if has_fact_payments:
        op.drop_constraint("fact_payments_order_id_fkey", "fact_payments", type_="foreignkey")

        op.alter_column(
            "fact_payments",
            "order_id",
            type_=sa.Integer(),
            existing_type=sa.String(100),
            existing_nullable=True,
            postgresql_using="order_id::integer",
        )
    op.alter_column(
        "fact_orders",
        "total_amount",
        type_=sa.Float(),
        existing_type=sa.Numeric(18, 2),
        existing_nullable=False,
        postgresql_using="total_amount::double precision",
    )
    op.alter_column(
        "fact_orders",
        "customer_id",
        type_=sa.Integer(),
        existing_type=sa.String(100),
        existing_nullable=False,
        postgresql_using="customer_id::integer",
    )
    op.alter_column(
        "fact_orders",
        "order_id",
        type_=sa.Integer(),
        existing_type=sa.String(100),
        existing_nullable=False,
        postgresql_using="order_id::integer",
    )
    if has_fact_payments:
        op.create_foreign_key(
            "fact_payments_order_id_fkey",
            "fact_payments",
            "fact_orders",
            ["order_id"],
            ["order_id"],
        )
