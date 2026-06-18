"""create CRM warehouse tables

Crea las 5 tablas del módulo CRM/Soporte:
  - dim_clientes_crm
  - fact_tickets
  - fact_interacciones
  - fact_sla_violaciones
  - fact_ticket_articulos

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── dim_clientes_crm ──────────────────────────────────────────────────────
    op.create_table(
        "dim_clientes_crm",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cliente_identidad_id", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("telefono", sa.String(30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("cliente_identidad_id", name="uq_dim_clientes_crm_identidad"),
        sa.UniqueConstraint("email", name="uq_dim_clientes_crm_email"),
    )
    op.create_index("ix_dim_clientes_crm_cliente_identidad_id", "dim_clientes_crm", ["cliente_identidad_id"])
    op.create_index("ix_dim_clientes_crm_email",                "dim_clientes_crm", ["email"])
    op.create_index("ix_dim_clientes_crm_created_at",           "dim_clientes_crm", ["created_at"])
    op.create_index("idx_dim_clientes_crm_email",               "dim_clientes_crm", ["email"])

    # ── fact_tickets ──────────────────────────────────────────────────────────
    op.create_table(
        "fact_tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticket_id",              sa.String(50),  nullable=False),
        sa.Column("asunto",                 sa.String(500), nullable=True),
        sa.Column("estado",                 sa.String(30),  nullable=False),
        sa.Column("prioridad",              sa.String(20),  nullable=False),
        sa.Column("canal",                  sa.String(20),  nullable=True),
        sa.Column("source_project",         sa.String(50),  nullable=True),
        sa.Column("cliente_identidad_id",   sa.String(100), nullable=True),
        sa.Column("agente_id",              sa.String(100), nullable=True),
        sa.Column("pedido_id_ref",          sa.String(100), nullable=True),
        sa.Column("suscripcion_id_red",     sa.String(100), nullable=True),
        sa.Column("fecha_vencimiento_sla",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_time_hours",  sa.Float(),     nullable=True),
        sa.Column("within_sla",             sa.Boolean(),   nullable=True),
        sa.Column("csat_score",             sa.Integer(),   nullable=True),
        sa.Column("opened_at",              sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at",            sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at",              sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",             sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("ticket_id", name="uq_fact_tickets_ticket_id"),
        sa.CheckConstraint(
            "estado IN ('Abierto', 'Progreso', 'Resuelto', 'Cerrado')",
            name="ck_fact_tickets_estado",
        ),
        sa.CheckConstraint(
            "prioridad IN ('Baja', 'Media', 'Alta', 'Crítica')",
            name="ck_fact_tickets_prioridad",
        ),
        sa.CheckConstraint(
            "canal IN ('Chat', 'Email', 'Teléfono', 'App') OR canal IS NULL",
            name="ck_fact_tickets_canal",
        ),
    )
    op.create_index("ix_fact_tickets_id",                 "fact_tickets", ["id"])
    op.create_index("ix_fact_tickets_ticket_id",          "fact_tickets", ["ticket_id"], unique=True)
    op.create_index("ix_fact_tickets_estado",             "fact_tickets", ["estado"])
    op.create_index("ix_fact_tickets_prioridad",          "fact_tickets", ["prioridad"])
    op.create_index("ix_fact_tickets_canal",              "fact_tickets", ["canal"])
    op.create_index("ix_fact_tickets_source_project",     "fact_tickets", ["source_project"])
    op.create_index("ix_fact_tickets_cliente_identidad_id","fact_tickets", ["cliente_identidad_id"])
    op.create_index("ix_fact_tickets_agente_id",          "fact_tickets", ["agente_id"])
    op.create_index("ix_fact_tickets_opened_at",          "fact_tickets", ["opened_at"])
    op.create_index("idx_fact_tickets_estado_prioridad",  "fact_tickets", ["estado", "prioridad"])
    op.create_index("idx_fact_tickets_source_opened",     "fact_tickets", ["source_project", "opened_at"])

    # ── fact_interacciones ────────────────────────────────────────────────────
    op.create_table(
        "fact_interacciones",
        sa.Column("id",              sa.Integer(),     primary_key=True),
        sa.Column("interaccion_id",  sa.String(100),   nullable=False),
        sa.Column("ticket_id",       sa.String(50),    nullable=False),
        sa.Column("autor_tipo",      sa.String(20),    nullable=False),
        sa.Column("autor_id",        sa.String(100),   nullable=True),
        sa.Column("contenido",       sa.Text(),        nullable=True),
        sa.Column("es_nota_interna", sa.Boolean(),     nullable=False, server_default=sa.text("false")),
        sa.Column("creado_en",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at",     sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("interaccion_id", name="uq_fact_interacciones_interaccion_id"),
    )
    op.create_index("ix_fact_interacciones_id",              "fact_interacciones", ["id"])
    op.create_index("ix_fact_interacciones_interaccion_id",  "fact_interacciones", ["interaccion_id"], unique=True)
    op.create_index("ix_fact_interacciones_ticket_id",       "fact_interacciones", ["ticket_id"])
    op.create_index("ix_fact_interacciones_autor_tipo",      "fact_interacciones", ["autor_tipo"])
    op.create_index("ix_fact_interacciones_creado_en",       "fact_interacciones", ["creado_en"])
    op.create_index("ix_fact_interacciones_ingested_at",     "fact_interacciones", ["ingested_at"])
    op.create_index("idx_fact_interacciones_ticket_creado",  "fact_interacciones", ["ticket_id", "creado_en"])

    # ── fact_sla_violaciones ──────────────────────────────────────────────────
    op.create_table(
        "fact_sla_violaciones",
        sa.Column("id",                   sa.Integer(),  primary_key=True),
        sa.Column("ticket_id",            sa.String(50),  nullable=False),
        sa.Column("cliente_identidad_id", sa.String(100), nullable=True),
        sa.Column("prioridad",            sa.String(20),  nullable=False),
        sa.Column("canal",                sa.String(20),  nullable=True),
        sa.Column("source_project",       sa.String(50),  nullable=True),
        sa.Column("sla_threshold_hours",  sa.Float(),     nullable=False),
        sa.Column("elapsed_hours",        sa.Float(),     nullable=False),
        sa.Column("breach_percentage",    sa.Float(),     nullable=False),
        sa.Column("threshold_crossed",    sa.Integer(),   nullable=False),
        sa.Column("escalation_required",  sa.Boolean(),   nullable=False, server_default=sa.text("false")),
        sa.Column("escalado_hacia",       sa.String(50),  nullable=True),
        sa.Column("fecha_vencimiento_sla",sa.DateTime(timezone=True), nullable=True),
        sa.Column("violation_detected_at",sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at",           sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_fact_sla_violaciones_id",                "fact_sla_violaciones", ["id"])
    op.create_index("ix_fact_sla_violaciones_ticket_id",         "fact_sla_violaciones", ["ticket_id"])
    op.create_index("ix_fact_sla_violaciones_prioridad",         "fact_sla_violaciones", ["prioridad"])
    op.create_index("ix_fact_sla_violaciones_source_project",    "fact_sla_violaciones", ["source_project"])
    op.create_index("ix_fact_sla_violaciones_threshold_crossed", "fact_sla_violaciones", ["threshold_crossed"])
    op.create_index("ix_fact_sla_violaciones_violation_detected_at", "fact_sla_violaciones", ["violation_detected_at"])
    op.create_index("idx_fact_sla_violaciones_ticket_ts",        "fact_sla_violaciones", ["ticket_id", "violation_detected_at"])
    op.create_index("idx_fact_sla_violaciones_threshold",        "fact_sla_violaciones", ["threshold_crossed", "prioridad"])

    # ── fact_ticket_articulos ─────────────────────────────────────────────────
    op.create_table(
        "fact_ticket_articulos",
        sa.Column("id",                    sa.Integer(),    primary_key=True),
        sa.Column("ticket_id",             sa.String(50),   nullable=False),
        sa.Column("articulo_id",           sa.String(100),  nullable=False),
        sa.Column("articulo_titulo",       sa.String(500),  nullable=True),
        sa.Column("articulo_categoria",    sa.String(100),  nullable=True),
        sa.Column("fue_enviado_al_cliente",sa.Boolean(),    nullable=False, server_default=sa.text("false")),
        sa.Column("agente_id",             sa.String(100),  nullable=True),
        sa.Column("vinculado_en",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at",           sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_fact_ticket_articulos_id",          "fact_ticket_articulos", ["id"])
    op.create_index("ix_fact_ticket_articulos_ticket_id",   "fact_ticket_articulos", ["ticket_id"])
    op.create_index("ix_fact_ticket_articulos_articulo_id", "fact_ticket_articulos", ["articulo_id"])
    op.create_index("ix_fact_ticket_articulos_vinculado_en","fact_ticket_articulos", ["vinculado_en"])
    op.create_index("idx_fact_ticket_articulos_ticket",     "fact_ticket_articulos", ["ticket_id"])
    op.create_index("idx_fact_ticket_articulos_articulo",   "fact_ticket_articulos", ["articulo_id"])


def downgrade() -> None:
    op.drop_table("fact_ticket_articulos")
    op.drop_table("fact_sla_violaciones")
    op.drop_table("fact_interacciones")
    op.drop_table("fact_tickets")
    op.drop_table("dim_clientes_crm")
