"""
Schemas Pydantic v2 para los endpoints de consulta del módulo de Inventario.

Estos modelos definen las respuestas de:
  GET /inventory/snapshot   →  InventorySnapshotResponse
  GET /locations/catalog    →  LocationsCatalogResponse
  GET /products/thresholds  →  ProductsThresholdsResponse

Consumidos por el módulo de Analítica (Proyecto 9) para carga inicial
y procesos de conciliación periódica.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums compartidos
# ---------------------------------------------------------------------------

class LocationType(str, Enum):
    WAREHOUSE           = "WAREHOUSE"
    DISTRIBUTION_CENTER = "DISTRIBUTION_CENTER"
    RETAIL_POINT        = "RETAIL_POINT"


class StockStatus(str, Enum):
    NORMAL       = "NORMAL"        # available_stock > critical_threshold
    CRITICAL     = "CRITICAL"      # 0 < available_stock <= critical_threshold
    OUT_OF_STOCK = "OUT_OF_STOCK"  # available_stock == 0


# ============================================================================
#  §1  GET /inventory/snapshot
# ============================================================================

class InventorySnapshotRow(BaseModel):
    """
    Fila del snapshot de inventario: estado físico vs reservado por SKU × ubicación.
    """
    sku_id:           str          = Field(..., description="Código SKU del producto")
    location_id:      str          = Field(..., description="UUID de la ubicación (texto)")
    location_code:    str          = Field(..., description="Código corto de la ubicación")
    location_name:    str          = Field(..., description="Nombre descriptivo de la ubicación")
    location_type:    LocationType = Field(..., description="Tipo de ubicación")
    city:             Optional[str]= Field(None, description="Ciudad de la ubicación")
    country:          str          = Field(..., description="País de la ubicación")

    physical_stock:   int          = Field(..., ge=0, description="Stock físico total en bodega")
    reserved_stock:   int          = Field(..., ge=0, description="Unidades comprometidas en reservas activas")
    available_stock:  int          = Field(..., ge=0, description="Unidades disponibles para nuevas reservas (físico − reservado)")
    critical_threshold: int        = Field(..., ge=0, description="Umbral mínimo configurado que dispara alertas")
    stock_status:     StockStatus  = Field(..., description="Estado derivado del nivel de stock")

    last_movement_at: Optional[str]= Field(None, description="Último movimiento registrado (ISO 8601 UTC)")
    updated_at:       str          = Field(..., description="Última actualización del registro (ISO 8601 UTC)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "sku_id":             "SKU-PROD-001",
                "location_id":        "a3bb189e-8bf9-3888-9912-ace4e6543002",
                "location_code":      "BODEGA-SCL-01",
                "location_name":      "Bodega Central Santiago",
                "location_type":      "WAREHOUSE",
                "city":               "Santiago",
                "country":            "Chile",
                "physical_stock":     350,
                "reserved_stock":     80,
                "available_stock":    270,
                "critical_threshold": 50,
                "stock_status":       "NORMAL",
                "last_movement_at":   "2026-05-28T08:30:00Z",
                "updated_at":         "2026-05-28T09:00:00Z",
            }
        }
    }


class PaginationMeta(BaseModel):
    """Metadatos de paginación incluidos en respuestas con conjuntos grandes de datos."""
    total:    int  = Field(..., description="Total de filas que coinciden con los filtros aplicados")
    limit:    int  = Field(..., description="Máximo de filas por página")
    offset:   int  = Field(..., description="Número de filas omitidas desde el inicio")
    pages:    int  = Field(..., description="Total de páginas disponibles")
    has_next: bool = Field(..., description="Indica si existe una página siguiente")
    has_prev: bool = Field(..., description="Indica si existe una página anterior")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 1240,
                "limit": 100,
                "offset": 0,
                "pages": 13,
                "has_next": True,
                "has_prev": False,
            }
        }
    }


class InventorySnapshotResponse(BaseModel):
    """Respuesta paginada de GET /inventory/snapshot."""
    data:         List[InventorySnapshotRow] = Field(..., description="Filas de inventario")
    meta:         PaginationMeta             = Field(..., description="Información de paginación")
    generated_at: str                        = Field(..., description="Timestamp de generación de la respuesta (ISO 8601 UTC)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "data": [
                    {
                        "sku_id":             "SKU-PROD-001",
                        "location_id":        "a3bb189e-8bf9-3888-9912-ace4e6543002",
                        "location_code":      "BODEGA-SCL-01",
                        "location_name":      "Bodega Central Santiago",
                        "location_type":      "WAREHOUSE",
                        "city":               "Santiago",
                        "country":            "Chile",
                        "physical_stock":     350,
                        "reserved_stock":     80,
                        "available_stock":    270,
                        "critical_threshold": 50,
                        "stock_status":       "NORMAL",
                        "last_movement_at":   "2026-05-28T08:30:00Z",
                        "updated_at":         "2026-05-28T09:00:00Z",
                    },
                    {
                        "sku_id":             "SKU-PROD-007",
                        "location_id":        "b5cc290f-9ca0-4999-aa23-bdf7f7654113",
                        "location_code":      "DC-NORTE-01",
                        "location_name":      "Centro Distribución Norte",
                        "location_type":      "DISTRIBUTION_CENTER",
                        "city":               "Antofagasta",
                        "country":            "Chile",
                        "physical_stock":     12,
                        "reserved_stock":     8,
                        "available_stock":    4,
                        "critical_threshold": 10,
                        "stock_status":       "CRITICAL",
                        "last_movement_at":   "2026-05-27T16:45:00Z",
                        "updated_at":         "2026-05-27T17:00:00Z",
                    },
                ],
                "meta": {
                    "total": 1240,
                    "limit": 100,
                    "offset": 0,
                    "pages": 13,
                    "has_next": True,
                    "has_prev": False,
                },
                "generated_at": "2026-05-28T10:00:00Z",
            }
        }
    }


# ============================================================================
#  §2  GET /locations/catalog
# ============================================================================

class LocationRow(BaseModel):
    """Registro de una ubicación física del módulo de Inventario."""
    location_id:   str          = Field(..., description="UUID de la ubicación (texto)")
    location_code: str          = Field(..., description="Código único corto de la ubicación")
    location_name: str          = Field(..., description="Nombre descriptivo")
    location_type: LocationType = Field(..., description="Clasificación del punto de almacenamiento")
    address:       Optional[str]= Field(None, description="Dirección física completa")
    city:          Optional[str]= Field(None, description="Ciudad")
    country:       str          = Field(..., description="País")
    is_active:     bool         = Field(..., description="Si la ubicación está operativa")
    created_at:    str          = Field(..., description="Fecha de creación (ISO 8601 UTC)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "location_id":   "a3bb189e-8bf9-3888-9912-ace4e6543002",
                "location_code": "BODEGA-SCL-01",
                "location_name": "Bodega Central Santiago",
                "location_type": "WAREHOUSE",
                "address":       "Av. Industrial 4500, Quilicura",
                "city":          "Santiago",
                "country":       "Chile",
                "is_active":     True,
                "created_at":    "2025-01-15T08:00:00Z",
            }
        }
    }


class LocationsCatalogResponse(BaseModel):
    """Respuesta de GET /locations/catalog."""
    data:         List[LocationRow] = Field(..., description="Lista de ubicaciones")
    total:        int               = Field(..., description="Total de ubicaciones retornadas")
    generated_at: str               = Field(..., description="Timestamp de generación (ISO 8601 UTC)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "data": [
                    {
                        "location_id":   "a3bb189e-8bf9-3888-9912-ace4e6543002",
                        "location_code": "BODEGA-SCL-01",
                        "location_name": "Bodega Central Santiago",
                        "location_type": "WAREHOUSE",
                        "address":       "Av. Industrial 4500, Quilicura",
                        "city":          "Santiago",
                        "country":       "Chile",
                        "is_active":     True,
                        "created_at":    "2025-01-15T08:00:00Z",
                    },
                    {
                        "location_id":   "b5cc290f-9ca0-4999-aa23-bdf7f7654113",
                        "location_code": "DC-NORTE-01",
                        "location_name": "Centro Distribución Norte",
                        "location_type": "DISTRIBUTION_CENTER",
                        "address":       "Ruta 1 Norte Km 12",
                        "city":          "Antofagasta",
                        "country":       "Chile",
                        "is_active":     True,
                        "created_at":    "2025-03-10T10:00:00Z",
                    },
                    {
                        "location_id":   "c7dd401g-0db1-5aaa-bb34-ceg8g8765224",
                        "location_code": "RETAIL-RM-05",
                        "location_name": "Tienda Providencia",
                        "location_type": "RETAIL_POINT",
                        "address":       "Av. Providencia 1234, Local 5",
                        "city":          "Santiago",
                        "country":       "Chile",
                        "is_active":     True,
                        "created_at":    "2025-06-01T09:30:00Z",
                    },
                ],
                "total": 3,
                "generated_at": "2026-05-28T10:00:00Z",
            }
        }
    }


# ============================================================================
#  §3  GET /products/thresholds
# ============================================================================

class ProductThresholdRow(BaseModel):
    """
    Estado crítico de un SKU agregado a través de todas sus ubicaciones activas.
    El campo critical_threshold es el máximo configurado entre todas las ubicaciones
    del SKU (refleja el nivel de alerta más conservador del sistema).
    """
    sku_id:               str  = Field(..., description="Código SKU del producto")
    product_name:         str  = Field(..., description="Nombre descriptivo del producto")
    category:             str  = Field(..., description="Categoría del producto")
    unit:                 str  = Field(..., description="Unidad de medida (ej: 'unidad', 'kg', 'caja')")
    critical_threshold:   int  = Field(..., ge=0, description="Umbral crítico máximo entre todas las ubicaciones del SKU")
    total_physical_stock: int  = Field(..., ge=0, description="Suma del stock físico en todas las ubicaciones")
    total_reserved_stock: int  = Field(..., ge=0, description="Suma de stock reservado en todas las ubicaciones")
    total_available_stock:int  = Field(..., ge=0, description="Stock disponible agregado (físico − reservado)")
    locations_count:      int  = Field(..., ge=0, description="Número de ubicaciones activas con este SKU")
    is_below_threshold:   bool = Field(..., description="True si el stock disponible total está en o bajo el umbral crítico")
    is_out_of_stock:      bool = Field(..., description="True si el stock disponible total es cero")
    last_updated:         str  = Field(..., description="Última actualización del inventario de este SKU (ISO 8601 UTC)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "sku_id":               "SKU-PROD-007",
                "product_name":         "Válvula de presión tipo B",
                "category":             "Repuestos industriales",
                "unit":                 "unidad",
                "critical_threshold":   10,
                "total_physical_stock": 12,
                "total_reserved_stock": 8,
                "total_available_stock":4,
                "locations_count":      2,
                "is_below_threshold":   True,
                "is_out_of_stock":      False,
                "last_updated":         "2026-05-27T17:00:00Z",
            }
        }
    }


class ProductsThresholdsResponse(BaseModel):
    """Respuesta de GET /products/thresholds."""
    data:                  List[ProductThresholdRow] = Field(..., description="Lista de SKUs con sus niveles críticos")
    total:                 int                       = Field(..., description="Total de SKUs retornados")
    total_below_threshold: int                       = Field(..., description="Cantidad de SKUs en estado CRITICAL o OUT_OF_STOCK")
    total_out_of_stock:    int                       = Field(..., description="Cantidad de SKUs completamente sin stock")
    generated_at:          str                       = Field(..., description="Timestamp de generación (ISO 8601 UTC)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "data": [
                    {
                        "sku_id":               "SKU-PROD-007",
                        "product_name":         "Válvula de presión tipo B",
                        "category":             "Repuestos industriales",
                        "unit":                 "unidad",
                        "critical_threshold":   10,
                        "total_physical_stock": 12,
                        "total_reserved_stock": 8,
                        "total_available_stock":4,
                        "locations_count":      2,
                        "is_below_threshold":   True,
                        "is_out_of_stock":      False,
                        "last_updated":         "2026-05-27T17:00:00Z",
                    },
                    {
                        "sku_id":               "SKU-PROD-023",
                        "product_name":         "Sensor de temperatura T200",
                        "category":             "Sensores",
                        "unit":                 "unidad",
                        "critical_threshold":   5,
                        "total_physical_stock": 0,
                        "total_reserved_stock": 0,
                        "total_available_stock":0,
                        "locations_count":      1,
                        "is_below_threshold":   True,
                        "is_out_of_stock":      True,
                        "last_updated":         "2026-05-28T06:15:00Z",
                    },
                ],
                "total": 2,
                "total_below_threshold": 2,
                "total_out_of_stock": 1,
                "generated_at": "2026-05-28T10:00:00Z",
            }
        }
    }
