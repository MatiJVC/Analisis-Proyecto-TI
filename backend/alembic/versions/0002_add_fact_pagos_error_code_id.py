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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("fact_pagos")]

    if "error_code_id" not in columns:
        op.add_column(
            "fact_pagos",
            sa.Column("error_code_id", sa.Integer(), nullable=True),
        )

    indexes = [idx["name"] for idx in inspector.get_indexes("fact_pagos")]
    if "ix_fact_pagos_error_code_id" not in indexes:
        op.create_index("ix_fact_pagos_error_code_id", "fact_pagos", ["error_code_id"])

    fks = [fk["name"] for fk in inspector.get_foreign_keys("fact_pagos")]
    if "fact_pagos_error_code_id_fkey" not in fks:
        op.create_foreign_key(
            "fact_pagos_error_code_id_fkey",
            "fact_pagos",
            "dim_error_codes",
            ["error_code_id"],
            ["id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("fact_pagos")]

    if "error_code_id" in columns:
        fks = [fk["name"] for fk in inspector.get_foreign_keys("fact_pagos")]
        if "fact_pagos_error_code_id_fkey" in fks:
            op.drop_constraint("fact_pagos_error_code_id_fkey", "fact_pagos", type_="foreignkey")
        
        indexes = [idx["name"] for idx in inspector.get_indexes("fact_pagos")]
        if "ix_fact_pagos_error_code_id" in indexes:
            op.drop_index("ix_fact_pagos_error_code_id", table_name="fact_pagos")
            
        op.drop_column("fact_pagos", "error_code_id")