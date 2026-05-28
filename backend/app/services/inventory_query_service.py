"""
Servicio de consulta para los endpoints de Inventario → Analítica.

Implementa las tres consultas SQL optimizadas que alimentan:
  - GET /inventory/snapshot
  - GET /locations/catalog
  - GET /products/thresholds

Diseño de las queries
─────────────────────
• Se usan consultas SQL nativas via SQLAlchemy text() para tener control
  explícito del plan de ejecución (JOINs, ORDER BY, LIMIT/OFFSET).
• Todos los parámetros se pasan con bindparams para prevenir inyección SQL.
• La paginación usa la técnica count + data en queries separadas para evitar
  el overhead de COUNT(*) OVER() en tablas con millones de filas.
• Los timestamps se formatean a ISO 8601 UTC directamente en SQL con
  to_char(...AT TIME ZONE 'UTC', ...) para consistencia con el módulo de Analítica.

Índices recomendados en la BD del Grupo 5 (Inventario)
───────────────────────────────────────────────────────
  CREATE INDEX CONCURRENTLY idx_inventory_sku_id      ON inventory (sku_id);
  CREATE INDEX CONCURRENTLY idx_inventory_location_id ON inventory (location_id);
  CREATE INDEX CONCURRENTLY idx_locations_type_active ON locations (location_type, is_active);
  CREATE INDEX CONCURRENTLY idx_products_sku          ON products   (sku_id);
  CREATE INDEX CONCURRENTLY idx_products_category     ON products   (category);
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Utilidad interna
# ---------------------------------------------------------------------------

def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_dict(row: Any) -> Dict[str, Any]:
    """Convierte un Row de SQLAlchemy a dict para Pydantic."""
    return dict(row._mapping)


# ============================================================================
#  §1  GET /inventory/snapshot
#      Estado físico vs reservado, cruzando inventory × locations
# ============================================================================

_SQL_SNAPSHOT_DATA = text("""
    SELECT *
    FROM (
        SELECT
            inv.sku_id,
            inv.location_id::TEXT                                           AS location_id,
            loc.code                                                        AS location_code,
            loc.name                                                        AS location_name,
            loc.location_type,
            loc.city,
            COALESCE(loc.country, 'Chile')                                 AS country,
            inv.physical_stock,
            inv.reserved_stock,
            GREATEST(inv.physical_stock - inv.reserved_stock, 0)           AS available_stock,
            inv.critical_threshold,
            CASE
                WHEN GREATEST(inv.physical_stock - inv.reserved_stock, 0) = 0
                     THEN 'OUT_OF_STOCK'
                WHEN GREATEST(inv.physical_stock - inv.reserved_stock, 0)
                     <= inv.critical_threshold
                     THEN 'CRITICAL'
                ELSE 'NORMAL'
            END                                                             AS stock_status,
            to_char(
                inv.last_movement_at AT TIME ZONE 'UTC',
                'YYYY-MM-DD"T"HH24:MI:SS"Z"'
            )                                                               AS last_movement_at,
            to_char(
                inv.updated_at AT TIME ZONE 'UTC',
                'YYYY-MM-DD"T"HH24:MI:SS"Z"'
            )                                                               AS updated_at
        FROM      inventory  inv
        INNER JOIN locations loc ON loc.id = inv.location_id
        WHERE     loc.is_active = TRUE
          AND     (:sku_id        IS NULL  OR inv.sku_id        = :sku_id)
          AND     (:location_id   IS NULL  OR inv.location_id   = :location_id::UUID)
          AND     (:location_type IS NULL  OR loc.location_type = :location_type)
    ) base
    WHERE :stock_status IS NULL
       OR base.stock_status = :stock_status
    ORDER BY base.sku_id         ASC,
             base.location_type  ASC,
             base.location_code  ASC
    LIMIT  :limit
    OFFSET :offset
""")

_SQL_SNAPSHOT_COUNT = text("""
    SELECT COUNT(*)
    FROM (
        SELECT 1
        FROM      inventory  inv
        INNER JOIN locations loc ON loc.id = inv.location_id
        WHERE     loc.is_active = TRUE
          AND     (:sku_id        IS NULL  OR inv.sku_id        = :sku_id)
          AND     (:location_id   IS NULL  OR inv.location_id   = :location_id::UUID)
          AND     (:location_type IS NULL  OR loc.location_type = :location_type)
          AND     (
                    :stock_status IS NULL
                    OR (
                        :stock_status = 'OUT_OF_STOCK'
                        AND GREATEST(inv.physical_stock - inv.reserved_stock, 0) = 0
                    )
                    OR (
                        :stock_status = 'CRITICAL'
                        AND GREATEST(inv.physical_stock - inv.reserved_stock, 0) > 0
                        AND GREATEST(inv.physical_stock - inv.reserved_stock, 0) <= inv.critical_threshold
                    )
                    OR (
                        :stock_status = 'NORMAL'
                        AND GREATEST(inv.physical_stock - inv.reserved_stock, 0) > inv.critical_threshold
                    )
                  )
    ) sub
""")


def get_inventory_snapshot(
    db:            Session,
    sku_id:        Optional[str],
    location_id:   Optional[str],
    location_type: Optional[str],
    stock_status:  Optional[str],
    limit:         int,
    offset:        int,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Retorna (filas, total) del estado actual de inventario con paginación.

    Estrategia de paginación:
      1. Ejecutar el COUNT con los mismos filtros (query separada, sin LIMIT).
      2. Ejecutar la query de datos con LIMIT/OFFSET.
    Esto evita el costoso COUNT(*) OVER() en tablas de millones de filas.
    """
    params = {
        "sku_id":        sku_id        or None,
        "location_id":   location_id   or None,
        "location_type": location_type or None,
        "stock_status":  stock_status  or None,
        "limit":         limit,
        "offset":        offset,
    }

    total: int = db.execute(_SQL_SNAPSHOT_COUNT, params).scalar_one()
    rows         = db.execute(_SQL_SNAPSHOT_DATA,  params).fetchall()

    return [_row_to_dict(r) for r in rows], total


# ============================================================================
#  §2  GET /locations/catalog
#      Catálogo de ubicaciones con filtro opcional por tipo
# ============================================================================

_SQL_LOCATIONS = text("""
    SELECT
        id::TEXT                                                        AS location_id,
        code                                                            AS location_code,
        name                                                            AS location_name,
        location_type,
        address,
        city,
        COALESCE(country, 'Chile')                                     AS country,
        is_active,
        to_char(
            created_at AT TIME ZONE 'UTC',
            'YYYY-MM-DD"T"HH24:MI:SS"Z"'
        )                                                               AS created_at
    FROM  locations
    WHERE (:location_type IS NULL  OR location_type = :location_type)
      AND (:is_active     IS NULL  OR is_active     = :is_active)
      AND (:city          IS NULL  OR city ILIKE '%' || :city || '%')
    ORDER BY
        CASE location_type
            WHEN 'WAREHOUSE'           THEN 1
            WHEN 'DISTRIBUTION_CENTER' THEN 2
            WHEN 'RETAIL_POINT'        THEN 3
            ELSE                            4
        END,
        name ASC
""")


def get_locations_catalog(
    db:            Session,
    location_type: Optional[str],
    is_active:     Optional[bool],
    city:          Optional[str],
) -> List[Dict[str, Any]]:
    """
    Retorna el catálogo de ubicaciones con filtros opcionales.
    No requiere paginación ya que el número de ubicaciones es acotado
    (máximo cientos, no millones).
    """
    params = {
        "location_type": location_type or None,
        "is_active":     is_active,
        "city":          city or None,
    }
    rows = db.execute(_SQL_LOCATIONS, params).fetchall()
    return [_row_to_dict(r) for r in rows]


# ============================================================================
#  §3  GET /products/thresholds
#      SKUs con niveles críticos, agregados a través de todas las ubicaciones
# ============================================================================

_SQL_THRESHOLDS = text("""
    WITH stock_por_sku AS (
        SELECT
            inv.sku_id,
            COALESCE(p.name,     inv.sku_id)       AS product_name,
            COALESCE(p.category, 'Sin categoría')  AS category,
            COALESCE(p.unit,     'unidad')          AS unit,
            MAX(inv.critical_threshold)             AS critical_threshold,
            SUM(inv.physical_stock)                 AS total_physical_stock,
            SUM(inv.reserved_stock)                 AS total_reserved_stock,
            SUM(
                GREATEST(inv.physical_stock - inv.reserved_stock, 0)
            )                                       AS total_available_stock,
            COUNT(DISTINCT inv.location_id)         AS locations_count,
            MAX(
                to_char(
                    inv.updated_at AT TIME ZONE 'UTC',
                    'YYYY-MM-DD"T"HH24:MI:SS"Z"'
                )
            )                                       AS last_updated
        FROM  inventory inv
        LEFT  JOIN products p ON p.sku_id = inv.sku_id
        WHERE (:sku_id    IS NULL  OR inv.sku_id  ILIKE '%' || :sku_id    || '%')
          AND (:category  IS NULL  OR p.category  =           :category)
        GROUP BY inv.sku_id, p.name, p.category, p.unit
    )
    SELECT
        sku_id,
        product_name,
        category,
        unit,
        critical_threshold,
        total_physical_stock,
        total_reserved_stock,
        total_available_stock,
        locations_count,
        (total_available_stock <= critical_threshold) AS is_below_threshold,
        (total_available_stock = 0)                   AS is_out_of_stock,
        last_updated
    FROM stock_por_sku
    WHERE :below_threshold IS NULL
       OR (
           :below_threshold = TRUE
           AND total_available_stock <= critical_threshold
       )
       OR (
           :below_threshold = FALSE
           AND total_available_stock >  critical_threshold
       )
    ORDER BY
        (total_available_stock <= critical_threshold) DESC,  -- críticos primero
        (total_available_stock = 0)                  DESC,  -- sin stock al frente
        sku_id                                        ASC
""")


def get_products_thresholds(
    db:              Session,
    sku_id:          Optional[str],
    category:        Optional[str],
    below_threshold: Optional[bool],
) -> List[Dict[str, Any]]:
    """
    Retorna los SKUs con sus niveles críticos agregados.
    Los productos con is_below_threshold=True o is_out_of_stock=True
    aparecen primero para facilitar el proceso de conciliación en Analítica.
    """
    params = {
        "sku_id":          sku_id    or None,
        "category":        category  or None,
        "below_threshold": below_threshold,
    }
    rows = db.execute(_SQL_THRESHOLDS, params).fetchall()
    return [_row_to_dict(r) for r in rows]
