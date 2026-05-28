"""
Worker asíncrono que consume la tabla inventory_outbox_events del módulo de
Inventario (Grupo 5) y reenvía cada evento al endpoint POST /events de Analítica.

Modo de operación (doble mecanismo para mínima latencia):
  1. LISTEN en el canal 'inventory_analytics_channel'  →  reacción inmediata
  2. Polling cada POLL_INTERVAL_SECONDS                →  recuperación ante caídas

Instalación de dependencias (en la DB del Grupo 5):
    pip install asyncpg httpx

Variables de entorno requeridas:
    INVENTORY_DB_URL       postgresql://user:pass@host:5432/inventory_db
    ANALYTICS_EVENTS_URL   http://analytics-service:8000/events
    ANALYTICS_API_KEY      (opcional) Bearer token si el endpoint lo requiere

Ejecutar:
    python -m app.workers.inventory_outbox_worker
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from typing import Any

import asyncpg
import httpx
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

INVENTORY_DB_URL: str = os.environ["INVENTORY_DB_URL"]
ANALYTICS_EVENTS_URL: str = os.environ["ANALYTICS_EVENTS_URL"]
ANALYTICS_API_KEY: str | None = os.getenv("ANALYTICS_API_KEY")

NOTIFY_CHANNEL      = "inventory_analytics_channel"
POLL_INTERVAL_SEC   = 30          # Polling de respaldo cada 30 s
BATCH_SIZE          = 50          # Filas por ciclo de procesamiento
HTTP_TIMEOUT_SEC    = 10.0        # Timeout por llamada HTTP
RETRY_BACKOFF_BASE  = 2           # Base para backoff exponencial (segundos)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("inventory.outbox_worker")


# ---------------------------------------------------------------------------
# Consultas SQL
# ---------------------------------------------------------------------------

SQL_FETCH_PENDING = """
    SELECT id, source, event_type, payload, attempts
    FROM   inventory_outbox_events
    WHERE  status IN ('pending', 'retrying')
      AND  (last_attempt_at IS NULL
            OR last_attempt_at < NOW() - (POWER(2, LEAST(attempts, 5)) || ' seconds')::INTERVAL)
    ORDER  BY created_at
    LIMIT  $1
    FOR UPDATE SKIP LOCKED
"""

SQL_MARK_SENT = """
    UPDATE inventory_outbox_events
    SET    status   = 'sent',
           sent_at  = NOW(),
           attempts = attempts + 1,
           last_attempt_at = NOW(),
           error_message = NULL
    WHERE  id = $1
"""

SQL_MARK_RETRYING = """
    UPDATE inventory_outbox_events
    SET    status           = CASE WHEN attempts + 1 >= max_attempts THEN 'failed' ELSE 'retrying' END,
           attempts         = attempts + 1,
           last_attempt_at  = NOW(),
           error_message    = $2
    WHERE  id = $1
"""


# ---------------------------------------------------------------------------
# Construcción del envelope HTTP
# ---------------------------------------------------------------------------

def build_event_envelope(row: asyncpg.Record) -> dict[str, Any]:
    """
    Construye el cuerpo JSON para POST /events a partir de una fila del outbox.
    Estructura: { source, event_type, payload }
    """
    payload = row["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)

    return {
        "source":     row["source"],
        "event_type": row["event_type"],
        "payload":    payload,
    }


# ---------------------------------------------------------------------------
# Envío HTTP
# ---------------------------------------------------------------------------

async def send_event(client: httpx.AsyncClient, envelope: dict[str, Any]) -> None:
    """
    Realiza el POST /events. Lanza httpx.HTTPStatusError si el servidor
    responde con 4xx/5xx para que el caller gestione el reintento.
    """
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if ANALYTICS_API_KEY:
        headers["Authorization"] = f"Bearer {ANALYTICS_API_KEY}"

    response = await client.post(
        ANALYTICS_EVENTS_URL,
        json=envelope,
        headers=headers,
        timeout=HTTP_TIMEOUT_SEC,
    )
    # 4xx del servidor de Analítica indica payload inválido (no reintentar)
    # 5xx o red caída → reintentar con backoff
    response.raise_for_status()


# ---------------------------------------------------------------------------
# Procesamiento de un lote de filas outbox
# ---------------------------------------------------------------------------

async def process_batch(pool: asyncpg.Pool) -> int:
    """
    Lee hasta BATCH_SIZE filas pendientes, las envía y actualiza su estado.
    Devuelve el número de filas procesadas exitosamente.
    """
    sent_count = 0

    async with pool.acquire() as conn:
        async with conn.transaction():
            rows = await conn.fetch(SQL_FETCH_PENDING, BATCH_SIZE)

        if not rows:
            return 0

        async with httpx.AsyncClient() as client:
            for row in rows:
                outbox_id  = row["id"]
                event_type = row["event_type"]

                try:
                    envelope = build_event_envelope(row)
                    await send_event(client, envelope)

                    async with conn.transaction():
                        await conn.execute(SQL_MARK_SENT, outbox_id)

                    sent_count += 1
                    log.info(
                        "Evento enviado | outbox_id=%s event_type=%s",
                        outbox_id, event_type,
                    )

                except httpx.HTTPStatusError as exc:
                    status_code = exc.response.status_code
                    error_msg = (
                        f"HTTP {status_code}: {exc.response.text[:500]}"
                    )

                    if 400 <= status_code < 500:
                        # Error de validación del payload — marcar como 'failed'
                        # directamente para no reintentar indefinidamente.
                        log.error(
                            "Payload inválido para Analítica (no reintentable) | "
                            "outbox_id=%s event_type=%s status=%s body=%s",
                            outbox_id, event_type, status_code, exc.response.text[:300],
                        )
                        async with conn.transaction():
                            await conn.execute(
                                """UPDATE inventory_outbox_events
                                   SET status='failed', attempts=attempts+1,
                                       last_attempt_at=NOW(), error_message=$2
                                   WHERE id=$1""",
                                outbox_id, error_msg,
                            )
                    else:
                        log.warning(
                            "Error servidor Analítica — se reintentará | "
                            "outbox_id=%s event_type=%s error=%s",
                            outbox_id, event_type, error_msg,
                        )
                        async with conn.transaction():
                            await conn.execute(SQL_MARK_RETRYING, outbox_id, error_msg)

                except (httpx.RequestError, httpx.TimeoutException) as exc:
                    error_msg = f"Red/Timeout: {type(exc).__name__}: {exc}"
                    log.warning(
                        "Error de red — se reintentará | outbox_id=%s event_type=%s error=%s",
                        outbox_id, event_type, error_msg,
                    )
                    async with conn.transaction():
                        await conn.execute(SQL_MARK_RETRYING, outbox_id, error_msg)

                except Exception as exc:
                    error_msg = f"Error inesperado: {type(exc).__name__}: {exc}"
                    log.exception(
                        "Error inesperado procesando outbox_id=%s", outbox_id
                    )
                    async with conn.transaction():
                        await conn.execute(SQL_MARK_RETRYING, outbox_id, error_msg)

    return sent_count


# ---------------------------------------------------------------------------
# Loop LISTEN/NOTIFY — reacción inmediata ante nuevos eventos
# ---------------------------------------------------------------------------

async def listen_and_dispatch(pool: asyncpg.Pool, wake_event: asyncio.Event) -> None:
    """
    Se suscribe al canal pg_notify. Cada notificación recibida activa
    inmediatamente el ciclo de procesamiento del outbox.
    """
    async with pool.acquire() as conn:
        def _on_notify(
            conn: asyncpg.Connection,
            pid: int,
            channel: str,
            payload: str,
        ) -> None:
            log.debug("NOTIFY recibida | channel=%s payload=%s", channel, payload[:120])
            wake_event.set()

        await conn.add_listener(NOTIFY_CHANNEL, _on_notify)
        log.info("Escuchando canal pg_notify '%s'", NOTIFY_CHANNEL)

        # Mantener la conexión viva mientras no se reciba señal de cierre
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            await conn.remove_listener(NOTIFY_CHANNEL, _on_notify)
            raise


# ---------------------------------------------------------------------------
# Loop principal de procesamiento
# ---------------------------------------------------------------------------

async def processing_loop(pool: asyncpg.Pool, wake_event: asyncio.Event) -> None:
    """
    Procesa el outbox cada vez que:
      a) llega una notificación LISTEN/NOTIFY (wake_event.set), o
      b) transcurre POLL_INTERVAL_SECONDS sin notificaciones (fallback).
    """
    log.info(
        "Worker iniciado | analytics_url=%s poll_interval=%ss",
        ANALYTICS_EVENTS_URL, POLL_INTERVAL_SEC,
    )

    while True:
        try:
            # Esperar notificación o timeout del polling
            try:
                await asyncio.wait_for(wake_event.wait(), timeout=POLL_INTERVAL_SEC)
            except asyncio.TimeoutError:
                log.debug("Polling de respaldo activado (sin NOTIFY en los últimos %ss)", POLL_INTERVAL_SEC)

            wake_event.clear()

            # Draining: procesar lotes hasta agotar las filas pendientes
            while True:
                sent = await process_batch(pool)
                if sent < BATCH_SIZE:
                    break   # No hay más filas pendientes
                log.info("Lote completo procesado (%s eventos). Continuando...", sent)

        except asyncio.CancelledError:
            log.info("processing_loop cancelado, saliendo limpiamente.")
            break
        except Exception:
            log.exception("Error inesperado en processing_loop. Reintentando en 10s.")
            await asyncio.sleep(10)


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

async def main() -> None:
    pool = await asyncpg.create_pool(
        dsn=INVENTORY_DB_URL,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )

    wake_event = asyncio.Event()

    # Lanzar el listener y el loop de procesamiento en paralelo
    listener_task   = asyncio.create_task(listen_and_dispatch(pool, wake_event))
    processing_task = asyncio.create_task(processing_loop(pool, wake_event))

    # Manejo de señales para apagado limpio
    loop = asyncio.get_running_loop()

    def _shutdown(sig: signal.Signals) -> None:
        log.info("Señal %s recibida. Iniciando apagado...", sig.name)
        listener_task.cancel()
        processing_task.cancel()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _shutdown, sig)

    try:
        await asyncio.gather(listener_task, processing_task, return_exceptions=True)
    finally:
        await pool.close()
        log.info("Worker detenido. Pool de conexiones cerrado.")


if __name__ == "__main__":
    # Validar variables de entorno antes de iniciar
    missing = [v for v in ("INVENTORY_DB_URL", "ANALYTICS_EVENTS_URL") if not os.getenv(v)]
    if missing:
        log.error("Variables de entorno faltantes: %s", ", ".join(missing))
        sys.exit(1)

    asyncio.run(main())
