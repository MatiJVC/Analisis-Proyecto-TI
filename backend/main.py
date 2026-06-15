import asyncio
import logging
import os
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import KeycloakUser, get_current_user, get_current_user_optional
from app.api.rate_limit import require_rate_limit, RATE_LIMIT_TABLE_DDL
from app.api.routes.events import ETL_RETRY_DDL, _run_etl, purge_stale_raw_events, retry_stale_events
from app.pagos.services.sla_service import run_sla_alert_check
from app.services.monitoring_service import run_payment_alert_check
from app.db import engine
# Importaciones de modelos para que SQLAlchemy los registre en su mapper.
# El orden importa: raw primero, luego warehouse, luego pagos.
from app.models.raw import RawEvent  # noqa: F401
from app.models.warehouse import (  # noqa: F401
    FactSubscription,
    FactOrder,
    FactIncident,
    DimUsuarios,
    DimProfesionales,
    DimZonas,
    DimEspecialidades,
    DimPacientes,
    FactVisitas,
    FactAlertas,
    FactFichasClinicas,
    FactTicket,
    DimClienteCRM,
    FactInteraccion,
    FactTicketArticulo,
    FactSlaViolacion,
    FactInventoryMovement,
    FactInventoryAlert,
)
from app.models.warehouse.alerts import PriorityAlert  # noqa: F401
from app.pagos.models import (  # noqa: F401
    CierreDiario,
    DimErrorCode,
    DimEstadosConciliacion,
    FactPagos,
    FactPaymentsEvent,
    FactSlaEvent,
)
from app.api import events_router, inventory_router, kpis_router, analytics_router


def _run_ddl(ddl: str) -> None:
    """Ejecuta un bloque DDL idempotente separado por ';'. Usado en lifespan."""
    from sqlalchemy import text
    with engine.connect() as conn:
        for stmt in ddl.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        conn.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await asyncio.to_thread(_run_ddl, RATE_LIMIT_TABLE_DDL)
    await asyncio.to_thread(_run_ddl, ETL_RETRY_DDL)

    async def _periodic_retry():
        while True:
            await asyncio.sleep(300)
            try:
                await asyncio.to_thread(retry_stale_events)
            except Exception:
                logger.exception("_periodic_retry: error en retry_stale_events")

    async def _cleanup_rate_limit_table():
        """Borra ventanas antiguas de api_rate_limit cada 2 minutos."""
        from sqlalchemy import text
        _WARN_THRESHOLD = 10_000
        while True:
            await asyncio.sleep(120)
            try:
                with engine.connect() as conn:
                    conn.execute(text(
                        "DELETE FROM api_rate_limit "
                        "WHERE window_start < NOW() - INTERVAL '2 minutes'"
                    ))
                    row_count = conn.execute(text("SELECT COUNT(*) FROM api_rate_limit")).scalar()
                    conn.commit()
                    if row_count > _WARN_THRESHOLD:
                        logger.warning(
                            "_cleanup_rate_limit_table: %d filas tras limpieza "
                            "(umbral %d) — posible fuga o tráfico inusualmente alto",
                            row_count, _WARN_THRESHOLD,
                        )
            except Exception:
                logger.exception("_cleanup_rate_limit_table: error en limpieza")

    async def _periodic_sla_check():
        """Evalúa SLA de pagos cada 5 minutos y crea alertas si el uptime cae."""
        while True:
            await asyncio.sleep(300)
            try:
                await asyncio.to_thread(run_sla_alert_check)
            except Exception:
                logger.exception("_periodic_sla_check: error inesperado")

    async def _periodic_payment_uptime_check():
        """Detecta anomalías de uptime de pagos cada 5 minutos y crea alertas."""
        while True:
            await asyncio.sleep(300)
            try:
                await asyncio.to_thread(run_payment_alert_check)
            except Exception:
                logger.exception("_periodic_payment_uptime_check: error inesperado")

    async def _periodic_purge_raw_events():
        """Elimina eventos terminales de fact_raw_events una vez al día."""
        while True:
            await asyncio.sleep(24 * 3600)
            try:
                await asyncio.to_thread(purge_stale_raw_events)
            except Exception:
                logger.exception("_periodic_purge_raw_events: error inesperado")

    retry_task = asyncio.create_task(_periodic_retry())
    cleanup_task = asyncio.create_task(_cleanup_rate_limit_table())
    sla_task = asyncio.create_task(_periodic_sla_check())
    payment_uptime_task = asyncio.create_task(_periodic_payment_uptime_check())
    purge_task = asyncio.create_task(_periodic_purge_raw_events())

    yield

    for task in [retry_task, cleanup_task, sla_task, payment_uptime_task, purge_task]:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


_is_dev = os.getenv("ENVIRONMENT", "production").lower() == "development"

app = FastAPI(
    title="Event Ingestion & Analytics API",
    description="Sistema de ingestión de eventos y análisis de KPIs para múltiples dominios (subscriptions, orders, iot, notifications)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs"        if _is_dev else None,
    redoc_url="/redoc"      if _is_dev else None,
    openapi_url="/openapi.json" if _is_dev else None,
)

# Orígenes permitidos (frontend Next.js). Configurable por env para producción.
_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
_raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", _default_origins)
_use_wildcard = _raw_origins.strip() == "*"
_allowed_origins = (
    ["*"]
    if _use_wildcard
    else [o.strip() for o in _raw_origins.split(",") if o.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=not _use_wildcard,  # credentials incompatible con wildcard
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(events_router, prefix="/v1")
app.include_router(kpis_router, prefix="/v1", dependencies=[Depends(require_rate_limit)])
app.include_router(inventory_router, prefix="/v1", dependencies=[Depends(require_rate_limit)])
app.include_router(analytics_router, prefix="/v1", dependencies=[Depends(require_rate_limit)])


@app.get("/", tags=["health"])
async def root():
    return {"message": "Event Ingestion & Analytics API is running", "status": "healthy"}


@app.get("/auth/me", tags=["auth"])
async def whoami(user: KeycloakUser = Depends(get_current_user)):
    """Devuelve los datos del usuario autenticado (Keycloak).

    Útil para que el frontend pruebe que el token llega bien validado.
    """
    return {
        "sub": user.sub,
        "username": user.username,
        "email": user.email,
        "roles": user.roles,
    }


@app.get("/auth/status", tags=["auth"])
async def auth_status(
    user: KeycloakUser | None = Depends(get_current_user_optional),
):
    """Endpoint público que reporta si el request trae token válido o no."""
    if user is None:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "username": user.username,
        "roles": user.roles,
    }
