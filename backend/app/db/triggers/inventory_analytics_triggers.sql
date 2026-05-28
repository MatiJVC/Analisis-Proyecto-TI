-- ============================================================================
--  TRIGGERS DE INVENTARIO  →  MÓDULO DE ANALÍTICA
--  Archivo : inventory_analytics_triggers.sql
--  Base    : PostgreSQL 14+  (sin extensiones para la estrategia principal)
-- ============================================================================
--
--  Propósito
--  ---------
--  Capturar automáticamente cada INSERT en inventory_movements y reservations,
--  construir el payload JSON que espera el endpoint POST /events de Analítica
--  y garantizar su entrega mediante el Patrón Outbox (estrategia A).
--
--  Se incluyen además dos alternativas:
--    [B]  pg_notify / LISTEN  →  liviana, sin tabla extra, requiere worker
--    [C]  pg_net              →  HTTP directo desde Postgres (extensión externa)
--
--  Eventos gestionados
--  -------------------
--    inventory_movements → stock_received | stock_dispatched | stock_adjusted
--                          stock_transfer_initiated | stock_out_error
--    reservations        → stock_reserved
--    (post-movimiento)   → critical_threshold_reached | stock_out_error
--                          (leídos de stock_levels)
--
--  IMPORTANTE: Este script se ejecuta en la base de datos del Grupo 5
--  (módulo de Inventario). La tabla raw_events y el endpoint /events
--  pertenecen al módulo de Analítica.
--
-- ============================================================================


-- ============================================================================
--  §0  ESTRUCTURA DE TABLAS ESPERADA  (DDL de referencia para el Grupo 5)
--      Ajusta los tipos según tu esquema real antes de crear los triggers.
-- ============================================================================

/*
-- Tabla: inventory_movements
-- Registra toda entrada, salida, ajuste y transferencia de stock.
CREATE TABLE IF NOT EXISTS inventory_movements (
    id            UUID         NOT NULL DEFAULT gen_random_uuid(),
    movement_type VARCHAR(50)  NOT NULL,
    -- Valores esperados: 'stock_received' | 'stock_dispatched' | 'stock_adjusted'
    --                    'stock_transfer_initiated' | 'stock_out_error'
    sku_id        VARCHAR(100) NOT NULL,
    location_id   UUID         NOT NULL,
    quantity      INTEGER      NOT NULL,   -- positivo=entrada, negativo=salida/ajuste
    reference_id  VARCHAR(100),            -- order_id u otro identificador externo
    unit_cost     NUMERIC(12, 2),          -- solo para stock_received
    notes         TEXT,
    created_by    VARCHAR(100),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_inventory_movements PRIMARY KEY (id)
);

-- Tabla: reservations
-- Reservas de stock vinculadas a pedidos.
CREATE TABLE IF NOT EXISTS reservations (
    reservation_id UUID         NOT NULL DEFAULT gen_random_uuid(),
    order_id       VARCHAR(100) NOT NULL,
    sku_id         VARCHAR(100) NOT NULL,
    location_id    UUID         NOT NULL,
    quantity       INTEGER      NOT NULL  CHECK (quantity > 0),
    status         VARCHAR(20)  NOT NULL  DEFAULT 'active',
    expires_at     TIMESTAMPTZ  NOT NULL,
    created_at     TIMESTAMPTZ  NOT NULL  DEFAULT NOW(),
    updated_at     TIMESTAMPTZ  NOT NULL  DEFAULT NOW(),
    CONSTRAINT pk_reservations PRIMARY KEY (reservation_id)
);

-- Tabla: stock_levels
-- Nivel de stock actual por SKU y ubicación.
-- El trigger lee esta tabla para detectar umbrales críticos.
CREATE TABLE IF NOT EXISTS stock_levels (
    sku_id        VARCHAR(100) NOT NULL,
    location_id   UUID         NOT NULL,
    current_stock INTEGER      NOT NULL  DEFAULT 0,
    minimum_stock INTEGER      NOT NULL  DEFAULT 0,   -- threshold_limite
    updated_at    TIMESTAMPTZ  NOT NULL  DEFAULT NOW(),
    CONSTRAINT pk_stock_levels PRIMARY KEY (sku_id, location_id),
    CONSTRAINT chk_stock_levels_non_negative CHECK (minimum_stock >= 0)
);
*/


-- ============================================================================
--  §1  TABLA OUTBOX  (Estrategia A — patrón de entrega garantizada)
--      Se crea en la base de datos del Grupo 5 (Inventario).
-- ============================================================================

CREATE TABLE IF NOT EXISTS inventory_outbox_events (
    id              BIGSERIAL    PRIMARY KEY,
    source          VARCHAR(50)  NOT NULL  DEFAULT 'inventory',
    event_type      VARCHAR(100) NOT NULL,
    payload         JSONB        NOT NULL,   -- solo los datos del evento (sin envelope)
    status          VARCHAR(20)  NOT NULL  DEFAULT 'pending',
    attempts        SMALLINT     NOT NULL  DEFAULT 0,
    max_attempts    SMALLINT     NOT NULL  DEFAULT 5,
    created_at      TIMESTAMPTZ  NOT NULL  DEFAULT NOW(),
    last_attempt_at TIMESTAMPTZ,
    sent_at         TIMESTAMPTZ,
    error_message   TEXT,
    CONSTRAINT chk_outbox_status
        CHECK (status IN ('pending', 'retrying', 'sent', 'failed'))
);

-- Índice para que el worker localice rápidamente filas pendientes
CREATE INDEX IF NOT EXISTS idx_outbox_status_created
    ON inventory_outbox_events (status, created_at)
    WHERE status IN ('pending', 'retrying');

COMMENT ON TABLE inventory_outbox_events IS
    'Patrón Outbox: buffer transaccional de eventos de inventario pendientes '
    'de envío al endpoint POST /events del módulo de Analítica.';


-- ============================================================================
--  §2  FUNCIÓN AUXILIAR — Formateo ISO 8601 en UTC con sufijo Z
--      Centraliza la conversión de TIMESTAMPTZ → texto para todos los triggers.
-- ============================================================================

CREATE OR REPLACE FUNCTION fn_to_iso8601_utc(p_ts TIMESTAMPTZ)
RETURNS TEXT
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $$
    SELECT to_char(p_ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"');
$$;

COMMENT ON FUNCTION fn_to_iso8601_utc(TIMESTAMPTZ) IS
    'Convierte TIMESTAMPTZ a texto ISO 8601 con sufijo Z (ej: 2026-05-28T10:00:00Z). '
    'Usado por los triggers de inventario para serializar fechas en JSON.';


-- ============================================================================
--  §3  FUNCIÓN TRIGGER — inventory_movements  →  outbox
-- ============================================================================
--
--  Mapeo movement_type (interno Grupo 5)  →  event_type (Analítica)
--  ---------------------------------------------------------------
--  'stock_received'          → 'stock_received'
--  'stock_dispatched'        → 'stock_dispatched'
--  'stock_adjusted'          → 'stock_adjusted'
--  'stock_transfer_initiated'→ 'stock_transfer_initiated'
--  'stock_out_error'         → 'stock_out_error'
--  cualquier otro valor      → ignorado (RETURN NEW sin efecto)
--
--  Tras movimientos de salida/ajuste se verifica el umbral crítico en
--  stock_levels y se genera un evento adicional si corresponde.
-- ============================================================================

CREATE OR REPLACE FUNCTION fn_inventory_movements_to_analytics()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
    v_event_type  VARCHAR(100);
    v_payload     JSONB;
    v_outbox_id   BIGINT;
    v_ts          TEXT;
BEGIN
    -- ------------------------------------------------------------------
    -- 1. Mapear movement_type al vocabulario de Analítica
    -- ------------------------------------------------------------------
    v_event_type := CASE NEW.movement_type
        WHEN 'stock_received'           THEN 'stock_received'
        WHEN 'stock_dispatched'         THEN 'stock_dispatched'
        WHEN 'stock_adjusted'           THEN 'stock_adjusted'
        WHEN 'stock_transfer_initiated' THEN 'stock_transfer_initiated'
        WHEN 'stock_out_error'          THEN 'stock_out_error'
        -- Aliases comunes que el Grupo 5 podría usar en su sistema interno:
        WHEN 'received'   THEN 'stock_received'
        WHEN 'entry'      THEN 'stock_received'
        WHEN 'dispatched' THEN 'stock_dispatched'
        WHEN 'shipment'   THEN 'stock_dispatched'
        WHEN 'adjusted'   THEN 'stock_adjusted'
        WHEN 'adjustment' THEN 'stock_adjusted'
        WHEN 'transfer'   THEN 'stock_transfer_initiated'
        ELSE NULL
    END;

    -- Tipo no reconocido → no generar evento, continuar la transacción
    IF v_event_type IS NULL THEN
        RAISE NOTICE 'fn_inventory_movements_to_analytics: movement_type=% no mapeado, evento omitido.',
            NEW.movement_type;
        RETURN NEW;
    END IF;

    -- ------------------------------------------------------------------
    -- 2. Timestamp en UTC con formato ISO 8601 Z
    -- ------------------------------------------------------------------
    v_ts := fn_to_iso8601_utc(NEW.created_at);

    -- ------------------------------------------------------------------
    -- 3. Construir payload según el tipo de movimiento
    --    Los campos nulos se excluyen para mantener JSON limpio.
    -- ------------------------------------------------------------------
    v_payload := jsonb_strip_nulls(
        jsonb_build_object(
            'movement_id',  NEW.id::TEXT,
            'sku_id',       NEW.sku_id,
            'location_id',  NEW.location_id::TEXT,
            'quantity',     NEW.quantity,
            'reference_id', NEW.reference_id,
            'notes',        NEW.notes,
            'created_by',   NEW.created_by,
            'created_at',   v_ts
        )
        -- unit_cost solo aplica a stock_received
        || CASE
               WHEN v_event_type = 'stock_received' AND NEW.unit_cost IS NOT NULL
               THEN jsonb_build_object('unit_cost', NEW.unit_cost)
               ELSE '{}'::JSONB
           END
    );

    -- ------------------------------------------------------------------
    -- 4. Insertar en outbox — DENTRO de la misma transacción.
    --    Si este INSERT falla, el INSERT original también se revierte,
    --    garantizando consistencia entre inventario y analítica.
    -- ------------------------------------------------------------------
    INSERT INTO inventory_outbox_events (source, event_type, payload)
    VALUES ('inventory', v_event_type, v_payload)
    RETURNING id INTO v_outbox_id;

    -- ------------------------------------------------------------------
    -- 5. pg_notify como señal inmediata para despertar al worker.
    --    Envuelto en bloque propio: un fallo aquí NO aborta la transacción.
    -- ------------------------------------------------------------------
    BEGIN
        PERFORM pg_notify(
            'inventory_analytics_channel',
            jsonb_build_object(
                'outbox_id',  v_outbox_id,
                'event_type', v_event_type
            )::TEXT
        );
    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'fn_inventory_movements_to_analytics: pg_notify falló (outbox_id=%). '
                      'El worker procesará el evento por polling. SQLSTATE=%, MSG=%',
            v_outbox_id, SQLSTATE, SQLERRM;
    END;

    -- ------------------------------------------------------------------
    -- 6. Verificar umbral crítico en stock_levels después de salidas.
    --    Genera eventos 'stock_out_error' o 'critical_threshold_reached'
    --    en el outbox si el stock bajó al límite.
    -- ------------------------------------------------------------------
    IF v_event_type IN ('stock_dispatched', 'stock_adjusted', 'stock_out_error') THEN
        BEGIN
            PERFORM fn_inventory_check_threshold(NEW.sku_id, NEW.location_id);
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'fn_inventory_movements_to_analytics: verificación de umbral falló '
                          'para sku_id=%, location_id=%. SQLSTATE=%, MSG=%',
                NEW.sku_id, NEW.location_id::TEXT, SQLSTATE, SQLERRM;
        END;
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION fn_inventory_movements_to_analytics() IS
    'Trigger AFTER INSERT en inventory_movements. Escribe en inventory_outbox_events '
    'el payload de cada movimiento de stock y verifica umbrales críticos.';


-- ============================================================================
--  §4  TRIGGER — inventory_movements
-- ============================================================================

DROP TRIGGER IF EXISTS trg_inventory_movements_analytics ON inventory_movements;

CREATE TRIGGER trg_inventory_movements_analytics
    AFTER INSERT
    ON inventory_movements
    FOR EACH ROW
    EXECUTE FUNCTION fn_inventory_movements_to_analytics();

COMMENT ON TRIGGER trg_inventory_movements_analytics ON inventory_movements IS
    'Dispara fn_inventory_movements_to_analytics después de cada INSERT '
    'para registrar el evento en el outbox de analítica.';


-- ============================================================================
--  §5  FUNCIÓN TRIGGER — reservations  →  outbox (stock_reserved)
--
--  Genera el evento 'stock_reserved' con los campos que requiere el
--  esquema estricto StockReservedPayload del módulo de Analítica:
--    reservation_id, order_id, sku_id, location_id, quantity,
--    created_at (ISO 8601), expires_at (ISO 8601, posterior a created_at)
-- ============================================================================

CREATE OR REPLACE FUNCTION fn_reservations_to_analytics()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
    v_payload    JSONB;
    v_outbox_id  BIGINT;
    v_created_ts TEXT;
    v_expires_ts TEXT;
BEGIN
    -- ------------------------------------------------------------------
    -- 1. Validación temprana (defensa ante datos incompletos del Grupo 5)
    -- ------------------------------------------------------------------
    IF NEW.quantity IS NULL OR NEW.quantity <= 0 THEN
        RAISE EXCEPTION
            'reservations.quantity debe ser un entero positivo. '
            'Recibido: %, reservation_id=%',
            NEW.quantity, NEW.reservation_id;
    END IF;

    IF NEW.expires_at IS NULL OR NEW.expires_at <= NEW.created_at THEN
        RAISE EXCEPTION
            'reservations.expires_at (%) debe ser posterior a created_at (%). '
            'reservation_id=%',
            NEW.expires_at, NEW.created_at, NEW.reservation_id;
    END IF;

    -- ------------------------------------------------------------------
    -- 2. Timestamps en ISO 8601 UTC
    -- ------------------------------------------------------------------
    v_created_ts := fn_to_iso8601_utc(NEW.created_at);
    v_expires_ts := fn_to_iso8601_utc(NEW.expires_at);

    -- ------------------------------------------------------------------
    -- 3. Payload — cumple exactamente con StockReservedPayload de Analítica
    -- ------------------------------------------------------------------
    v_payload := jsonb_build_object(
        'reservation_id', NEW.reservation_id::TEXT,
        'order_id',       NEW.order_id,
        'sku_id',         NEW.sku_id,
        'location_id',    NEW.location_id::TEXT,
        'quantity',       NEW.quantity,
        'created_at',     v_created_ts,
        'expires_at',     v_expires_ts
    );

    -- ------------------------------------------------------------------
    -- 4. Insertar en outbox (transacción atómica con el INSERT original)
    -- ------------------------------------------------------------------
    INSERT INTO inventory_outbox_events (source, event_type, payload)
    VALUES ('inventory', 'stock_reserved', v_payload)
    RETURNING id INTO v_outbox_id;

    -- ------------------------------------------------------------------
    -- 5. pg_notify (no crítico — fallo no aborta la transacción)
    -- ------------------------------------------------------------------
    BEGIN
        PERFORM pg_notify(
            'inventory_analytics_channel',
            jsonb_build_object(
                'outbox_id',  v_outbox_id,
                'event_type', 'stock_reserved',
                'sku_id',     NEW.sku_id
            )::TEXT
        );
    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'fn_reservations_to_analytics: pg_notify falló (outbox_id=%). '
                      'SQLSTATE=%, MSG=%', v_outbox_id, SQLSTATE, SQLERRM;
    END;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION fn_reservations_to_analytics() IS
    'Trigger AFTER INSERT en reservations. Genera el evento stock_reserved '
    'con validación de cantidad y fechas antes de insertar en el outbox.';


-- ============================================================================
--  §6  TRIGGER — reservations
-- ============================================================================

DROP TRIGGER IF EXISTS trg_reservations_analytics ON reservations;

CREATE TRIGGER trg_reservations_analytics
    AFTER INSERT
    ON reservations
    FOR EACH ROW
    EXECUTE FUNCTION fn_reservations_to_analytics();

COMMENT ON TRIGGER trg_reservations_analytics ON reservations IS
    'Dispara fn_reservations_to_analytics después de cada INSERT '
    'para registrar el evento stock_reserved en el outbox de analítica.';


-- ============================================================================
--  §7  FUNCIÓN AUXILIAR — Verificación de umbral crítico
--
--  Llamada desde fn_inventory_movements_to_analytics después de movimientos
--  de salida. Genera eventos adicionales en el outbox si el stock cayó al
--  límite o quedó en cero.
--
--  Condiciones:
--    current_stock = 0            → stock_out_error
--    current_stock <= minimum_stock  (y > 0) → critical_threshold_reached
-- ============================================================================

CREATE OR REPLACE FUNCTION fn_inventory_check_threshold(
    p_sku_id      VARCHAR(100),
    p_location_id UUID
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
    v_stock      RECORD;
    v_event_type VARCHAR(100);
    v_ts         TEXT;
BEGIN
    -- Leer estado actual del stock para este SKU + ubicación
    SELECT current_stock, minimum_stock
    INTO   v_stock
    FROM   stock_levels
    WHERE  sku_id       = p_sku_id
      AND  location_id  = p_location_id;

    -- Si no existe registro en stock_levels, no hay umbral que verificar
    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Determinar qué tipo de alerta corresponde
    IF v_stock.current_stock <= 0 THEN
        v_event_type := 'stock_out_error';
    ELSIF v_stock.current_stock <= v_stock.minimum_stock THEN
        v_event_type := 'critical_threshold_reached';
    ELSE
        RETURN;   -- Stock por encima del umbral → ningún evento
    END IF;

    v_ts := fn_to_iso8601_utc(NOW());

    -- Insertar alerta en el outbox.
    -- El payload cumple con CriticalAlertPayload requerido por Analítica:
    --   sku_id, location_id, current_stock, threshold_limite
    INSERT INTO inventory_outbox_events (source, event_type, payload)
    VALUES (
        'inventory',
        v_event_type,
        jsonb_build_object(
            'sku_id',          p_sku_id,
            'location_id',     p_location_id::TEXT,
            'current_stock',   v_stock.current_stock,
            'threshold_limite', v_stock.minimum_stock,
            'detected_at',     v_ts
        )
    );

    RAISE NOTICE 'fn_inventory_check_threshold: evento % generado para sku_id=%, '
                 'current_stock=%, minimum_stock=%',
        v_event_type, p_sku_id,
        v_stock.current_stock, v_stock.minimum_stock;
END;
$$;

COMMENT ON FUNCTION fn_inventory_check_threshold(VARCHAR, UUID) IS
    'Verifica si el stock cayó al umbral crítico o a cero. '
    'Genera stock_out_error o critical_threshold_reached en el outbox.';


-- ============================================================================
--  §8  [ESTRATEGIA B] VARIANTE pg_notify / LISTEN
--
--  Úsala si prefieres NO tener tabla outbox y gestionar la entrega desde
--  la aplicación con asyncpg (ver inventory_outbox_worker.py, sección LISTEN).
--  ADVERTENCIA: si el worker está caído cuando llega la notificación, el
--  evento se pierde. Combinar con Outbox es la opción más robusta.
-- ============================================================================

CREATE OR REPLACE FUNCTION fn_inventory_notify_only()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
    v_event_type VARCHAR(100);
    v_payload    JSONB;
    v_ts         TEXT;
BEGIN
    v_event_type := CASE NEW.movement_type
        WHEN 'stock_received'            THEN 'stock_received'
        WHEN 'stock_dispatched'          THEN 'stock_dispatched'
        WHEN 'stock_adjusted'            THEN 'stock_adjusted'
        WHEN 'stock_transfer_initiated'  THEN 'stock_transfer_initiated'
        WHEN 'stock_out_error'           THEN 'stock_out_error'
        WHEN 'received'                  THEN 'stock_received'
        WHEN 'dispatched'                THEN 'stock_dispatched'
        WHEN 'adjusted'                  THEN 'stock_adjusted'
        WHEN 'transfer'                  THEN 'stock_transfer_initiated'
        ELSE NULL
    END;

    IF v_event_type IS NULL THEN
        RETURN NEW;
    END IF;

    v_ts := fn_to_iso8601_utc(NEW.created_at);

    -- Construir el JSON completo que recibirá el worker vía LISTEN
    v_payload := jsonb_strip_nulls(jsonb_build_object(
        'source',     'inventory',
        'event_type', v_event_type,
        'payload', jsonb_build_object(
            'movement_id',  NEW.id::TEXT,
            'sku_id',       NEW.sku_id,
            'location_id',  NEW.location_id::TEXT,
            'quantity',     NEW.quantity,
            'reference_id', NEW.reference_id,
            'created_by',   NEW.created_by,
            'created_at',   v_ts,
            'unit_cost',    NEW.unit_cost
        )
    ));

    -- pg_notify tiene límite de 8000 bytes por payload.
    -- Para payloads grandes, enviar solo la referencia (outbox_id).
    PERFORM pg_notify(
        'inventory_analytics_channel',
        v_payload::TEXT
    );

    RETURN NEW;
END;
$$;

/*  Para activar la estrategia B en inventory_movements, ejecutar:
    DROP TRIGGER IF EXISTS trg_inventory_movements_analytics ON inventory_movements;
    CREATE TRIGGER trg_inventory_movements_notify_only
        AFTER INSERT ON inventory_movements
        FOR EACH ROW
        EXECUTE FUNCTION fn_inventory_notify_only();
*/


-- ============================================================================
--  §9  [ESTRATEGIA C] VARIANTE pg_net (HTTP directo desde PostgreSQL)
--
--  Requiere la extensión pg_net (disponible en Supabase y compilable en
--  PostgreSQL estándar: https://github.com/supabase/pg_net).
--
--  Ventaja: sin worker externo.
--  Desventaja: HTTP síncrono en el ciclo de la transacción puede degradar
--  el rendimiento de escritura. Usar solo para volúmenes bajos.
-- ============================================================================

/*
-- Paso 1: habilitar la extensión (DBA con superusuario)
CREATE EXTENSION IF NOT EXISTS pg_net;

-- Paso 2: configurar la URL del servicio de Analítica como GUC de la BD
--   ALTER DATABASE inventario_db SET app.analytics_events_url =
--       'http://analytics-service:8000/events';

CREATE OR REPLACE FUNCTION fn_inventory_movements_pgnet()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
    v_event_type     VARCHAR(100);
    v_payload        JSONB;
    v_envelope       JSONB;
    v_request_id     BIGINT;
    v_analytics_url  TEXT;
    v_ts             TEXT;
BEGIN
    v_event_type := CASE NEW.movement_type
        WHEN 'stock_received'           THEN 'stock_received'
        WHEN 'stock_dispatched'         THEN 'stock_dispatched'
        WHEN 'stock_adjusted'           THEN 'stock_adjusted'
        WHEN 'stock_transfer_initiated' THEN 'stock_transfer_initiated'
        WHEN 'stock_out_error'          THEN 'stock_out_error'
        WHEN 'received'   THEN 'stock_received'
        WHEN 'dispatched' THEN 'stock_dispatched'
        WHEN 'adjusted'   THEN 'stock_adjusted'
        WHEN 'transfer'   THEN 'stock_transfer_initiated'
        ELSE NULL
    END;

    IF v_event_type IS NULL THEN
        RETURN NEW;
    END IF;

    v_ts := fn_to_iso8601_utc(NEW.created_at);

    v_payload := jsonb_strip_nulls(jsonb_build_object(
        'movement_id',  NEW.id::TEXT,
        'sku_id',       NEW.sku_id,
        'location_id',  NEW.location_id::TEXT,
        'quantity',     NEW.quantity,
        'reference_id', NEW.reference_id,
        'unit_cost',    NEW.unit_cost,
        'created_by',   NEW.created_by,
        'created_at',   v_ts
    ));

    v_envelope := jsonb_build_object(
        'source',     'inventory',
        'event_type', v_event_type,
        'payload',    v_payload
    );

    -- Leer URL del servicio de Analítica desde la configuración de la BD
    v_analytics_url := current_setting('app.analytics_events_url', TRUE);
    IF v_analytics_url IS NULL OR v_analytics_url = '' THEN
        RAISE EXCEPTION
            'GUC app.analytics_events_url no configurado. '
            'Ejecute: ALTER DATABASE <db> SET app.analytics_events_url = ''http://...''';
    END IF;

    -- Llamada HTTP POST asíncrona mediante pg_net
    SELECT net.http_post(
        url                  := v_analytics_url,
        headers              := '{"Content-Type": "application/json",
                                  "X-Source": "inventory-trigger"}'::JSONB,
        body                 := v_envelope::TEXT,
        timeout_milliseconds := 5000
    ) INTO v_request_id;

    RAISE NOTICE 'fn_inventory_movements_pgnet: request_id=% enviado para event_type=%',
        v_request_id, v_event_type;

    RETURN NEW;
END;
$$;
*/


-- ============================================================================
--  §10  VERIFICACIÓN Y EJEMPLOS DE PRUEBA
-- ============================================================================

-- ---
-- Verificar triggers instalados en las tablas
-- ---
/*
SELECT
    tgname        AS trigger_nombre,
    relname       AS tabla,
    tgenabled     AS habilitado,
    tgtype,
    proname       AS funcion
FROM pg_trigger  t
JOIN pg_class    c ON c.oid = t.tgrelid
JOIN pg_proc     p ON p.oid = t.tgfoid
WHERE relname IN ('inventory_movements', 'reservations')
ORDER BY tabla, trigger_nombre;
*/

-- ---
-- Ejemplo 1: INSERT stock_received → debe generar 1 fila en outbox
-- ---
/*
BEGIN;
    INSERT INTO inventory_movements (movement_type, sku_id, location_id, quantity, unit_cost, reference_id)
    VALUES (
        'stock_received',
        'SKU-PROD-001',
        'a3bb189e-8bf9-3888-9912-ace4e6543002',
        100,
        25.50,
        'PO-2026-00042'
    );

    -- Verificar outbox
    SELECT id, event_type, payload, status
    FROM   inventory_outbox_events
    ORDER  BY created_at DESC
    LIMIT  3;
ROLLBACK;  -- Cambiar a COMMIT en prueba real
*/

-- ---
-- Ejemplo 2: INSERT reservations → stock_reserved con validación de fechas
-- ---
/*
BEGIN;
    INSERT INTO reservations (order_id, sku_id, location_id, quantity, expires_at)
    VALUES (
        'ord-2026-00123',
        'SKU-PROD-001',
        'a3bb189e-8bf9-3888-9912-ace4e6543002',
        5,
        NOW() + INTERVAL '1 day'
    );

    SELECT id, event_type, payload #>> '{reservation_id}' AS reservation_id,
           payload #>> '{expires_at}' AS expires_at, status
    FROM   inventory_outbox_events
    ORDER  BY created_at DESC
    LIMIT  1;
ROLLBACK;
*/

-- ---
-- Ejemplo 3: Reserva con expires_at en el pasado → debe lanzar EXCEPTION
-- ---
/*
BEGIN;
    INSERT INTO reservations (order_id, sku_id, location_id, quantity, expires_at)
    VALUES (
        'ord-2026-00999',
        'SKU-PROD-001',
        'a3bb189e-8bf9-3888-9912-ace4e6543002',
        1,
        NOW() - INTERVAL '1 hour'    -- ← fecha inválida
    );
ROLLBACK;
-- Debe fallar con: "reservations.expires_at debe ser posterior a created_at"
*/

-- ---
-- Ejemplo 4: Simular critical_threshold_reached (requiere stock_levels poblado)
-- ---
/*
BEGIN;
    -- Insertar nivel crítico de stock
    INSERT INTO stock_levels (sku_id, location_id, current_stock, minimum_stock)
    VALUES ('SKU-PROD-001', 'a3bb189e-8bf9-3888-9912-ace4e6543002', 3, 10)
    ON CONFLICT (sku_id, location_id) DO UPDATE
        SET current_stock = 3;

    -- Este despacho debe disparar critical_threshold_reached (stock=3 < minimum=10)
    INSERT INTO inventory_movements (movement_type, sku_id, location_id, quantity)
    VALUES ('stock_dispatched', 'SKU-PROD-001', 'a3bb189e-8bf9-3888-9912-ace4e6543002', -5);

    SELECT event_type, payload, status
    FROM   inventory_outbox_events
    ORDER  BY created_at DESC
    LIMIT  2;
ROLLBACK;
*/

-- ---
-- Consultar estado del outbox en producción
-- ---
/*
SELECT
    status,
    COUNT(*)         AS total,
    MIN(created_at)  AS mas_antiguo,
    MAX(attempts)    AS max_intentos
FROM inventory_outbox_events
GROUP BY status
ORDER BY status;
*/
