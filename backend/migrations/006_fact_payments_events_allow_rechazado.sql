-- =============================================================================
-- Migration 006 — Permitir status 'Rechazado' en fact_payments_events
--
-- app/etl/processors/payment_processor.py (el processor real registrado en
-- _ETL_PROCESSORS para source='payments') resuelve un pago rechazado sin
-- error_code de monto/transacción como estado 'Rechazado' (ver
-- payment_processor._resolve_status_name / payment_service.confirm_payment).
-- FactPagos lo guarda bien vía estado_conciliacion_id (tabla de dimensión, sin
-- CHECK), pero fact_payments_events.status es una columna de texto con un
-- CheckConstraint que solo permitía 4 valores sin 'Rechazado' — el código lo
-- esquivaba silenciosamente reescribiendo el status a 'esperando_revisión'
-- antes de insertar, con lo que esos pagos rechazados quedaban contados como
-- "pendientes de revisión" en vez de fallos en get_payment_kpis/get_payment_timeline
-- (app/pagos/services/payment_analytics_service.py) y en el dashboard de /pagos.
--
-- Cambio aditivo sobre una constraint existente: se dropea y se recrea con el
-- valor nuevo agregado, sin tocar filas existentes.
--
-- NO se gestiona vía Alembic a propósito (mismo motivo que 004/005): el
-- alembic_version puede estar desincronizado entre entornos y es compartido
-- por todos los módulos, no solo pagos.
--
-- Ejecutar manualmente contra la base de datos (dev y producción) antes o
-- junto con el deploy del código que deja de reescribir 'Rechazado'. Es
-- idempotente: se puede correr más de una vez sin efecto adicional.
-- =============================================================================

ALTER TABLE fact_payments_events
  DROP CONSTRAINT IF EXISTS ck_fact_payments_events_status;

ALTER TABLE fact_payments_events
  ADD CONSTRAINT ck_fact_payments_events_status
  CHECK (status IN ('esperando_revisión', 'Aprobado', 'discrepancia_de_monto', 'discrepancia_de_transacciones', 'Rechazado'));

-- ── Resultado ─────────────────────────────────────────────────────────────────
SELECT conname, pg_get_constraintdef(oid) AS definicion
FROM   pg_constraint
WHERE  conname = 'ck_fact_payments_events_status';
