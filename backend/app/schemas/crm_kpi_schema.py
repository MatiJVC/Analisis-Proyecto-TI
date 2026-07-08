from typing import List, Optional

from pydantic import BaseModel, Field


class CRMKPIsResponse(BaseModel):
    totalCustomers: int = Field(..., description="Clientes únicos registrados")
    openTickets: int = Field(..., description="Tickets en estado Abierto o Progreso")
    avgResponseTimeMinutes: float = Field(..., description="Tiempo promedio de resolución en minutos")
    criticalTickets: int = Field(..., description="Tickets abiertos con prioridad Alta o Crítica")
    ticketsCreatedToday: int = Field(..., description="Tickets creados hoy (ticket.creado)")
    resolutionRate: float = Field(..., description="Porcentaje de tickets cerrados sobre el total")


class CRMTimelinePoint(BaseModel):
    date: str
    opened: int
    resolved: int


class CRMTimelineResponse(BaseModel):
    days: int
    points: List[CRMTimelinePoint]


class CRMTicketRow(BaseModel):
    ticketId: str
    asunto: str
    estado: str
    prioridad: str
    canal: str
    sourceProject: str
    openedAt: str
    updatedAt: str


class CRMTicketsResponse(BaseModel):
    tickets: List[CRMTicketRow]


class CRMSLASummary(BaseModel):
    totalViolations: int
    criticalViolations: int
    slaComplianceRate: float = Field(..., description="Porcentaje de tickets resueltos dentro del SLA")
    ticketsEvaluated: int = Field(0, description="Tickets con dato de SLA (within_sla no-nulo); 0 = sin datos para evaluar")


class CRMDistributionItem(BaseModel):
    name: str
    count: int
    percentage: float


class CRMDistributionResponse(BaseModel):
    total: int
    items: List[CRMDistributionItem]


class CRMExternalTicketResponse(BaseModel):
    """Espejo del TicketDto real expuesto por el CRM externo
    (GET /api/v1/analytics/estado-ticket/:id de pgti-proyecto-crm-backend).

    Todos los campos salvo ticket_id/estado son opcionales porque el CRM
    externo puede omitirlos según el tipo de ticket. Verificar contra la
    doc oficial del TicketDto si se agregan más campos en el futuro.
    """

    ticket_id: str
    estado: str
    prioridad: Optional[str] = None
    canal: Optional[str] = None
    asunto: Optional[str] = None
    descripcion: Optional[str] = None
    cliente_id: Optional[int] = None
    cliente_nombre: Optional[str] = None
    agente_id: Optional[str] = None
    fecha_vencimiento_sla: Optional[str] = None
    pedido_id_ref: Optional[str] = None
    pago_id_ref: Optional[str] = None
    salud_ref: Optional[str] = None
    resolucion: Optional[str] = None
    # Nombre real del campo en el CRM externo — distinto de nuestro
    # `suscripcion_id_red` interno (typo histórico ya documentado en tests).
    suscripcion_id_ref: Optional[str] = None
    creado_en: Optional[str] = None
    actualizado_en: Optional[str] = None
