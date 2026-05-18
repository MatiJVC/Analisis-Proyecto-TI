# RESUMEN: Tabla fact_payments_events - Auditoría Inmutable

## ✅ Implementado

He diseñado e implementado una **tabla de auditoría inmutable** `fact_payments_events` que registra de forma atómica cada evento enviado por la pasarela de pagos (Proyecto 04) hacia el sistema de analítica (Proyecto 09).

### 📋 Artefactos Creados

1. **Modelo ORM** (`backend/app/models/warehouse/pagos/fact_payments_events.py`)
   - Tabla: `fact_payments_events`
   - Campos: id (PK), transaction_id (UUID), order_id, subscription_id, amount, token_transaccion, codigo_error, status, timestamp_evento
   - Índices optimizados para queries analíticas

2. **Integración en Endpoint** (`backend/app/api/routes/events.py`)
   - Al recibir `intento_pago`: inserta fila con estado `'esperando_revisión'`
   - Al recibir `confirmar_pago`: inserta fila con estado final (`'Aprobado'`, `'discrepancia_de_monto'`, etc.)
   - Cada evento es **inmutable** (solo se inserta, nunca se modifica)

3. **Documentación Completa** (`PAYMENT_EVENTS_DESIGN.md`)
   - Especificación de campos y constraints
   - Payloads de ejemplo para `intento_pago` y `confirmar_pago`
   - Reglas de validación (Pydantic)
   - Queries analíticas SQL
   - Diagrama de flujo ACID

4. **Test End-to-End** (`backend/tests/test_fact_payments_events.py`)
   - Verifica que el flujo completo (intento → confirmación) genera dos filas inmutables
   - Valida estados, timestamps y correlación por `transaction_id`

### 🔄 Flujo de Ingesta

```
POST /events (intento_pago)
  ↓
Validar payload (Pydantic)
  ↓
Insertar en fact_pagos (estado='esperando_revisión')
  ↓
INSERTAR AUDITORÍA en fact_payments_events (status='esperando_revisión')
  ↓
COMMIT + HTTP 201
  ↓
---
POST /events (confirmar_pago)
  ↓
Buscar por token, validar consistencia, actualizar fact_pagos
  ↓
INSERTAR AUDITORÍA en fact_payments_events (status='Aprobado'/error)
  ↓
COMMIT + HTTP 201
```

### 📊 Estados Posibles

1. `esperando_revisión` — Estado inicial tras intento
2. `Aprobado` — Confirmado exitosamente
3. `discrepancia_de_monto` — Monto no coincide
4. `discrepancia_de_transacciones` — Transaction ID no coincide
5. `Error rechazo` — Rechazado (fondos, etc.)

### 🔒 Propiedades ACID

✅ **Atomicity:** INSERT auditoría + COMMIT o rollback total
✅ **Consistency:** Validaciones Pydantic + constraints SQL
✅ **Isolation:** Transacciones SQLAlchemy aisladas
✅ **Durability:** PostgreSQL garantiza persistencia

## 📝 Ejemplos de Payloads

### Request: intento_pago

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

### Response (HTTP 201)

```json
{
  "message": "event stored",
  "event_id": 42,
  "source": "payments",
  "event_type": "intento_pago"
}
```

### Base de Datos (fact_payments_events)

| id | transaction_id | order_id | amount | status | timestamp_evento |
|----|---|---|---|---|---|
| 101 | 550e8400... | ORD-2026-001 | 99.99 | esperando_revisión | 2026-05-16T14:30:00+00:00 |

---

### Request: confirmar_pago

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

### Base de Datos (fact_payments_events) — Nueva Fila Insertada

| id | transaction_id | order_id | amount | status | timestamp_evento |
|----|---|---|---|---|---|
| 101 | 550e8400... | ORD-2026-001 | 99.99 | esperando_revisión | 2026-05-16T14:30:00+00:00 |
| 102 | 550e8400... | ORD-2026-001 | 99.99 | Aprobado | 2026-05-16T14:35:00+00:00 |

**Ventaja:** Historial completo de transición de estados sin sobrescrituras.

## 🧪 Ejecutar el Test

### Requisitos Previos

1. PostgreSQL corriendo en `localhost:5434` con BD `proyecto_ti`
2. Dependencias Python instaladas:
   ```bash
   cd backend
   python -m pip install -r requirements.txt
   # O manualmente:
   python -m pip install psycopg sqlalchemy python-dotenv
   ```

### Comando de Prueba

```bash
cd backend
python tests/test_fact_payments_events.py
```

**Salida esperada:**

```
================================================================================
fact_payments_events Immutable Audit Table Test
================================================================================
✅ Database tables created/verified
🧹 Test data cleaned

📝 Step 1: Registering payment attempt (intento_pago)
  ✓ Raw event created: id=1
  ✓ FactPagos inserted: transaction_id=...
  ✓ Audit event inserted: id=101, status=esperando_revisión

✅ Step 2: Confirming payment (confirmar_pago)
  ✓ FactPagos updated: status_id=2
  ✓ Audit event inserted: id=102, status=Aprobado

🔍 Verifying immutable audit trail:
  Total audit events for tx ....: 2
    - id=101, status=esperando_revisión, amount=99.99, timestamp=2026-05-16T14:30:00+00:00
    - id=102, status=Aprobado, amount=99.99, timestamp=2026-05-16T14:35:00+00:00

📊 Sample analytics queries:
  - Total events: 2
  - Aprobado count: 1
  - Conversion rate: 50.00%
  - Status distribution:
      esperando_revisión: 1
      Aprobado: 1

✅ Test PASSED: Immutable audit trail verified

================================================================================
```

## 📈 Queries Analíticas

### 1. Historial de una transacción

```sql
SELECT * FROM fact_payments_events 
WHERE transaction_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY timestamp_evento ASC;
```

### 2. Tasa de conversión

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

## 🎯 Integraciones Posteriores

1. **Power BI:** Consumir `fact_payments_events` para dashboards (KPIs, tendencias)
2. **Alertas:** Monitorizar tasa de rechazo > 0.5% en ventana de 15 min
3. **Webhook:** Notificar a sistemas externos (contabilidad, reconciliación)
4. **Reconciliación:** Tabla `cierre_diario` compara totales aprobados vs reportados

## 📦 Cambios Git

```bash
git add backend/app/models/warehouse/pagos/fact_payments_events.py
git add backend/app/api/routes/events.py
git add backend/main.py
git add backend/tests/test_fact_payments_events.py
git add PAYMENT_EVENTS_DESIGN.md
git commit -m "feat(payments): immutable audit table fact_payments_events for payment gateway events"
```

---

**Creado:** 2026-05-16  
**Versión:** 1.0  
**Tecnología:** Python/FastAPI + SQLAlchemy + PostgreSQL  
**Status:** ✅ Listo para integración con Power BI y alertas
