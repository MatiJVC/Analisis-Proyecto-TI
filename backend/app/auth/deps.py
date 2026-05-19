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
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .keycloak import KeycloakAuthError, decode_token, extract_roles


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


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> KeycloakUser:
    """Exige un token válido. 401 si no viene o está mal."""
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
    """Devuelve el usuario si el token viene y es válido. None en otro caso."""
    if creds is None or creds.scheme.lower() != "bearer":
        return None
    try:
        claims = decode_token(creds.credentials)
    except KeycloakAuthError:
        return None
    return _claims_to_user(claims)


def require_roles(*required: str):
    """Crea una dependencia que verifica que el usuario tenga TODOS los roles."""
    required_set = set(required)

    def _checker(user: KeycloakUser = Depends(get_current_user)) -> KeycloakUser:
        if not required_set.issubset(user.roles):
            faltantes = sorted(required_set - set(user.roles))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Faltan roles requeridos: {faltantes}",
            )
        return user

    return _checker


def require_any_role(roles: Iterable[str]):
    """Igual que require_roles pero basta con tener UNO de los roles."""
    allowed = set(roles)

    def _checker(user: KeycloakUser = Depends(get_current_user)) -> KeycloakUser:
        if allowed.isdisjoint(user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere uno de los roles: {sorted(allowed)}",
            )
        return user

    return _checker
