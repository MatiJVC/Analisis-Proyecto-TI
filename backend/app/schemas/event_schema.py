from pydantic import BaseModel, Field
from typing import Any, Dict, Literal
from uuid import UUID
from datetime import datetime


class EventCreate(BaseModel):
    source: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Proyecto origen del evento (ej: subscriptions, orders, salud, incidents)",
    )
    event_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Tipo de evento específico (ej: renewal_success, order_placed)",
    )
    # Dict[str, Any] acepta cualquier estructura JSON válida sin romper el schema.
    # Usa default_factory=dict para que proyectos sin payload no fallen la validación.
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Cuerpo libre del evento — cualquier objeto JSON válido",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "source": "subscriptions",
                "event_type": "renewal_success",
                "payload": {
                    "contract_id": 1,
                    "user_id": 10,
                    "plan_id": 2,
                    "renewal_date": "2026-05-08",
                    "status": "completed",
                },
            }
        }
    }


class AcknowledgeResponse(BaseModel):
    """Respuesta 202 — confirma recepción sin esperar procesamiento ETL."""
    status: Literal["acknowledged"]
    event_id: UUID

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "acknowledged",
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    }


class EventResponse(BaseModel):
    event_id: UUID
    source: str
    event_type: str
    payload: Dict[str, Any] | None = None
    processed: bool
    ingested_at: datetime

    model_config = {"from_attributes": True}


# Kept for backward compatibility with any existing callers
class EventCreateResponse(BaseModel):
    message: str
    event_id: UUID
    source: str
    event_type: str

    model_config = {"from_attributes": True}
