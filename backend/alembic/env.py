import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Importar todos los modelos para que Base.metadata los registre antes de la migración
from app.db.base import Base  # noqa: F401
from app.models.raw import RawEvent  # noqa: F401
from app.models.warehouse import (  # noqa: F401
    FactSubscription, FactOrder, FactIncident,
    DimUsuarios, DimProfesionales, DimZonas, DimEspecialidades, DimPacientes,
    FactVisitas, FactAlertas, FactFichasClinicas,
    FactTicket, DimClienteCRM, FactInteraccion, FactTicketArticulo,
    FactSlaViolacion, FactInventoryMovement, FactInventoryAlert,
    DimProduct, DimLocation,
)
from app.models.warehouse.alerts import PriorityAlert  # noqa: F401
from app.models.warehouse.fact_iot import FactIoT  # noqa: F401
from app.models.warehouse.fact_notifications import FactNotifications  # noqa: F401
from app.pagos.models import (  # noqa: F401
    CierreDiario, DimErrorCode, DimEstadosConciliacion,
    FactPagos, FactPaymentsEvent, FactSlaEvent,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Sobreescribir la URL con la variable de entorno (tiene prioridad sobre alembic.ini)
_db_url = os.getenv("DATABASE_URL")
if _db_url:
    config.set_main_option("sqlalchemy.url", _db_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
