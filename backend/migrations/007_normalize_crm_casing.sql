-- =============================================================================
-- Migration 007 — Backfill de casing en CRM (normalizar tickets históricos)
--
-- La ingesta ya normaliza estado/prioridad/canal al canónico español
-- capitalizado con tilde (crm_processor._normalize_*), pero los tickets
-- ingeridos ANTES de esa normalización quedaron con el casing crudo del CRM
-- externo (minúscula sin tilde: "abierto", "alta", "critica", "email",
-- "telefono"...). Eso duplicaba categorías en los gráficos de distribución
-- ("alta" vs "Alta") y hacía que los conteos que filtran por el valor canónico
-- (tickets abiertos, críticos, cerrados) se saltaran los históricos.
--
-- Este script alinea la data histórica al canónico. Es idempotente: correrlo
-- de nuevo no cambia nada (los valores ya canónicos no matchean los WHERE).
--
-- NO se gestiona vía Alembic a propósito (misma razón que 004/005/006: el
-- esquema de prod se creó con create_all() y el puntero alembic_version es
-- compartido/inconsistente). Ejecutar manualmente contra cada entorno (dev y
-- producción).
--
-- NOTA: si fact_tickets tiene un CheckConstraint sobre estado/prioridad/canal,
-- estos UPDATE solo escriben valores permitidos por él, así que no lo violan.
-- =============================================================================

-- ── fact_tickets.estado ─────────────────────────────────────────────────────
UPDATE fact_tickets SET estado = 'Abierto'  WHERE estado = 'abierto';
UPDATE fact_tickets SET estado = 'Progreso' WHERE estado = 'progreso';
UPDATE fact_tickets SET estado = 'Resuelto' WHERE estado = 'resuelto';
UPDATE fact_tickets SET estado = 'Cerrado'  WHERE estado = 'cerrado';

-- ── fact_tickets.prioridad ──────────────────────────────────────────────────
UPDATE fact_tickets SET prioridad = 'Baja'    WHERE prioridad = 'baja';
UPDATE fact_tickets SET prioridad = 'Media'   WHERE prioridad = 'media';
UPDATE fact_tickets SET prioridad = 'Alta'    WHERE prioridad = 'alta';
UPDATE fact_tickets SET prioridad = 'Crítica' WHERE prioridad IN ('critica', 'crítica');

-- ── fact_tickets.canal ──────────────────────────────────────────────────────
UPDATE fact_tickets SET canal = 'Chat'     WHERE canal = 'chat';
UPDATE fact_tickets SET canal = 'Email'    WHERE canal = 'email';
UPDATE fact_tickets SET canal = 'Teléfono' WHERE canal IN ('telefono', 'teléfono');
UPDATE fact_tickets SET canal = 'App'      WHERE canal = 'app';

-- ── fact_sla_violaciones (mismos campos crudos del payload) ─────────────────
UPDATE fact_sla_violaciones SET prioridad = 'Baja'    WHERE prioridad = 'baja';
UPDATE fact_sla_violaciones SET prioridad = 'Media'   WHERE prioridad = 'media';
UPDATE fact_sla_violaciones SET prioridad = 'Alta'    WHERE prioridad = 'alta';
UPDATE fact_sla_violaciones SET prioridad = 'Crítica' WHERE prioridad IN ('critica', 'crítica');
UPDATE fact_sla_violaciones SET canal = 'Chat'     WHERE canal = 'chat';
UPDATE fact_sla_violaciones SET canal = 'Email'    WHERE canal = 'email';
UPDATE fact_sla_violaciones SET canal = 'Teléfono' WHERE canal IN ('telefono', 'teléfono');
UPDATE fact_sla_violaciones SET canal = 'App'      WHERE canal = 'app';

-- ── Verificación: no deben quedar valores en minúscula ──────────────────────
SELECT 'fact_tickets.estado'    AS campo, estado    AS valor, COUNT(*) FROM fact_tickets       GROUP BY estado
UNION ALL
SELECT 'fact_tickets.prioridad' AS campo, prioridad AS valor, COUNT(*) FROM fact_tickets       GROUP BY prioridad
UNION ALL
SELECT 'fact_tickets.canal'     AS campo, canal     AS valor, COUNT(*) FROM fact_tickets       GROUP BY canal
ORDER BY campo, valor;
