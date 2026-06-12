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


def downgrade() -> None:
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
