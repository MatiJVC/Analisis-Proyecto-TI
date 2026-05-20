from typing import List
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
    uptime: float = Field(..., description="Disponibilidad simulada basada en tasa de error de red")

    model_config = {"json_schema_extra": {"example": {
        "totalTransactions": 45892,
        "failedPayments": 412,
        "failureRate": 0.9,
        "revenue": 3245600.00,
        "avgTransactionValue": 70.72,
        "uptime": 99.85,
    }}}
