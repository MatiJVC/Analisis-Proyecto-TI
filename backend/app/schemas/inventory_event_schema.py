"""
Esquema de validación Pydantic v2 para eventos del módulo de Inventario (Grupo 5).
Endpoint destino: POST /events  —  source debe ser "inventory"

Validación condicional del payload según event_type:
  - stock_reserved            → StockReservedPayload      (campos estrictos + fechas cruzadas)
  - critical_threshold_reached
    stock_out_error            → CriticalAlertPayload      (campos de alerta obligatorios)
  - resto de event_types      → GenericInventoryPayload   (sin restricciones adicionales)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Tipo literal para los event_types de inventario
# ---------------------------------------------------------------------------

InventoryEventType = Literal[
    "stock_received",
    "stock_reserved",
    "stock_dispatched",
    "stock_adjusted",
    "stock_transfer_initiated",
    "stock_out_error",
    "critical_threshold_reached",
]

INVENTORY_ALERT_TYPES = ("critical_threshold_reached", "stock_out_error")


# ---------------------------------------------------------------------------
# Payload: stock_reserved
# ---------------------------------------------------------------------------

class StockReservedPayload(BaseModel):
    """Payload requerido cuando event_type == 'stock_reserved'."""

    reservation_id: UUID = Field(
        ...,
        description="Identificador único de la reserva (UUID v4)",
    )
    order_id: Union[UUID, str] = Field(
        ...,
        description="Identificador del pedido asociado (UUID v4 o string libre, ej: 'ord-2026-00123')",
    )
    sku_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Código SKU del producto reservado",
    )
    location_id: Union[UUID, int] = Field(
        ...,
        description="Identificador de la bodega/ubicación (UUID v4 o entero serial de PostgreSQL)",
    )
    quantity: int = Field(
        ...,
        description="Cantidad de unidades reservadas",
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp de creación de la reserva en formato ISO 8601 (ej: '2026-05-28T10:00:00Z')",
    )
    expires_at: datetime = Field(
        ...,
        description="Timestamp de expiración de la reserva en formato ISO 8601. Debe ser posterior a created_at",
    )

    @field_validator("quantity")
    @classmethod
    def quantity_debe_ser_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(
                f"El campo 'quantity' debe ser un entero mayor a 0. Valor recibido: {v}"
            )
        return v

    @field_validator("sku_id")
    @classmethod
    def sku_id_no_puede_estar_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El campo 'sku_id' no puede estar vacío ni contener solo espacios")
        return v

    @model_validator(mode="after")
    def expires_at_debe_ser_posterior_a_created_at(self) -> "StockReservedPayload":
        if self.expires_at <= self.created_at:
            raise ValueError(
                "El campo 'expires_at' debe ser posterior a 'created_at'. "
                f"Recibido — created_at: '{self.created_at.isoformat()}', "
                f"expires_at: '{self.expires_at.isoformat()}'. "
                "Verifique que las fechas estén en formato ISO 8601 y que la expiración sea futura."
            )
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "reservation_id": "550e8400-e29b-41d4-a716-446655440000",
                "order_id": "ord-2026-00123",
                "sku_id": "SKU-PROD-001",
                "location_id": "a3bb189e-8bf9-3888-9912-ace4e6543002",
                "quantity": 5,
                "created_at": "2026-05-28T10:00:00Z",
                "expires_at": "2026-05-29T10:00:00Z",
            }
        }
    }


# ---------------------------------------------------------------------------
# Payload: critical_threshold_reached / stock_out_error
# ---------------------------------------------------------------------------

class CriticalAlertPayload(BaseModel):
    """Payload requerido para alertas críticas de stock (critical_threshold_reached, stock_out_error)."""

    sku_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Código SKU del producto afectado",
    )
    location_id: Union[UUID, int, str] = Field(
        ...,
        description="Identificador de la bodega/ubicación (UUID, entero serial o string)",
    )
    current_stock: int = Field(
        ...,
        ge=0,
        description="Stock actual en la ubicación al momento del evento (0 o mayor)",
    )
    threshold_limite: int = Field(
        ...,
        ge=0,
        description="Umbral mínimo configurado que disparó la alerta (0 o mayor)",
    )

    @field_validator("sku_id")
    @classmethod
    def sku_id_no_puede_estar_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El campo 'sku_id' no puede estar vacío ni contener solo espacios")
        return v

    @field_validator("current_stock")
    @classmethod
    def current_stock_debe_ser_no_negativo(cls, v: int) -> int:
        if v < 0:
            raise ValueError(
                f"El campo 'current_stock' no puede ser negativo. Valor recibido: {v}"
            )
        return v

    @field_validator("threshold_limite")
    @classmethod
    def threshold_debe_ser_no_negativo(cls, v: int) -> int:
        if v < 0:
            raise ValueError(
                f"El campo 'threshold_limite' no puede ser negativo. Valor recibido: {v}"
            )
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "sku_id": "SKU-PROD-001",
                "location_id": "a3bb189e-8bf9-3888-9912-ace4e6543002",
                "current_stock": 2,
                "threshold_limite": 10,
            }
        }
    }


# ---------------------------------------------------------------------------
# Payload genérico (para los demás event_types)
# ---------------------------------------------------------------------------

class GenericInventoryPayload(BaseModel):
    """Payload sin restricciones estrictas para event_types que no requieren estructura fija."""

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Esquema principal del evento de inventario
# ---------------------------------------------------------------------------

class InventoryEventCreate(BaseModel):
    """
    Esquema completo de validación para eventos del módulo de Inventario.
    Aplica validación condicional del payload según el valor de event_type.

    Reglas:
      - source              : debe ser exactamente "inventory"
      - event_type          : valor dentro del conjunto de tipos de inventario permitidos
      - payload (stock_reserved)             : StockReservedPayload (UUID, fechas ISO 8601, quantity > 0)
      - payload (critical_threshold_reached,
                 stock_out_error)             : CriticalAlertPayload (sku_id, location_id, stocks)
      - payload (resto)                       : objeto libre con campos adicionales permitidos
    """

    source: Literal["inventory"] = Field(
        ...,
        description="Fuente del evento. Debe ser exactamente 'inventory'",
    )
    event_type: InventoryEventType = Field(
        ...,
        description=(
            "Tipo de evento de inventario. Valores permitidos: "
            "stock_received, stock_reserved, stock_dispatched, stock_adjusted, "
            "stock_transfer_initiated, stock_out_error, critical_threshold_reached"
        ),
    )
    payload: Dict[str, Any] = Field(
        ...,
        description=(
            "Cuerpo del evento. La estructura requerida varía según event_type. "
            "Ver documentación de StockReservedPayload y CriticalAlertPayload."
        ),
    )

    @field_validator("source")
    @classmethod
    def source_debe_ser_inventory(cls, v: str) -> str:
        if v != "inventory":
            raise ValueError(
                f"El campo 'source' debe ser 'inventory' para este endpoint. "
                f"Valor recibido: '{v}'"
            )
        return v

    @model_validator(mode="after")
    def validar_payload_segun_event_type(self) -> "InventoryEventCreate":
        event_type = self.event_type
        payload = self.payload

        if event_type == "stock_reserved":
            _validar_con_esquema(
                payload=payload,
                schema_cls=StockReservedPayload,
                event_type=event_type,
                campos_requeridos=[
                    "reservation_id", "order_id", "sku_id",
                    "location_id", "quantity", "created_at", "expires_at",
                ],
            )

        elif event_type in INVENTORY_ALERT_TYPES:
            _validar_con_esquema(
                payload=payload,
                schema_cls=CriticalAlertPayload,
                event_type=event_type,
                campos_requeridos=["sku_id", "location_id", "current_stock", "threshold_limite"],
            )

        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "Reserva de stock (stock_reserved)",
                    "value": {
                        "source": "inventory",
                        "event_type": "stock_reserved",
                        "payload": {
                            "reservation_id": "550e8400-e29b-41d4-a716-446655440000",
                            "order_id": "ord-2026-00123",
                            "sku_id": "SKU-PROD-001",
                            "location_id": "a3bb189e-8bf9-3888-9912-ace4e6543002",
                            "quantity": 5,
                            "created_at": "2026-05-28T10:00:00Z",
                            "expires_at": "2026-05-29T10:00:00Z",
                        },
                    },
                },
                {
                    "summary": "Umbral crítico alcanzado (critical_threshold_reached)",
                    "value": {
                        "source": "inventory",
                        "event_type": "critical_threshold_reached",
                        "payload": {
                            "sku_id": "SKU-PROD-001",
                            "location_id": "a3bb189e-8bf9-3888-9912-ace4e6543002",
                            "current_stock": 2,
                            "threshold_limite": 10,
                        },
                    },
                },
                {
                    "summary": "Stock recibido (stock_received)",
                    "value": {
                        "source": "inventory",
                        "event_type": "stock_received",
                        "payload": {
                            "sku_id": "SKU-PROD-001",
                            "location_id": 42,
                            "quantity_received": 100,
                            "received_at": "2026-05-28T08:30:00Z",
                        },
                    },
                },
            ]
        }
    }


# ---------------------------------------------------------------------------
# Helper interno de validación
# ---------------------------------------------------------------------------

def _validar_con_esquema(
    payload: Dict[str, Any],
    schema_cls: type[BaseModel],
    event_type: str,
    campos_requeridos: list[str],
) -> None:
    """
    Valida un payload dict contra un esquema Pydantic.
    Lanza ValueError con mensajes en español si falla.
    """
    campos_faltantes = [c for c in campos_requeridos if c not in payload]
    if campos_faltantes:
        raise ValueError(
            f"El payload para el evento '{event_type}' está incompleto. "
            f"Campos obligatorios faltantes: {campos_faltantes}. "
            f"Revise que el módulo de Inventario envíe todos los campos requeridos."
        )

    try:
        schema_cls(**payload)
    except Exception as exc:
        raise ValueError(
            f"El payload para '{event_type}' contiene datos con formato incorrecto: {exc}. "
            f"Asegúrese de que los UUIDs sean válidos, las fechas estén en formato ISO 8601 "
            f"y los campos numéricos sean enteros válidos."
        ) from exc
