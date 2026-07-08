"""
Tests para app.services.crm_analytics_service.

Cubre todas las funciones del servicio usando mocks de sesión SQLAlchemy:
  - get_crm_kpis: estructura del dict, valores numéricos
  - get_crm_timeline: longitud de lista, campos por día
  - get_recent_tickets: límite respetado, campos del ticket serializado
  - get_sla_summary: totalViolations, criticalViolations, slaComplianceRate
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_db_scalar(value):
    """Mock que devuelve el mismo valor en .scalar() independiente de filtros."""
    db = MagicMock()
    db.query.return_value.scalar.return_value = value
    db.query.return_value.filter.return_value.scalar.return_value = value
    db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = value
    db.query.return_value.filter.return_value.filter.return_value.filter.return_value.scalar.return_value = value
    return db


def _make_db_rows(rows):
    """Mock que devuelve `rows` para .group_by(...).all(), con y sin .filter() previo."""
    db = MagicMock()
    db.query.return_value.filter.return_value.group_by.return_value.all.return_value = rows
    db.query.return_value.group_by.return_value.all.return_value = rows
    return db


def _make_ticket(ticket_id="T-001", asunto="Test", estado="Abierto",
                 prioridad="Media", canal="email", source_project="proj",
                 opened_at=None, updated_at=None):
    t = MagicMock()
    t.ticket_id = ticket_id
    t.asunto = asunto
    t.estado = estado
    t.prioridad = prioridad
    t.canal = canal
    t.source_project = source_project
    t.opened_at = opened_at or datetime(2026, 6, 1, 10, 0, 0)
    t.updated_at = updated_at or datetime(2026, 6, 1, 11, 0, 0)
    return t


# ─── get_crm_kpis ─────────────────────────────────────────────────────────────

class TestGetCrmKpis:
    def _make_kpi_db(self):
        db = MagicMock()
        # Orden de llamadas: total_customers, open_tickets,
        # avg_response_time, avg_csat, messages_today, resolved, total
        scalar_values = [50, 12, 2.5, 4.2, 30, 8, 20]
        scalar_iter = iter(scalar_values)

        def _scalar():
            try:
                return next(scalar_iter)
            except StopIteration:
                return 0

        db.query.return_value.scalar.side_effect = _scalar
        db.query.return_value.filter.return_value.scalar.side_effect = _scalar
        db.query.return_value.filter.return_value.in_.return_value.scalar.side_effect = _scalar
        db.query.return_value.filter.return_value.filter.return_value.scalar.side_effect = _scalar
        return db

    def test_returns_all_expected_keys(self):
        from app.services.crm_analytics_service import get_crm_kpis
        db = _make_db_scalar(0)
        result = get_crm_kpis(db)
        expected_keys = {
            "totalCustomers", "openTickets", "avgResponseTimeMinutes",
            "criticalTickets", "ticketsCreatedToday", "resolutionRate"
        }
        assert expected_keys.issubset(result.keys())

    def test_all_values_are_numeric(self):
        from app.services.crm_analytics_service import get_crm_kpis
        db = _make_db_scalar(0)
        result = get_crm_kpis(db)
        for key, val in result.items():
            assert isinstance(val, (int, float)), f"{key} debería ser numérico"

    def test_resolution_rate_never_divides_by_zero(self):
        """Cuando total=0, la lógica usa `total = ... or 1` para evitar ZeroDivisionError."""
        from app.services.crm_analytics_service import get_crm_kpis
        db = _make_db_scalar(0)
        result = get_crm_kpis(db)
        assert "resolutionRate" in result
        assert result["resolutionRate"] == 0.0

    def test_avg_response_time_none_returns_zero(self):
        from app.services.crm_analytics_service import get_crm_kpis
        db = MagicMock()
        # avg_response_time scalar devuelve None
        db.query.return_value.scalar.return_value = None
        db.query.return_value.filter.return_value.scalar.return_value = None
        db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = None
        result = get_crm_kpis(db)
        assert result["avgResponseTimeMinutes"] == 0.0

    def test_critical_tickets_and_created_today_are_ints(self):
        from app.services.crm_analytics_service import get_crm_kpis
        db = _make_db_scalar(3)
        result = get_crm_kpis(db)
        assert isinstance(result["criticalTickets"], int)
        assert isinstance(result["ticketsCreatedToday"], int)


# ─── get_crm_timeline ─────────────────────────────────────────────────────────

class TestGetCrmTimeline:
    def test_default_14_days(self):
        from app.services.crm_analytics_service import get_crm_timeline
        db = _make_db_scalar(0)
        result = get_crm_timeline(db)
        assert len(result) == 14

    def test_custom_days_parameter(self):
        from app.services.crm_analytics_service import get_crm_timeline
        db = _make_db_scalar(0)
        result = get_crm_timeline(db, days=7)
        assert len(result) == 7

    def test_each_point_has_required_fields(self):
        from app.services.crm_analytics_service import get_crm_timeline
        db = _make_db_scalar(0)
        result = get_crm_timeline(db, days=3)
        for point in result:
            assert "date" in point
            assert "opened" in point
            assert "resolved" in point

    def test_dates_are_in_iso_format(self):
        from app.services.crm_analytics_service import get_crm_timeline
        db = _make_db_scalar(0)
        result = get_crm_timeline(db, days=3)
        for point in result:
            # Debe poder parsearse como fecha YYYY-MM-DD
            datetime.strptime(point["date"], "%Y-%m-%d")

    def test_values_are_ints(self):
        from app.services.crm_analytics_service import get_crm_timeline
        db = _make_db_scalar(5)
        result = get_crm_timeline(db, days=2)
        for point in result:
            assert isinstance(point["opened"], int)
            assert isinstance(point["resolved"], int)

    def test_ordered_chronologically(self):
        from app.services.crm_analytics_service import get_crm_timeline
        db = _make_db_scalar(0)
        result = get_crm_timeline(db, days=5)
        dates = [point["date"] for point in result]
        assert dates == sorted(dates)


# ─── get_recent_tickets ───────────────────────────────────────────────────────

class TestGetRecentTickets:
    def test_returns_list_of_dicts(self):
        from app.services.crm_analytics_service import get_recent_tickets
        tickets = [_make_ticket("T-001"), _make_ticket("T-002")]
        db = MagicMock()
        db.query.return_value.order_by.return_value.limit.return_value.all.return_value = tickets
        result = get_recent_tickets(db, limit=10)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_each_ticket_has_all_fields(self):
        from app.services.crm_analytics_service import get_recent_tickets
        tickets = [_make_ticket()]
        db = MagicMock()
        db.query.return_value.order_by.return_value.limit.return_value.all.return_value = tickets
        result = get_recent_tickets(db)
        t = result[0]
        for field in ("ticketId", "asunto", "estado", "prioridad", "canal",
                      "sourceProject", "openedAt", "updatedAt"):
            assert field in t, f"Campo faltante: {field}"

    def test_respects_limit(self):
        from app.services.crm_analytics_service import get_recent_tickets
        db = MagicMock()
        db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
        get_recent_tickets(db, limit=5)
        db.query.return_value.order_by.return_value.limit.assert_called_with(5)

    def test_empty_db_returns_empty_list(self):
        from app.services.crm_analytics_service import get_recent_tickets
        db = MagicMock()
        db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
        result = get_recent_tickets(db)
        assert result == []

    def test_none_fields_default_to_empty_string(self):
        from app.services.crm_analytics_service import get_recent_tickets
        t = MagicMock()
        t.ticket_id = "T-999"
        t.asunto = None
        t.estado = "Abierto"
        t.prioridad = "Baja"
        t.canal = None
        t.source_project = None
        t.opened_at = datetime(2026, 6, 1, 10, 0, 0)
        t.updated_at = datetime(2026, 6, 1, 11, 0, 0)

        db = MagicMock()
        db.query.return_value.order_by.return_value.limit.return_value.all.return_value = [t]
        result = get_recent_tickets(db)
        assert result[0]["asunto"] == ""
        assert result[0]["canal"] == ""
        assert result[0]["sourceProject"] == ""


# ─── get_sla_summary ─────────────────────────────────────────────────────────

class TestGetSlaSummary:
    def test_returns_all_sla_keys(self):
        from app.services.crm_analytics_service import get_sla_summary
        db = _make_db_scalar(0)
        result = get_sla_summary(db)
        assert "totalViolations" in result
        assert "criticalViolations" in result
        assert "slaComplianceRate" in result
        assert "ticketsEvaluated" in result

    def test_sla_compliance_is_percentage(self):
        from app.services.crm_analytics_service import get_sla_summary
        db = _make_db_scalar(10)
        result = get_sla_summary(db)
        rate = result["slaComplianceRate"]
        assert 0.0 <= rate <= 100.0

    def test_all_violations_count_ints(self):
        from app.services.crm_analytics_service import get_sla_summary
        db = _make_db_scalar(5)
        result = get_sla_summary(db)
        assert isinstance(result["totalViolations"], int)
        assert isinstance(result["criticalViolations"], int)

    def test_no_tickets_evaluated_reports_zero(self):
        """Sin tickets evaluables: no lanza ZeroDivisionError, compliance 0.0 y
        ticketsEvaluated=0 (el frontend usa eso para mostrar 'Sin datos')."""
        from app.services.crm_analytics_service import get_sla_summary
        db = _make_db_scalar(0)
        result = get_sla_summary(db)
        assert result["slaComplianceRate"] == 0.0
        assert result["ticketsEvaluated"] == 0


# ─── get_tickets_by_channel ────────────────────────────────────────────────────

class TestGetTicketsByChannel:
    def test_returns_distribution_with_percentages(self):
        from app.services.crm_analytics_service import get_tickets_by_channel
        db = _make_db_rows([("Chat", 6), ("Email", 4)])
        result = get_tickets_by_channel(db)
        assert result["total"] == 10
        assert {"name": "Chat", "count": 6, "percentage": 60.0} in result["items"]
        assert {"name": "Email", "count": 4, "percentage": 40.0} in result["items"]

    def test_empty_returns_zero_total_no_division_error(self):
        from app.services.crm_analytics_service import get_tickets_by_channel
        db = _make_db_rows([])
        result = get_tickets_by_channel(db)
        assert result == {"total": 0, "items": []}

    def test_merges_mixed_casing(self):
        """Casing mezclado histórico ("email" vs "Email") se fusiona en una
        sola categoría canónica."""
        from app.services.crm_analytics_service import get_tickets_by_channel
        db = _make_db_rows([("email", 4), ("Email", 6), ("telefono", 5)])
        result = get_tickets_by_channel(db)
        assert result["total"] == 15
        by_name = {item["name"]: item["count"] for item in result["items"]}
        assert by_name == {"Email": 10, "Teléfono": 5}


# ─── get_tickets_by_priority ───────────────────────────────────────────────────

class TestGetTicketsByPriority:
    def test_returns_distribution(self):
        from app.services.crm_analytics_service import get_tickets_by_priority
        db = _make_db_rows([("Alta", 3), ("Media", 7)])
        result = get_tickets_by_priority(db)
        assert result["total"] == 10
        names = {item["name"] for item in result["items"]}
        assert names == {"Alta", "Media"}

    def test_merges_mixed_casing(self):
        """El bug reportado: "alta"/"Alta" y "critica"/"Crítica" ya no
        aparecen como categorías duplicadas."""
        from app.services.crm_analytics_service import get_tickets_by_priority
        db = _make_db_rows([
            ("alta", 2), ("Alta", 3),
            ("critica", 1), ("Crítica", 4),
            ("Media", 5),
        ])
        result = get_tickets_by_priority(db)
        assert result["total"] == 15
        by_name = {item["name"]: item["count"] for item in result["items"]}
        assert by_name == {"Alta": 5, "Crítica": 5, "Media": 5}


# ─── get_tickets_by_source_project ─────────────────────────────────────────────

class TestGetTicketsBySourceProject:
    def test_returns_distribution(self):
        from app.services.crm_analytics_service import get_tickets_by_source_project
        db = _make_db_rows([("orders", 5), ("pagos", 5)])
        result = get_tickets_by_source_project(db)
        assert result["total"] == 10
        assert all(item["percentage"] == 50.0 for item in result["items"])

    def test_empty_returns_zero_total(self):
        from app.services.crm_analytics_service import get_tickets_by_source_project
        db = _make_db_rows([])
        result = get_tickets_by_source_project(db)
        assert result == {"total": 0, "items": []}


# ─── _clasificar_modulo ─────────────────────────────────────────────────────────

class TestClasificarModulo:
    def test_agente_id_prefijo_numerico_mapea_grupo(self):
        from app.services.crm_analytics_service import _clasificar_modulo
        assert _clasificar_modulo("p8.agent@ucn.cl", None, None, None, None) == "IoT"
        assert _clasificar_modulo("p7.agent@ucn.cl", None, None, None, None) == "CRM"
        assert _clasificar_modulo("p1.agent@ucn.cl", None, None, None, None) == "Salud"

    def test_agente_id_numero_fuera_de_rango_cae_a_fallback(self):
        from app.services.crm_analytics_service import _clasificar_modulo
        assert _clasificar_modulo("p99.agent@ucn.cl", "PED-1", None, None, None) == "Pedidos"

    def test_sin_agente_id_usa_referencia_pedido(self):
        from app.services.crm_analytics_service import _clasificar_modulo
        assert _clasificar_modulo(None, "PED-1", None, None, None) == "Pedidos"

    def test_sin_agente_id_usa_referencia_pago(self):
        from app.services.crm_analytics_service import _clasificar_modulo
        assert _clasificar_modulo(None, None, "PAG-1", None, None) == "Pagos"

    def test_sin_agente_id_usa_referencia_salud(self):
        from app.services.crm_analytics_service import _clasificar_modulo
        assert _clasificar_modulo(None, None, None, "SAL-1", None) == "Salud"

    def test_sin_agente_id_usa_referencia_suscripcion(self):
        from app.services.crm_analytics_service import _clasificar_modulo
        assert _clasificar_modulo(None, None, None, None, "SUB-1") == "Suscripciones"

    def test_sin_nada_cae_a_crm(self):
        from app.services.crm_analytics_service import _clasificar_modulo
        assert _clasificar_modulo(None, None, None, None, None) == "CRM"

    def test_agente_id_sin_formato_p_numero_usa_fallback(self):
        from app.services.crm_analytics_service import _clasificar_modulo
        assert _clasificar_modulo("agente.random@ucn.cl", None, "PAG-1", None, None) == "Pagos"


# ─── get_critical_tickets_by_module ─────────────────────────────────────────────

class TestGetCriticalTicketsByModule:
    def test_agrupa_por_modulo_clasificado(self):
        from app.services.crm_analytics_service import get_critical_tickets_by_module
        db = MagicMock()
        rows = [
            ("p8.agent@ucn.cl", None, None, None, None),   # IoT
            ("p8.agent@ucn.cl", None, None, None, None),   # IoT
            (None, "PED-1", None, None, None),             # Pedidos
        ]
        db.query.return_value.filter.return_value.all.return_value = rows
        result = get_critical_tickets_by_module(db)
        assert result["total"] == 3
        by_name = {item["name"]: item["count"] for item in result["items"]}
        assert by_name == {"IoT": 2, "Pedidos": 1}

    def test_sin_tickets_criticos_devuelve_vacio(self):
        from app.services.crm_analytics_service import get_critical_tickets_by_module
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        result = get_critical_tickets_by_module(db)
        assert result == {"total": 0, "items": []}
