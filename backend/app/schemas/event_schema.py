from pydantic import BaseModel, Field
from typing import Dict, Any
from datetime import datetime


class EventCreate(BaseModel):

    source: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Fuente del evento (ej: subscriptions, orders, iot_devices, notifications)",
        example="subscriptions"
    )
    event_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Tipo de evento específico (ej: renewal_success, creation_failed)",
        example="renewal_success"
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Datos del evento en formato JSON",
        example={
            "contract_id": 1,
            "user_id": 10,
            "plan_id": 2
        }
    )

    class Config:
        json_schema_extra = {
            "example": {
                "source": "subscriptions",
                "event_type": "renewal_success",
                "payload": {
                    "contract_id": 1,
                    "user_id": 10,
                    "plan_id": 2,
                    "renewal_date": "2026-05-08",
                    "status": "completed"
                }
            }
        }


class EventResponse(BaseModel):
    id: int
    source: str
    event_type: str
    payload: Dict[str, Any] | None = None
    processed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class EventCreateResponse(BaseModel):
    message: str
    event_id: int
    source: str
    event_type: str

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "message": "event stored",
                "event_id": 1,
                "source": "subscriptions",
                "event_type": "renewal_success"
            }
        }
