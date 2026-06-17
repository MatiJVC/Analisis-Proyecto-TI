"""add fact_pagos.payment_method column

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fact_pagos",
        sa.Column("payment_method", sa.String(100), nullable=True),
    )
    op.create_index("ix_fact_pagos_payment_method", "fact_pagos", ["payment_method"])


def downgrade() -> None:
    op.drop_index("ix_fact_pagos_payment_method", table_name="fact_pagos")
    op.drop_column("fact_pagos", "payment_method")
