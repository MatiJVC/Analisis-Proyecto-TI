from pydantic import BaseModel, Field


class KPIResponse(BaseModel):
    kpi: str = Field(..., description="Nombre del KPI")
    value: float = Field(..., ge=0.0, le=1.0, description="Valor del KPI (0.0 a 1.0)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "kpi": "renewal_rate",
                "value": 0.82
            }
        }


class SubscriptionStats(BaseModel):
    total: int = Field(..., ge=0, description="Total de suscripciones")
    active: int = Field(..., ge=0, description="Suscripciones activas")
    renewed: int = Field(..., ge=0, description="Suscripciones renovadas")
    with_billing_success: int = Field(..., ge=0, description="Suscripciones con facturación exitosa")
    with_auto_service: int = Field(..., ge=0, description="Suscripciones con auto-servicio")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total": 100,
                "active": 95,
                "renewed": 82,
                "with_billing_success": 97,
                "with_auto_service": 67
            }
        }


class SubscriptionSummary(BaseModel):
    renewal_rate: float = Field(..., ge=0.0, le=1.0, description="Tasa de renovación")
    error_rate: float = Field(..., ge=0.0, le=1.0, description="Tasa de errores en facturación")
    auto_service_rate: float = Field(..., ge=0.0, le=1.0, description="Tasa de auto-servicio")
    stats: SubscriptionStats = Field(..., description="Estadísticas detalladas")
    
    class Config:
        json_schema_extra = {
            "example": {
                "renewal_rate": 0.82,
                "error_rate": 0.03,
                "auto_service_rate": 0.67,
                "stats": {
                    "total": 100,
                    "active": 95,
                    "renewed": 82,
                    "with_billing_success": 97,
                    "with_auto_service": 67
                }
            }
        }
