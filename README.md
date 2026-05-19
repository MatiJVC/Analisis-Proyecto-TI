# Análisis Proyecto TI

## Servicios necesarios

| Servicio   | Origen                                                                 | Puerto |
| ---------- | ---------------------------------------------------------------------- | ------ |
| Postgres   | `docker-compose.yml` (este repo)                                       | 5434   |
| Backend    | FastAPI (`backend/`)                                                   | 8000   |
| Frontend   | Next.js (`Frontend/`)                                                  | 3000   |
| Keycloak   | Repo del equipo de identidad: `git@gitlab.com:bloppaa/sistema-identidad.git` | 8080   |

## 0) Levantar Keycloak (otro repo)

En una carpeta **fuera** de este proyecto:

```bash
git clone git@gitlab.com:bloppaa/sistema-identidad.git
cd sistema-identidad
docker compose up -d
```

Consola admin: <http://localhost:8080> (admin / admin).

Pedir al equipo de identidad que registre nuestro cliente en el realm
`sistema-centralizado` con:

| Campo                 | Valor                          |
| --------------------- | ------------------------------ |
| Client ID             | `proyecto-analisis-ti`         |
| Client authentication | **Off** (cliente público)      |
| Standard flow         | ✓                              |
| Direct access grants  | ✓                              |
| Valid redirect URIs   | `http://localhost:3000/*`      |
| Web origins           | `http://localhost:3000`        |

Si cambia el Client ID, hay que actualizar:

- `Frontend/.env` → `NEXT_PUBLIC_KEYCLOAK_CLIENT_ID`
- (no afecta al backend, que solo valida tokens del realm)

## 1) Levantar Postgres

```bash
docker compose up -d
```

## 2) Levantar backend (FastAPI)

Primera vez:

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m fastapi dev
```

Si ya tienes `.venv`:

```bash
cd backend
.venv\Scripts\Activate.ps1
python -m fastapi dev
```

Endpoints útiles para probar la integración con Keycloak:

- `GET /auth/status` — público, dice si el token es válido.
- `GET /auth/me` — exige `Authorization: Bearer <jwt>`, devuelve el usuario.

## 3) Levantar frontend (Next.js)

```bash
cd Frontend
npm install
npm run dev
```

Al abrir <http://localhost:3000> el frontend redirige automáticamente al login
de Keycloak. Tras autenticarse vuelve al dashboard con el token cargado, y
todas las llamadas a la API ya viajan con `Authorization: Bearer <jwt>`.

## Cómo proteger un endpoint del backend

```python
from fastapi import Depends
from app.auth import get_current_user, require_roles, KeycloakUser

@router.get("/protegido")
def protegido(user: KeycloakUser = Depends(get_current_user)):
    return {"hola": user.username}

@router.get("/solo-admin", dependencies=[Depends(require_roles("admin"))])
def solo_admin():
    return {"ok": True}
```

Actualmente los endpoints de KPIs y eventos están **abiertos** (modo opcional):
el frontend ya manda el token, pero el backend no lo exige todavía. Cuando
quieran obligar login en cada endpoint, basta con agregarles
`Depends(get_current_user)` o ponerlo a nivel de router.

## Variables de entorno

`Frontend/.env`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_KEYCLOAK_URL=http://localhost:8080
NEXT_PUBLIC_KEYCLOAK_REALM=sistema-centralizado
NEXT_PUBLIC_KEYCLOAK_CLIENT_ID=proyecto-analisis-ti
```

`backend/.env`:

```
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5434/proyecto_ti
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=sistema-centralizado
KEYCLOAK_AUDIENCE=account
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```
