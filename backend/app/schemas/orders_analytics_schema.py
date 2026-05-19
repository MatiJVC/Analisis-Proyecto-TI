"""
Schemas Pydantic para respuestas de analítica de órdenes.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class KPISResponse(BaseModel):
    """Response modelo para KPIs consolidados de órdenes."""
    
    total_orders: int = Field(..., description="Total de órdenes")
    delivery_rate: float = Field(..., ge=0.0, le=1.0, description="Tasa de entregas completadas (0.0-1.0)")
    payment_failure_rate: float = Field(..., ge=0.0, le=1.0, description="Tasa de pagos fallidos (0.0-1.0)")
    payment_success_rate: float = Field(..., ge=0.0, le=1.0, description="Tasa de pagos exitosos (0.0-1.0)")
    avg_processing_time_hours: float = Field(..., description="Tiempo promedio de procesamiento en horas")
    revenue_total: float = Field(..., description="Ingresos totales en moneda")
    average_order_value: float = Field(..., description="Valor promedio por orden")
    sla_compliance: float = Field(..., ge=0.0, le=1.0, description="Cumplimiento SLA (entregas + pagos exitosos)")
    stock_reservation_rate: float = Field(..., ge=0.0, le=1.0, description="Tasa de órdenes con stock reservado")
    fulfillment_rate: float = Field(..., ge=0.0, le=1.0, description="Fulfillment completo (pago + entrega)")

    class Config:
        json_schema_extra = {
            "example": {
                "total_orders": 150,
                "delivery_rate": 0.92,
                "payment_failure_rate": 0.08,
                "payment_success_rate": 0.92,
                "avg_processing_time_hours": 24.5,
                "revenue_total": 2500000.00,
                "average_order_value": 16666.67,
                "sla_compliance": 0.88,
                "stock_reservation_rate": 0.95,
                "fulfillment_rate": 0.87
            }
        }


class ChannelMetric(BaseModel):
    """Métrica para un canal de venta."""
    channel: str
    order_count: int
    revenue: float
    percentage_of_total: float


class ChannelsResponse(BaseModel):
    """Response para distribución de órdenes por canal."""
    total_orders: int
    channels: List[ChannelMetric]

    class Config:
        json_schema_extra = {
            "example": {
                "total_orders": 150,
                "channels": [
                    {
                        "channel": "web",
                        "order_count": 75,
                        "revenue": 1250000.0,
                        "percentage_of_total": 50.0
                    },
                    {
                        "channel": "app",
                        "order_count": 50,
                        "revenue": 833000.0,
                        "percentage_of_total": 33.3
                    },
                    {
                        "channel": "call_center",
                        "order_count": 25,
                        "revenue": 417000.0,
                        "percentage_of_total": 16.7
                    }
                ]
            }
        }


class StatusMetric(BaseModel):
    """Métrica para un estado de orden."""
    status: str
    count: int
    percentage_of_total: float


class StatusResponse(BaseModel):
    """Response para distribución de órdenes por estado."""
    total_orders: int
    statuses: List[StatusMetric]

    class Config:
        json_schema_extra = {
            "example": {
                "total_orders": 150,
                "statuses": [
                    {
                        "status": "delivered",
                        "count": 138,
                        "percentage_of_total": 92.0
                    },
                    {
                        "status": "paid",
                        "count": 8,
                        "percentage_of_total": 5.3
                    },
                    {
                        "status": "payment_failed",
                        "count": 4,
                        "percentage_of_total": 2.7
                    }
                ]
            }
        }


class TimelinePoint(BaseModel):
    """Punto en una línea de tiempo."""
    date: str = Field(..., description="Fecha en formato YYYY-MM-DD")
    order_count: int
    delivered_count: int = 0
    failed_count: int = 0
    revenue: float
    avg_order_value: float


class TimelineResponse(BaseModel):
    """Response para órdenes agrupadas por fecha."""
    start_date: str
    end_date: str
    total_orders: int
    timeline: List[TimelinePoint]

    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2026-05-01",
                "end_date": "2026-05-09",
                "total_orders": 150,
                "timeline": [
                    {
                        "date": "2026-05-09",
                        "order_count": 25,
                        "revenue": 416666.67,
                        "avg_order_value": 16666.67
                    },
                    {
                        "date": "2026-05-08",
                        "order_count": 20,
                        "revenue": 333333.33,
                        "avg_order_value": 16666.67
                    }
                ]
            }
        }


class ErrorResponse(BaseModel):
    """Response para errores."""
    error: str
    detail: Optional[str] = None
    status_code: int

    class Config:
        json_schema_extra = {
            "example": {
                "error": "No data available",
                "detail": "No orders found in database",
                "status_code": 404
            }
        }
