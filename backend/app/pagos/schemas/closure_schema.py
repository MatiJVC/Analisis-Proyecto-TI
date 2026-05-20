from pydantic import BaseModel, Field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


class CierreDiarioPayload(BaseModel):
    fecha: date = Field(..., description="Fecha del cierre en formato YYYY-MM-DD")
    reported_total: Decimal = Field(..., description="Monto total reportado por la pasarela")
    reported_count: int = Field(..., description="Cantidad de transacciones reportadas")
    reference_id: Optional[str] = Field(None, description="ID externo del reporte consolidado")
    timestamp_event: datetime = Field(..., description="Timestamp UTC del evento de cierre")
