"""
Dependencias FastAPI para autenticación con Keycloak.

Modos de uso:

    from app.auth import get_current_user, get_current_user_optional, require_roles

    @router.get("/me")
    def me(user = Depends(get_current_user)):                    # exige token
        return user

    @router.get("/public-or-private")
    def maybe(user = Depends(get_current_user_optional)):        # token opcional
        return {"logged_in": user is not None}

    @router.get("/admin", dependencies=[Depends(require_roles("admin"))])
    def admin():                                                  # exige rol
        ...

Si DISABLE_AUTH=true en el entorno, todas las dependencias devuelven un
usuario ficticio con rol "admin" y no se valida ningún token.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .keycloak import KeycloakAuthError, decode_token, extract_roles


_DISABLE_AUTH = os.getenv("DISABLE_AUTH", "false").lower() == "true"
_ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

_SAFE_ENVS = {"development", "test"}
if _DISABLE_AUTH and _ENVIRONMENT not in _SAFE_ENVS:
    import sys
    print(
        f"FATAL: DISABLE_AUTH=true no está permitido en ENVIRONMENT={_ENVIRONMENT!r}. "
        "Solo se permite en 'development' o 'test'. "
        "Elimine DISABLE_AUTH del entorno.",
        file=sys.stderr,
    )
    sys.exit(1)

_DUMMY_USER_CLAIMS = {
    "sub": "dummy-sub",
    "preferred_username": "dev-user",
    "email": "dev@local.dev",
    "realm_access": {"roles": ["admin", "analista", "salud", "subscriptions", "orders", "incidents"]},
}

# auto_error=False permite que sea opcional sin levantar 403 si no viene header.
_bearer = HTTPBearer(auto_error=False)


@dataclass
class KeycloakUser:
    """Representación liviana del usuario autenticado."""

    sub: str
    username: str | None
    email: str | None
    roles: list[str] = field(default_factory=list)
    claims: dict = field(default_factory=dict)

    def has_role(self, role: str) -> bool:
        return role in self.roles


def _claims_to_user(claims: dict) -> KeycloakUser:
    return KeycloakUser(
        sub=str(claims.get("sub", "")),
        username=claims.get("preferred_username"),
        email=claims.get("email"),
        roles=extract_roles(claims),
        claims=claims,
    )


def _dummy_user() -> KeycloakUser:
    return _claims_to_user(_DUMMY_USER_CLAIMS)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> KeycloakUser:
    """Exige un token válido. 401 si no viene o está mal.
    Con DISABLE_AUTH=true devuelve siempre el usuario ficticio."""
    if _DISABLE_AUTH:
        return _dummy_user()

    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta token Bearer",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_token(creds.credentials)
    except KeycloakAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return _claims_to_user(claims)


def get_current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> KeycloakUser | None:
    """Devuelve el usuario si el token viene y es válido. None en otro caso.
    Con DISABLE_AUTH=true devuelve siempre el usuario ficticio."""
    if _DISABLE_AUTH:
        return _dummy_user()

    if creds is None or creds.scheme.lower() != "bearer":
        return None
    try:
        claims = decode_token(creds.credentials)
    except KeycloakAuthError:
        return None
    return _claims_to_user(claims)


def require_roles(*required: str):
    """Crea una dependencia que verifica que el usuario tenga TODOS los roles.
    Con DISABLE_AUTH=true siempre pasa."""
    required_set = set(required)

    def _checker(user: KeycloakUser = Depends(get_current_user)) -> KeycloakUser:
        if _DISABLE_AUTH:
            return user
        if not required_set.issubset(user.roles):
            faltantes = sorted(required_set - set(user.roles))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Faltan roles requeridos: {faltantes}",
            )
        return user

    return _checker


def require_any_role(roles: Iterable[str]):
    """Igual que require_roles pero basta con tener UNO de los roles.
    Con DISABLE_AUTH=true siempre pasa."""
    allowed = set(roles)

    def _checker(user: KeycloakUser = Depends(get_current_user)) -> KeycloakUser:
        if _DISABLE_AUTH:
            return user
        if allowed.isdisjoint(user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere uno de los roles: {sorted(allowed)}",
            )
        return user

    return _checker