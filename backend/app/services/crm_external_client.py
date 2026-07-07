"""
Cliente HTTP para la consulta en vivo de un ticket contra el CRM externo
(pgti-proyecto-crm-backend, microservicio de otro equipo).

Es una consulta puntual de reconciliación — no reemplaza el pipeline
asíncrono de eventos (POST /v1/events, source=crm) ni escribe en nuestra BD.
Mismo patrón síncrono que app/auth/keycloak.py (httpx.get con timeout).
"""
from __future__ import annotations

import os
from typing import Any

import httpx

CRM_EXTERNAL_BASE_URL = os.getenv(
    "CRM_EXTERNAL_BASE_URL", "https://pgti-proyecto-crm-backend.vercel.app"
).rstrip("/")
# Sin default: es un secreto, no se hardcodea en el código.
CRM_EXTERNAL_API_KEY = os.getenv("CRM_EXTERNAL_API_KEY")
CRM_EXTERNAL_TIMEOUT = float(os.getenv("CRM_EXTERNAL_TIMEOUT_SECONDS", "5.0"))


class CRMExternalError(Exception):
    """Error genérico al consultar el CRM externo."""


class CRMExternalTimeoutError(CRMExternalError):
    pass


class CRMExternalAuthError(CRMExternalError):
    pass


class CRMExternalNotFoundError(CRMExternalError):
    pass


def get_ticket_estado(ticket_id: str) -> dict[str, Any]:
    """Consulta el estado real de un ticket contra el CRM externo.

    Endpoint documentado por el equipo del CRM:
      GET {base}/api/v1/analytics/estado-ticket/{ticket_id}?api_key=...
    Respuesta esperada: {"ok": true, "ticket": {...}} o {"ok": false, "message": "..."}.
    """
    if not CRM_EXTERNAL_API_KEY:
        raise CRMExternalAuthError("CRM_EXTERNAL_API_KEY no configurada")

    url = f"{CRM_EXTERNAL_BASE_URL}/api/v1/analytics/estado-ticket/{ticket_id}"

    try:
        resp = httpx.get(
            url,
            params={"api_key": CRM_EXTERNAL_API_KEY},
            timeout=CRM_EXTERNAL_TIMEOUT,
        )
    except httpx.TimeoutException as exc:
        raise CRMExternalTimeoutError(
            f"Timeout consultando el CRM externo para ticket '{ticket_id}'"
        ) from exc
    except httpx.HTTPError as exc:
        raise CRMExternalError(f"Error de red consultando el CRM externo: {exc}") from exc

    try:
        data = resp.json()
    except ValueError as exc:
        raise CRMExternalError(
            f"Respuesta no-JSON del CRM externo (status {resp.status_code})"
        ) from exc

    if data.get("ok") is True:
        ticket = data.get("ticket")
        if ticket is None:
            raise CRMExternalError("Respuesta 'ok' del CRM externo sin campo 'ticket'")
        # El TicketDto real usa "id", no "ticket_id" (confirmado jul-2026 con el
        # equipo del CRM externo) — normalizamos al nombre que espera nuestro schema.
        if "ticket_id" not in ticket and "id" in ticket:
            ticket = {**ticket, "ticket_id": ticket["id"]}
        return ticket

    message = str(data.get("message", "")).lower()
    if "no encontrado" in message or resp.status_code == 404:
        raise CRMExternalNotFoundError(f"Ticket '{ticket_id}' no encontrado en el CRM externo")
    if "api_key" in message or resp.status_code in (401, 403):
        raise CRMExternalAuthError(f"CRM externo rechazó la api_key: {data.get('message')}")

    raise CRMExternalError(
        data.get("message") or f"CRM externo respondió con error (status {resp.status_code})"
    )
