from typing import List, Dict, Any, Literal
from pydantic import BaseModel, Field


class PaymentTimelinePoint(BaseModel):
    date: str = Field(..., description="Hora en formato HH:00 (UTC)")
    successful: int = Field(..., description="Transacciones aprobadas en esa hora")
    failed: int = Field(..., description="Transacciones fallidas en esa hora (0 si ninguna)")
    amount: float = Field(..., description="Monto total aprobado en esa hora")

    model_config = {"json_schema_extra": {"example": {
        "date": "14:00",
        "successful": 1200,
        "failed": 5,
        "amount": 84000.00,
    }}}


class PaymentKPIsResponse(BaseModel):
    totalTransactions: int = Field(..., description="Total de intentos de pago iniciados (esperando_revisión)")
    failedPayments: int = Field(..., description="Transacciones cuyo estado final no fue Aprobado")
    failureRate: float = Field(..., description="(failedPayments / totalTransactions) * 100")
    revenue: float = Field(..., description="Suma de amount donde status = Aprobado")
    avgTransactionValue: float = Field(..., description="revenue / transacciones aprobadas")
    uptime: float = Field(..., description="Uptime real calculado desde fact_sla_events (SLA mínimo: 99.5%)")

    model_config = {"json_schema_extra": {"example": {
        "totalTransactions": 45892,
        "failedPayments": 412,
        "failureRate": 0.9,
        "revenue": 3245600.00,
        "avgTransactionValue": 70.72,
        "uptime": 99.85,
    }}}


class FailureReason(BaseModel):
    reason: str   = Field(..., description="Descripción legible del error (de dim_error_codes.descripcion)")
    categoria: str | None = Field(default=None, description="Categoría del error (interno/proveedor/tarjeta/validacion)")
    count: int    = Field(..., description="Transacciones con este error en la ventana")
    percentage: float = Field(..., description="Porcentaje sobre el total de fallidas")

    model_config = {"json_schema_extra": {"example": {"reason": "Fondos insuficientes", "categoria": "tarjeta", "count": 186, "percentage": 45.1}}}


class PaymentFailuresResponse(BaseModel):
    rejection_rate: float            = Field(..., description="(failed / total) * 100")
    total: int                       = Field(..., description="Total de transacciones en la ventana")
    failed: int                      = Field(..., description="Transacciones cuyo estado no es Aprobado")
    reasons: List[FailureReason]     = Field(..., description="Top N razones de fallo ordenadas por frecuencia")

    model_config = {"json_schema_extra": {"example": {
        "rejection_rate": 2.1,
        "total": 45892,
        "failed": 964,
        "reasons": [
            {"reason": "Fondos insuficientes", "count": 186, "percentage": 45.1},
            {"reason": "Tarjeta rechazada",    "count": 98,  "percentage": 23.8},
        ],
    }}}


class ConciliationStatus(BaseModel):
    status: str     = Field(..., description="Nombre del estado (Aprobado, esperando_revisión, discrepancia_*)")
    count: int      = Field(..., description="Transacciones en este estado")
    percentage: float = Field(..., description="Porcentaje sobre el total")

    model_config = {"json_schema_extra": {"example": {"status": "Aprobado", "count": 44820, "percentage": 97.7}}}


class PaymentConciliationResponse(BaseModel):
    statuses: List[ConciliationStatus] = Field(..., description="Desglose por estado de conciliación")
    total: int                         = Field(..., description="Total de transacciones en la ventana")
    approval_rate: float               = Field(..., description="(Aprobado / total) * 100")

    model_config = {"json_schema_extra": {"example": {
        "statuses": [
            {"status": "Aprobado",            "count": 44820, "percentage": 97.7},
            {"status": "esperando_revisión",  "count": 660,   "percentage": 1.4},
            {"status": "discrepancia_de_monto","count": 412,  "percentage": 0.9},
        ],
        "total": 45892,
        "approval_rate": 97.7,
    }}}


class PaymentMethodPoint(BaseModel):
    name: str   = Field(..., description="Nombre legible del método de pago")
    value: float = Field(..., description="Porcentaje de transacciones aprobadas con este método")
    count: int   = Field(..., description="Transacciones aprobadas con este método en la ventana")

    model_config = {"json_schema_extra": {"example": {"name": "Tarjeta de Crédito", "value": 48.5, "count": 21820}}}


class PaymentMethodsResponse(BaseModel):
    methods: list[PaymentMethodPoint] = Field(..., description="Distribución por método de pago (solo transacciones Aprobado)")
    total: int                        = Field(..., description="Total de transacciones aprobadas en la ventana")

    model_config = {"json_schema_extra": {"example": {
        "methods": [
            {"name": "Tarjeta de Crédito", "value": 48.5, "count": 21820},
            {"name": "Tarjeta de Débito",  "value": 27.3, "count": 12288},
        ],
        "total": 45000,
    }}}


class SlaActiveEvent(BaseModel):
    id: int
    tipo: str = Field(..., description="'downtime' | 'degraded'")
    timestamp_inicio: str = Field(..., description="ISO 8601 UTC")
    descripcion: str | None = None


class SlaAlert(BaseModel):
    id: int
    severity: str
    message: str
    created_at: str = Field(..., description="ISO 8601 UTC")


class SlaStatusResponse(BaseModel):
    uptime_pct: float = Field(..., description="Uptime real en la ventana consultada (0–100)")
    sla_ok: bool = Field(..., description="True si uptime_pct >= 99.5%")
    sla_threshold: float = Field(..., description="Umbral SLA configurado (99.5%)")
    active_events: List[SlaActiveEvent] = Field(..., description="Eventos downtime/degraded aún activos")
    recent_alerts: List[SlaAlert] = Field(..., description="Alertas SLA no reconocidas (últimas 24 h)")
    alert_created: bool = Field(..., description="True si esta consulta generó una nueva alerta crítica")

    model_config = {"json_schema_extra": {"example": {
        "uptime_pct": 98.7,
        "sla_ok": False,
        "sla_threshold": 99.5,
        "active_events": [
            {"id": 3, "tipo": "downtime", "timestamp_inicio": "2026-05-22T10:15:00Z", "descripcion": "Proveedor no disponible"}
        ],
        "recent_alerts": [
            {"id": 7, "severity": "critical", "message": "SLA de pagos por debajo del umbral: uptime=98.70%", "created_at": "2026-05-22T10:20:00Z"}
        ],
        "alert_created": True,
    }}}


class SlaTimelinePoint(BaseModel):
    date: str = Field(..., description="Día en formato YYYY-MM-DD (UTC)")
    downtimeMinutes: float = Field(..., description="Minutos de downtime acumulados ese día")
    degradedMinutes: float = Field(..., description="Minutos de degradación acumulados ese día")

    model_config = {"json_schema_extra": {"example": {
        "date": "2026-07-05", "downtimeMinutes": 12.5, "degradedMinutes": 3.0,
    }}}


# ── Dashboard ─────────────────────────────────────────────────────────────────

class KpiResumen(BaseModel):
    volumenTransDiario: int = Field(..., description="Total de transacciones iniciadas en las últimas 24h")
    crecimientoVolumen: float = Field(..., description="% de cambio respecto a las 24h anteriores")
    tasaRechazo: float = Field(..., description="% de transacciones fallidas sobre el total")
    uptimeSLA: float = Field(..., description="Uptime real del servicio en las últimas 24h (0–100)")


class TransaccionDiaria(BaseModel):
    hora: str = Field(..., description="Hora en formato HH:MM")
    exitosas: int
    rechazadas: int


class VolumenPorMetodo(BaseModel):
    metodo: str = Field(..., description="Nombre legible del método de pago")
    volumenTrans: int = Field(..., description="Cantidad de transacciones aprobadas con este método")


class DashboardResponse(BaseModel):
    kpiResumen: KpiResumen
    transaccionesDiarias: List[TransaccionDiaria]
    volumenPorMetodo: List[VolumenPorMetodo]


# ── Auditoría / Reportes ──────────────────────────────────────────────────────

class ReporteHistorico(BaseModel):
    id: str
    fecha: str = Field(..., description="Fecha del cierre en formato YYYY-MM-DD")
    tipo: str = Field(default="Cierre Diario")
    estado: Literal["completo", "en_proceso", "fallido"]


class DetalleReporteHisto(BaseModel):
    id_reporte: str
    fecha: str = Field(..., description="Fecha del cierre en formato YYYY-MM-DD")
    kpiResumen: KpiResumen
    volumenPorMetodo: List[VolumenPorMetodo]


class GenerarReporteResponse(BaseModel):
    success: bool


class CierreDescuadrePoint(BaseModel):
    fecha: str = Field(..., description="Fecha del cierre en formato YYYY-MM-DD")
    reportedTotal: float = Field(..., description="Monto total reportado por el origen")
    internalTotal: float | None = Field(default=None, description="Monto total interno conciliado (null si aún no concilia)")
    reportedCount: int = Field(..., description="Conteo de transacciones reportadas")
    internalCount: int | None = Field(default=None, description="Conteo de transacciones internas (null si aún no concilia)")

    model_config = {"json_schema_extra": {"example": {
        "fecha": "2026-07-05", "reportedTotal": 84000.0, "internalTotal": 83950.0,
        "reportedCount": 120, "internalCount": 119,
    }}}
