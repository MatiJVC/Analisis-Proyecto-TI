#!/bin/sh
set -e

echo "Preparando base de datos..."

python - <<'PYEOF'
import sys
sys.path.insert(0, '/app')

from sqlalchemy import inspect, text
from alembic.config import Config
from alembic import command

from app.db import engine, Base

# Registrar todos los modelos en Base.metadata
import app.models.raw          # noqa: F401
import app.models.warehouse    # noqa: F401
import app.pagos.models        # noqa: F401

alembic_cfg = Config('/app/alembic.ini')
insp = inspect(engine)
existing_tables = set(insp.get_table_names())

with engine.connect() as conn:
    has_alembic = conn.execute(
        text("SELECT 1 FROM information_schema.tables WHERE table_name='alembic_version'")
    ).scalar()

if not existing_tables or not has_alembic:
    print("Instalación nueva o sin tracking alembic — creando schema desde modelos...")
    Base.metadata.create_all(bind=engine)
    command.stamp(alembic_cfg, 'head')
    print("Schema creado y alembic estampado en head.")
else:
    print("Schema existente con alembic — aplicando migraciones pendientes...")
    command.upgrade(alembic_cfg, 'head')
    print("Migraciones aplicadas.")
PYEOF

echo "Iniciando servidor..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4