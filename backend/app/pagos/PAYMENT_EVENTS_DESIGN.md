# Diseño: Tabla de Eventos de Pagos (fact_payments_events)

## Resumen Ejecutivo

El **Proyecto 09 (Analítica)** ingesta eventos atómicos de la **Pasarela de Pagos (Proyecto 04)** y los registra de forma **inmutable** en la tabla `fact_payments_events`. Esta tabla actúa como **tabla de auditoría transaccional** que preserva todos los eventos sin modificaciones posteriores.

## Modelo de Base de Datos

### Tabla: `fact_payments_events`

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO INCREMENT | Identificador único del evento (secuencial) |
| `transaction_id` | UUID | NOT NULL, INDEX | Identificador único de la transacción |
| `order_id` | VARCHAR(255) | NULLABLE, INDEX | ID de la orden asociada (puede ser NULL) |
| `subscription_id` | VARCHAR(255) | NULLABLE, INDEX | ID de suscripción (puede ser NULL) |
| `amount` | NUMERIC(18, 2) | NOT NULL | Monto de la transacción (máx 16 dígitos, 2 decimales) |
| `token_transaccion` | VARCHAR(255) | NOT NULL, INDEX | Token único para confirmación posterior |
| `codigo_error` | VARCHAR(100) | NULLABLE | Código de error si aplica |
| `status` | VARCHAR(100) | NOT NULL, INDEX | Estado del pago (ver tabla de estados) |
| `timestamp_evento` | TIMESTAMP WITH TIMEZONE | NOT NULL, INDEX, UTC | Marca de tiempo UTC del evento |

### Estados Posibles (status)

Los estados de `status` se alinean con el **flujo operativo del negocio**:

1. **`esperando_revisión`** — Estado inicial tras recibir `intento_pago`
2. **`Aprobado`** — Pago confirmado y aprobado por la pasarela
3. **`discrepancia_de_monto`** — El monto confirmado no coincide con lo registrado
4. **`discrepancia_de_transacciones`** — El transaction_id confirmado no coincide
5. **`Error rechazo`** — Rechazado por razones varias (fondos insuficientes, etc.)

### Índices

```sql
CREATE INDEX idx_fact_payments_events_tx_token_ts 
  ON fact_payments_events(transaction_id, token_transaccion, timestamp_evento);
```

## Flujo de Ingesta: Endpoint POST /events

### Endpoint

```
POST /events
Content-Type: application/json
```

### Payloads por Tipo de Evento

#### 1. Evento: `intento_pago` (Paso 1)

**Descripción:** Se registra un intento de pago inicial. Se inserta fila con estado `esperando_revisión`.

**Request:**

```json
{
  "source": "payments",
  "event_type": "intento_pago",
  "payload": {
    "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
    "order_id": "ORD-2026-001",
    "subscription_id": null,
    "monto": 99.99,
    "token_transaccion": "tk_2026_05_001_abc123xyz",
    "timestamp_evento": "2026-05-16T14:30:00Z"
  }
}
```

**Response (HTTP 201):**

```json
{
  "message": "event stored",
  "event_id": 42,
  "source": "payments",
  "event_type": "intento_pago"
}
```

**Resultado en DB:**

```sql
INSERT INTO fact_payments_events (
  transaction_id, order_id, subscription_id, amount, 
  token_transaccion, codigo_error, status, timestamp_evento
) VALUES (
  '550e8400-e29b-41d4-a716-446655440000', 'ORD-2026-001', NULL, 99.99,
  'tk_2026_05_001_abc123xyz', NULL, 'esperando_revisión', '2026-05-16T14:30:00+00:00'
);
```

#### 2. Evento: `confirmar_pago` (Paso 2)

**Descripción:** Se recibe confirmación de la pasarela. Se **inserta una nueva fila** con el estado final (Aprobado, error, discrepancia).

**Request:**

```json
{
  "source": "payments",
  "event_type": "confirmar_pago",
  "payload": {
    "token_transaccion": "tk_2026_05_001_abc123xyz",
    "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
    "approved": true,
    "codigo_error": null,
    "timestamp_evento": "2026-05-16T14:35:00Z"
  }
}
```

**Response (HTTP 201):**

```json
{
  "message": "event stored",
  "event_id": 43,
  "source": "payments",
  "event_type": "confirmar_pago"
}
```

**Resultado en DB:**

```sql
-- Nueva fila se inserta (auditoría inmutable)
INSERT INTO fact_payments_events (
  transaction_id, order_id, subscription_id, amount, 
  token_transaccion, codigo_error, status, timestamp_evento
) VALUES (
  '550e8400-e29b-41d4-a716-446655440000', 'ORD-2026-001', NULL, 99.99,
  'tk_2026_05_001_abc123xyz', NULL, 'Aprobado', '2026-05-16T14:35:00+00:00'
);
```

### Reglas de Validación (Pydantic)

#### `AttemptPaymentPayload`

```python
class AttemptPaymentPayload(BaseModel):
    transaction_id: UUID  # No puede ser vacío
    order_id: Optional[str] = None
    subscription_id: Optional[str] = None
    monto: Decimal  # Must be non-negative
    token_transaccion: str  # 1-255 chars
    timestamp_evento: datetime  # UTC
```

#### `ConfirmPaymentPayload`

```python
class ConfirmPaymentPayload(BaseModel):
    token_transaccion: str  # 1-255 chars; used as lookup key
    transaction_id: Optional[UUID] = None
    approved: bool  # True => Aprobado, False => discrepancia/error
    codigo_error: Optional[str] = None  # Max 100 chars
    timestamp_evento: datetime  # UTC
```

## Respuestas HTTP

| Código | Escenario |
|--------|-----------|
| **201 Created** | Evento validado e insertado exitosamente |
| **400 Bad Request** | Payload inválido (campos faltantes, tipos incorrectos, validación fallida) |
| **500 Internal Server Error** | Error de BD o procesamiento inesperado |

## Ejemplo de Error (HTTP 400)

```json
{
  "detail": "Invalid payment attempt payload: 1 validation error for AttemptPaymentPayload\nmonto\n  ensure this value is greater than or equal to 0 (type=value_error.number.not_ge; limit_value=0)"
}
```

## Arquitectura de Inserción

### Flujo de Procesamiento

```
1. POST /events
   ↓
2. Validar payload con Pydantic (AttemptPaymentPayload o ConfirmPaymentPayload)
   ↓
3. Crear/buscar entity en tabla transaccional (FactPagos o dim_estados_conciliacion)
   ↓
4. INSERTAR fila INMUTABLE en fact_payments_events
   ↓
5. COMMIT
   ↓
6. Retornar HTTP 201
```

### Propiedades ACID

- **Atomicity:** Cada POST /events inserta exactamente una fila o revierte todo (rollback)
- **Consistency:** Las validaciones Pydantic + constraints SQL aseguran datos válidos
- **Isolation:** Transacciones SQL aisladas (SQLAlchemy Session default)
- **Durability:** Commits a PostgreSQL garantizan persistencia

## Ventajas del Diseño

✅ **Inmutabilidad:** Los eventos nunca se modifican; solo se insertan nuevos registros.  
✅ **Auditoría completa:** Historial completo de cada transacción (intento → confirmación).  
✅ **Trazabilidad:** Cada evento tiene timestamp UTC y token para correlación.  
✅ **Escalabilidad:** Índices en `transaction_id`, `token_transaccion`, `timestamp_evento` para queries rápidas.  
✅ **Compliance:** Compatible con regulaciones (PCI-DSS, auditoría financiera).

## Queries Analíticas de Ejemplo

### 1. Ver historial completo de una transacción

```sql
SELECT * FROM fact_payments_events 
WHERE transaction_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY timestamp_evento ASC;
```

### 2. Conversión (% aprobados vs intento)

```sql
SELECT 
  COUNT(CASE WHEN status = 'Aprobado' THEN 1 END)::FLOAT / 
  COUNT(DISTINCT transaction_id) AS conversion_rate
FROM fact_payments_events
WHERE timestamp_evento >= NOW() - INTERVAL '1 day'
  AND status IN ('esperando_revisión', 'Aprobado');
```

### 3. Volumen por período

```sql
SELECT 
  DATE_TRUNC('hour', timestamp_evento) AS hour,
  COUNT(*) as event_count,
  SUM(amount) as total_amount
FROM fact_payments_events
WHERE timestamp_evento >= NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', timestamp_evento)
ORDER BY hour DESC;
```

### 4. Tasa de rechazo y motivos

```sql
SELECT 
  status,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM fact_payments_events WHERE timestamp_evento >= NOW() - INTERVAL '1 day'), 2) as percent
FROM fact_payments_events
WHERE timestamp_evento >= NOW() - INTERVAL '1 day'
GROUP BY status
ORDER BY count DESC;
```

## Integraciones Posteriores

1. **Power BI:** Consumir `fact_payments_events` para dashboards de KPIs (conversión, AOV, etc.)
2. **Alertas:** Monitorizar tasa de rechazo > 0.5% en ventana móvil de 15 min (modelo `PriorityAlert`)
3. **Webhook:** Enviar POST a sistemas externos (reconciliación, contabilidad) cuando `status = 'Aprobado'`
4. **Cierre diario:** Tabla `cierre_diario` compara totales aprobados vs reportados

---

**Creado:** 2026-05-16  
**Versión:** 1.0  
**Tecnología:** Python/FastAPI + SQLAlchemy + PostgreSQL
