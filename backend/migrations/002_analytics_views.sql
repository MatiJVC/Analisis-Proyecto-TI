-- =============================================================================
-- Migration 002 — Silver Layer Views (Power BI — ready)
-- Transforms JSONB payload into typed relational columns.
-- Both views are additive: re-run safely with CREATE OR REPLACE.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- vw_crm_tickets
-- Source: fact_raw_events WHERE source = 'crm'
-- Purpose: ticket-level analytics with SLA compliance (8-hour threshold)
--
-- Expected payload shape (CRM events):
-- {
--   "ticket_id":        "T-00123",
--   "customer_id":      "C-4567",
--   "priority":         "high",          -- low | medium | high | critical
--   "status":           "resolved",      -- open | in_progress | resolved | escalated
--   "category":         "billing",
--   "assigned_agent_id":"A-89",
--   "channel":          "email",         -- email | chat | phone | web
--   "created_at":       "2026-05-21T10:00:00Z",
--   "resolved_at":      "2026-05-21T17:30:00Z",   -- null if still open
--   "escalated":        false
-- }
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_crm_tickets AS
SELECT
    -- Audit
    event_id,
    ingested_at,
    event_type,

    -- Ticket identity
    payload ->> 'ticket_id'                                         AS ticket_id,
    payload ->> 'customer_id'                                       AS customer_id,
    payload ->> 'assigned_agent_id'                                 AS assigned_agent_id,

    -- Categorical dimensions
    payload ->> 'priority'                                          AS priority,
    payload ->> 'status'                                            AS status,
    payload ->> 'category'                                          AS category,
    payload ->> 'channel'                                           AS channel,
    (payload ->> 'escalated')::BOOLEAN                              AS escalated,

    -- Temporal dimensions (cast from ISO-8601 strings inside JSONB)
    (payload ->> 'created_at')::TIMESTAMPTZ                         AS created_at,
    (payload ->> 'resolved_at')::TIMESTAMPTZ                        AS resolved_at,

    -- SLA metric: resolution time in hours (NULL = still open)
    CASE
        WHEN payload ->> 'resolved_at' IS NOT NULL
         AND payload ->> 'created_at'  IS NOT NULL
        THEN
            EXTRACT(EPOCH FROM (
                (payload ->> 'resolved_at')::TIMESTAMPTZ
              - (payload ->> 'created_at')::TIMESTAMPTZ
            )) / 3600.0
    END                                                             AS resolution_hours,

    -- SLA compliance flag: resolved within 8-hour threshold
    -- NULL = ticket still open (Power BI handles this as "pending" in visuals)
    CASE
        WHEN payload ->> 'resolved_at' IS NOT NULL
         AND payload ->> 'created_at'  IS NOT NULL
        THEN
            EXTRACT(EPOCH FROM (
                (payload ->> 'resolved_at')::TIMESTAMPTZ
              - (payload ->> 'created_at')::TIMESTAMPTZ
            )) / 3600.0 <= 8.0
    END                                                             AS within_sla,

    -- Escalation rate helper: pre-compute for DAX measures
    CASE
        WHEN (payload ->> 'escalated')::BOOLEAN IS TRUE THEN 1 ELSE 0
    END                                                             AS is_escalated_int

FROM fact_raw_events
WHERE source = 'crm';

COMMENT ON VIEW vw_crm_tickets IS
    'Silver view — CRM ticket events with SLA (8 h) compliance calculation. Connects to Power BI via DirectQuery or import.';


-- -----------------------------------------------------------------------------
-- vw_order_events
-- Source: fact_raw_events WHERE source = 'orders'
-- Purpose: order-level analytics with fulfillment, revenue and channel metrics
--
-- Expected payload shape (order events):
-- {
--   "order_id":       "ORD-78901",
--   "customer_id":    "C-4567",
--   "status":         "delivered",    -- pending | processing | shipped | delivered | cancelled
--   "channel":        "web",          -- web | app | call_center | store
--   "total_amount":   149.99,
--   "currency":       "CLP",
--   "order_date":     "2026-05-20T14:00:00Z",
--   "expected_date":  "2026-05-23T18:00:00Z",
--   "delivery_date":  "2026-05-23T15:45:00Z",   -- null if not yet delivered
--   "payment_status": "approved",
--   "items": [
--     {"sku":"SKU-001","name":"Producto A","qty":2,"unit_price":49.99},
--     {"sku":"SKU-002","name":"Producto B","qty":1,"unit_price":50.01}
--   ]
-- }
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_order_events AS
SELECT
    -- Audit
    event_id,
    ingested_at,
    event_type,

    -- Order identity
    payload ->> 'order_id'                                          AS order_id,
    payload ->> 'customer_id'                                       AS customer_id,

    -- Categorical dimensions
    payload ->> 'status'                                            AS status,
    payload ->> 'channel'                                           AS channel,
    payload ->> 'payment_status'                                    AS payment_status,
    payload ->> 'currency'                                          AS currency,

    -- Financial measures (explicit cast to NUMERIC for accurate aggregation)
    (payload ->> 'total_amount')::NUMERIC(18, 2)                    AS total_amount,

    -- Temporal dimensions
    (payload ->> 'order_date')::TIMESTAMPTZ                         AS order_date,
    (payload ->> 'expected_date')::TIMESTAMPTZ                      AS expected_date,
    (payload ->> 'delivery_date')::TIMESTAMPTZ                      AS delivery_date,

    -- Lead time in hours: order → delivery (NULL = not yet delivered)
    CASE
        WHEN payload ->> 'delivery_date' IS NOT NULL
         AND payload ->> 'order_date'    IS NOT NULL
        THEN
            EXTRACT(EPOCH FROM (
                (payload ->> 'delivery_date')::TIMESTAMPTZ
              - (payload ->> 'order_date')::TIMESTAMPTZ
            )) / 3600.0
    END                                                             AS lead_time_hours,

    -- On-time delivery flag (delivery <= expected)
    CASE
        WHEN payload ->> 'delivery_date' IS NOT NULL
         AND payload ->> 'expected_date' IS NOT NULL
        THEN
            (payload ->> 'delivery_date')::TIMESTAMPTZ
         <= (payload ->> 'expected_date')::TIMESTAMPTZ
    END                                                             AS delivered_on_time,

    -- Items array preserved for sub-selection in Power BI (via JSON field)
    payload -> 'items'                                              AS items_json,

    -- Item count — avoids parsing the array in DAX
    CASE
        WHEN jsonb_typeof(payload -> 'items') = 'array'
        THEN jsonb_array_length(payload -> 'items')
        ELSE 0
    END                                                             AS item_count

FROM fact_raw_events
WHERE source = 'orders';

COMMENT ON VIEW vw_order_events IS
    'Silver view — order events with fulfillment, revenue and on-time delivery metrics. Connects to Power BI via DirectQuery or import.';
