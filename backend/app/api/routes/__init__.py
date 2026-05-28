from .events import router as events_router
from .inventory import router as inventory_router
from .kpis import router as kpis_router

__all__ = ["events_router", "inventory_router", "kpis_router"]
