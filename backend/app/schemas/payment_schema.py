from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime
from decimal import Decimal


ALLOWED_ESTADOS = [
    "Aprobado",
    "esperando_revisión",
    "discrepancia_de_monto",
    "discrepancia_de_transacciones",
]


class AttemptPaymentPayload(BaseModel):
    transaction_id: UUID = Field(..., description="UUID de la transacción")
    order_id: Optional[str] = Field(None, description="ID de orden (nullable)")
    subscription_id: Optional[str] = Field(None, description="ID de suscripción (nullable)")
    monto: Decimal = Field(..., description="Monto de la transacción, decimal con 2 decimales")
    token_transaccion: str = Field(..., min_length=1, max_length=255)
    timestamp_evento: datetime = Field(..., description="Timestamp UTC del evento")

    @validator("monto")
    def monto_positive(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("monto must be non-negative")
        return v


class ConfirmPaymentPayload(BaseModel):
    token_transaccion: str = Field(..., min_length=1, max_length=255)
    transaction_id: Optional[UUID] = Field(None, description="UUID de la transacción para verificación")
    approved: bool = Field(..., description="True si el pago fue aprobado por el proveedor")
    codigo_error: Optional[str] = Field(None, max_length=100)
    timestamp_evento: datetime = Field(..., description="Timestamp UTC del evento de confirmación")

