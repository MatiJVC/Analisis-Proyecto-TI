"""
Suite de tests — eventos CRM (Proyecto 07 → Proyecto 09).

Contratos de payload alineados con el MER adjunto:
  Entidades: Cliente, Ticket, Interaccion, Articulo_kb, Ticket_articulo

  Prioridades  : Baja | Media | Alta | Crítica          (Ticket.prioridad)
  Estado       : Abierto | Progreso | Resuelto | Cerrado (Ticket.estado)
  Canales      : Chat | Email | Teléfono | App           (Ticket.canal)
  Autor tipo   : Cliente | Agente | Sistema              (Interaccion.autor_tipo)
  Origen       : orders | salud | subscriptions | pagos | iot | otros
  Umbrales SLA : 75 | 100 | 150  (% del límite crítico de 8 h)

NOTA: el MER define el campo como 'suscripcion_id_red' (no 'ref').
      Se usa ese nombre exacto en todos los payloads.
"""

import uuid as _uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.models.raw.raw_events import RawEvent


# =============================================================================
# Payloads canónicos — contratos acordados con el Proyecto 07
# =============================================================================

# ── 1. Creación de ticket ────────────────────────────────────────────────────
# Ticket.estado inicial = Abierto
TICKET_CREADO = {
    "source": "crm",
    "event_type": "ticket.creado",
    "payload": {
        # Ticket
        "ticket_id": "TKT-2026-00500",
        "asunto": "Pedido no llegó en el plazo prometido",
        "estado": "Abierto",
        "prioridad": "Alta",                           # Baja | Media | Alta | Crítica
        "canal": "Chat",                               # Chat | Email | Teléfono | App
        "fecha_vencimiento_sla": "2026-05-22T17:00:00Z",  # Ticket.fecha_vencimiento_sla

        # Cliente (deduplicación por email o teléfono, PK = identidad_id UUID)
        "cliente_identidad_id": "c3d4e5f6-0001-4aaa-bbb2-000000000001",  # UUID público
        "email": "cliente@empresa.cl",                 # Unique en Cliente
        "telefono": "+56912345678",

        # Agente asignado (UUID)
        "agente_id": "a1b2c3d4-0000-0000-0000-000000000089",

        # Proyecto que originó el problema → segmentación del dashboard
        "source_project": "orders",

        # Referencias cruzadas (NULLABLE en el MER)
        "pedido_id_ref": "ORD-2026-78901",
        "suscripcion_id_red": "SUB-4567",              # ← 'red', exactamente como el MER
    },
}

# ── 2. Asignación ─────────────────────────────────────────────────────────────
# Ticket.estado → Progreso
TICKET_ASIGNADO = {
    "source": "crm",
    "event_type": "ticket.asignado",
    "payload": {
        "ticket_id": "TKT-2026-00500",
        "estado": "Progreso",
        "agente_id": "a1b2c3d4-0000-0000-0000-000000000089",
        "agente_nombre": "María González",
        "assigned_at": "2026-05-22T09:08:00Z",
        "response_time_minutes": 8,
    },
}

# ── 3. Escalamiento ───────────────────────────────────────────────────────────
# Ticket.estado sigue en Progreso; la prioridad puede subir
TICKET_ESCALADO = {
    "source": "crm",
    "event_type": "ticket.escalado",
    "payload": {
        "ticket_id": "TKT-2026-00500",
        "estado": "Progreso",
        "escalado_desde_agente": "a1b2c3d4-0000-0000-0000-000000000089",
        "escalado_hacia": "incidents",                 # Proyecto 11
        "escalado_hacia_agente": "a1b2c3d4-0000-0000-SUPER-000000000001",
        "motivo": "Requiere coordinación con logística externa",
        "escalated_at": "2026-05-22T12:00:00Z",
        "prioridad_al_escalar": "Crítica",
    },
}

# ── 4. Resolución ─────────────────────────────────────────────────────────────
# Ticket.estado → Resuelto
TICKET_RESUELTO = {
    "source": "crm",
    "event_type": "ticket.resuelto",
    "payload": {
        "ticket_id": "TKT-2026-00500",
        "estado": "Resuelto",

        # Campos para joins con el Silver layer
        "cliente_identidad_id": "c3d4e5f6-0001-4aaa-bbb2-000000000001",
        "pedido_id_ref": "ORD-2026-78901",
        "suscripcion_id_red": "SUB-4567",
        "prioridad": "Crítica",
        "canal": "Chat",
        "source_project": "orders",
        "agente_id": "a1b2c3d4-0000-0000-SUPER-000000000001",

        # Tiempo de resolución y SLA
        "created_at": "2026-05-22T09:00:00Z",
        "resolved_at": "2026-05-22T16:30:00Z",
        "resolution_time_hours": 7.5,
        "within_sla": True,                            # 7.5 h < 8 h

        "resolution_notes": "Coordinado con operador logístico; reentrega confirmada",

        # kb_articulo_usado NO va aquí: viaja por kb.articulo.usado (Ticket_articulo)
    },
}

# ── 5. Cierre formal ──────────────────────────────────────────────────────────
# Ticket.estado → Cerrado
TICKET_CERRADO = {
    "source": "crm",
    "event_type": "ticket.cerrado",
    "payload": {
        "ticket_id": "TKT-2026-00500",
        "estado": "Cerrado",
        "closed_at": "2026-05-22T17:00:00Z",
        "csat_score": 4,                               # 1–5
        "csat_comment": "Buen servicio pero tardó más de lo esperado",
        "closed_by": "customer",                       # customer | agent | auto
    },
}

# ── 6. Interacción (Interaccion en el MER) ────────────────────────────────────
# Una interacción = un mensaje o nota interna sobre un ticket.
INTERACCION_CREADA = {
    "source": "crm",
    "event_type": "interaccion.creada",
    "payload": {
        # Interaccion.id → UUID
        "interaccion_id": "int-2026-00500-001",
        # Interaccion.ticket_id → FK
        "ticket_id": "TKT-2026-00500",
        # Interaccion.autor_tipo → Enum: Cliente | Agente | Sistema
        "autor_tipo": "Agente",
        # Interaccion.autor_id → UUID del autor
        "autor_id": "a1b2c3d4-0000-0000-0000-000000000089",
        # Interaccion.contenido
        "contenido": "Le contactamos para informarle que su pedido está siendo reagendado.",
        # Interaccion.es_nota_interna: False = visible al cliente, True = solo agentes
        "es_nota_interna": False,
        # Interaccion.creado_en
        "creado_en": "2026-05-22T10:15:00Z",
    },
}

NOTA_INTERNA_CREADA = {
    "source": "crm",
    "event_type": "interaccion.creada",
    "payload": {
        "interaccion_id": "int-2026-00500-002",
        "ticket_id": "TKT-2026-00500",
        "autor_tipo": "Agente",
        "autor_id": "a1b2c3d4-0000-0000-0000-000000000089",
        "contenido": "INTERNO: Esperando confirmación de la bodega. No escalar aún.",
        "es_nota_interna": True,
        "creado_en": "2026-05-22T11:00:00Z",
    },
}

# ── 7. Uso de KB (Ticket_articulo en el MER) ──────────────────────────────────
# Campos exactos del MER: ticket_id, articulo_id, fue_enviado_al_cliente,
#                          agente_id, vinculado_en
KB_ARTICULO_USADO = {
    "source": "crm",
    "event_type": "kb.articulo.usado",
    "payload": {
        # Ticket_articulo.ticket_id (FK)
        "ticket_id": "TKT-2026-00500",
        # Ticket_articulo.articulo_id (FK → Articulo_kb)
        "articulo_id": "KB-LOGISTICA-012",
        # Ticket_articulo.fue_enviado_al_cliente
        "fue_enviado_al_cliente": True,
        # Ticket_articulo.agente_id (UUID)
        "agente_id": "a1b2c3d4-0000-0000-0000-000000000089",
        # Ticket_articulo.vinculado_en
        "vinculado_en": "2026-05-22T14:00:00Z",
        # Datos del artículo (Articulo_kb) para enriquecer el Bronze Layer
        "articulo_titulo": "Protocolo de reentrega para pedidos fallidos",
        "articulo_categoria": "logistica",
    },
}

# ── 8. Violación de SLA ───────────────────────────────────────────────────────
TICKET_SLA_VIOLADO = {
    "source": "crm",
    "event_type": "ticket.sla_violado",
    "payload": {
        "ticket_id": "TKT-2026-00599",
        "cliente_identidad_id": "c3d4e5f6-0001-4aaa-bbb2-000000000099",
        "prioridad": "Crítica",
        "estado": "Progreso",
        "source_project": "salud",
        "canal": "Teléfono",

        # SLA
        "sla_threshold_hours": 8,
        "elapsed_hours": 9.6,
        "breach_percentage": 120.0,
        "threshold_crossed": 100,              # 75 | 100 | 150

        "alert_sent_to": ["supervisor@empresa.cl", "ops@empresa.cl"],
        "escalation_required": True,
        "escalado_hacia": "incidents",

        # Marcas temporales
        "created_at": "2026-05-22T06:00:00Z",
        "fecha_vencimiento_sla": "2026-05-22T14:00:00Z",
        "violation_detected_at": "2026-05-22T15:36:00Z",
    },
}


# =============================================================================
# Helper
# =============================================================================

def _saved(mock_db: MagicMock) -> RawEvent:
    assert mock_db.add.call_count >= 1, "db.add() nunca fue llamado"
    return mock_db.add.call_args[0][0]


# =============================================================================
# 1. ticket.creado — alineado con Ticket del MER
# =============================================================================

class TestTicketCreado:
    def test_201(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=TICKET_CREADO).status_code == 202

    def test_estado_inicial_es_abierto(self, client: TestClient, mock_db: MagicMock):
        """El MER define estado inicial = Abierto al crear el ticket."""
        client.post("/v1/events", json=TICKET_CREADO)
        assert _saved(mock_db).payload["estado"] == "Abierto"

    def test_prioridad_en_espanol_capitalized(self, client: TestClient, mock_db: MagicMock):
        """Enum del MER: Baja | Media | Alta | Crítica."""
        client.post("/v1/events", json=TICKET_CREADO)
        assert _saved(mock_db).payload["prioridad"] in {"Baja", "Media", "Alta", "Crítica"}

    def test_canal_enum_mer(self, client: TestClient, mock_db: MagicMock):
        """Enum del MER: Chat | Email | Teléfono | App."""
        client.post("/v1/events", json=TICKET_CREADO)
        assert _saved(mock_db).payload["canal"] in {"Chat", "Email", "Teléfono", "App"}

    def test_cliente_identidad_id_es_uuid(self, client: TestClient, mock_db: MagicMock):
        """Cliente.identidad_id es el UUID público — separado del PK entero."""
        client.post("/v1/events", json=TICKET_CREADO)
        _uuid.UUID(_saved(mock_db).payload["cliente_identidad_id"])

    def test_campos_deduplicacion_email_telefono(self, client: TestClient, mock_db: MagicMock):
        """email (Unique) y telefono para deduplicación en Silver layer."""
        client.post("/v1/events", json=TICKET_CREADO)
        p = _saved(mock_db).payload
        assert "email" in p
        assert "telefono" in p

    def test_fecha_vencimiento_sla_presente(self, client: TestClient, mock_db: MagicMock):
        """Ticket.fecha_vencimiento_sla es campo explícito en el MER."""
        client.post("/v1/events", json=TICKET_CREADO)
        assert "fecha_vencimiento_sla" in _saved(mock_db).payload

    def test_source_project_para_segmentacion(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_CREADO)
        p = _saved(mock_db).payload
        assert "source_project" in p
        assert p["source_project"] in {
            "orders", "salud", "subscriptions", "pagos", "iot", "otros"
        }

    def test_suscripcion_id_red_nombre_correcto(self, client: TestClient, mock_db: MagicMock):
        """El MER define 'suscripcion_id_red' — ese es el nombre oficial del campo."""
        client.post("/v1/events", json=TICKET_CREADO)
        p = _saved(mock_db).payload
        assert "suscripcion_id_red" in p, (
            "El campo se llama 'suscripcion_id_red' según el MER (no 'suscripcion_id_ref')"
        )

    def test_pedido_id_ref_presente(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_CREADO)
        assert "pedido_id_ref" in _saved(mock_db).payload


# =============================================================================
# 2. ticket.asignado — Ticket.estado → Progreso
# =============================================================================

class TestTicketAsignado:
    def test_201(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=TICKET_ASIGNADO).status_code == 202

    def test_estado_cambia_a_progreso(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_ASIGNADO)
        assert _saved(mock_db).payload["estado"] == "Progreso"

    def test_ticket_id_consistente(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_ASIGNADO)
        assert _saved(mock_db).payload["ticket_id"] == TICKET_CREADO["payload"]["ticket_id"]

    def test_agente_id_uuid(self, client: TestClient, mock_db: MagicMock):
        """Ticket.agente_id es UUID (referencia al agente)."""
        client.post("/v1/events", json=TICKET_ASIGNADO)
        _uuid.UUID(_saved(mock_db).payload["agente_id"])

    def test_response_time_para_sla(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_ASIGNADO)
        assert "response_time_minutes" in _saved(mock_db).payload


# =============================================================================
# 3. ticket.escalado — escalamiento al Proyecto 11
# =============================================================================

class TestTicketEscalado:
    def test_201(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=TICKET_ESCALADO).status_code == 202

    def test_estado_progreso_durante_escalamiento(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_ESCALADO)
        assert _saved(mock_db).payload["estado"] == "Progreso"

    def test_escalado_hacia_incidents(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_ESCALADO)
        assert _saved(mock_db).payload["escalado_hacia"] == "incidents"

    def test_prioridad_escalada_en_espanol(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_ESCALADO)
        assert _saved(mock_db).payload["prioridad_al_escalar"] in {
            "Baja", "Media", "Alta", "Crítica"
        }


# =============================================================================
# 4. ticket.resuelto — Ticket.estado → Resuelto
# =============================================================================

class TestTicketResuelto:
    def test_201(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=TICKET_RESUELTO).status_code == 202

    def test_estado_resuelto(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_RESUELTO)
        assert _saved(mock_db).payload["estado"] == "Resuelto"

    def test_sin_campo_kb_embedded(self, client: TestClient, mock_db: MagicMock):
        """
        El uso de KB viaja por Ticket_articulo → evento kb.articulo.usado.
        NO debe ir embedded en ticket.resuelto.
        """
        client.post("/v1/events", json=TICKET_RESUELTO)
        p = _saved(mock_db).payload
        assert "kb_articulo_usado" not in p
        assert "fue_enviado_al_cliente" not in p

    def test_within_sla_booleano(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_RESUELTO)
        assert isinstance(_saved(mock_db).payload["within_sla"], bool)

    def test_referencias_cruzadas_para_joins(self, client: TestClient, mock_db: MagicMock):
        """Los FK externos se repiten en resuelto para facilitar queries Silver."""
        client.post("/v1/events", json=TICKET_RESUELTO)
        p = _saved(mock_db).payload
        assert "pedido_id_ref" in p
        assert "suscripcion_id_red" in p

    def test_source_project_en_resolucion(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_RESUELTO)
        assert "source_project" in _saved(mock_db).payload


# =============================================================================
# 5. ticket.cerrado — Ticket.estado → Cerrado
# =============================================================================

class TestTicketCerrado:
    def test_201(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=TICKET_CERRADO).status_code == 202

    def test_estado_cerrado(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_CERRADO)
        assert _saved(mock_db).payload["estado"] == "Cerrado"

    def test_csat_score_en_rango(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_CERRADO)
        assert 1 <= _saved(mock_db).payload["csat_score"] <= 5

    def test_ticket_id_consistente_ciclo_completo(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_CERRADO)
        assert _saved(mock_db).payload["ticket_id"] == TICKET_CREADO["payload"]["ticket_id"]


# =============================================================================
# 6. interaccion.creada — entidad Interaccion del MER
# =============================================================================

class TestInteraccionCreada:
    def test_201_mensaje_cliente_visible(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=INTERACCION_CREADA).status_code == 202

    def test_201_nota_interna(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=NOTA_INTERNA_CREADA).status_code == 202

    def test_event_type_correcto(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INTERACCION_CREADA)
        assert _saved(mock_db).event_type == "interaccion.creada"

    def test_autor_tipo_enum_mer(self, client: TestClient, mock_db: MagicMock):
        """Interaccion.autor_tipo: Cliente | Agente | Sistema."""
        client.post("/v1/events", json=INTERACCION_CREADA)
        assert _saved(mock_db).payload["autor_tipo"] in {"Cliente", "Agente", "Sistema"}

    def test_es_nota_interna_booleano(self, client: TestClient, mock_db: MagicMock):
        """Interaccion.es_nota_interna distingue mensajes internos de cara al cliente."""
        client.post("/v1/events", json=NOTA_INTERNA_CREADA)
        assert _saved(mock_db).payload["es_nota_interna"] is True

    def test_ticket_vinculado(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INTERACCION_CREADA)
        assert _saved(mock_db).payload["ticket_id"] == TICKET_CREADO["payload"]["ticket_id"]

    def test_autor_id_presente(self, client: TestClient, mock_db: MagicMock):
        """Interaccion.autor_id es UUID del autor."""
        client.post("/v1/events", json=INTERACCION_CREADA)
        assert "autor_id" in _saved(mock_db).payload


# =============================================================================
# 7. kb.articulo.usado — mapea a Ticket_articulo del MER
# =============================================================================

class TestKbArticuloUsado:
    def test_201(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=KB_ARTICULO_USADO).status_code == 202

    def test_es_evento_independiente(self, client: TestClient, mock_db: MagicMock):
        """Ticket_articulo es una entidad separada → evento propio, no embedded."""
        client.post("/v1/events", json=KB_ARTICULO_USADO)
        saved = _saved(mock_db)
        assert saved.event_type == "kb.articulo.usado"
        assert saved.source == "crm"

    def test_campos_ticket_articulo_del_mer(self, client: TestClient, mock_db: MagicMock):
        """
        Campos obligatorios del MER para Ticket_articulo:
        ticket_id, articulo_id, fue_enviado_al_cliente, agente_id, vinculado_en
        """
        client.post("/v1/events", json=KB_ARTICULO_USADO)
        p = _saved(mock_db).payload
        assert "ticket_id" in p
        assert "articulo_id" in p
        assert "fue_enviado_al_cliente" in p
        assert "agente_id" in p
        assert "vinculado_en" in p

    def test_fue_enviado_al_cliente_es_booleano(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=KB_ARTICULO_USADO)
        assert isinstance(_saved(mock_db).payload["fue_enviado_al_cliente"], bool)

    def test_ticket_id_vincula_al_ticket(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=KB_ARTICULO_USADO)
        assert _saved(mock_db).payload["ticket_id"] == TICKET_CREADO["payload"]["ticket_id"]

    def test_multiples_articulos_por_ticket(self, client: TestClient, mock_db: MagicMock):
        """Un ticket puede tener N Ticket_articulo registros."""
        segundo = {
            **KB_ARTICULO_USADO,
            "payload": {
                **KB_ARTICULO_USADO["payload"],
                "articulo_id": "KB-LOGISTICA-025",
                "articulo_titulo": "Checklist de verificación de entrega",
            },
        }
        r1 = client.post("/v1/events", json=KB_ARTICULO_USADO)
        r2 = client.post("/v1/events", json=segundo)
        assert r1.status_code == 202
        assert r2.status_code == 202
        assert mock_db.add.call_count == 2


# =============================================================================
# 8. ticket.sla_violado — umbrales 75 / 100 / 150
# =============================================================================

class TestTicketSlaViolado:
    def test_201(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=TICKET_SLA_VIOLADO).status_code == 202

    def test_threshold_crossed_75_100_o_150(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_SLA_VIOLADO)
        assert _saved(mock_db).payload["threshold_crossed"] in {75, 100, 150}

    def test_prioridad_critica_sla_8h(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_SLA_VIOLADO)
        p = _saved(mock_db).payload
        assert p["prioridad"] == "Crítica"
        assert p["sla_threshold_hours"] == 8

    def test_fecha_vencimiento_sla_registrada(self, client: TestClient, mock_db: MagicMock):
        """fecha_vencimiento_sla del MER debe estar también en la violación."""
        client.post("/v1/events", json=TICKET_SLA_VIOLADO)
        assert "fecha_vencimiento_sla" in _saved(mock_db).payload

    def test_escalado_hacia_incidents(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_SLA_VIOLADO)
        assert _saved(mock_db).payload["escalado_hacia"] == "incidents"

    def test_source_project_en_sla_violado(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=TICKET_SLA_VIOLADO)
        assert "source_project" in _saved(mock_db).payload


# =============================================================================
# 9. Validaciones generales — rechaza payloads inválidos
# =============================================================================

class TestCRMValidaciones:
    def test_missing_source_devuelve_422(self, client: TestClient, mock_db: MagicMock):
        bad = {k: v for k, v in TICKET_CREADO.items() if k != "source"}
        assert client.post("/v1/events", json=bad).status_code == 422
        mock_db.add.assert_not_called()

    def test_missing_event_type_devuelve_422(self, client: TestClient, mock_db: MagicMock):
        bad = {k: v for k, v in TICKET_CREADO.items() if k != "event_type"}
        assert client.post("/v1/events", json=bad).status_code == 422
        mock_db.add.assert_not_called()

    def test_payload_como_lista_devuelve_422(self, client: TestClient, mock_db: MagicMock):
        bad = {**TICKET_CREADO, "payload": ["esto", "no", "es", "un", "objeto"]}
        assert client.post("/v1/events", json=bad).status_code == 422
        mock_db.add.assert_not_called()
