from .events import router as events_router
from .kpis import router as kpis_router
from app.pagos.routes.analytics import router as analytics_router

__all__ = ["events_router", "kpis_router", "analytics_router"]
