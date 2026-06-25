from .fact_subscription import FactSubscription
from .fact_orders import FactOrder
from .fact_incidents import FactIncident
from .fact_tickets import FactTicket
from .dim_clientes_crm import DimClienteCRM
from .fact_interacciones import FactInteraccion
from .fact_ticket_articulos import FactTicketArticulo
from .fact_sla_violaciones import FactSlaViolacion
from .fact_inventory_movements import FactInventoryMovement
from .fact_inventory_alerts import FactInventoryAlert
from .dim_products import DimProduct
from .dim_locations import DimLocation
from .fact_iot import FactIoT
from .fact_notifications import FactNotifications

# Healthcare System DWH Models
try:
    from .dim_usuarios import DimUsuarios
    from .dim_profesionales import DimProfesionales
    from .dim_zonas import DimZonas
    from .dim_especialidades import DimEspecialidades
    from .dim_pacientes import DimPacientes
    from .fact_visitas import FactVisitas
    from .fact_alertas import FactAlertas
    from .fact_fichas_clinicas import FactFichasClinicas
    from .agg_visitas_diarias import AggVisitasDiarias
    from .agg_alertas import AggAlertas
    from .audit_pipeline import AuditPipeline
except ImportError:
    # Fallback if files are in salud/ subdirectory
    from .salud.dim_usuarios import DimUsuarios
    from .salud.dim_profesionales import DimProfesionales
    from .salud.dim_zonas import DimZonas
    from .salud.dim_especialidades import DimEspecialidades
    from .salud.dim_pacientes import DimPacientes
    from .salud.fact_visitas import FactVisitas
    from .salud.fact_alertas import FactAlertas
    from .salud.fact_fichas_clinicas import FactFichasClinicas
    from .salud.agg_visitas_diarias import AggVisitasDiarias
    from .salud.agg_alertas import AggAlertas
    from .salud.audit_pipeline import AuditPipeline

__all__ = [
    "FactSubscription",
    "FactOrder",
    "FactIncident",
    "FactTicket",
    "DimClienteCRM",
    "FactInteraccion",
    "FactTicketArticulo",
    "FactSlaViolacion",
    "FactInventoryMovement",
    "FactInventoryAlert",
    "DimProduct",
    "DimLocation",
    "DimUsuarios",
    "DimProfesionales",
    "DimZonas",
    "DimEspecialidades",
    "DimPacientes",
    "FactVisitas",
    "FactAlertas",
    "FactIoT",
    "FactNotifications",
    "FactFichasClinicas",
    "AggVisitasDiarias",
    "AggAlertas",
    "AuditPipeline",
]

