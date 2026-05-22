-- =============================================================================
-- Migration 003 — Vistas Silver: módulo CRM (Proyecto 07 → Proyecto 09)
--
-- Alineadas con el MER:
--   Cliente(id, identidad_id, nombre_completo, email, telefono, ...)
--   Ticket(id, cliente_id, agente_id, asunto, estado, prioridad, canal,
--          fecha_vencimiento_sla, pedido_id_ref, suscripcion_id_red)
--   Interaccion(id, ticket_id, autor_tipo, autor_id, contenido,
--               es_nota_interna, creado_en)
--   Articulo_kb(id, titulo, contenido, categoria)
--   Ticket_articulo(id, ticket_id, articulo_id, fue_enviado_al_cliente,
--                   agente_id, vinculado_en)
--
-- Estados  : Abierto | Progreso | Resuelto | Cerrado
-- Prioridad: Baja | Media | Alta | Crítica
-- Canal    : Chat | Email | Teléfono | App
-- SLA base : 8 horas para Crítica; umbrales 75% | 100% | 150%
-- =============================================================================


-- =============================================================================
-- vw_crm_tickets
-- Una fila por cada ticket.resuelto — base de análisis de tiempos y SLA.
-- =============================================================================
CREATE OR REPLACE VIEW vw_crm_tickets AS
SELECT
    id                                                                  AS raw_event_id,
    created_at                                                          AS ingested_at,

    -- Ticket
    payload ->> 'ticket_id'                                             AS ticket_id,
    payload ->> 'asunto'                                                AS asunto,
    payload ->> 'estado'                                                AS estado,

    -- Cliente (identidad_id = UUID público del Cliente)
    payload ->> 'cliente_identidad_id'                                  AS cliente_identidad_id,
    payload ->> 'email'                                                 AS email,

    -- Clasificación (enum del MER)
    payload ->> 'prioridad'                                             AS prioridad,
    payload ->> 'canal'                                                 AS canal,
    payload ->> 'source_project'                                        AS source_project,

    -- Agente
    payload ->> 'agente_id'                                             AS agente_id,

    -- Referencias cruzadas con otros proyectos
    payload ->> 'pedido_id_ref'                                         AS pedido_id_ref,
    payload ->> 'suscripcion_id_red'                                    AS suscripcion_id_red,

    -- Marcas temporales
    (payload ->> 'created_at')::TIMESTAMPTZ                            AS ticket_created_at,
    (payload ->> 'resolved_at')::TIMESTAMPTZ                           AS resolved_at,

    -- SLA
    (payload ->> 'resolution_time_hours')::NUMERIC                     AS resolution_time_hours,
    (payload ->> 'within_sla')::BOOLEAN                                AS within_sla,

    -- SLA crítico (8 h): solo aplica para prioridad Crítica
    CASE
        WHEN payload ->> 'prioridad' = 'Crítica'
        THEN (payload ->> 'resolution_time_hours')::NUMERIC <= 8.0
    END                                                                 AS cumple_sla_critico,

    -- Nivel numérico para ordenar (4=Crítica, 3=Alta, 2=Media, 1=Baja)
    CASE payload ->> 'prioridad'
        WHEN 'Crítica' THEN 4
        WHEN 'Alta'    THEN 3
        WHEN 'Media'   THEN 2
        WHEN 'Baja'    THEN 1
        ELSE 0
    END                                                                 AS prioridad_nivel,

    payload ->> 'resolution_notes'                                      AS resolution_notes

FROM raw_events
WHERE source     = 'crm'
  AND event_type = 'ticket.resuelto';

COMMENT ON VIEW vw_crm_tickets IS
    'Silver CRM: tickets resueltos con SLA, prioridad, canal, origen y refs cruzadas. Alineado con MER Ticket.';


-- =============================================================================
-- vw_crm_interacciones
-- Mapa la entidad Interaccion del MER.
-- Permite analizar volumen, tiempos de respuesta y uso de notas internas.
-- =============================================================================
CREATE OR REPLACE VIEW vw_crm_interacciones AS
SELECT
    id                                                                  AS raw_event_id,
    created_at                                                          AS ingested_at,

    payload ->> 'interaccion_id'                                        AS interaccion_id,
    payload ->> 'ticket_id'                                             AS ticket_id,

    -- Interaccion.autor_tipo: Cliente | Agente | Sistema
    payload ->> 'autor_tipo'                                            AS autor_tipo,
    payload ->> 'autor_id'                                              AS autor_id,

    payload ->> 'contenido'                                             AS contenido,

    -- Interaccion.es_nota_interna: True = solo agentes, False = visible al cliente
    (payload ->> 'es_nota_interna')::BOOLEAN                           AS es_nota_interna,

    (payload ->> 'creado_en')::TIMESTAMPTZ                             AS creado_en

FROM raw_events
WHERE source     = 'crm'
  AND event_type = 'interaccion.creada';

COMMENT ON VIEW vw_crm_interacciones IS
    'Silver CRM: interacciones sobre tickets (mensajes + notas internas). Mapa entidad Interaccion del MER.';


-- =============================================================================
-- vw_crm_ticket_articulo
-- Mapa la entidad Ticket_articulo del MER (junction Ticket ↔ Articulo_kb).
-- Base para calcular tasa de uso de KB.
-- =============================================================================
CREATE OR REPLACE VIEW vw_crm_ticket_articulo AS
SELECT
    id                                                                  AS raw_event_id,
    created_at                                                          AS ingested_at,

    -- Ticket_articulo.ticket_id (FK)
    payload ->> 'ticket_id'                                             AS ticket_id,

    -- Ticket_articulo.articulo_id (FK → Articulo_kb)
    payload ->> 'articulo_id'                                           AS articulo_id,

    -- Ticket_articulo.fue_enviado_al_cliente
    (payload ->> 'fue_enviado_al_cliente')::BOOLEAN                    AS fue_enviado_al_cliente,

    -- Ticket_articulo.agente_id
    payload ->> 'agente_id'                                             AS agente_id,

    -- Ticket_articulo.vinculado_en
    (payload ->> 'vinculado_en')::TIMESTAMPTZ                          AS vinculado_en,

    -- Datos enriquecidos de Articulo_kb (opcionales en el Bronze)
    payload ->> 'articulo_titulo'                                       AS articulo_titulo,
    payload ->> 'articulo_categoria'                                    AS articulo_categoria

FROM raw_events
WHERE source     = 'crm'
  AND event_type = 'kb.articulo.usado';

COMMENT ON VIEW vw_crm_ticket_articulo IS
    'Silver CRM: uso de artículos KB por ticket. Mapa entidad Ticket_articulo del MER.';


-- =============================================================================
-- vw_crm_tasa_kb
-- KPI global de uso de base de conocimiento (meta: 60%).
-- Lógica: tickets con ≥1 Ticket_articulo / total tickets resueltos
-- =============================================================================
CREATE OR REPLACE VIEW vw_crm_tasa_kb AS
WITH resueltos AS (
    SELECT DISTINCT payload ->> 'ticket_id' AS ticket_id
    FROM raw_events
    WHERE source = 'crm' AND event_type = 'ticket.resuelto'
),
con_kb AS (
    SELECT DISTINCT payload ->> 'ticket_id' AS ticket_id
    FROM raw_events
    WHERE source = 'crm' AND event_type = 'kb.articulo.usado'
)
SELECT
    COUNT(r.ticket_id)                                                  AS total_resueltos,
    COUNT(k.ticket_id)                                                  AS con_kb,
    ROUND(
        COUNT(k.ticket_id) * 100.0 / NULLIF(COUNT(r.ticket_id), 0), 2
    )                                                                   AS tasa_kb_pct,
    60.0                                                                AS meta_kb_pct,
    COUNT(k.ticket_id) * 100.0 / NULLIF(COUNT(r.ticket_id), 0) >= 60.0 AS cumple_meta
FROM resueltos r
LEFT JOIN con_kb k USING (ticket_id);

COMMENT ON VIEW vw_crm_tasa_kb IS
    'KPI: tasa de uso KB sobre tickets resueltos. tasa_kb_pct vs meta=60%. Entidad Ticket_articulo como fuente.';


-- =============================================================================
-- vw_crm_escalaciones
-- Violaciones SLA con threshold cruzado (75/100/150) y destino (Proyecto 11).
-- =============================================================================
CREATE OR REPLACE VIEW vw_crm_escalaciones AS
SELECT
    id                                                                  AS raw_event_id,
    created_at                                                          AS ingested_at,

    payload ->> 'ticket_id'                                             AS ticket_id,
    payload ->> 'cliente_identidad_id'                                  AS cliente_identidad_id,
    payload ->> 'prioridad'                                             AS prioridad,
    payload ->> 'estado'                                                AS estado,
    payload ->> 'source_project'                                        AS source_project,
    payload ->> 'canal'                                                 AS canal,

    -- SLA
    (payload ->> 'sla_threshold_hours')::NUMERIC                        AS sla_threshold_hours,
    (payload ->> 'elapsed_hours')::NUMERIC                             AS elapsed_hours,
    (payload ->> 'breach_percentage')::NUMERIC                         AS breach_percentage,

    -- Umbral específico cruzado (75 | 100 | 150)
    (payload ->> 'threshold_crossed')::INTEGER                         AS threshold_crossed,

    -- Nivel de gravedad
    CASE (payload ->> 'threshold_crossed')::INTEGER
        WHEN 75  THEN 'Advertencia'
        WHEN 100 THEN 'Crítico'
        WHEN 150 THEN 'Severo'
        ELSE          'Desconocido'
    END                                                                 AS nivel_gravedad,

    payload ->> 'escalado_hacia'                                        AS escalado_hacia,
    (payload ->> 'escalation_required')::BOOLEAN                       AS escalation_required,

    -- Marcas temporales (Ticket.fecha_vencimiento_sla del MER)
    (payload ->> 'fecha_vencimiento_sla')::TIMESTAMPTZ                 AS fecha_vencimiento_sla,
    (payload ->> 'created_at')::TIMESTAMPTZ                            AS ticket_created_at,
    (payload ->> 'violation_detected_at')::TIMESTAMPTZ                 AS violation_detected_at

FROM raw_events
WHERE source     = 'crm'
  AND event_type = 'ticket.sla_violado';

COMMENT ON VIEW vw_crm_escalaciones IS
    'Silver CRM: violaciones SLA. threshold_crossed (75/100/150), nivel_gravedad, destino escalamiento.';


-- =============================================================================
-- vw_crm_volumen_por_proyecto
-- Segmenta tickets por source_project para identificar proyectos con más soporte.
-- Dashboard: "¿qué proyecto origina más tickets de soporte?"
-- =============================================================================
CREATE OR REPLACE VIEW vw_crm_volumen_por_proyecto AS
SELECT
    payload ->> 'source_project'                                        AS source_project,
    payload ->> 'prioridad'                                             AS prioridad,
    payload ->> 'canal'                                                 AS canal,
    COUNT(*)                                                            AS total_tickets,
    MIN(created_at)                                                     AS primer_ticket,
    MAX(created_at)                                                     AS ultimo_ticket
FROM raw_events
WHERE source     = 'crm'
  AND event_type = 'ticket.creado'
GROUP BY
    payload ->> 'source_project',
    payload ->> 'prioridad',
    payload ->> 'canal'
ORDER BY total_tickets DESC;

COMMENT ON VIEW vw_crm_volumen_por_proyecto IS
    'Silver CRM: volumen de tickets por proyecto origen, prioridad y canal. Para detectar puntos de mejora del ecosistema.';


-- =============================================================================
-- vw_crm_ciclo_de_vida
-- Reconstruye el ciclo completo Abierto→Progreso→Resuelto→Cerrado por ticket.
-- Permite calcular tiempos de cada etapa.
-- =============================================================================
CREATE OR REPLACE VIEW vw_crm_ciclo_de_vida AS
SELECT
    ticket_id,
    MAX(CASE WHEN event_type = 'ticket.creado'   THEN ts END)          AS creado_at,
    MAX(CASE WHEN event_type = 'ticket.asignado' THEN ts END)          AS asignado_at,
    MAX(CASE WHEN event_type = 'ticket.escalado' THEN ts END)          AS escalado_at,
    MAX(CASE WHEN event_type = 'ticket.resuelto' THEN ts END)          AS resuelto_at,
    MAX(CASE WHEN event_type = 'ticket.cerrado'  THEN ts END)          AS cerrado_at,

    -- Tiempo hasta primera respuesta (minutos)
    EXTRACT(EPOCH FROM (
        MAX(CASE WHEN event_type = 'ticket.asignado' THEN ts END) -
        MAX(CASE WHEN event_type = 'ticket.creado'   THEN ts END)
    )) / 60.0                                                           AS tiempo_primera_respuesta_min,

    -- Tiempo total de resolución (horas)
    EXTRACT(EPOCH FROM (
        MAX(CASE WHEN event_type = 'ticket.resuelto' THEN ts END) -
        MAX(CASE WHEN event_type = 'ticket.creado'   THEN ts END)
    )) / 3600.0                                                         AS tiempo_resolucion_horas,

    -- ¿Fue escalado al Proyecto 11?
    BOOL_OR(event_type = 'ticket.escalado')                            AS fue_escalado

FROM (
    SELECT
        payload ->> 'ticket_id'                                         AS ticket_id,
        event_type,
        created_at                                                      AS ts
    FROM raw_events
    WHERE source = 'crm'
      AND event_type IN (
          'ticket.creado', 'ticket.asignado', 'ticket.escalado',
          'ticket.resuelto', 'ticket.cerrado'
      )
) ev
GROUP BY ticket_id;

COMMENT ON VIEW vw_crm_ciclo_de_vida IS
    'Silver CRM: tiempos de cada etapa del ciclo Abierto→Cerrado por ticket. Para SLAs y benchmarks.';
