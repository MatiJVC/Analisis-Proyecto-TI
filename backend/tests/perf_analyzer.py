"""
=============================================================================
  ANALIZADOR DE RESULTADOS  —  POST /events  Load Test
=============================================================================

Lee los archivos CSV generados por Locust y produce:
  1. Tabla de percentiles de latencia por tipo de evento.
  2. Comparación de tamaño JSON vs Protocol Buffers (estimado).
  3. Análisis de throughput sostenido vs objetivo (100 RPS).
  4. Recomendación final de migración a Protobuf.

Uso:
  python backend/tests/perf_analyzer.py \\
         --stats  backend/tests/results/load_test_stats.csv \\
         --history backend/tests/results/load_test_stats_history.csv \\
         --target-rps 100

Los archivos CSV se generan con:
  locust ... --csv backend/tests/results/load_test
=============================================================================
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Factores de compresión JSON → Protobuf3 (fracción del tamaño JSON)
# Metodología: benchmarks de Google LLC (2014) + Auth0 Engineering (2021).
# Rango típico para payloads < 512 B: 0.28–0.45
PROTO_FACTORS: Dict[str, float] = {
    "stock_received":             0.36,
    "stock_dispatched":           0.37,
    "stock_reserved":             0.40,
    "stock_out_error":            0.30,
    "critical_threshold_reached": 0.30,
    "[Aggregated]":               0.36,  # fallback para la fila total de Locust
}

# Umbrales de latencia (ms)
P95_WARN  = 200
P95_CRIT  = 500
P99_WARN  = 400
P99_CRIT  = 1000

# Umbral de error rate (%)
ERR_WARN  = 1.0
ERR_CRIT  = 5.0

# Colores ANSI (desactivar con NO_COLOR=1)
_USE_COLOR = os.getenv("NO_COLOR", "") == "" and sys.stdout.isatty()

def _c(text: str, code: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"

RED    = "31"
YELLOW = "33"
GREEN  = "32"
CYAN   = "36"
BOLD   = "1"
DIM    = "2"


# ---------------------------------------------------------------------------
# Parsers de CSV de Locust
# ---------------------------------------------------------------------------

def parse_stats_csv(path: str) -> List[Dict[str, Any]]:
    """
    Lee load_test_stats.csv de Locust.
    Columnas relevantes: Name, Request Count, Failure Count,
    Median Response Time, 95%ile, 99%ile, Average Response Time,
    Max Response Time, Average Content Size, Requests/s.
    """
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row.get("Name") in ("", "Aggregated"):
                continue
            rows.append({
                "name":       row["Name"],
                "count":      int(row.get("Request Count", 0) or 0),
                "failures":   int(row.get("Failure Count", 0) or 0),
                "p50_ms":     float(row.get("Median Response Time", 0) or 0),
                "p95_ms":     float(row.get("95%ile (ms)", row.get("95%ile", 0)) or 0),
                "p99_ms":     float(row.get("99%ile (ms)", row.get("99%ile", 0)) or 0),
                "avg_ms":     float(row.get("Average Response Time", 0) or 0),
                "max_ms":     float(row.get("Max Response Time", 0) or 0),
                "avg_bytes":  float(row.get("Average Content Size", 0) or 0),
                "rps":        float(row.get("Requests/s", 0) or 0),
            })
    return rows


def parse_history_csv(path: str) -> List[Dict[str, Any]]:
    """
    Lee load_test_stats_history.csv para calcular throughput sostenido
    y detectar degradación de latencia con el tiempo.
    """
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row.get("Name") not in ("[Aggregated]", "Aggregated"):
                continue
            rows.append({
                "timestamp": int(row.get("Timestamp", 0)),
                "rps":       float(row.get("Requests/s", 0) or 0),
                "p95_ms":    float(row.get("95%ile (ms)", row.get("95%ile", 0)) or 0),
                "failures":  int(row.get("Failure Count", 0) or 0),
            })
    return rows


# ---------------------------------------------------------------------------
# Funciones de análisis
# ---------------------------------------------------------------------------

def _event_type_from_name(name: str) -> str:
    """Extrae el event_type del nombre de la tarea Locust '[event_type]'."""
    if "[" in name and "]" in name:
        return name.split("[")[-1].rstrip("]")
    return name


def _latency_color(ms: float, warn: float, crit: float) -> str:
    if ms >= crit:
        return RED
    if ms >= warn:
        return YELLOW
    return GREEN


def _error_color(rate: float) -> str:
    if rate >= ERR_CRIT:
        return RED
    if rate >= ERR_WARN:
        return YELLOW
    return GREEN


def analyze(
    stats_path:   str,
    history_path: Optional[str],
    target_rps:   float,
) -> None:

    if not os.path.exists(stats_path):
        print(f"[perf_analyzer] Archivo no encontrado: {stats_path}")
        print("  Asegúrese de ejecutar Locust con: --csv backend/tests/results/load_test")
        sys.exit(1)

    rows = parse_stats_csv(stats_path)
    if not rows:
        print("[perf_analyzer] El archivo de estadísticas está vacío.")
        sys.exit(1)

    history = parse_history_csv(history_path) if history_path and os.path.exists(history_path) else []

    sep  = "=" * 82
    sep2 = "-" * 82

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{_c(sep, BOLD)}")
    print(_c(f"  ANÁLISIS DE PERFORMANCE  —  POST /events  [{now}]", BOLD))
    print(_c(sep, BOLD))

    # ─────────────────────────────────────────────────────────────────────────
    # TABLA 1: Latencias por tipo de evento
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n  {_c('LATENCIA POR TIPO DE EVENTO (ms)', BOLD)}\n")

    hdr_lat = (
        f"  {'Tipo de evento':<35} {'count':>7} "
        f"{'p50':>7} {'p95':>7} {'p99':>7} {'avg':>7} {'max':>8} {'err%':>6}"
    )
    print(_c(hdr_lat, DIM))
    print(f"  {sep2}")

    total_count    = 0
    total_failures = 0
    warn_events: List[str] = []
    crit_events: List[str] = []

    for row in rows:
        event_type = _event_type_from_name(row["name"])
        count      = row["count"]
        failures   = row["failures"]
        err_rate   = (failures / count * 100) if count else 0
        total_count    += count
        total_failures += failures

        p95_col  = _c(f"{row['p95_ms']:>7.1f}", _latency_color(row["p95_ms"], P95_WARN, P95_CRIT))
        p99_col  = _c(f"{row['p99_ms']:>7.1f}", _latency_color(row["p99_ms"], P99_WARN, P99_CRIT))
        err_col  = _c(f"{err_rate:>5.1f}%", _error_color(err_rate))

        print(
            f"  {event_type:<35} {count:>7} "
            f"{row['p50_ms']:>7.1f} {p95_col} {p99_col} "
            f"{row['avg_ms']:>7.1f} {row['max_ms']:>8.1f} {err_col}"
        )

        if row["p95_ms"] >= P95_CRIT:
            crit_events.append(event_type)
        elif row["p95_ms"] >= P95_WARN:
            warn_events.append(event_type)

    global_err = (total_failures / total_count * 100) if total_count else 0
    print(f"  {sep2}")
    print(
        f"  {'TOTAL':<35} {total_count:>7} "
        f"{'—':>7} {'—':>7} {'—':>7} {'—':>7} {'—':>8} "
        + _c(f"{global_err:>5.1f}%", _error_color(global_err))
    )

    # ─────────────────────────────────────────────────────────────────────────
    # TABLA 2: Throughput sostenido (del history)
    # ─────────────────────────────────────────────────────────────────────────
    if history:
        sustained_rps = [h["rps"] for h in history if h["rps"] > 0]
        rps_values    = sustained_rps[-20:] if len(sustained_rps) > 20 else sustained_rps
        avg_rps   = sum(rps_values) / len(rps_values) if rps_values else 0
        min_rps   = min(rps_values) if rps_values else 0
        max_rps   = max(rps_values) if rps_values else 0
        drift_pct = abs(avg_rps - target_rps) / target_rps * 100 if target_rps else 0

        print(f"\n\n  {_c('THROUGHPUT SOSTENIDO', BOLD)}\n")
        print(f"  Objetivo          : {target_rps:.0f} RPS")
        rps_col = _c(f"{avg_rps:.1f} RPS", GREEN if drift_pct < 10 else YELLOW if drift_pct < 20 else RED)
        print(f"  Promedio medido   : {rps_col}  (desviación del objetivo: {drift_pct:.1f}%)")
        print(f"  Mínimo / Máximo   : {min_rps:.1f} / {max_rps:.1f} RPS  (ventana: últimos {len(rps_values)} puntos)")

        # Detectar degradación progresiva de latencia
        if len(history) >= 10:
            first_half = [h["p95_ms"] for h in history[:len(history)//2] if h["p95_ms"] > 0]
            second_half= [h["p95_ms"] for h in history[len(history)//2:] if h["p95_ms"] > 0]
            if first_half and second_half:
                p95_start = sum(first_half) / len(first_half)
                p95_end   = sum(second_half) / len(second_half)
                degradation = (p95_end - p95_start) / p95_start * 100 if p95_start else 0
                deg_color = RED if degradation > 20 else YELLOW if degradation > 5 else GREEN
                print(
                    f"  Degradación p95   : {_c(f'{degradation:+.1f}%', deg_color)} "
                    f"(inicio: {p95_start:.0f} ms → fin: {p95_end:.0f} ms)"
                )

    # ─────────────────────────────────────────────────────────────────────────
    # TABLA 3: JSON vs Protobuf
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n\n  {_c('ANÁLISIS DE PAYLOAD  —  JSON vs Protocol Buffers 3', BOLD)}\n")

    hdr_size = (
        f"  {'Tipo de evento':<35} {'JSON avg(B)':>11} {'Proto est.(B)':>13} "
        f"{'Ahorro':>8} {'KB total JSON':>14} {'KB total Proto':>15}"
    )
    print(_c(hdr_size, DIM))
    print(f"  {sep2}")

    total_json_kb  = 0.0
    total_proto_kb = 0.0

    for row in rows:
        event_type = _event_type_from_name(row["name"])
        avg_json   = row["avg_bytes"]
        factor     = PROTO_FACTORS.get(event_type, 0.37)
        avg_proto  = avg_json * factor
        saving     = (1 - factor) * 100
        json_kb    = avg_json  * row["count"] / 1024
        proto_kb   = avg_proto * row["count"] / 1024
        total_json_kb  += json_kb
        total_proto_kb += proto_kb

        saving_col = _c(f"{saving:.0f}%", GREEN if saving >= 50 else YELLOW if saving >= 30 else DIM)
        print(
            f"  {event_type:<35} {avg_json:>11.0f} {avg_proto:>13.0f} "
            f"{saving_col:>8} {json_kb:>13.1f} {proto_kb:>14.1f}"
        )

    global_saving = (1 - total_proto_kb / total_json_kb) * 100 if total_json_kb else 0
    bw_saved_kb_s = (total_json_kb - total_proto_kb) / (total_count / target_rps) if target_rps and total_count else 0

    print(f"  {sep2}")
    print(
        f"  {'TOTAL ACUMULADO':<35} {'':>11} {'':>13} "
        + _c(f"{global_saving:>7.1f}%", GREEN if global_saving >= 40 else YELLOW)
        + f" {total_json_kb:>13.1f} {total_proto_kb:>14.1f}"
    )
    print(f"\n  Bandwidth ahorrado a {target_rps:.0f} RPS: {_c(f'{bw_saved_kb_s:.1f} KB/s', CYAN)}")
    print(f"  (equivale a {bw_saved_kb_s * 3600 / 1024:.1f} MB/hora en tráfico de red entrante)")

    # ─────────────────────────────────────────────────────────────────────────
    # RECOMENDACIÓN FINAL
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n\n  {_c('RECOMENDACIÓN DE MIGRACIÓN A PROTOCOL BUFFERS', BOLD)}\n")

    max_p95 = max((r["p95_ms"] for r in rows), default=0)
    max_p99 = max((r["p99_ms"] for r in rows), default=0)

    score = 0
    details: List[Tuple[str, str, str]] = []  # (symbol, label, detail)

    def _add(cond: bool, symbol: str, label: str, detail: str) -> None:
        nonlocal score
        if cond:
            score += 1
        details.append(("✗" if cond else "✓", label, detail))

    _add(max_p95 >= P95_CRIT,  "✗", "Latencia p95 CRÍTICA",
         f"p95 = {max_p95:.0f} ms  ≥  {P95_CRIT} ms")
    _add(max_p95 >= P95_WARN and max_p95 < P95_CRIT, "⚠", "Latencia p95 advertencia",
         f"p95 = {max_p95:.0f} ms  ∈  [{P95_WARN}, {P95_CRIT}) ms")
    _add(max_p99 >= P99_CRIT,  "✗", "Latencia p99 CRÍTICA",
         f"p99 = {max_p99:.0f} ms  ≥  {P99_CRIT} ms")
    _add(global_err >= ERR_WARN, "✗", "Tasa de error elevada",
         f"err = {global_err:.1f}%  ≥  {ERR_WARN}%")
    _add(global_saving >= 50,  "✗", "Ahorro de bandwidth > 50%",
         f"Protobuf reduciría {global_saving:.0f}% del tráfico")
    _add(bw_saved_kb_s >= 30,  "✗", "Ahorro absoluto > 30 KB/s",
         f"Equivale a {bw_saved_kb_s * 3600 / 1024:.0f} MB/hora")

    for sym, label, detail in details:
        col  = RED if sym == "✗" else GREEN
        line = f"  {_c(sym, col)}  {label:<35}  {detail}"
        print(line)

    print()
    if score >= 3:
        verdict_text = "MIGRAR A PROTOBUF"
        verdict_col  = RED
        verdict_icon = "🔴"
    elif score >= 1:
        verdict_text = "MONITOREAR / PRUEBA CON MÁS CARGA"
        verdict_col  = YELLOW
        verdict_icon = "🟡"
    else:
        verdict_text = "MANTENER JSON"
        verdict_col  = GREEN
        verdict_icon = "🟢"

    print(f"  Veredicto: {verdict_icon}  {_c(verdict_text, f'{BOLD};{verdict_col}')}")

    if score >= 3:
        print(f"\n  {_c('Pasos sugeridos para la migración:', BOLD)}")
        steps = [
            "Definir events.proto con los mensajes InventoryEvent, StockReservedPayload,",
            "  CriticalAlertPayload (espejo exacto de los schemas Pydantic actuales).",
            "Compilar: protoc --python_out=app/proto --pyi_out=app/proto events.proto",
            "Crear endpoint paralelo POST /events/proto con media type application/x-protobuf.",
            "Ejecutar este mismo test apuntando al nuevo endpoint para medir la mejora.",
            "Migrar gradualmente: enviar ambos formatos (JSON + Proto) durante 2 semanas.",
            "Deprecar el endpoint JSON una vez que el 95% del tráfico migre a Proto.",
        ]
        for i, step in enumerate(steps, 1):
            print(f"    {i}. {step}")

    print(f"\n{_c(sep, BOLD)}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Analiza los resultados del load test de POST /events.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--stats",
        default="backend/tests/results/load_test_stats.csv",
        help="Ruta al archivo load_test_stats.csv generado por Locust",
    )
    parser.add_argument(
        "--history",
        default="backend/tests/results/load_test_stats_history.csv",
        help="Ruta al archivo load_test_stats_history.csv (opcional)",
    )
    parser.add_argument(
        "--target-rps",
        type=float,
        default=100.0,
        help="RPS objetivo configurado en el test (default: 100)",
    )
    args = parser.parse_args()
    analyze(args.stats, args.history, args.target_rps)


if __name__ == "__main__":
    _cli()
