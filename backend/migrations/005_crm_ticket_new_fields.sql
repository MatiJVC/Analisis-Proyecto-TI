-- =============================================================================
-- Migration 005 — Nuevos campos de fact_tickets (alineación con TicketDto real)
--
-- El CRM externo (pgti-proyecto-crm-backend) expone en su TicketDto real los
-- campos cliente_id, cliente_nombre, pago_id_ref, salud_ref y resolucion, sin
-- columna equivalente en fact_tickets. Se agregan aquí como columnas nullable
-- (operación de solo metadata en Postgres, no reescribe la tabla, no toca
-- CheckConstraints ni datos existentes).
--
-- NO se gestiona vía Alembic a propósito: el esquema de producción fue creado
-- con create_all() y nunca tuvo alembic_version poblada; introducir Alembic
-- ahora arriesgaría marcar esta migración como "aplicada" sin ejecutar su SQL
-- (ver backend/entrypoint.sh) y afectaría el puntero global compartido por
-- todos los módulos, no solo CRM.
--
-- Ejecutar manualmente contra la base de datos (dev y producción) antes o
-- junto con el deploy del código que puebla estas columnas. Es idempotente:
-- se puede correr más de una vez sin efecto adicional.
-- =============================================================================

ALTER TABLE fact_tickets
  ADD COLUMN IF NOT EXISTS cliente_id INTEGER,
  ADD COLUMN IF NOT EXISTS cliente_nombre VARCHAR(255),
  ADD COLUMN IF NOT EXISTS pago_id_ref VARCHAR(100),
  ADD COLUMN IF NOT EXISTS salud_ref VARCHAR(100),
  ADD COLUMN IF NOT EXISTS resolucion TEXT;

-- ── Resultado ─────────────────────────────────────────────────────────────────
SELECT column_name, data_type, is_nullable
FROM   information_schema.columns
WHERE  table_name = 'fact_tickets'
  AND  column_name IN ('cliente_id', 'cliente_nombre', 'pago_id_ref', 'salud_ref', 'resolucion')
ORDER  BY column_name;
