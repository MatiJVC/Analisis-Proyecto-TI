# Contrato de eventos CRM → Proyecto 09 (Analítica)

Dirigido al equipo del CRM (`pgti-proyecto-crm-backend`, Proyecto 07). Describe
qué debe enviarse a nuestro endpoint de ingesta para que el dashboard de
Soporte/CRM refleje el estado real de los tickets.

## Endpoint

```
POST /v1/events
Content-Type: application/json

{
  "source": "crm",
  "event_type": "<uno de los listados abajo>",
  "payload": { ... }
}
```

Respuesta inmediata **202 Accepted** (`{"message": "event stored", "event_id": ..., ...}`);
el procesamiento es asíncrono, no bloquea al emisor.

## Por qué este documento

Hoy solo llega `ticket.creado`. Las transiciones de estado
(asignación/resolución/cierre) **nunca llegan** a nuestro pipeline — viven
únicamente en su sistema y nosotros las vemos solo de forma puntual vía
`GET /v1/kpis/crm/tickets/{id}/live`. Resultado: nuestras KPIs de resolución
(`resolutionRate`, `avgResponseTimeMinutes`) quedan en 0% aunque el ticket
esté resuelto en su sistema. **Para que se corrija, deben emitir los eventos
de transición** (`ticket.asignado`/`resuelto`/`cerrado`) a este endpoint,
además de `ticket.creado`.

## Forma aceptada del payload

Aceptamos su `TicketDto` **nativo** tal como lo devuelve `GET
/api/v1/analytics/estado-ticket/{id}` — no hace falta transformarlo:

| Su campo nativo | Equivalente interno | Notas |
|---|---|---|
| `id` | `ticket_id` | Se acepta cualquiera de los dos; si no viene `ticket_id`, usamos `id`. |
| `estado` | `estado` | Minúscula sin tilde aceptada (`abierto`, `resuelto`, `cerrado`, `progreso`) — se normaliza internamente. |
| `prioridad` | `prioridad` | Minúscula sin tilde aceptada (`baja`, `media`, `alta`, `critica`). |
| `canal` | `canal` | Minúscula sin tilde aceptada (`chat`, `email`, `telefono`, `app`). |
| `creado_en` | — | Usado como `opened_at` en `ticket.creado`, y como inicio para calcular el tiempo de resolución si no viene `resolution_time_hours`. |
| `actualizado_en` | — | Usado como `resolved_at`/`closed_at` si no vienen esos campos explícitos. |
| `suscripcion_id_ref` | `suscripcion_id_red` | Se acepta el nombre nativo `_ref`; internamente se guarda como `_red` (nombre histórico de nuestro modelo). |
| `resolucion`, `agente_id`, `pago_id_ref`, `pedido_id_ref`, `salud_ref`, `fecha_vencimiento_sla`, `cliente_id`, `cliente_nombre` | igual | Passthrough directo. |

**No es necesario enviar `resolution_time_hours` ni `resolved_at`/`closed_at`
explícitos** — si no vienen, los calculamos nosotros a partir de `creado_en` y
`actualizado_en`. Si prefieren enviarlos explícitos, tienen prioridad sobre el
cálculo.

## Eventos soportados (`event_type`)

### `ticket.creado`
Crea el ticket. Payload = su `TicketDto` en el momento de creación.
```json
{
  "source": "crm",
  "event_type": "ticket.creado",
  "payload": {
    "id": "b2fba3fb-6ca5-4924-855e-85bdd0b64a07",
    "asunto": "No puedo pagar mi suscripción",
    "estado": "abierto",
    "prioridad": "critica",
    "canal": "email",
    "cliente_id": 10,
    "cliente_nombre": "Enzo Inostroza",
    "creado_en": "2026-07-09T03:11:04.261Z",
    "fecha_vencimiento_sla": "2026-07-09T11:11:04.191Z",
    "pago_id_ref": null,
    "pedido_id_ref": null,
    "salud_ref": null,
    "suscripcion_id_ref": null
  }
}
```

### `ticket.asignado`
Requiere que el ticket ya exista (fue creado antes). Cambia `estado → Progreso`.
```json
{"source": "crm", "event_type": "ticket.asignado",
 "payload": {"id": "b2fba3fb-...", "agente_id": "p04.agente@crm"}}
```

### `ticket.escalado`
```json
{"source": "crm", "event_type": "ticket.escalado",
 "payload": {"id": "b2fba3fb-...", "prioridad_al_escalar": "critica"}}
```

### `ticket.resuelto` — **el que falta hoy y corrige las KPIs**
```json
{
  "source": "crm",
  "event_type": "ticket.resuelto",
  "payload": {
    "id": "b2fba3fb-6ca5-4924-855e-85bdd0b64a07",
    "estado": "resuelto",
    "actualizado_en": "2026-07-09T03:11:55.972Z",
    "resolucion": "Se reembolsó el cargo duplicado"
  }
}
```
Acepta la transición desde `Abierto` o `Progreso` (no es obligatorio pasar
primero por `ticket.asignado`).

### `ticket.cerrado`
```json
{"source": "crm", "event_type": "ticket.cerrado",
 "payload": {"id": "b2fba3fb-...", "actualizado_en": "...", "csat_score": 4}}
```
Acepta la transición desde `Abierto`, `Progreso` o `Resuelto`. Si el ticket se
cierra directo (sin pasar por `resuelto`), igual queda contabilizado en la
tasa de resolución y en el tiempo de resolución.

### `ticket.sla_violado`, `interaccion.creada`, `kb.articulo.usado`
Sin cambios — ver los tests existentes (`backend/tests/test_crm_events.py`)
para el payload completo.

## Qué NO cambia

- Reabrir un ticket ya terminal (`Resuelto`/`Cerrado`) sigue rechazado — el
  evento se descarta si no respeta el flujo `Abierto → Progreso →
  {Resuelto | Cerrado}`.
- Un `estado`/`prioridad`/`canal` no reconocido descarta el evento (fail-fast)
  en vez de guardarlo con un dato inválido.
