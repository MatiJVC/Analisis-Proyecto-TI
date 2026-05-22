from typing import List, Dict, Any
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
