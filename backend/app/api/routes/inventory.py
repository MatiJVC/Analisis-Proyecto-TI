"""
Endpoints REST de consulta del módulo de Inventario (Grupo 5).

Expuestos para el proceso de carga inicial y conciliación periódica
del módulo de Analítica (Proyecto 9).

  GET /inventory/snapshot              →  Estado físico vs reservado (paginado)
  GET /inventory/locations/catalog     →  Catálogo de ubicaciones (filtrable)
  GET /inventory/products/thresholds   →  SKUs con niveles críticos

Todos los endpoints son de solo lectura (GET).
No requieren body; los filtros se pasan como query parameters.
Las respuestas incluyen siempre el campo `generated_at` (ISO 8601 UTC)
para que Analítica pueda detectar datos desactualizados en la conciliación.
"""

from __future__ import annotations

import logging
import math
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import require_any_role
from app.db import get_db
from app.schemas.inventory_query_schemas import (
    InventoryKPIsResponse,
    InventorySnapshotResponse,
    InventoryStockStatusResponse,
    LocationsCatalogResponse,
    LocationType,
    PaginationMeta,
    ProductsThresholdsResponse,
    StockStatus,
)
from app.services.inventory_query_service import (
    _now_utc_iso,
    get_inventory_kpis,
    get_inventory_snapshot,
    get_locations_catalog,
    get_products_thresholds,
    get_stock_status_summary,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/inventory",
    tags=["inventory — consulta analítica"],
    dependencies=[Depends(require_any_role(["admin", "analista", "inventory"]))],
    responses={
        400: {"description": "Parámetro de consulta inválido"},
        401: {"description": "Falta token Bearer o token inválido"},
        403: {"description": "El usuario no tiene rol suficiente"},
        500: {"description": "Error interno del servidor"},
    },
)


# ============================================================================
#  §0  GET /inventory/kpis
# ============================================================================

@router.get(
    "/kpis",
    response_model=InventoryKPIsResponse,
    status_code=status.HTTP_200_OK,
    summary="KPIs globales de inventario",
    description="""
Retorna los indicadores clave de inventario agregados para el dashboard de analítica.

- **total_skus**: total de SKUs únicos con stock registrado en ubicaciones activas.
- **warehouses_count**: número de bodegas (`WAREHOUSE`) activas.
- **low_stock_count**: SKUs cuyo stock disponible total (físico − reservado) está en o bajo el umbral crítico.
- **out_of_stock_count**: SKUs sin stock disponible en ninguna ubicación.
- **total_stock_value**: `0.0` — requiere `unit_price` por producto (pendiente del grupo de inventario).
- **turnover_rate**: `0.0` — requiere historial de movimientos vía eventos EDA (pendiente).
""",
)
async def get_kpis(db: Session = Depends(get_db)) -> InventoryKPIsResponse:
    try:
        kpis = get_inventory_kpis(db)
        return InventoryKPIsResponse(**kpis, generated_at=_now_utc_iso())
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error al obtener los KPIs de inventario")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener los KPIs de inventario",
        )


# ============================================================================
#  §0b GET /inventory/stock-status
# ============================================================================

@router.get(
    "/stock-status",
    response_model=InventoryStockStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Distribución de SKUs por estado de stock",
    description="""
Retorna cuántos SKUs se encuentran en cada estado de stock:

- **NORMAL**: stock disponible por encima del umbral crítico.
- **CRITICAL**: stock disponible en o bajo el umbral, pero mayor que cero.
- **OUT_OF_STOCK**: sin unidades disponibles en ninguna ubicación activa.

Los estados se calculan igual que en `/inventory/snapshot` para consistencia.
""",
)
async def get_stock_status(db: Session = Depends(get_db)) -> InventoryStockStatusResponse:
    try:
        data, total = get_stock_status_summary(db)
        return InventoryStockStatusResponse(
            data=data,
            total_skus=total,
            generated_at=_now_utc_iso(),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error al obtener el resumen de estado de stock")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener el resumen de estado de stock",
        )


# ============================================================================
#  §1  GET /inventory/snapshot
# ============================================================================

@router.get(
    "/snapshot",
    response_model=InventorySnapshotResponse,
    status_code=status.HTTP_200_OK,
    summary="Snapshot de inventario (saldo físico vs reservado)",
    description="""
Retorna el estado actual del inventario cruzando las tablas `inventory` y `locations`.

Cada fila representa un par **(SKU × ubicación)** con:
- `physical_stock`: unidades registradas físicamente en bodega.
- `reserved_stock`: unidades comprometidas en reservas activas (`status = 'active'`).
- `available_stock`: `physical_stock − reserved_stock` (mínimo 0).
- `stock_status`: clasificación derivada (`NORMAL` / `CRITICAL` / `OUT_OF_STOCK`).

**Uso recomendado por Analítica:**
- Carga inicial completa: `GET /inventory/snapshot?limit=500&offset=0` e iterar.
- Conciliación incremental: filtrar por `stock_status=CRITICAL` o `stock_status=OUT_OF_STOCK`.
- Drill-down por SKU: pasar `sku_id=SKU-PROD-001`.

**Paginación:** use `limit` (máx 500) y `offset` para navegar conjuntos grandes.
El campo `meta.total` indica el total de filas que coinciden con los filtros.
""",
)
async def get_snapshot(
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=500,
            description="Máximo de filas por respuesta (1–500). Por defecto: 100.",
        ),
    ] = 100,
    offset: Annotated[
        int,
        Query(ge=0, description="Filas a omitir desde el inicio (para paginación). Por defecto: 0."),
    ] = 0,
    sku_id: Annotated[
        Optional[str],
        Query(description="Filtrar por SKU exacto. Ej: `SKU-PROD-001`"),
    ] = None,
    location_id: Annotated[
        Optional[str],
        Query(description="Filtrar por UUID de ubicación (formato texto). Ej: `a3bb189e-...`"),
    ] = None,
    location_type: Annotated[
        Optional[LocationType],
        Query(description="Filtrar por tipo de ubicación: `WAREHOUSE`, `DISTRIBUTION_CENTER` o `RETAIL_POINT`"),
    ] = None,
    stock_status: Annotated[
        Optional[StockStatus],
        Query(description="Filtrar por estado de stock: `NORMAL`, `CRITICAL` o `OUT_OF_STOCK`"),
    ] = None,
    db: Session = Depends(get_db),
) -> InventorySnapshotResponse:

    try:
        rows, total = get_inventory_snapshot(
            db=db,
            sku_id=sku_id,
            location_id=location_id,
            location_type=location_type.value if location_type else None,
            stock_status=stock_status.value   if stock_status  else None,
            limit=limit,
            offset=offset,
        )

        pages    = math.ceil(total / limit) if total > 0 else 0
        has_next = (offset + limit) < total
        has_prev = offset > 0

        return InventorySnapshotResponse(
            data=rows,
            meta=PaginationMeta(
                total=total,
                limit=limit,
                offset=offset,
                pages=pages,
                has_next=has_next,
                has_prev=has_prev,
            ),
            generated_at=_now_utc_iso(),
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error al obtener el snapshot de inventario")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener el snapshot de inventario",
        )


# ============================================================================
#  §2  GET /locations/catalog
# ============================================================================

@router.get(
    "/locations/catalog",
    response_model=LocationsCatalogResponse,
    status_code=status.HTTP_200_OK,
    summary="Catálogo de ubicaciones físicas",
    description="""
Retorna la lista de todas las ubicaciones físicas del módulo de Inventario.

Filtros opcionales:
- `location_type`: devuelve solo bodegas (`WAREHOUSE`), centros de distribución
  (`DISTRIBUTION_CENTER`) o puntos de venta (`RETAIL_POINT`).
- `is_active`: `true` para solo ubicaciones operativas (recomendado).
- `city`: búsqueda parcial por ciudad (case-insensitive).

**Uso recomendado por Analítica:**
- Ejecutar una vez en la carga inicial para poblar `dim_locations`.
- Refrescar semanalmente o cuando se reciba el evento `location_created`.
""",
)
async def get_locations(
    location_type: Annotated[
        Optional[LocationType],
        Query(
            description="Filtrar por tipo: `WAREHOUSE`, `DISTRIBUTION_CENTER`, `RETAIL_POINT`.",
        ),
    ] = None,
    is_active: Annotated[
        Optional[bool],
        Query(description="Si se indica `true`, retorna solo ubicaciones operativas activas."),
    ] = None,
    city: Annotated[
        Optional[str],
        Query(min_length=2, max_length=100, description="Búsqueda parcial por nombre de ciudad."),
    ] = None,
    db: Session = Depends(get_db),
) -> LocationsCatalogResponse:

    try:
        rows = get_locations_catalog(
            db=db,
            location_type=location_type.value if location_type else None,
            is_active=is_active,
            city=city,
        )

        return LocationsCatalogResponse(
            data=rows,
            total=len(rows),
            generated_at=_now_utc_iso(),
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error al obtener el catálogo de ubicaciones")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener el catálogo de ubicaciones",
        )


# ============================================================================
#  §3  GET /products/thresholds
# ============================================================================

@router.get(
    "/products/thresholds",
    response_model=ProductsThresholdsResponse,
    status_code=status.HTTP_200_OK,
    summary="SKUs con niveles críticos de stock",
    description="""
Lista todos los SKUs con su `critical_threshold` configurado y el resumen
de stock agregado a través de **todas las ubicaciones activas**.

Los SKUs se ordenan priorizando los más críticos:
1. `is_out_of_stock = true` (sin stock en ninguna ubicación).
2. `is_below_threshold = true` (stock por debajo del umbral, pero > 0).
3. Resto ordenado alfabéticamente por `sku_id`.

Filtros opcionales:
- `sku_id`: búsqueda parcial por código SKU.
- `category`: filtrar por categoría exacta del producto.
- `below_threshold`: `true` para retornar solo SKUs en estado crítico o sin stock.

**Uso recomendado por Analítica:**
- Carga inicial del módulo de alertas de inventario.
- Conciliación diaria ejecutando `GET /products/thresholds?below_threshold=true`.
- La respuesta incluye `total_below_threshold` y `total_out_of_stock` para
  generar KPIs de resumen sin necesidad de iterar todos los registros.
""",
)
async def get_thresholds(
    sku_id: Annotated[
        Optional[str],
        Query(description="Búsqueda parcial por código SKU (case-insensitive). Ej: `PROD-007`"),
    ] = None,
    category: Annotated[
        Optional[str],
        Query(description="Filtrar por categoría exacta del producto. Ej: `Repuestos industriales`"),
    ] = None,
    below_threshold: Annotated[
        Optional[bool],
        Query(
            description=(
                "Si es `true`, retorna solo SKUs con `is_below_threshold = true` "
                "(incluye `is_out_of_stock`). Si es `false`, solo los que están sobre el umbral."
            )
        ),
    ] = None,
    db: Session = Depends(get_db),
) -> ProductsThresholdsResponse:

    try:
        rows = get_products_thresholds(
            db=db,
            sku_id=sku_id,
            category=category,
            below_threshold=below_threshold,
        )

        total_below   = sum(1 for r in rows if r.get("is_below_threshold"))
        total_out     = sum(1 for r in rows if r.get("is_out_of_stock"))

        return ProductsThresholdsResponse(
            data=rows,
            total=len(rows),
            total_below_threshold=total_below,
            total_out_of_stock=total_out,
            generated_at=_now_utc_iso(),
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error al obtener los umbrales de productos")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener los umbrales de productos",
        )
