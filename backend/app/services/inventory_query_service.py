from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_dict(row: Any) -> Dict[str, Any]:
    return dict(row._mapping)


# ============================================================================
#  §1  GET /inventory/snapshot
#      Estado por (sku_id × location_id). El stock físico se calcula desde
#      fact_inventory_movements (received − dispatched + adjusted − transfer);
#      si el par no tiene movimientos, cae al current_stock de la última alerta.
#      El universo de filas es (movimientos ∪ alertas), enriquecido con
#      dim_locations. reserved_stock se deriva de las reservas menos despachos.
# ============================================================================

# CTEs base compartidos por snapshot, KPIs y stock-status. Definen el stock
# físico por (sku_id × location_id) calculado desde los movimientos, con
# fallback al current_stock de la última alerta, sobre el universo de pares
# (movimientos ∪ alertas). Cada endpoint agrega/formatea sobre stock_per_location.
_STOCK_BASE_CTES = """
    WITH physical_from_movements AS (
        SELECT
            sku_id,
            location_id,
            (
                  COALESCE(SUM(quantity) FILTER (WHERE event_type = 'stock_received'), 0)
                - COALESCE(SUM(quantity) FILTER (WHERE event_type = 'stock_dispatched'), 0)
                + COALESCE(SUM(quantity) FILTER (WHERE event_type = 'stock_adjusted'), 0)
                - COALESCE(SUM(quantity) FILTER (WHERE event_type = 'stock_transfer_initiated'), 0)
            ) AS physical_stock,
            MAX(movement_at) AS last_movement_at
        FROM fact_inventory_movements
        WHERE location_id IS NOT NULL
        GROUP BY sku_id, location_id
    ),
    net_reservations AS (
        SELECT
            sku_id,
            location_id,
            GREATEST(0, COALESCE(SUM(quantity) FILTER (
                WHERE event_type = 'stock_reserved'
            ), 0) - COALESCE(SUM(quantity) FILTER (
                WHERE event_type IN ('stock_dispatched', 'stock_released', 'reservation_cancelled')
                AND order_id IS NOT NULL
            ), 0)) AS reserved_stock
        FROM fact_inventory_movements
        WHERE event_type IN ('stock_reserved', 'stock_dispatched', 'stock_released', 'reservation_cancelled')
        GROUP BY sku_id, location_id
    ),
    latest_alert AS (
        SELECT DISTINCT ON (sku_id, location_id)
            sku_id,
            location_id,
            current_stock,
            threshold_limite,
            is_stock_out,
            alert_at
        FROM fact_inventory_alerts
        WHERE location_id IS NOT NULL
        ORDER BY sku_id, location_id, alert_at DESC
    ),
    universe AS (
        SELECT sku_id, location_id FROM physical_from_movements
        UNION
        SELECT sku_id, location_id FROM latest_alert
    ),
    stock_per_location AS (
        SELECT
            u.sku_id,
            u.location_id,
            COALESCE(m.physical_stock, la.current_stock, 0)  AS physical_stock,
            COALESCE(r.reserved_stock, 0)                    AS reserved_stock,
            GREATEST(0, COALESCE(m.physical_stock, la.current_stock, 0)
                        - COALESCE(r.reserved_stock, 0))     AS available_stock,
            COALESCE(la.threshold_limite, 0)                 AS critical_threshold,
            COALESCE(la.is_stock_out, FALSE)                 AS is_stock_out,
            CASE
                WHEN COALESCE(la.is_stock_out, FALSE)
                     OR COALESCE(m.physical_stock, la.current_stock, 0) = 0 THEN 'OUT_OF_STOCK'
                WHEN COALESCE(m.physical_stock, la.current_stock, 0)
                     <= COALESCE(la.threshold_limite, 0)                    THEN 'CRITICAL'
                ELSE                                                             'NORMAL'
            END                                              AS stock_status,
            m.last_movement_at                               AS last_movement_at,
            la.alert_at                                      AS alert_at
        FROM universe u
        LEFT JOIN physical_from_movements m USING (sku_id, location_id)
        LEFT JOIN net_reservations       r USING (sku_id, location_id)
        LEFT JOIN latest_alert          la USING (sku_id, location_id)
    )
"""

# snapshot_rows enriquece stock_per_location con dim_locations y formatea fechas.
_SNAPSHOT_ROWS_CTE = """
    , snapshot_rows AS (
        SELECT
            s.sku_id,
            s.location_id,
            s.location_id                                    AS location_code,
            COALESCE(dl.location_name, s.location_id)        AS location_name,
            COALESCE(dl.location_type, 'WAREHOUSE')          AS location_type,
            dl.city,
            'Chile'                                          AS country,
            s.physical_stock,
            s.reserved_stock,
            s.available_stock,
            s.critical_threshold,
            s.stock_status,
            to_char(COALESCE(s.last_movement_at, s.alert_at),
                    'YYYY-MM-DD"T"HH24:MI:SS"Z"')            AS last_movement_at,
            to_char(COALESCE(s.alert_at, s.last_movement_at),
                    'YYYY-MM-DD"T"HH24:MI:SS"Z"')            AS updated_at
        FROM stock_per_location s
        LEFT JOIN dim_locations dl ON dl.location_id = s.location_id
    )
"""


def get_inventory_snapshot(
    db:            Session,
    sku_id:        Optional[str],
    location_id:   Optional[str],
    location_type: Optional[str],
    stock_status:  Optional[str],
    limit:         int,
    offset:        int,
) -> Tuple[List[Dict[str, Any]], int]:
    conditions = []
    params: Dict[str, Any] = {"limit": limit, "offset": offset}

    if sku_id:
        conditions.append("sku_id = :sku_id")
        params["sku_id"] = sku_id
    if location_id:
        conditions.append("location_id = :location_id")
        params["location_id"] = location_id
    if stock_status:
        conditions.append("stock_status = :stock_status")
        params["stock_status"] = stock_status

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    base = _STOCK_BASE_CTES + _SNAPSHOT_ROWS_CTE
    data_sql = (
        base
        + f" SELECT * FROM snapshot_rows {where_clause} "
        + "ORDER BY sku_id ASC, location_id ASC LIMIT :limit OFFSET :offset"
    )
    count_sql = base + f" SELECT COUNT(*) FROM snapshot_rows {where_clause}"

    total = db.execute(text(count_sql), params).scalar_one()
    rows = db.execute(text(data_sql), params).fetchall()
    return [_row_to_dict(r) for r in rows], int(total)


# ============================================================================
#  §2  GET /locations/catalog
#      Ubicaciones desde fact_inventory_alerts enriquecidas con dim_locations
# ============================================================================

_SQL_LOCATIONS = text("""
    WITH location_ids AS (
        SELECT DISTINCT location_id
        FROM fact_inventory_alerts
        WHERE location_id IS NOT NULL
    )
    SELECT
        li.location_id,
        li.location_id                                                      AS location_code,
        COALESCE(dl.location_name, li.location_id)                          AS location_name,
        COALESCE(dl.location_type, 'WAREHOUSE')                             AS location_type,
        dl.address,
        dl.city,
        'Chile'                                                             AS country,
        TRUE                                                                AS is_active,
        to_char(MIN(fa.ingested_at), 'YYYY-MM-DD"T"HH24:MI:SS"Z"')        AS created_at
    FROM location_ids li
    LEFT JOIN dim_locations dl ON dl.location_id = li.location_id
    LEFT JOIN fact_inventory_alerts fa ON fa.location_id = li.location_id
    WHERE (CAST(:location_type AS TEXT) IS NULL
           OR COALESCE(dl.location_type, 'WAREHOUSE') = CAST(:location_type AS TEXT))
    AND   (CAST(:is_active AS BOOLEAN) IS NULL OR CAST(:is_active AS BOOLEAN) = TRUE)
    AND   (CAST(:city AS TEXT) IS NULL OR dl.city = CAST(:city AS TEXT))
    GROUP BY li.location_id, dl.location_name, dl.location_type, dl.address, dl.city
    ORDER BY li.location_id
""")


def get_locations_catalog(
    db:            Session,
    location_type: Optional[str],
    is_active:     Optional[bool],
    city:          Optional[str],
) -> List[Dict[str, Any]]:
    params = {
        "location_type": location_type or None,
        "is_active":     is_active,
        "city":          city or None,
    }
    try:
        rows = db.execute(_SQL_LOCATIONS, params).fetchall()
        return [_row_to_dict(r) for r in rows]
    except ProgrammingError:
        db.rollback()
        return []


# ============================================================================
#  §3  GET /products/thresholds
#      Agrega por sku_id con metadata real de dim_products y reserved_stock
# ============================================================================

_SQL_THRESHOLDS = text("""
    WITH latest_per_location AS (
        SELECT DISTINCT ON (sku_id, location_id)
            sku_id,
            location_id,
            current_stock,
            threshold_limite,
            alert_at
        FROM fact_inventory_alerts
        ORDER BY sku_id, location_id, alert_at DESC
    ),
    net_reservations AS (
        SELECT
            sku_id,
            GREATEST(0,
                COALESCE(SUM(quantity) FILTER (
                    WHERE event_type = 'stock_reserved'
                ), 0)
                -
                COALESCE(SUM(quantity) FILTER (
                    WHERE event_type IN ('stock_dispatched', 'stock_released', 'reservation_cancelled')
                    AND order_id IS NOT NULL
                ), 0)
            ) AS reserved_stock
        FROM fact_inventory_movements
        WHERE event_type IN (
            'stock_reserved', 'stock_dispatched',
            'stock_released', 'reservation_cancelled'
        )
        GROUP BY sku_id
    ),
    stock_por_sku AS (
        SELECT
            l.sku_id,
            COALESCE(p.product_name, l.sku_id)                             AS product_name,
            COALESCE(p.category,     'Sin categoría')                      AS category,
            COALESCE(p.unit,         'unidad')                             AS unit,
            MAX(l.threshold_limite)                                        AS critical_threshold,
            SUM(l.current_stock)                                           AS total_physical_stock,
            COALESCE(MAX(r.reserved_stock), 0)                             AS total_reserved_stock,
            GREATEST(0, SUM(l.current_stock) - COALESCE(MAX(r.reserved_stock), 0))
                                                                           AS total_available_stock,
            COUNT(DISTINCT l.location_id)                                  AS locations_count,
            to_char(MAX(l.alert_at), 'YYYY-MM-DD"T"HH24:MI:SS"Z"')       AS last_updated
        FROM latest_per_location l
        LEFT JOIN dim_products p ON p.sku_id = l.sku_id
        LEFT JOIN net_reservations r ON r.sku_id = l.sku_id
        WHERE (CAST(:sku_id AS TEXT) IS NULL
               OR l.sku_id ILIKE '%' || CAST(:sku_id AS TEXT) || '%')
        GROUP BY l.sku_id, p.product_name, p.category, p.unit
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
        (total_available_stock <= critical_threshold)                       AS is_below_threshold,
        (total_available_stock = 0)                                         AS is_out_of_stock,
        last_updated
    FROM stock_por_sku
    WHERE CAST(:below_threshold AS BOOLEAN) IS NULL
    OR (CAST(:below_threshold AS BOOLEAN) = TRUE  AND total_available_stock <= critical_threshold)
    OR (CAST(:below_threshold AS BOOLEAN) = FALSE AND total_available_stock >  critical_threshold)
    ORDER BY
        (total_available_stock = 0)              DESC,
        (total_available_stock <= critical_threshold) DESC,
        sku_id                                   ASC
""")


def get_products_thresholds(
    db:              Session,
    sku_id:          Optional[str],
    category:        Optional[str],
    below_threshold: Optional[bool],
) -> List[Dict[str, Any]]:
    params = {
        "sku_id":          sku_id or None,
        "below_threshold": below_threshold,
    }
    try:
        rows = db.execute(_SQL_THRESHOLDS, params).fetchall()
        return [_row_to_dict(r) for r in rows]
    except ProgrammingError:
        db.rollback()
        return []


# ============================================================================
#  §4  GET /inventory/kpis
#      total_stock_value desde dim_products × stock actual
#      turnover_rate    desde fact_inventory_movements
# ============================================================================

_SQL_KPI_SKUS = text(_STOCK_BASE_CTES + """
    , per_sku AS (
        SELECT
            spl.sku_id,
            SUM(spl.physical_stock)                                       AS total_available,
            SUM(spl.physical_stock * COALESCE(p.unit_price, 0::numeric))  AS stock_value,
            MAX(spl.critical_threshold)                                   AS threshold
        FROM stock_per_location spl
        LEFT JOIN dim_products p ON p.sku_id = spl.sku_id
        GROUP BY spl.sku_id
    )
    SELECT
        COUNT(*)                                              AS total_skus,
        COALESCE(SUM(stock_value), 0)                         AS total_stock_value,
        COUNT(*) FILTER (WHERE total_available <= threshold)  AS low_stock_count,
        COUNT(*) FILTER (WHERE total_available = 0)           AS out_of_stock_count
    FROM per_sku
""")

_SQL_KPI_WAREHOUSES = text(_STOCK_BASE_CTES + """
    SELECT COUNT(DISTINCT location_id) AS warehouses_count
    FROM stock_per_location
""")

_SQL_KPI_TURNOVER = text(_STOCK_BASE_CTES + """
    , dispatched AS (
        SELECT COALESCE(SUM(quantity), 0)::float AS total_dispatched
        FROM fact_inventory_movements
        WHERE event_type = 'stock_dispatched'
        AND   quantity IS NOT NULL
    ),
    avg_inv AS (
        SELECT COALESCE(AVG(physical_stock), 0)::float AS avg_stock
        FROM stock_per_location
        WHERE physical_stock > 0
    )
    SELECT
        CASE
            WHEN avg_inv.avg_stock > 0
            THEN ROUND((dispatched.total_dispatched / avg_inv.avg_stock)::numeric, 2)
            ELSE 0.0
        END AS turnover_rate
    FROM dispatched, avg_inv
""")


def get_inventory_kpis(db: Session) -> Dict[str, Any]:
    _zero = {
        "total_skus": 0, "total_stock_value": 0.0, "warehouses_count": 0,
        "low_stock_count": 0, "out_of_stock_count": 0, "turnover_rate": 0.0,
    }
    try:
        sku_row = db.execute(_SQL_KPI_SKUS).fetchone()
        wh_row  = db.execute(_SQL_KPI_WAREHOUSES).fetchone()
        tr_row  = db.execute(_SQL_KPI_TURNOVER).fetchone()
    except ProgrammingError:
        db.rollback()
        return _zero
    return {
        "total_skus":         int(sku_row.total_skus)          if sku_row else 0,
        "total_stock_value":  float(sku_row.total_stock_value) if sku_row else 0.0,
        "warehouses_count":   int(wh_row.warehouses_count)     if wh_row  else 0,
        "low_stock_count":    int(sku_row.low_stock_count)      if sku_row else 0,
        "out_of_stock_count": int(sku_row.out_of_stock_count)   if sku_row else 0,
        "turnover_rate":      float(tr_row.turnover_rate)       if tr_row  else 0.0,
    }


# ============================================================================
#  §5  GET /inventory/stock-status
# ============================================================================

_SQL_STOCK_STATUS = text(_STOCK_BASE_CTES + """
    , stock_por_sku AS (
        SELECT
            sku_id,
            SUM(physical_stock)     AS total_available,
            MAX(critical_threshold) AS threshold,
            BOOL_OR(is_stock_out)   AS any_stock_out
        FROM stock_per_location
        GROUP BY sku_id
    ),
    classified AS (
        SELECT
            CASE
                WHEN total_available = 0 OR any_stock_out THEN 'OUT_OF_STOCK'
                WHEN total_available <= threshold          THEN 'CRITICAL'
                ELSE                                           'NORMAL'
            END AS status
        FROM stock_por_sku
    ),
    totales AS (SELECT COUNT(*) AS n FROM classified)
    SELECT
        c.status,
        COUNT(*)                                             AS count,
        ROUND(100.0 * COUNT(*) / NULLIF(t.n, 0), 2)         AS percentage
    FROM classified c, totales t
    GROUP BY c.status, t.n
    ORDER BY
        CASE c.status
            WHEN 'OUT_OF_STOCK' THEN 1
            WHEN 'CRITICAL'     THEN 2
            ELSE                     3
        END
""")


def get_stock_status_summary(db: Session) -> Tuple[List[Dict[str, Any]], int]:
    rows = db.execute(_SQL_STOCK_STATUS).fetchall()
    data  = [_row_to_dict(r) for r in rows]
    total = sum(int(r["count"]) for r in data)
    return data, total
