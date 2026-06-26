import asyncio
import logging
import os
import uuid as _uuid
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import KeycloakUser, get_current_user, get_current_user_optional
from app.api.rate_limit import require_rate_limit
from app.api.routes.events import ETL_QUEUE, _run_etl, retry_stale_events
from app.db import engine, Base
from app.redis_client import redis_client
# Importaciones de modelos para que SQLAlchemy los registre en Base.metadata antes
# de llamar a create_all. El orden importa: raw primero, luego warehouse, luego pagos.
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
from app.api import events_router, inventory_router, kpis_router, analytics_router, auditoria_router

_ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
if _ENVIRONMENT == "development":
    # En producción/staging, el schema se gestiona con: alembic upgrade head
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async def _periodic_retry():
        while True:
            await asyncio.sleep(300)
            try:
                await asyncio.to_thread(retry_stale_events)
            except Exception:
                logger.exception("_periodic_retry: error en retry_stale_events")

    async def _etl_consumer():
        while True:
            try:
                item = await asyncio.to_thread(redis_client.blpop, ETL_QUEUE, 10)
                if item:
                    _, value = item
                    event_id_str, source = value.split("|", 1)
                    await asyncio.to_thread(_run_etl, _uuid.UUID(event_id_str), source)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(1)

    retry_task = asyncio.create_task(_periodic_retry())
    consumer_task = asyncio.create_task(_etl_consumer()) if redis_client is not None else None

    yield

    retry_task.cancel()
    try:
        await retry_task
    except asyncio.CancelledError:
        pass

    if consumer_task is not None:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Event Ingestion & Analytics API",
    description="Sistema de ingestión de eventos y análisis de KPIs para múltiples dominios (subscriptions, orders, iot, notifications)",
    version="1.0.0",
    lifespan=lifespan,
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
app.include_router(auditoria_router, prefix="/v1", dependencies=[Depends(require_rate_limit)])


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
