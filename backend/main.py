import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import KeycloakUser, get_current_user, get_current_user_optional
from app.db import engine, Base
from app.models.raw import RawEvent
from app.models.warehouse import (
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
)
from app.api import events_router, kpis_router
_ = (
    RawEvent,
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
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Event Ingestion & Analytics API",
    description="Sistema de ingestión de eventos y análisis de KPIs para múltiples dominios (subscriptions, orders, iot, notifications)",
    version="1.0.0"
)

# Orígenes permitidos (frontend Next.js). Configurable por env para producción.
_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
_allowed_origins = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", _default_origins).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events_router)
app.include_router(kpis_router)


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
