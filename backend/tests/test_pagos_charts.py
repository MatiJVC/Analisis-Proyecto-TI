"""
Tests de los dos gráficos analíticos nuevos del módulo de pagos (jul-2026):

  • get_sla_timeline       — serie diaria de downtime/degradación (fact_sla_events)
  • get_cierres_descuadre  — descuadre reportado-vs-interno (cierre_diario)
  • GET /v1/auditoria/cierres — contrato del endpoint

La lógica de solape por día de get_sla_timeline y el mapeo/orden de
get_cierres_descuadre se prueban con SQLite in-memory (ambas tablas usan tipos
estándar compatibles). El endpoint se prueba a nivel de ruta mockeando el servicio,
igual que test_payments_analytics.py.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.pagos.models.fact_sla_events import FactSlaEvent
from app.pagos.models.cierre_diario import CierreDiario
from app.pagos.services.sla_service import get_sla_timeline
from app.pagos.services.auditoria_service import get_cierres_descuadre


# ─── get_sla_timeline (SQLite) ───────────────────────────────────────────────

class TestGetSlaTimeline:

    @pytest.fixture
    def sla_session(self, db_session):
        """db_session + tabla fact_sla_events creada en el engine SQLite."""
        FactSlaEvent.__table__.create(db_session.get_bind(), checkfirst=True)
        yield db_session

    def test_devuelve_un_punto_por_dia(self, sla_session):
        result = get_sla_timeline(sla_session, days=14)
        assert len(result) == 14
        # Ordenado ascendente por fecha, sin huecos.
        fechas = [p["date"] for p in result]
        assert fechas == sorted(fechas)
        for p in result:
            assert set(p.keys()) == {"date", "downtimeMinutes", "degradedMinutes"}

    def test_sin_eventos_todo_en_cero(self, sla_session):
        result = get_sla_timeline(sla_session, days=7)
        assert all(p["downtimeMinutes"] == 0.0 and p["degradedMinutes"] == 0.0 for p in result)

    def test_downtime_cerrado_suma_minutos(self, sla_session):
        # Evento de 30 min de downtime hace 2 días.
        inicio = datetime.now(tz=timezone.utc) - timedelta(days=2)
        sla_session.add(FactSlaEvent(
            tipo="downtime",
            timestamp_inicio=inicio,
            timestamp_fin=inicio + timedelta(minutes=30),
        ))
        sla_session.flush()

        result = get_sla_timeline(sla_session, days=14)
        total_down = sum(p["downtimeMinutes"] for p in result)
        total_deg = sum(p["degradedMinutes"] for p in result)
        assert total_down == pytest.approx(30.0, abs=0.1)
        assert total_deg == 0.0

    def test_separa_downtime_de_degraded(self, sla_session):
        base = datetime.now(tz=timezone.utc) - timedelta(days=1)
        sla_session.add(FactSlaEvent(
            tipo="downtime", timestamp_inicio=base, timestamp_fin=base + timedelta(minutes=10),
        ))
        sla_session.add(FactSlaEvent(
            tipo="degraded", timestamp_inicio=base, timestamp_fin=base + timedelta(minutes=20),
        ))
        sla_session.flush()

        result = get_sla_timeline(sla_session, days=14)
        assert sum(p["downtimeMinutes"] for p in result) == pytest.approx(10.0, abs=0.1)
        assert sum(p["degradedMinutes"] for p in result) == pytest.approx(20.0, abs=0.1)

    def test_evento_abierto_se_recorta_a_ahora(self, sla_session):
        # Evento abierto (fin NULL) iniciado hace 20 min → ~20 min de downtime hoy.
        inicio = datetime.now(tz=timezone.utc) - timedelta(minutes=20)
        sla_session.add(FactSlaEvent(
            tipo="downtime", timestamp_inicio=inicio, timestamp_fin=None,
        ))
        sla_session.flush()

        result = get_sla_timeline(sla_session, days=7)
        total_down = sum(p["downtimeMinutes"] for p in result)
        assert total_down == pytest.approx(20.0, abs=1.0)


# ─── get_cierres_descuadre (SQLite) ──────────────────────────────────────────

class TestGetCierresDescuadre:

    @pytest.fixture
    def cierre_session(self, db_session):
        CierreDiario.__table__.create(db_session.get_bind(), checkfirst=True)
        yield db_session

    def _add_cierre(self, db, fecha, r_total, r_count, i_total, i_count):
        db.add(CierreDiario(
            fecha=fecha,
            reported_total=r_total, reported_count=r_count,
            internal_total=i_total, internal_count=i_count,
            estado_id=1,
        ))

    def test_orden_ascendente_por_fecha(self, cierre_session):
        from datetime import date
        self._add_cierre(cierre_session, date(2026, 7, 3), 300, 30, 300, 30)
        self._add_cierre(cierre_session, date(2026, 7, 1), 100, 10, 100, 10)
        self._add_cierre(cierre_session, date(2026, 7, 2), 200, 20, 200, 20)
        cierre_session.flush()

        result = get_cierres_descuadre(cierre_session, limit=30)
        fechas = [c["fecha"] for c in result]
        assert fechas == ["2026-07-01", "2026-07-02", "2026-07-03"]

    def test_limit_toma_los_mas_recientes(self, cierre_session):
        from datetime import date
        for d in range(1, 6):
            self._add_cierre(cierre_session, date(2026, 7, d), d * 100, d * 10, d * 100, d * 10)
        cierre_session.flush()

        result = get_cierres_descuadre(cierre_session, limit=2)
        fechas = [c["fecha"] for c in result]
        # Los 2 más recientes, en orden ascendente.
        assert fechas == ["2026-07-04", "2026-07-05"]

    def test_internal_none_se_mapea_a_null(self, cierre_session):
        from datetime import date
        self._add_cierre(cierre_session, date(2026, 7, 1), 500, 50, None, None)
        cierre_session.flush()

        result = get_cierres_descuadre(cierre_session, limit=30)
        assert result[0]["internalTotal"] is None
        assert result[0]["internalCount"] is None
        assert result[0]["reportedTotal"] == 500.0
        assert result[0]["reportedCount"] == 50


# ─── GET /v1/auditoria/cierres (contrato de ruta) ────────────────────────────

_CIERRES_DATA = [
    {"fecha": "2026-07-01", "reportedTotal": 100.0, "internalTotal": 99.0,
     "reportedCount": 10, "internalCount": 9},
    {"fecha": "2026-07-02", "reportedTotal": 200.0, "internalTotal": None,
     "reportedCount": 20, "internalCount": None},
]


class TestCierresEndpoint:

    def test_returns_200_list(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.auditoria.get_cierres_descuadre",
            lambda db, limit: _CIERRES_DATA,
        )
        resp = client.get("/v1/auditoria/cierres")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_each_point_has_required_fields(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.auditoria.get_cierres_descuadre",
            lambda db, limit: _CIERRES_DATA,
        )
        body = client.get("/v1/auditoria/cierres").json()
        for point in body:
            for field in ("fecha", "reportedTotal", "internalTotal",
                          "reportedCount", "internalCount"):
                assert field in point, f"Missing field: {field}"

    def test_internal_null_round_trips(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.auditoria.get_cierres_descuadre",
            lambda db, limit: _CIERRES_DATA,
        )
        body = client.get("/v1/auditoria/cierres").json()
        assert body[1]["internalTotal"] is None

    def test_default_limit_is_30(self, client: TestClient, monkeypatch):
        captured = {}
        def _capture(db, limit):
            captured["limit"] = limit
            return _CIERRES_DATA
        monkeypatch.setattr("app.pagos.routes.auditoria.get_cierres_descuadre", _capture)
        client.get("/v1/auditoria/cierres")
        assert captured["limit"] == 30

    def test_limit_over_180_returns_422(self, client: TestClient):
        assert client.get("/v1/auditoria/cierres?limit=181").status_code == 422

    def test_service_error_returns_500(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.auditoria.get_cierres_descuadre",
            lambda db, limit: (_ for _ in ()).throw(RuntimeError("cierres fail")),
        )
        assert client.get("/v1/auditoria/cierres").status_code == 500
