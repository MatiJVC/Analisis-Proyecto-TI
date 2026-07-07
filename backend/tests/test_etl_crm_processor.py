"""
Tests para CRM ETL processor.

Cubre:
  - process_crm_event: todos los event_types soportados
  - Validación de campos requeridos (ticket_id, interaccion_id, articulo_id)
  - Manejo de event_type desconocido → CRMProcessingError
  - _parse_dt: strings ISO y None
  - _upsert_cliente: crea / actualiza DimClienteCRM
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_raw_event(event_type: str, payload: dict):
    raw = MagicMock()
    raw.event_type = event_type
    raw.payload = payload
    return raw


def _make_db(query_result=None):
    """Mock de sesión SQLAlchemy. query(...).filter(...).first() devuelve query_result."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = query_result
    return db


# ─── _parse_dt ────────────────────────────────────────────────────────────────

class TestParseDt:
    def test_none_returns_none(self):
        from app.etl.processors.crm_processor import _parse_dt
        assert _parse_dt(None) is None

    def test_datetime_passthrough(self):
        from app.etl.processors.crm_processor import _parse_dt
        dt = datetime(2026, 1, 15, 10, 0, 0)
        assert _parse_dt(dt) == dt

    def test_iso_string_parsed(self):
        from app.etl.processors.crm_processor import _parse_dt
        result = _parse_dt("2026-06-13T10:30:00")
        assert isinstance(result, datetime)
        assert result.year == 2026
        assert result.month == 6

    def test_iso_string_with_Z_parsed(self):
        from app.etl.processors.crm_processor import _parse_dt
        result = _parse_dt("2026-06-13T10:30:00Z")
        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_invalid_string_returns_none(self):
        from app.etl.processors.crm_processor import _parse_dt
        assert _parse_dt("not-a-date") is None

    def test_non_string_non_datetime_returns_none(self):
        from app.etl.processors.crm_processor import _parse_dt
        assert _parse_dt(12345) is None


# ─── process_crm_event: evento desconocido ────────────────────────────────────

class TestProcessCrmEventUnknown:
    def test_unknown_event_type_raises(self):
        from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
        db = _make_db()
        raw = _make_raw_event("evento.inexistente", {})
        with pytest.raises(CRMProcessingError, match="no soportado"):
            process_crm_event(db, raw)


# ─── ticket.creado ────────────────────────────────────────────────────────────

class TestHandleTicketCreado:
    def test_missing_ticket_id_raises(self):
        from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
        db = _make_db()
        raw = _make_raw_event("ticket.creado", {"asunto": "Test sin id"})
        with pytest.raises(CRMProcessingError, match="ticket_id"):
            process_crm_event(db, raw)

    def test_creates_ticket_and_flushes(self):
        from app.etl.processors.crm_processor import process_crm_event
        db = _make_db(query_result=None)  # ticket no existe aún
        payload = {
            "ticket_id": "T-001",
            "asunto": "Problema con factura",
            "estado": "Abierto",
            "prioridad": "Alta",
            "canal": "Email",
        }
        raw = _make_raw_event("ticket.creado", payload)
        result = process_crm_event(db, raw)
        assert db.add.called
        assert db.flush.called

    def test_upserts_cliente_when_identidad_present(self):
        from app.etl.processors.crm_processor import process_crm_event
        db = _make_db(query_result=None)
        payload = {
            "ticket_id": "T-002",
            "cliente_identidad_id": "CLI-99",
            "email": "test@example.com",
        }
        raw = _make_raw_event("ticket.creado", payload)
        process_crm_event(db, raw)
        # add llamado al menos una vez (para cliente y para ticket)
        assert db.add.call_count >= 1

    def test_skips_cliente_when_no_identidad(self):
        from app.etl.processors.crm_processor import _upsert_cliente
        db = _make_db()
        result = _upsert_cliente(db, {"email": "solo@email.com"})
        assert result is None
        db.add.assert_not_called()


# ─── ticket.asignado ─────────────────────────────────────────────────────────

class TestHandleTicketAsignado:
    def test_missing_ticket_id_raises(self):
        from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
        db = _make_db()
        raw = _make_raw_event("ticket.asignado", {"agente_id": "AGT-1"})
        with pytest.raises(CRMProcessingError, match="ticket_id"):
            process_crm_event(db, raw)

    def test_updates_agente_and_estado(self):
        from app.etl.processors.crm_processor import process_crm_event
        existing_ticket = MagicMock()
        existing_ticket.estado = "Abierto"
        existing_ticket.agente_id = None

        db = _make_db(query_result=existing_ticket)
        payload = {"ticket_id": "T-003", "agente_id": "AGT-5"}
        raw = _make_raw_event("ticket.asignado", payload)
        process_crm_event(db, raw)

        assert existing_ticket.agente_id == "AGT-5"
        assert existing_ticket.estado == "Progreso"
        assert db.flush.called

    def test_asignado_rechaza_si_ya_en_progreso(self):
        from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
        existing_ticket = MagicMock()
        existing_ticket.estado = "Progreso"
        existing_ticket.ticket_id = "T-003"

        db = _make_db(query_result=existing_ticket)
        raw = _make_raw_event("ticket.asignado", {"ticket_id": "T-003"})
        with pytest.raises(CRMProcessingError, match="Transición inválida"):
            process_crm_event(db, raw)

    def test_asignado_rechaza_ticket_inexistente(self):
        from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
        db = _make_db(query_result=None)
        raw = _make_raw_event("ticket.asignado", {"ticket_id": "NO-EXISTE"})
        with pytest.raises(CRMProcessingError, match="no encontrado"):
            process_crm_event(db, raw)


# ─── ticket.escalado ─────────────────────────────────────────────────────────

class TestHandleTicketEscalado:
    def test_updates_prioridad_al_escalar(self):
        from app.etl.processors.crm_processor import process_crm_event
        existing_ticket = MagicMock()
        existing_ticket.prioridad = "Media"
        existing_ticket.estado = "Progreso"

        db = _make_db(query_result=existing_ticket)
        payload = {"ticket_id": "T-004", "prioridad_al_escalar": "Crítica"}
        raw = _make_raw_event("ticket.escalado", payload)
        process_crm_event(db, raw)

        assert existing_ticket.prioridad == "Crítica"

    def test_escalado_rechaza_si_abierto(self):
        from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
        existing_ticket = MagicMock()
        existing_ticket.estado = "Abierto"
        existing_ticket.ticket_id = "T-004"

        db = _make_db(query_result=existing_ticket)
        raw = _make_raw_event("ticket.escalado", {"ticket_id": "T-004"})
        with pytest.raises(CRMProcessingError, match="Transición inválida"):
            process_crm_event(db, raw)

    def test_escalado_rechaza_ticket_inexistente(self):
        from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
        db = _make_db(query_result=None)
        raw = _make_raw_event("ticket.escalado", {"ticket_id": "NO-EXISTE"})
        with pytest.raises(CRMProcessingError, match="no encontrado"):
            process_crm_event(db, raw)

    def test_missing_ticket_id_raises(self):
        from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
        db = _make_db()
        raw = _make_raw_event("ticket.escalado", {})
        with pytest.raises(CRMProcessingError, match="ticket_id"):
            process_crm_event(db, raw)


# ─── ticket.resuelto ─────────────────────────────────────────────────────────

class TestHandleTicketResuelto:
    def test_sets_estado_resuelto(self):
        from app.etl.processors.crm_processor import process_crm_event
        existing_ticket = MagicMock()
        existing_ticket.estado = "Progreso"
        existing_ticket.within_sla = None

        db = _make_db(query_result=existing_ticket)
        payload = {
            "ticket_id": "T-005",
            "resolution_time_hours": 2.5,
            "within_sla": True,
        }
        raw = _make_raw_event("ticket.resuelto", payload)
        process_crm_event(db, raw)

        assert existing_ticket.estado == "Resuelto"
        assert existing_ticket.resolution_time_hours == 2.5
        assert existing_ticket.within_sla is True

    def test_resolved_at_set_when_provided(self):
        from app.etl.processors.crm_processor import process_crm_event
        existing_ticket = MagicMock()
        existing_ticket.estado = "Progreso"
        db = _make_db(query_result=existing_ticket)
        payload = {
            "ticket_id": "T-005b",
            "resolved_at": "2026-06-01T12:00:00Z",
        }
        raw = _make_raw_event("ticket.resuelto", payload)
        process_crm_event(db, raw)
        assert existing_ticket.resolved_at is not None

    def test_resuelto_rechaza_si_abierto(self):
        from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
        existing_ticket = MagicMock()
        existing_ticket.estado = "Abierto"
        existing_ticket.ticket_id = "T-005c"

        db = _make_db(query_result=existing_ticket)
        raw = _make_raw_event("ticket.resuelto", {"ticket_id": "T-005c"})
        with pytest.raises(CRMProcessingError, match="Transición inválida"):
            process_crm_event(db, raw)

    def test_resuelto_rechaza_ticket_inexistente(self):
        from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
        db = _make_db(query_result=None)
        raw = _make_raw_event("ticket.resuelto", {"ticket_id": "NO-EXISTE"})
        with pytest.raises(CRMProcessingError, match="no encontrado"):
            process_crm_event(db, raw)


# ─── ticket.cerrado ──────────────────────────────────────────────────────────

class TestHandleTicketCerrado:
    def test_sets_estado_cerrado_with_csat(self):
        from app.etl.processors.crm_processor import process_crm_event
        existing_ticket = MagicMock()
        existing_ticket.estado = "Resuelto"
        db = _make_db(query_result=existing_ticket)
        payload = {"ticket_id": "T-006", "csat_score": 5}
        raw = _make_raw_event("ticket.cerrado", payload)
        process_crm_event(db, raw)

        assert existing_ticket.estado == "Cerrado"
        assert existing_ticket.csat_score == 5

    def test_cerrado_rechaza_si_en_progreso(self):
        from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
        existing_ticket = MagicMock()
        existing_ticket.estado = "Progreso"
        existing_ticket.ticket_id = "T-006b"

        db = _make_db(query_result=existing_ticket)
        raw = _make_raw_event("ticket.cerrado", {"ticket_id": "T-006b"})
        with pytest.raises(CRMProcessingError, match="Transición inválida"):
            process_crm_event(db, raw)

    def test_cerrado_rechaza_ticket_inexistente(self):
        from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
        db = _make_db(query_result=None)
        raw = _make_raw_event("ticket.cerrado", {"ticket_id": "NO-EXISTE"})
        with pytest.raises(CRMProcessingError, match="no encontrado"):
            process_crm_event(db, raw)

    def test_missing_ticket_id_raises(self):
        from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
        db = _make_db()
        raw = _make_raw_event("ticket.cerrado", {})
        with pytest.raises(CRMProcessingError, match="ticket_id"):
            process_crm_event(db, raw)


# ─── interaccion.creada ───────────────────────────────────────────────────────

class TestHandleInteraccionCreada:
    def test_missing_interaccion_id_raises(self):
        from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
        db = _make_db()
        raw = _make_raw_event("interaccion.creada", {"ticket_id": "T-001"})
        with pytest.raises(CRMProcessingError, match="interaccion_id"):
            process_crm_event(db, raw)

    def test_creates_interaccion(self):
        from app.etl.processors.crm_processor import process_crm_event
        db = _make_db(query_result=None)
        payload = {
            "interaccion_id": "INT-001",
            "ticket_id": "T-001",
            "autor_tipo": "Agente",
            "contenido": "Revisando el caso",
        }
        raw = _make_raw_event("interaccion.creada", payload)
        process_crm_event(db, raw)
        assert db.add.called and db.flush.called

    def test_idempotent_if_already_exists(self):
        from app.etl.processors.crm_processor import process_crm_event
        existing = MagicMock()
        db = _make_db(query_result=existing)
        payload = {"interaccion_id": "INT-001", "ticket_id": "T-001"}
        raw = _make_raw_event("interaccion.creada", payload)
        result = process_crm_event(db, raw)
        assert result is existing
        db.add.assert_not_called()


# ─── kb.articulo.usado ────────────────────────────────────────────────────────

class TestHandleKbArticuloUsado:
    def test_missing_fields_raises(self):
        from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
        db = _make_db()
        raw = _make_raw_event("kb.articulo.usado", {"ticket_id": "T-001"})
        with pytest.raises(CRMProcessingError, match="articulo_id"):
            process_crm_event(db, raw)

    def test_creates_registro(self):
        from app.etl.processors.crm_processor import process_crm_event
        db = _make_db()
        payload = {
            "ticket_id": "T-001",
            "articulo_id": "ART-42",
            "articulo_titulo": "Guía de facturación",
            "fue_enviado_al_cliente": True,
        }
        raw = _make_raw_event("kb.articulo.usado", payload)
        process_crm_event(db, raw)
        assert db.add.called


# ─── ticket.sla_violado ───────────────────────────────────────────────────────

class TestHandleTicketSlaViolado:
    def test_missing_ticket_id_raises(self):
        from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
        db = _make_db()
        raw = _make_raw_event("ticket.sla_violado", {})
        with pytest.raises(CRMProcessingError, match="ticket_id"):
            process_crm_event(db, raw)

    def test_creates_violacion_with_defaults(self):
        from app.etl.processors.crm_processor import process_crm_event
        db = _make_db()
        payload = {"ticket_id": "T-007"}
        raw = _make_raw_event("ticket.sla_violado", payload)
        process_crm_event(db, raw)
        assert db.add.called and db.flush.called

    def test_breach_percentage_float_cast(self):
        from app.etl.processors.crm_processor import process_crm_event
        db = _make_db()
        payload = {
            "ticket_id": "T-008",
            "breach_percentage": "145.5",
            "elapsed_hours": "10",
        }
        raw = _make_raw_event("ticket.sla_violado", payload)
        # no debe lanzar excepción — casteo a float debe funcionar
        process_crm_event(db, raw)
        assert db.flush.called


# ─── Normalización de casing (CRM externo envía minúscula sin tilde) ──────────

class TestNormalizeEstado:
    def test_passthrough_canonical(self):
        from app.etl.processors.crm_processor import _normalize_estado
        assert _normalize_estado("Progreso") == "Progreso"

    def test_lowercase_external_casing(self):
        from app.etl.processors.crm_processor import _normalize_estado
        assert _normalize_estado("abierto") == "Abierto"
        assert _normalize_estado("progreso") == "Progreso"
        assert _normalize_estado("resuelto") == "Resuelto"
        assert _normalize_estado("cerrado") == "Cerrado"

    def test_unrecognized_value_raises(self):
        from app.etl.processors.crm_processor import _normalize_estado, CRMProcessingError
        with pytest.raises(CRMProcessingError, match="estado"):
            _normalize_estado("pendiente")


class TestNormalizePrioridad:
    def test_passthrough_canonical(self):
        from app.etl.processors.crm_processor import _normalize_prioridad
        assert _normalize_prioridad("Crítica") == "Crítica"

    def test_lowercase_sin_tilde(self):
        from app.etl.processors.crm_processor import _normalize_prioridad
        assert _normalize_prioridad("baja") == "Baja"
        assert _normalize_prioridad("media") == "Media"
        assert _normalize_prioridad("alta") == "Alta"
        assert _normalize_prioridad("critica") == "Crítica"

    def test_unrecognized_value_raises(self):
        from app.etl.processors.crm_processor import _normalize_prioridad, CRMProcessingError
        with pytest.raises(CRMProcessingError, match="prioridad"):
            _normalize_prioridad("urgente")


class TestNormalizeCanal:
    def test_none_passthrough(self):
        from app.etl.processors.crm_processor import _normalize_canal
        assert _normalize_canal(None) is None

    def test_lowercase_sin_tilde(self):
        from app.etl.processors.crm_processor import _normalize_canal
        assert _normalize_canal("chat") == "Chat"
        assert _normalize_canal("email") == "Email"
        assert _normalize_canal("telefono") == "Teléfono"
        assert _normalize_canal("app") == "App"

    def test_unrecognized_value_raises(self):
        from app.etl.processors.crm_processor import _normalize_canal, CRMProcessingError
        with pytest.raises(CRMProcessingError, match="canal"):
            _normalize_canal("whatsapp")


class TestTicketCreadoCasingReal:
    """El CRM externo real envía estado/prioridad/canal en minúscula sin tilde."""

    def test_ticket_creado_con_casing_externo_real(self):
        from app.etl.processors.crm_processor import process_crm_event
        db = _make_db(query_result=None)
        payload = {
            "ticket_id": "T-EXT-001",
            "estado": "abierto",
            "prioridad": "critica",
            "canal": "telefono",
        }
        raw = _make_raw_event("ticket.creado", payload)
        result = process_crm_event(db, raw)
        assert result.estado == "Abierto"
        assert result.prioridad == "Crítica"
        assert result.canal == "Teléfono"

    def test_ticket_creado_con_prioridad_no_reconocida_falla(self):
        from app.etl.processors.crm_processor import process_crm_event, CRMProcessingError
        db = _make_db(query_result=None)
        payload = {"ticket_id": "T-EXT-002", "prioridad": "urgente"}
        raw = _make_raw_event("ticket.creado", payload)
        with pytest.raises(CRMProcessingError, match="prioridad"):
            process_crm_event(db, raw)


class TestTicketCreadoNuevosCampos:
    def test_popula_campos_del_ticket_dto_externo(self):
        from app.etl.processors.crm_processor import process_crm_event
        db = _make_db(query_result=None)
        payload = {
            "ticket_id": "T-NEW-001",
            "cliente_id": 8823,
            "cliente_nombre": "María Fernández",
            "pago_id_ref": "PAY-2026-00981",
            "salud_ref": "HC-2026-00021",
        }
        raw = _make_raw_event("ticket.creado", payload)
        result = process_crm_event(db, raw)
        assert result.cliente_id == 8823
        assert result.cliente_nombre == "María Fernández"
        assert result.pago_id_ref == "PAY-2026-00981"
        assert result.salud_ref == "HC-2026-00021"


class TestTicketResueltoResolucion:
    def test_guarda_resolucion_cuando_viene_en_payload(self):
        from app.etl.processors.crm_processor import process_crm_event
        existing_ticket = MagicMock()
        existing_ticket.estado = "Progreso"
        db = _make_db(query_result=existing_ticket)
        payload = {"ticket_id": "T-005d", "resolucion": "Se reembolsó el cargo duplicado"}
        raw = _make_raw_event("ticket.resuelto", payload)
        process_crm_event(db, raw)
        assert existing_ticket.resolucion == "Se reembolsó el cargo duplicado"
