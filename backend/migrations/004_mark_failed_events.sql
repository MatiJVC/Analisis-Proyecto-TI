-- =============================================================================
-- Migration 004 — Marcar eventos ETL con fallo permanente
--
-- La columna failed (boolean DEFAULT false) ya existe en fact_raw_events.
-- retry_stale_events() reintenta todos los eventos con processed=false en loop,
-- causando spam de logs. Este script marca como failed=true los eventos que
-- nunca podrán procesarse.
--
-- Ejecutar manualmente cuando haya backlog de eventos atascados.
-- =============================================================================

-- ── 1. Payload vacío (cualquier módulo) ──────────────────────────────────────
UPDATE fact_raw_events
SET    failed = true
WHERE  processed = false
  AND  failed   = false
  AND  payload  = '{}'::jsonb;

-- ── 2. CRM: event_type no soportado ─────────────────────────────────────────
UPDATE fact_raw_events
SET    failed = true
WHERE  processed = false
  AND  failed   = false
  AND  source   = 'crm'
  AND  event_type NOT IN (
         'ticket.creado', 'ticket.asignado', 'ticket.escalado',
         'ticket.resuelto', 'ticket.cerrado',
         'interaccion.creada', 'kb.articulo.usado', 'ticket.sla_violado'
       );

-- ── 3. CRM ticket.*: sin ticket_id ──────────────────────────────────────────
UPDATE fact_raw_events
SET    failed = true
WHERE  processed = false
  AND  failed   = false
  AND  source   = 'crm'
  AND  event_type IN (
         'ticket.creado', 'ticket.asignado', 'ticket.escalado',
         'ticket.resuelto', 'ticket.cerrado'
       )
  AND  (payload->>'ticket_id') IS NULL;

-- ── 4. CRM ticket.creado: valores que violan CheckConstraints ────────────────
UPDATE fact_raw_events
SET    failed = true
WHERE  processed = false
  AND  failed   = false
  AND  source   = 'crm'
  AND  event_type = 'ticket.creado'
  AND  (
         (payload->>'prioridad') IS NOT NULL
         AND (payload->>'prioridad') NOT IN ('Baja', 'Media', 'Alta', 'Crítica')
       )
   OR  (
         (payload->>'canal') IS NOT NULL
         AND (payload->>'canal') NOT IN ('Chat', 'Email', 'Teléfono', 'App')
       );

-- ── 5. CRM interaccion.creada: sin interaccion_id ───────────────────────────
UPDATE fact_raw_events
SET    failed = true
WHERE  processed = false
  AND  failed   = false
  AND  source   = 'crm'
  AND  event_type = 'interaccion.creada'
  AND  (payload->>'interaccion_id') IS NULL;

-- ── 6. CRM kb.articulo.usado: sin ticket_id o articulo_id ───────────────────
UPDATE fact_raw_events
SET    failed = true
WHERE  processed = false
  AND  failed   = false
  AND  source   = 'crm'
  AND  event_type = 'kb.articulo.usado'
  AND  (
         (payload->>'ticket_id') IS NULL
         OR (payload->>'articulo_id') IS NULL
       );

-- ── Resultado ─────────────────────────────────────────────────────────────────
SELECT source, event_type, COUNT(*) AS marcados_failed
FROM   fact_raw_events
WHERE  failed = true
GROUP  BY source, event_type
ORDER  BY marcados_failed DESC;
