"""
KPIs router — dispatcher.

Cada dominio vive en su propio módulo:
  kpis_subscriptions.py  →  /kpis/subscriptions/*
  kpis_orders.py         →  /kpis/orders/*
  kpis_salud.py          →  /kpis/salud/*
  kpis_incidents.py      →  /kpis/incidents/*
  kpis_overview.py       →  /kpis/overview/*
  kpis_crm.py            →  /kpis/crm/*
  kpis_iot.py            →  /kpis/iot/*
  kpis_notifications.py  →  /kpis/notifications/*
"""

from fastapi import APIRouter

from .kpis_subscriptions import router as subscriptions_router
from .kpis_orders import router as orders_router
from .kpis_salud import router as salud_router
from .kpis_incidents import router as incidents_router
from .kpis_overview import router as overview_router
from .kpis_crm import router as crm_router
from .kpis_iot import router as iot_router
from .kpis_notifications import router as notifications_router

router = APIRouter(
    prefix="/kpis",
    responses={
        401: {"description": "Falta token Bearer o token inválido"},
        403: {"description": "El usuario no tiene rol suficiente"},
        500: {"description": "Internal server error"},
    },
)

router.include_router(subscriptions_router)
router.include_router(orders_router)
router.include_router(salud_router)
router.include_router(incidents_router)
router.include_router(overview_router)
router.include_router(crm_router)
router.include_router(iot_router)
router.include_router(notifications_router)
