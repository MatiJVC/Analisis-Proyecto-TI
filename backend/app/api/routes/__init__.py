from .events import router as events_router
from .inventory import router as inventory_router
from .kpis import router as kpis_router
from app.pagos.routes.analytics import router as analytics_router
from app.pagos.routes.auditoria import router as auditoria_router

__all__ = ["events_router", "inventory_router", "kpis_router", "analytics_router", "auditoria_router"]
