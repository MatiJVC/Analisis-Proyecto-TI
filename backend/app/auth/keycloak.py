"""
Validación de tokens JWT emitidos por Keycloak.

Descarga la JWKS pública del realm una sola vez (con cache) y verifica
firma, expiración e issuer en cada request. No hace requests a Keycloak
en caliente: solo la primera vez o cuando rotan las claves.
"""
from __future__ import annotations

import os
import sys
import threading
import time
from typing import Any

import httpx
from jose import jwt
from jose.exceptions import JWTError


KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080").rstrip("/")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "sistema-centralizado")

_ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
if _ENVIRONMENT != "development" and KEYCLOAK_URL.startswith("http://"):
    print(
        f"FATAL: KEYCLOAK_URL usa HTTP ({KEYCLOAK_URL}) en entorno '{_ENVIRONMENT}'. "
        "Configure KEYCLOAK_URL con HTTPS para proteger el descubrimiento de JWKS.",
        file=sys.stderr,
        flush=True,
    )
    sys.exit(1)
# Audiencia esperada en el token. Keycloak por defecto pone "account".
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "account")
# Refrescar el JWKS cada N segundos (rota cuando admin cambia las claves).
JWKS_CACHE_TTL = int(os.getenv("KEYCLOAK_JWKS_TTL", "3600"))

ISSUER = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
JWKS_URL = f"{ISSUER}/protocol/openid-connect/certs"

# Hardcoded allowlist — never accept "none" or symmetric algorithms even if
# Keycloak's JWKS were somehow tampered or misconfigured.
ALLOWED_ALGORITHMS = {"RS256", "RS384", "RS512"}


class KeycloakAuthError(Exception):
    """Error de autenticación contra Keycloak."""


_jwks_cache: dict[str, Any] = {"keys": None, "fetched_at": 0.0}
_jwks_lock = threading.Lock()


def _fetch_and_cache_jwks() -> dict[str, Any]:
    """HTTP fetch + cache update. Caller MUST hold _jwks_lock."""
    try:
        resp = httpx.get(JWKS_URL, timeout=5.0)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise KeycloakAuthError(
            f"No se pudo obtener JWKS de Keycloak en {JWKS_URL}: {exc}"
        ) from exc
    _jwks_cache["keys"] = resp.json()
    _jwks_cache["fetched_at"] = time.time()
    return _jwks_cache["keys"]


def _get_jwks() -> dict[str, Any]:
    now = time.time()
    with _jwks_lock:
        if (
            _jwks_cache["keys"] is not None
            and now - _jwks_cache["fetched_at"] < JWKS_CACHE_TTL
        ):
            return _jwks_cache["keys"]
        return _fetch_and_cache_jwks()


def _find_key(kid: str) -> dict[str, Any] | None:
    jwks = _get_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    # Key not in cache — could be a newly rotated key. Invalidate and re-fetch
    # inside a single lock scope so concurrent threads don't each trigger a
    # separate HTTP call to Keycloak.
    with _jwks_lock:
        _jwks_cache["fetched_at"] = 0.0
        jwks = _fetch_and_cache_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


def decode_token(token: str) -> dict[str, Any]:
    """Verifica firma, expiración e issuer. Devuelve los claims."""
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise KeycloakAuthError("Token mal formado") from exc

    kid = unverified_header.get("kid")
    if not kid:
        raise KeycloakAuthError("Token sin 'kid'")

    key = _find_key(kid)
    if key is None:
        raise KeycloakAuthError("Clave pública no encontrada para el kid del token")

    alg = key.get("alg", "RS256")
    if alg not in ALLOWED_ALGORITHMS:
        raise KeycloakAuthError(f"Algoritmo JWK no permitido: {alg}")

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[alg],
            audience=KEYCLOAK_AUDIENCE,
            issuer=ISSUER,
        )
    except JWTError as exc:
        raise KeycloakAuthError(f"Token inválido: {exc}") from exc

    return claims


def extract_roles(claims: dict[str, Any]) -> list[str]:
    """Une roles de realm + roles de cliente en una sola lista."""
    roles: list[str] = []
    realm = claims.get("realm_access") or {}
    roles.extend(realm.get("roles", []) or [])

    resource = claims.get("resource_access") or {}
    for client_data in resource.values():
        roles.extend(client_data.get("roles", []) or [])

    return roles
