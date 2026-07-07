"""
Tests de app.pagos.services.auditoria_service.generar_reporte_hoy.

Cubre una regresión real: el cierre diario debe calcular "hoy" en UTC, igual que
el resto del módulo de pagos (FactPagos.timestamp_evento, get_payment_kpis,
sla_service, etc.). Usar date.today() (hora LOCAL del servidor) puede diferir del
día calendario UTC en husos horarios detrás de UTC (ej. UTC-4), generando un
cierre con una ventana que no incluye eventos recién ingeridos — reporte con 0
transacciones pese a haber datos reales (detectado probando /pagos en jul-2026).
"""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from app.pagos.services.auditoria_service import generar_reporte_hoy


class _FixedDateTime(datetime):
    """Subclase de datetime que fija el instante devuelto por now(tz=...)."""

    _fixed_instant = datetime(2026, 1, 1, 2, 0, 0, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        if tz is not None:
            return cls._fixed_instant.astimezone(tz)
        return cls._fixed_instant


class _WrongLocalDate(date):
    """Simula date.today() devolviendo el día calendario LOCAL (distinto al UTC)."""

    @classmethod
    def today(cls):
        # Un huso horario detrás de UTC (ej. UTC-4) haría que la hora local
        # todavía sea "31 de diciembre" cuando en UTC ya es "1 de enero".
        return date(2025, 12, 31)


class TestGenerarReporteHoyUsaFechaUTC:

    @patch("app.pagos.services.auditoria_service.process_cierre_diario")
    @patch("app.pagos.services.auditoria_service.date", _WrongLocalDate)
    @patch("app.pagos.services.auditoria_service.datetime", _FixedDateTime)
    def test_usa_fecha_utc_no_fecha_local(self, mock_process, db_session=None):
        """Regresión: 'today' debe salir de datetime.now(tz=utc).date(), no de
        date.today() (local). Si el código revierte a date.today(), este test
        detecta que fecha=2025-12-31 (local) en vez de 2026-01-01 (UTC real)."""
        db = MagicMock()
        db.query.return_value.join.return_value.filter.return_value.one.return_value = MagicMock(
            cnt=0, total=0
        )

        generar_reporte_hoy(db)

        assert mock_process.called, "process_cierre_diario nunca fue llamado"
        payload = mock_process.call_args[0][1]
        assert payload["fecha"] == date(2026, 1, 1), (
            f"Se esperaba la fecha UTC (2026-01-01), pero se usó {payload['fecha']!r} "
            "— generar_reporte_hoy volvió a usar date.today() (hora local) en vez de UTC."
        )
