"""add fact_pagos.error_code_id FK to dim_error_codes

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fact_pagos",
        sa.Column("error_code_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_fact_pagos_error_code_id", "fact_pagos", ["error_code_id"])
    op.create_foreign_key(
        "fact_pagos_error_code_id_fkey",
        "fact_pagos",
        "dim_error_codes",
        ["error_code_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fact_pagos_error_code_id_fkey", "fact_pagos", type_="foreignkey")
    op.drop_index("ix_fact_pagos_error_code_id", table_name="fact_pagos")
    op.drop_column("fact_pagos", "error_code_id")