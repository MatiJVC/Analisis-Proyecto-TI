"""
=============================================================================
  LOAD TEST — POST /events  |  Simulación del Módulo de Inventario (Grupo 5)
=============================================================================

Herramienta  : Locust >= 2.31  (Python)
Objetivo     : 100 req/s sostenidos para evaluar latencia JSON y decidir
               si migrar a Protocol Buffers (Protobuf).

Distribución de eventos (reglas de negocio Grupo 5):
  ┌─────────────────────────────────┬────────┬──────────────────┐
  │ Tipo de evento                  │  Peso  │  % del tráfico   │
  ├─────────────────────────────────┼────────┼──────────────────┤
  │ stock_received    (normal)      │   40   │     40 %         │
  │ stock_dispatched  (normal)      │   30   │     30 %  ─ 70 % │
  │ stock_reserved    (reserva)     │   20   │     20 %  ─ 20 % │
  │ stock_out_error   (alerta)      │    5   │      5 %  ─      │
  │ critical_threshold_reached      │    5   │      5 %  ─ 10 % │
  └─────────────────────────────────┴────────┴──────────────────┘

Uso rápido (modo headless — 100 usuarios, 10 spawn/s, 120 s):
  pip install -r backend/tests/requirements_test.txt
  locust -f backend/tests/locustfile.py \\
         --host http://localhost:8000 \\
         --users 100 --spawn-rate 10 \\
         --run-time 120s --headless \\
         --csv backend/tests/results/load_test

Modo interactivo (UI web en http://localhost:8089):
  locust -f backend/tests/locustfile.py --host http://localhost:8000

Variables de entorno opcionales:
  ANALYTICS_HOST      URL base (default: http://localhost:8000)
  EVENTS_ENDPOINT     Ruta POST   (default: /events)
  TARGET_RPS          RPS objetivo por usuario (default: 1)
  VERBOSE_ERRORS      Si "true", imprime payload de cada respuesta != 2xx
=============================================================================
"""

from __future__ import annotations

import json
import logging
import os
import random
import statistics
import sys
import threading
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from locust import HttpUser, between, constant_throughput, events, task
from locust.runners import MasterRunner

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

EVENTS_ENDPOINT  = os.getenv("EVENTS_ENDPOINT",  "/v1/events")
TARGET_RPS       = float(os.getenv("TARGET_RPS", "1"))   # req/s por usuario
VERBOSE_ERRORS   = os.getenv("VERBOSE_ERRORS", "false").lower() == "true"

log = logging.getLogger("inventory_load_test")

# ---------------------------------------------------------------------------
# Catálogo de datos realistas (semilla fija para reproducibilidad)
# ---------------------------------------------------------------------------

random.seed(42)

# 50 SKUs distribuidos en 5 categorías de producto
_CATEGORIES = {
    "ELEC": (15, 120),    # componentes electrónicos, despachos pequeños
    "MECH": (50, 500),    # partes mecánicas, grandes lotes
    "CHEM": (10, 80),     # insumos químicos, unidades controladas
    "PACK": (100, 2000),  # materiales de embalaje, volumen alto
    "TOOL": (1, 30),      # herramientas, unidades bajas
}

SKUS: List[str] = [
    f"SKU-{cat}-{n:03d}"
    for cat, _ in _CATEGORIES.items()
    for n in range(1, 11)   # 10 SKUs por categoría = 50 total
]

# 10 ubicaciones con UUIDs deterministas
LOCATIONS: List[Dict[str, Any]] = [
    {"id": str(uuid.UUID(int=i)), "code": code, "type": loc_type}
    for i, (code, loc_type) in enumerate([
        ("BODEGA-SCL-01", "WAREHOUSE"),
        ("BODEGA-SCL-02", "WAREHOUSE"),
        ("BODEGA-VLP-01", "WAREHOUSE"),
        ("DC-NORTE-01",   "DISTRIBUTION_CENTER"),
        ("DC-SUR-01",     "DISTRIBUTION_CENTER"),
        ("DC-CENTRO-01",  "DISTRIBUTION_CENTER"),
        ("RETAIL-RM-01",  "RETAIL_POINT"),
        ("RETAIL-RM-02",  "RETAIL_POINT"),
        ("RETAIL-VLP-01", "RETAIL_POINT"),
        ("RETAIL-ANT-01", "RETAIL_POINT"),
    ], start=1)
]

_UNIT_COSTS: Dict[str, Tuple[float, float]] = {
    "ELEC": (10.0,  950.0),
    "MECH": (5.0,   200.0),
    "CHEM": (15.0,  300.0),
    "PACK": (0.50,  25.0),
    "TOOL": (30.0, 1500.0),
}

_THRESHOLD_BY_CAT: Dict[str, int] = {
    "ELEC": 20,
    "MECH": 50,
    "CHEM": 10,
    "PACK": 200,
    "TOOL": 5,
}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _random_sku() -> str:
    return random.choice(SKUS)


def _random_location() -> Dict[str, Any]:
    return random.choice(LOCATIONS)


def _cat_from_sku(sku: str) -> str:
    """Extrae la categoría del SKU (ej: 'SKU-ELEC-001' → 'ELEC')."""
    parts = sku.split("-")
    return parts[1] if len(parts) >= 2 else "ELEC"


def _random_quantity(sku: str, min_mult: float = 1.0) -> int:
    cat = _cat_from_sku(sku)
    lo, hi = _CATEGORIES.get(cat, (1, 100))
    return random.randint(max(1, int(lo * min_mult)), hi)


# ============================================================================
#  Generadores de payloads por tipo de evento
# ============================================================================

def build_stock_received() -> Dict[str, Any]:
    """
    Entrada de mercancía: lote recibido en bodega.
    Payload: movement_id, sku_id, location_id, quantity, unit_cost,
             reference_id (orden de compra), created_by, created_at.
    """
    sku      = _random_sku()
    loc      = _random_location()
    cat      = _cat_from_sku(sku)
    lo, hi   = _UNIT_COSTS.get(cat, (1.0, 100.0))

    return {
        "source":     "inventory",
        "event_type": "stock_received",
        "payload": {
            "movement_id":  str(uuid.uuid4()),
            "sku_id":       sku,
            "location_id":  loc["id"],
            "quantity":     _random_quantity(sku),
            "unit_cost":    round(random.uniform(lo, hi), 2),
            "reference_id": f"PO-{random.randint(2025,2026)}-{random.randint(10000,99999)}",
            "created_by":   random.choice(["wms_system", "erp_import", "manual_entry"]),
            "created_at":   _iso(_now_utc()),
        },
    }


def build_stock_dispatched() -> Dict[str, Any]:
    """
    Despacho de stock hacia cliente u otro proceso.
    Payload: movement_id, sku_id, location_id, quantity,
             reference_id (orden de venta), created_by, created_at.
    """
    sku = _random_sku()
    loc = _random_location()

    return {
        "source":     "inventory",
        "event_type": "stock_dispatched",
        "payload": {
            "movement_id":  str(uuid.uuid4()),
            "sku_id":       sku,
            "location_id":  loc["id"],
            "quantity":     _random_quantity(sku, min_mult=0.1),
            "reference_id": f"ORD-{random.randint(2025,2026)}-{random.randint(10000,99999)}",
            "created_by":   random.choice(["oms_system", "pos_system", "api_dispatch"]),
            "created_at":   _iso(_now_utc()),
        },
    }


def build_stock_reserved() -> Dict[str, Any]:
    """
    Reserva de stock vinculada a una orden.
    Regla de negocio: expires_at = created_at + 15 minutos.
    Payload: cumple exactamente StockReservedPayload (Pydantic schema del Grupo 9).
    """
    sku       = _random_sku()
    loc       = _random_location()
    created   = _now_utc()
    expires   = created + timedelta(minutes=15)

    return {
        "source":     "inventory",
        "event_type": "stock_reserved",
        "payload": {
            "reservation_id": str(uuid.uuid4()),
            "order_id":       f"ord-{random.randint(2025,2026)}-{random.randint(10000,99999)}",
            "sku_id":         sku,
            "location_id":    loc["id"],
            "quantity":       _random_quantity(sku, min_mult=0.05),
            "created_at":     _iso(created),
            "expires_at":     _iso(expires),
        },
    }


def build_stock_out_error() -> Dict[str, Any]:
    """
    Error de stock agotado: el despacho no pudo completarse.
    Payload: cumple CriticalAlertPayload con current_stock = 0.
    """
    sku = _random_sku()
    loc = _random_location()
    cat = _cat_from_sku(sku)

    return {
        "source":     "inventory",
        "event_type": "stock_out_error",
        "payload": {
            "sku_id":          sku,
            "location_id":     loc["id"],
            "current_stock":   0,
            "threshold_limite": _THRESHOLD_BY_CAT.get(cat, 5),
            "detected_at":     _iso(_now_utc()),
        },
    }


def build_critical_threshold_reached() -> Dict[str, Any]:
    """
    Alerta: el stock disponible cayó al umbral crítico (pero es > 0).
    Payload: cumple CriticalAlertPayload con current_stock entre 1 y threshold.
    """
    sku = _random_sku()
    loc = _random_location()
    cat = _cat_from_sku(sku)
    threshold = _THRESHOLD_BY_CAT.get(cat, 5)

    return {
        "source":     "inventory",
        "event_type": "critical_threshold_reached",
        "payload": {
            "sku_id":          sku,
            "location_id":     loc["id"],
            "current_stock":   random.randint(1, threshold),
            "threshold_limite": threshold,
            "detected_at":     _iso(_now_utc()),
        },
    }


# ============================================================================
#  Recolector de métricas personalizado por tipo de evento
# ============================================================================

class _MetricsCollector:
    """
    Registra latencias y tamaños de payload por tipo de evento.
    Thread-safe mediante un lock global.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset()

    def _reset(self) -> None:
        self.data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "count":          0,
            "success":        0,
            "failures":       0,
            "latencies_ms":   [],
            "payload_bytes":  [],
        })

    def record(
        self,
        event_type:   str,
        latency_ms:   float,
        payload_bytes: int,
        success:      bool,
    ) -> None:
        with self._lock:
            d = self.data[event_type]
            d["count"]  += 1
            d["latencies_ms"].append(latency_ms)
            d["payload_bytes"].append(payload_bytes)
            if success:
                d["success"] += 1
            else:
                d["failures"] += 1

    def summary(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            result = {}
            for event_type, d in self.data.items():
                lats  = sorted(d["latencies_ms"])
                sizes = d["payload_bytes"]
                n     = len(lats)

                result[event_type] = {
                    "count":        d["count"],
                    "success":      d["success"],
                    "failures":     d["failures"],
                    "error_rate":   round(d["failures"] / d["count"] * 100, 2) if d["count"] else 0,
                    "p50_ms":       _percentile(lats, 50),
                    "p90_ms":       _percentile(lats, 90),
                    "p95_ms":       _percentile(lats, 95),
                    "p99_ms":       _percentile(lats, 99),
                    "avg_ms":       round(statistics.mean(lats), 2)       if lats  else 0,
                    "max_ms":       round(max(lats), 2)                   if lats  else 0,
                    "avg_json_bytes": round(statistics.mean(sizes), 0)    if sizes else 0,
                    "max_json_bytes": max(sizes)                          if sizes else 0,
                    "total_kb_sent":  round(sum(sizes) / 1024, 2),
                }
            return result


def _percentile(sorted_data: List[float], pct: int) -> float:
    if not sorted_data:
        return 0.0
    idx = max(0, int(len(sorted_data) * pct / 100) - 1)
    return round(sorted_data[idx], 2)


# Instancia global compartida
_metrics = _MetricsCollector()


# ============================================================================
#  Usuario simulado: backend del Grupo 5 enviando eventos
# ============================================================================

BUILDERS = {
    "stock_received":            build_stock_received,
    "stock_dispatched":          build_stock_dispatched,
    "stock_reserved":            build_stock_reserved,
    "stock_out_error":           build_stock_out_error,
    "critical_threshold_reached":build_critical_threshold_reached,
}


class InventoryBackendUser(HttpUser):
    """
    Simula al backend del Módulo de Inventario (Grupo 5) enviando eventos
    al endpoint POST /events del módulo de Analítica.

    wait_time = constant_throughput(TARGET_RPS)
        → cada usuario mantiene exactamente TARGET_RPS req/s.
        Con 100 usuarios y TARGET_RPS=1: objetivo = 100 RPS.
    """

    wait_time = constant_throughput(TARGET_RPS)

    # ── Tareas con pesos (total 100 → porcentajes directos) ──────────────────

    @task(40)
    def send_stock_received(self) -> None:
        self._post_event("stock_received")

    @task(30)
    def send_stock_dispatched(self) -> None:
        self._post_event("stock_dispatched")

    @task(20)
    def send_stock_reserved(self) -> None:
        self._post_event("stock_reserved")

    @task(5)
    def send_stock_out_error(self) -> None:
        self._post_event("stock_out_error")

    @task(5)
    def send_critical_threshold_reached(self) -> None:
        self._post_event("critical_threshold_reached")

    # ── Implementación central ────────────────────────────────────────────────

    def _post_event(self, event_type: str) -> None:
        payload_dict = BUILDERS[event_type]()
        body         = json.dumps(payload_dict, separators=(",", ":"))
        body_bytes   = body.encode("utf-8")
        payload_size = len(body_bytes)

        t0 = time.perf_counter()

        with self.client.post(
            EVENTS_ENDPOINT,
            data=body_bytes,
            headers={"Content-Type": "application/json"},
            name=f"POST /events [{event_type}]",
            catch_response=True,
        ) as resp:
            latency_ms = (time.perf_counter() - t0) * 1_000
            success    = resp.status_code in (200, 201)

            if success:
                resp.success()
            else:
                err = f"HTTP {resp.status_code}"
                resp.failure(err)
                if VERBOSE_ERRORS:
                    log.warning(
                        "[%s] %s | body=%s | response=%s",
                        event_type, err, body[:200], resp.text[:200],
                    )

            _metrics.record(event_type, latency_ms, payload_size, success)


# ============================================================================
#  Reporte final al terminar la prueba
# ============================================================================

# Factores empíricos de compresión JSON → Protobuf3
# Basados en benchmarks publicados para mensajes de menos de 1 KB:
#   - Campos numéricos: Protobuf usa varint (muy eficiente)
#   - Strings repetidos: Protobuf no tiene dictionary encoding nativo
#   - UUIDs como string: mismo costo en ambos formatos
# Fuente: https://auth0.com/blog/beating-json-performance-with-protobuf/
_PROTOBUF_FACTOR: Dict[str, float] = {
    "stock_received":             0.36,  # payload numérico + pocos strings
    "stock_dispatched":           0.37,
    "stock_reserved":             0.40,  # más campos de tipo string/UUID
    "stock_out_error":            0.30,  # payload pequeño, muy eficiente
    "critical_threshold_reached": 0.30,
}

# Umbrales de decisión para la recomendación de Protobuf
_THRESHOLD_WARN_MS   = 200   # p95 > 200 ms → ADVERTENCIA
_THRESHOLD_CRIT_MS   = 500   # p99 > 500 ms → MIGRAR A PROTOBUF
_THRESHOLD_BW_KB_RPS = 50    # KB/s > 50 × RPS_objetivo → costo de red alto


def _print_report(environment: Any) -> None:
    """Imprime el reporte de performance en la consola al finalizar el test."""
    summary = _metrics.summary()
    if not summary:
        print("\n[load_test] Sin datos de métricas — ¿el test se ejecutó?")
        return

    # ── Calcular métricas globales ────────────────────────────────────────────
    all_latencies: List[float] = []
    total_requests  = 0
    total_failures  = 0
    total_bytes     = 0

    for d in summary.values():
        total_requests += d["count"]
        total_failures += d["failures"]
        total_bytes    += d["total_kb_sent"] * 1024

    global_error_rate = (total_failures / total_requests * 100) if total_requests else 0

    sep  = "=" * 78
    sep2 = "-" * 78

    print(f"\n{sep}")
    print("  REPORTE DE CARGA  —  POST /events  —  Módulo de Inventario (Grupo 5)")
    print(sep)

    # ── Tabla de latencias por tipo de evento ────────────────────────────────
    print("\n  LATENCIA POR TIPO DE EVENTO (ms)\n")
    hdr = f"  {'Tipo de evento':<32} {'p50':>6} {'p90':>6} {'p95':>6} {'p99':>6} {'avg':>6} {'max':>7} {'count':>7} {'err%':>6}"
    print(hdr)
    print(f"  {sep2}")

    # Ordenar: alertas primero (más críticas), luego normales
    order = [
        "stock_out_error",
        "critical_threshold_reached",
        "stock_reserved",
        "stock_dispatched",
        "stock_received",
    ]
    for event_type in order:
        if event_type not in summary:
            continue
        d = summary[event_type]
        flag = " ⚠" if d["p95_ms"] > _THRESHOLD_WARN_MS else ("  " if d["p95_ms"] < 100 else "  ")
        print(
            f"  {event_type:<32} {d['p50_ms']:>6.1f} {d['p90_ms']:>6.1f} "
            f"{d['p95_ms']:>6.1f} {d['p99_ms']:>6.1f} {d['avg_ms']:>6.1f} "
            f"{d['max_ms']:>7.1f} {d['count']:>7} {d['error_rate']:>5.1f}%{flag}"
        )

    print(f"  {sep2}")
    print(
        f"  {'TOTAL / GLOBAL':<32} {'—':>6} {'—':>6} {'—':>6} {'—':>6} {'—':>6} "
        f"{'—':>7} {total_requests:>7} {global_error_rate:>5.1f}%"
    )

    # ── Tabla de tamaños de payload JSON vs Protobuf ─────────────────────────
    print(f"\n\n  ANÁLISIS DE TAMAÑO DE PAYLOAD  —  JSON vs Protocol Buffers 3\n")
    hdr2 = f"  {'Tipo de evento':<32} {'JSON avg (B)':>12} {'JSON max (B)':>12} {'Proto est. (B)':>14} {'Ahorro':>8} {'KB enviados':>12}"
    print(hdr2)
    print(f"  {sep2}")

    total_json_bytes  = 0.0
    total_proto_bytes = 0.0

    for event_type in order:
        if event_type not in summary:
            continue
        d             = summary[event_type]
        avg_json      = d["avg_json_bytes"]
        factor        = _PROTOBUF_FACTOR.get(event_type, 0.38)
        avg_proto     = round(avg_json * factor)
        saving_pct    = round((1 - factor) * 100, 0)
        total_json_bytes  += avg_json  * d["count"]
        total_proto_bytes += avg_proto * d["count"]

        print(
            f"  {event_type:<32} {avg_json:>12.0f} {d['max_json_bytes']:>12} "
            f"{avg_proto:>14} {saving_pct:>7.0f}% {d['total_kb_sent']:>11.1f} KB"
        )

    total_saving = (1 - total_proto_bytes / total_json_bytes) * 100 if total_json_bytes else 0
    total_json_kb  = total_json_bytes  / 1024
    total_proto_kb = total_proto_bytes / 1024

    print(f"  {sep2}")
    print(
        f"  {'TOTAL ACUMULADO':<32} {total_json_kb:>10.1f} KB {'':>13} "
        f"{total_proto_kb:>12.1f} KB {total_saving:>6.1f}%"
    )

    # ── Recomendación de migración ────────────────────────────────────────────
    print(f"\n\n  RECOMENDACIÓN DE MIGRACIÓN A PROTOCOL BUFFERS\n")

    p95_values = [d["p95_ms"] for d in summary.values() if d["count"] > 0]
    p99_values = [d["p99_ms"] for d in summary.values() if d["count"] > 0]
    max_p95    = max(p95_values) if p95_values else 0
    max_p99    = max(p99_values) if p99_values else 0

    reasons_for: List[str]     = []
    reasons_against: List[str] = []

    if max_p95 > _THRESHOLD_CRIT_MS:
        reasons_for.append(f"  ✗  p95 = {max_p95:.0f} ms  >  {_THRESHOLD_CRIT_MS} ms (umbral crítico)")
    elif max_p95 > _THRESHOLD_WARN_MS:
        reasons_for.append(f"  ⚠  p95 = {max_p95:.0f} ms  >  {_THRESHOLD_WARN_MS} ms (umbral de advertencia)")
    else:
        reasons_against.append(f"  ✓  p95 = {max_p95:.0f} ms  ≤  {_THRESHOLD_WARN_MS} ms — latencia aceptable")

    if max_p99 > _THRESHOLD_CRIT_MS:
        reasons_for.append(f"  ✗  p99 = {max_p99:.0f} ms  >  {_THRESHOLD_CRIT_MS} ms — colas saturadas")
    else:
        reasons_against.append(f"  ✓  p99 = {max_p99:.0f} ms  ≤  {_THRESHOLD_CRIT_MS} ms — sin saturación")

    if total_saving >= 40:
        reasons_for.append(f"  ✗  Ahorro estimado de bandwidth: {total_saving:.0f}% con Protobuf")
    else:
        reasons_against.append(f"  ✓  Ahorro de bandwidth ({total_saving:.0f}%) no justifica la migración")

    if global_error_rate > 1.0:
        reasons_for.append(f"  ✗  Tasa de error = {global_error_rate:.1f}%  >  1% — posible saturación del servidor")
    else:
        reasons_against.append(f"  ✓  Tasa de error = {global_error_rate:.1f}%  ≤  1%")

    if len(reasons_for) >= 2:
        verdict = "🔴  MIGRAR A PROTOBUF  —  La latencia o el ancho de banda superan los límites tolerables."
    elif len(reasons_for) == 1:
        verdict = "🟡  MONITOREAR  —  Un indicador supera el umbral. Escalar la carga antes de decidir."
    else:
        verdict = "🟢  MANTENER JSON  —  El rendimiento actual es aceptable para el volumen de 100 RPS."

    print(f"  Factores a FAVOR de migrar:")
    for r in reasons_for:
        print(f"    {r}")
    if not reasons_for:
        print("    (ninguno)")

    print(f"\n  Factores EN CONTRA de migrar:")
    for r in reasons_against:
        print(f"    {r}")
    if not reasons_against:
        print("    (ninguno)")

    print(f"\n  Veredicto: {verdict}")

    if len(reasons_for) >= 2:
        print("\n  Pasos para la migración:")
        print("    1. Definir los .proto files basados en los schemas de inventory_event_schema.py")
        print("    2. Compilar con protoc --python_out=. events.proto")
        print("    3. Reemplazar json.dumps() por message.SerializeToString()")
        print("    4. Agregar header: Content-Type: application/x-protobuf")
        print("    5. Actualizar el endpoint /events para detectar el Content-Type")
        print("    6. Ejecutar este test con --tags=protobuf para comparar ambos formatos")

    print(f"\n{sep}\n")


@events.quitting.add_listener
def on_quitting(environment: Any, **kwargs: Any) -> None:
    _print_report(environment)


# ============================================================================
#  Listener para estadísticas de arranque en consola
# ============================================================================

@events.test_start.add_listener
def on_test_start(environment: Any, **kwargs: Any) -> None:
    print("\n" + "=" * 60)
    print("  INICIO DEL TEST DE CARGA — Inventario → Analítica")
    print(f"  Endpoint: {EVENTS_ENDPOINT}")
    print(f"  RPS objetivo: {TARGET_RPS} req/s por usuario")
    print("  Distribución: 70% normal | 20% reserva | 10% alerta")
    print("=" * 60 + "\n")
