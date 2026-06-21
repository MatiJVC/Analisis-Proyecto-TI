# Análisis Proyecto TI

## Servicios necesarios

| Servicio   | Origen                                                                 | URL / Puerto |
| ---------- | ---------------------------------------------------------------------- | ------------ |
| Postgres   | `docker-compose.yml` (este repo)                                       | localhost:5434 |
| Backend    | FastAPI (`backend/`)                                                   | localhost:8000 |
| Frontend   | Next.js (`Frontend/`)                                                  | localhost:3000 |
| Keycloak   | Externo (grupo de identidad), expuesto vía **ngrok** en prod           | https://underarm-those-stardust.ngrok-free.dev |

## 0) Sistema de identidad (Keycloak)

**Por defecto el proyecto apunta al Keycloak del grupo 1 que ya está en
producción** (URL en la tabla de arriba). No necesitas levantar nada local
para autenticarte. Los `.env` ya vienen apuntados ahí.

Datos del realm/cliente que el grupo de identidad ya configuró:

| Campo                 | Valor                                                  |
| --------------------- | ------------------------------------------------------ |
| Realm                 | `sistema-centralizado`                                 |
| Client ID             | `p9`                                                   |
| Client authentication | **Off** (cliente público con PKCE)                     |
| Standard flow         | ✓                                                      |
| Direct access grants  | ✓                                                      |
| Valid redirect URIs   | `http://localhost:3000/*`                              |
| Web origins           | `http://localhost:3000`                                |

Si alguno de esos campos no está bien configurado, el login redirige y
queda colgado. En ese caso, escribir al grupo 1 para que lo arregle desde
la consola admin de Keycloak.

### Modo local (opcional, para desarrollo offline)

Si quieres correr todo sin depender de ngrok (por ejemplo, sin internet
o cuando hay rate-limit), clona el repo del Keycloak local en una
carpeta fuera de este proyecto:

```bash
git clone git@gitlab.com:bloppaa/sistema-identidad.git
cd sistema-identidad
docker compose up -d
```

Consola admin local: <http://localhost:8080> (admin / admin).

Y crea un `Frontend/.env.local` (gitignored) con los valores locales:

```
NEXT_PUBLIC_KEYCLOAK_URL=http://localhost:8080
NEXT_PUBLIC_KEYCLOAK_CLIENT_ID=proyecto-analisis-ti
```

Y un `backend/.env.local` con:

```
KEYCLOAK_URL=http://localhost:8080
```

Después corre el script idempotente para crear roles/usuarios/cliente
en el realm local:

```powershell
.\scripts\bootstrap-keycloak.ps1
```

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

## Roles y permisos

El sistema usa **roles de realm** de Keycloak (`sistema-centralizado`).
Mantener en sync con `backend/app/api/routes/kpis.py` (constantes
`SUBS_ROLES`, `ORDERS_ROLES`, etc.) y `Frontend/lib/roles.ts`
(`ROLE_MATRIX`).

### Roles definidos

| Rol             | Descripción                                                |
| --------------- | ---------------------------------------------------------- |
| `admin`         | Acceso total. Ve todos los dashboards.                     |
| `analista`      | Lectura de todos los dashboards (overview + 4 dominios).   |
| `salud`         | Equipo de salud. Solo `/kpis/salud/*` y `/health`.         |
| `subscriptions` | Equipo de suscripciones. Solo `/kpis/subscriptions/*`.     |
| `orders`        | Equipo de órdenes. Solo `/kpis/orders/*` y `/orders`.      |
| `incidents`     | Equipo de incidentes. Solo `/kpis/incidents/*`.            |

### Matriz de acceso (backend)

| Endpoint                | Roles permitidos                          |
| ----------------------- | ----------------------------------------- |
| `/auth/*`, `/events/*`  | cualquier autenticado                     |
| `/kpis/overview/*`      | `admin`, `analista`                       |
| `/kpis/orders/*`        | `admin`, `analista`, `orders`             |
| `/kpis/subscriptions/*` | `admin`, `analista`, `subscriptions`      |
| `/kpis/salud/*`         | `admin`, `analista`, `salud`              |
| `/kpis/incidents/*`     | `admin`, `analista`, `incidents`          |

Sin token o con rol incorrecto, el backend responde `401` o `403`.
El frontend filtra el sidebar y bloquea las páginas con `<RoleGate>`.

### Usuarios de prueba

#### Prod (ngrok del grupo 1) — default

El grupo de identidad creó usuarios bajo el patrón `p9-<rol>@ucn.cl` para
nuestro proyecto. Confirmado al menos:

| Email                       | Password    | Rol asignado    |
| --------------------------- | ----------- | --------------- |
| `p9-subscriptions@ucn.cl`   | `Subs123!`  | `subscriptions` |

Si necesitas usuarios para otros roles (admin, salud, orders, incidents,
etc.), pídeselos al grupo 1.

#### Modo local (opcional)

Si estás corriendo el Keycloak local con `.env.local`, hay un script
idempotente que crea los 11 roles, 11 usuarios de prueba y el cliente
`proyecto-analisis-ti` desde cero (útil porque ese container no
persiste datos):

```powershell
.\scripts\bootstrap-keycloak.ps1
# Si Keycloak corre en otra URL:
.\scripts\bootstrap-keycloak.ps1 -KeycloakUrl http://otra-url:8080
```

Usuarios que crea (todos con email `<usuario>@ucn.cl`):

| Usuario          | Password       | Rol             |
| ---------------- | -------------- | --------------- |
| `admingrupo9`    | `admin`        | `admin`         |
| `analista`       | `Analista123!` | `analista`      |
| `salud`          | `Salud123!`    | `salud`         |
| `subscriptions`  | `Subs123!`     | `subscriptions` |
| `orders`         | `Orders123!`   | `orders`        |
| `incidents`      | `Inc123!`      | `incidents`     |
| `iot`            | `Iot123!`      | `iot`           |
| `notificaciones` | `Notif123!`    | `notifications` |
| `pagos`          | `Pagos123!`    | `payments`      |
| `inventario`     | `Inv123!`      | `inventory`     |
| `crm`            | `Crm123!`      | `crm`           |

Al hacer login en <http://localhost:3000>, cada usuario ve solo los menús
y dashboards que le corresponden.

## Cómo proteger un endpoint del backend

```python
from fastapi import Depends
from app.auth import get_current_user, require_roles, require_any_role, KeycloakUser

@router.get("/protegido")
def protegido(user: KeycloakUser = Depends(get_current_user)):
    return {"hola": user.username}

# Exige TODOS los roles listados.
@router.get("/solo-admin", dependencies=[Depends(require_roles("admin"))])
def solo_admin():
    return {"ok": True}

# Exige al menos UNO de los roles (lo que usan los endpoints de KPIs).
@router.get("/kpis-salud", dependencies=[Depends(require_any_role(["admin", "analista", "salud"]))])
def kpis_salud():
    return {"ok": True}
```

Los endpoints de `/kpis/*` ya exigen los roles de la matriz de arriba.
Los de `/events/*` siguen abiertos a cualquier autenticado (el frontend
manda el token, pero no se discrimina por rol al ingestar eventos).

## Variables de entorno

`Frontend/.env` (apunta a Keycloak prod por defecto):

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_KEYCLOAK_URL=https://underarm-those-stardust.ngrok-free.dev
NEXT_PUBLIC_KEYCLOAK_REALM=sistema-centralizado
NEXT_PUBLIC_KEYCLOAK_CLIENT_ID=p9
```

`backend/.env` (apunta a Keycloak prod por defecto):

```
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5434/proyecto_ti
KEYCLOAK_URL=https://underarm-those-stardust.ngrok-free.dev
KEYCLOAK_REALM=sistema-centralizado
KEYCLOAK_AUDIENCE=account
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Para volver a un Keycloak local, sobreescribe estas variables en
`Frontend/.env.local` y `backend/.env.local` (ver sección [Modo local](#modo-local-opcional-para-desarrollo-offline)).

## Troubleshooting de Keycloak

| Síntoma | Causa probable | Solución |
| --- | --- | --- |
| Login redirige y queda colgado en una página de error | Faltan `redirect URIs` o `web origins` en el cliente `p9` | Pedir al grupo 1 que agregue `http://localhost:3000/*` y `http://localhost:3000` |
| El token llega al backend pero responde `401 Invalid audience` | El cliente `p9` no incluye `account` en el `aud` del token | En `backend/.env` cambiar `KEYCLOAK_AUDIENCE=p9` y reiniciar el backend |
| El frontend recibe un HTML con "Visit Site" en vez del login | El intersticial de ngrok-free está activo | Pedir al grupo 1 que desactive el banner en su configuración de ngrok |
| Errores `429 Too Many Requests` o login esporádico | Rate limit de ngrok-free (~120 req/min) | Esperar 1 minuto, o cambiar a modo local si la cuota se mantiene saturada |
| `FATAL: KEYCLOAK_URL usa HTTP ... en entorno 'production'` al arrancar el backend | El check de seguridad rechaza HTTP fuera de development | Asegurarse de que `KEYCLOAK_URL` empiece con `https://` o setear `ENVIRONMENT=development` |
