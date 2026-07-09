"""Tests del processor CRM con el payload NATIVO del CRM externo.

Verifica que crm_processor acepta los eventos tal como el CRM externo los
emitiría — `id` en vez de `ticket_id`, estado/prioridad/canal en minúscula,
`creado_en`/`actualizado_en` y SIN `resolution_time_hours`/`resolved_at` — y
que las KPIs de resolución (resolutionRate / avgResponseTimeMinutes) dejan de
dar 0 cuando esos eventos entran por el pipeline.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
from app.models.warehouse.fact_tickets import FactTicket
from app.models.warehouse.dim_clientes_crm import DimClienteCRM
from app.services.crm_analytics_service import get_crm_kpis

_TID = "b2fba3fb-6ca5-4924-855e-85bdd0b64a07"


class _RawEvent:
    """Stand-in mínimo de RawEvent (solo lo que usa process_crm_event)."""

    def __init__(self, event_type, payload):
        self.source = "crm"
        self.event_type = event_type
        self.payload = payload


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    FactTicket.__table__.create(engine, checkfirst=True)
    DimClienteCRM.__table__.create(engine, checkfirst=True)
    Session = sessionmaker(bind=engine, autoflush=False)
    s = Session()
    try:
        yield s
    finally:
        s.close()
        engine.dispose()


def _ingest(session, event_type, payload):
    return process_crm_event(session, _RawEvent(event_type, payload))


def _creado(**over):
    """Payload de creación en la forma nativa real del CRM externo."""
    p = {
        "id": _TID,                       # nativo: 'id', no 'ticket_id'
        "asunto": "hola brayan",
        "estado": "abierto",              # minúscula
        "prioridad": "critica",
        "canal": "email",
        "creado_en": "2026-07-09T10:00:00Z",
        "suscripcion_id_ref": "SUB-9",    # nativo: '_ref', no '_red'
    }
    p.update(over)
    return p


class TestPayloadNativo:
    def test_id_sirve_como_ticket_id_y_normaliza(self, session):
        t = _ingest(session, "ticket.creado", _creado())
        assert t.ticket_id == _TID
        assert t.estado == "Abierto"
        assert t.prioridad == "Crítica"
        assert t.canal == "Email"

    def test_opened_at_desde_creado_en(self, session):
        t = _ingest(session, "ticket.creado", _creado())
        assert (t.opened_at.year, t.opened_at.month, t.opened_at.day, t.opened_at.hour) == (2026, 7, 9, 10)

    def test_suscripcion_id_ref_aceptado(self, session):
        t = _ingest(session, "ticket.creado", _creado())
        assert t.suscripcion_id_red == "SUB-9"

    def test_transicion_referenciando_por_id(self, session):
        _ingest(session, "ticket.creado", _creado())
        t = _ingest(session, "ticket.asignado", {"id": _TID})
        assert t.estado == "Progreso"

    def test_resuelto_calcula_tiempo_desde_timestamps(self, session):
        _ingest(session, "ticket.creado", _creado())
        t = _ingest(session, "ticket.resuelto", {
            "id": _TID,
            "estado": "resuelto",
            "actualizado_en": "2026-07-09T12:00:00Z",   # +2h de creado_en
            "resolucion": "resuelto ok",
            # SIN resolution_time_hours ni resolved_at
        })
        assert t.estado == "Resuelto"
        assert t.resolved_at is not None
        assert t.resolution_time_hours == pytest.approx(2.0)
        assert t.resolucion == "resuelto ok"

    def test_resuelto_usa_opened_at_si_falta_creado_en(self, session):
        _ingest(session, "ticket.creado", _creado())    # opened_at = 10:00
        t = _ingest(session, "ticket.resuelto", {
            "id": _TID,
            "estado": "resuelto",
            "actualizado_en": "2026-07-09T13:00:00Z",   # +3h
        })
        assert t.resolution_time_hours == pytest.approx(3.0)

    def test_resuelto_respeta_resolution_time_explicito(self, session):
        _ingest(session, "ticket.creado", _creado())
        t = _ingest(session, "ticket.resuelto", {
            "id": _TID, "estado": "resuelto",
            "actualizado_en": "2026-07-09T12:00:00Z",
            "resolution_time_hours": 5.5,
        })
        assert t.resolution_time_hours == pytest.approx(5.5)

    def test_within_sla_derivado_del_vencimiento(self, session):
        _ingest(session, "ticket.creado", _creado(fecha_vencimiento_sla="2026-07-09T11:00:00Z"))
        t = _ingest(session, "ticket.resuelto", {
            "id": _TID, "estado": "resuelto",
            "actualizado_en": "2026-07-09T12:00:00Z",   # 12:00 > venc 11:00
        })
        assert t.within_sla is False

    def test_cerrado_directo_completa_resolucion(self, session):
        _ingest(session, "ticket.creado", _creado())    # opened 10:00
        t = _ingest(session, "ticket.cerrado", {
            "id": _TID, "estado": "cerrado",
            "actualizado_en": "2026-07-09T13:00:00Z",   # +3h
        })
        assert t.estado == "Cerrado"
        assert t.closed_at is not None
        assert t.resolved_at is not None                # completado para timeline/rate
        assert t.resolution_time_hours == pytest.approx(3.0)

    def test_estado_no_reconocido_sigue_fallando(self, session):
        with pytest.raises(CRMProcessingError):
            _ingest(session, "ticket.creado", _creado(estado="frozen"))


class TestKpisSeMuevenConPayloadNativo:
    def test_resolution_rate_y_tiempo_dejan_de_ser_cero(self, session):
        _ingest(session, "ticket.creado", _creado())
        _ingest(session, "ticket.resuelto", {
            "id": _TID, "estado": "resuelto",
            "actualizado_en": "2026-07-09T12:00:00Z",
        })
        session.flush()
        kpis = get_crm_kpis(session)
        assert kpis["resolutionRate"] == 100.0                       # 1 de 1
        assert kpis["avgResponseTimeMinutes"] == pytest.approx(120.0)  # 2h * 60
        assert kpis["openTickets"] == 0
