# 📊 Event Ingestion & Analytics API

Sistema de ingestión de eventos y análisis de KPIs en tiempo real para múltiples dominios (órdenes, suscripciones, IoT, notificaciones).

## 🚀 Quick Start

### 1. Instalar Dependencias
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configurar Base de Datos
```bash
# Crear archivo .env con conexión a PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5434/analytics_db
```

### 3. Iniciar Servidor
```bash
python main.py
# O con auto-reload
fastapi dev
```

Servidor corriendo en: **http://localhost:8000**  
Documentación interactiva: **http://localhost:8000/docs**

---

## 📡 Eventos Permitidos

### POST /events

Endpoint para enviar eventos que se procesan **automáticamente**.

#### Headers Requeridos
```
Content-Type: application/json
```

---

## 🛒 Dominio: ORDERS

### Eventos Soportados

#### 1. **pedido_creado** - Orden Creada
```json
POST http://localhost:8000/events

{
  "source": "orders",
  "event_type": "pedido_creado",
  "payload": {
    "order_id": 1000,
    "customer_id": 100,
    "sales_channel": "web",
    "total_amount": 50000.00,
    "total_items": 2
  }
}
```
**Campos obligatorios:** `order_id`, `customer_id`  
**Campos opcionales:** `sales_channel`, `total_amount`, `total_items`  
**Resultado:** Crea nuevo registro en `fact_orders` con estado `created`

---

#### 2. **stock_reservado** - Stock Reservado
```json
{
  "source": "orders",
  "event_type": "stock_reservado",
  "payload": {
    "order_id": 1000,
    "customer_id": 100
  }
}
```
**Campos obligatorios:** `order_id`, `customer_id`  
**Resultado:** Actualiza `stock_reserved=TRUE`, status=`stock_reserved`

---

#### 3. **pedido_pagado** - Pago Exitoso
```json
{
  "source": "orders",
  "event_type": "pedido_pagado",
  "payload": {
    "order_id": 1000,
    "customer_id": 100
  }
}
```
**Campos obligatorios:** `order_id`, `customer_id`  
**Resultado:** Actualiza `payment_success=TRUE`, status=`paid`

---

#### 4. **pago_fallido** - Pago Fallido
```json
{
  "source": "orders",
  "event_type": "pago_fallido",
  "payload": {
    "order_id": 1000,
    "customer_id": 100
  }
}
```
**Campos obligatorios:** `order_id`, `customer_id`  
**Resultado:** Actualiza `payment_success=FALSE`, status=`payment_failed`

---

#### 5. **listo_para_despacho** - Listo para Despacho
```json
{
  "source": "orders",
  "event_type": "listo_para_despacho",
  "payload": {
    "order_id": 1000,
    "customer_id": 100
  }
}
```
**Campos obligatorios:** `order_id`, `customer_id`  
**Resultado:** Actualiza status=`ready_for_dispatch`

---

#### 6. **pedido_en_transito** - En Tránsito
```json
{
  "source": "orders",
  "event_type": "pedido_en_transito",
  "payload": {
    "order_id": 1000,
    "customer_id": 100
  }
}
```
**Campos obligatorios:** `order_id`, `customer_id`  
**Resultado:** Actualiza status=`in_transit`

---

#### 7. **pedido_entregado** - Entregado (Final)
```json
{
  "source": "orders",
  "event_type": "pedido_entregado",
  "payload": {
    "order_id": 1000,
    "customer_id": 100
  }
}
```
**Campos obligatorios:** `order_id`, `customer_id`  
**Resultado:** 
- Actualiza `delivery_completed=TRUE`, status=`delivered`
- Calcula automáticamente `processing_time_seconds`

---

#### 8. **stock_agotado** - Stock Agotado
```json
{
  "source": "orders",
  "event_type": "stock_agotado",
  "payload": {
    "order_id": 1000,
    "customer_id": 100
  }
}
```
**Campos obligatorios:** `order_id`, `customer_id`  
**Resultado:** Actualiza `stock_reserved=FALSE`, status=`stock_unavailable`

---

## 🔄 Dominio: SUBSCRIPTIONS

### Eventos Soportados

#### 1. **subscription_created** - Suscripción Creada
```json
POST http://localhost:8000/events

{
  "source": "subscriptions",
  "event_type": "subscription_created",
  "payload": {
    "contract_id": "CTR-7000",
    "user_id": 700,
    "plan_id": 3,
    "start_date": "2026-05-09"
  }
}
```
**Campos obligatorios:** `contract_id`, `user_id`, `plan_id`  
**Campos opcionales:** `start_date`  
**Resultado:** Crea nuevo registro en `fact_subscriptions` con estado `active`

---

#### 2. **renewal_success** - Renovación Exitosa
```json
{
  "source": "subscriptions",
  "event_type": "renewal_success",
  "payload": {
    "contract_id": "CTR-7000",
    "user_id": 700,
    "plan_id": 3
  }
}
```
**Campos obligatorios:** `contract_id`, `user_id`, `plan_id`  
**Resultado:** Actualiza `renewed=TRUE`

---

#### 3. **renewal_failed** - Renovación Fallida
```json
{
  "source": "subscriptions",
  "event_type": "renewal_failed",
  "payload": {
    "contract_id": "CTR-7000",
    "user_id": 700,
    "plan_id": 3
  }
}
```
**Campos obligatorios:** `contract_id`, `user_id`, `plan_id`  
**Resultado:** Actualiza `renewed=FALSE`

---

#### 4. **payment_success** - Pago Exitoso
```json
{
  "source": "subscriptions",
  "event_type": "payment_success",
  "payload": {
    "contract_id": "CTR-7000",
    "user_id": 700,
    "plan_id": 3
  }
}
```
**Campos obligatorios:** `contract_id`, `user_id`, `plan_id`  
**Resultado:** 
- Actualiza `billing_success=TRUE`
- Incrementa `billing_attempts`
- Registra `billing_date`

---

#### 5. **payment_failed** - Pago Fallido
```json
{
  "source": "subscriptions",
  "event_type": "payment_failed",
  "payload": {
    "contract_id": "CTR-7000",
    "user_id": 700,
    "plan_id": 3
  }
}
```
**Campos obligatorios:** `contract_id`, `user_id`, `plan_id`  
**Resultado:** 
- Actualiza `billing_success=FALSE`
- Incrementa `billing_attempts`
- Registra `billing_date`

---

## 📊 Response Format

### Success (201 Created)
```json
{
  "message": "event stored",
  "event_id": 123,
  "source": "orders",
  "event_type": "pedido_creado"
}
```

### Error (400 Bad Request)
```json
{
  "detail": "Invalid event data"
}
```

### Error (500 Internal Server Error)
```json
{
  "detail": "Error al guardar el evento: ..."
}
```

---

## 🔍 Analytics Endpoints

### Orders KPIs
```bash
GET http://localhost:8000/kpis/orders/kpis
GET http://localhost:8000/kpis/orders/channels
GET http://localhost:8000/kpis/orders/status
GET http://localhost:8000/kpis/orders/timeline?days=30
GET http://localhost:8000/kpis/orders/health
```

### Subscriptions KPIs
```bash
GET http://localhost:8000/kpis/subscriptions/renewal-rate
GET http://localhost:8000/kpis/subscriptions/error-rate
GET http://localhost:8000/kpis/subscriptions/auto-service-rate
GET http://localhost:8000/kpis/subscriptions/summary
```

---

## 🧪 Testing con Postman

### Importar Collection

1. Crear nueva request
2. **Method:** POST
3. **URL:** http://localhost:8000/events
4. **Headers:** Content-Type: application/json
5. **Body (raw):** Pegar payload de arriba

O usar el script de testing:
```bash
python app/scripts/test_orders_analytics.py
```

---

## ⚡ Auto-Processing (ETL Automático)

Todos los eventos son **procesados automáticamente**:

```
POST /events (orders)
  ↓
✅ Guardado en raw_events
✅ Procesado automáticamente a fact_orders
✅ KPIs actualizados en tiempo real
```

**No requiere ejecutar scripts ETL manualmente.**

---

## 📁 Estructura del Proyecto

```
backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── events.py           (POST /events)
│   │       └── kpis.py             (GET /kpis/*)
│   ├── etl/
│   │   └── processors/
│   │       ├── order_processor.py   (Auto-ETL Orders)
│   │       └── subscription_processor.py (Auto-ETL Subscriptions)
│   ├── models/
│   │   ├── raw/
│   │   │   └── raw_events.py       (Tabla de eventos crudos)
│   │   └── warehouse/
│   │       ├── fact_orders.py      (Tabla analítica Orders)
│   │       └── fact_subscriptions.py (Tabla analítica Subscriptions)
│   ├── services/
│   │   └── orders_analytics_service.py (KPI calculations)
│   └── schemas/
│       └── orders_analytics_schema.py (Response models)
├── main.py                         (Servidor FastAPI)
└── requirements.txt
```

---

## 🔐 Validaciones

### Orders
- ✅ `order_id` requerido y único
- ✅ `customer_id` requerido
- ✅ Division by zero protegido en KPIs
- ✅ Status actualizado según event_type

### Subscriptions
- ✅ `contract_id` requerido y único (String)
- ✅ `user_id`, `plan_id` requeridos
- ✅ Billing attempts incrementado automáticamente
- ✅ Billing date registrado en pagos

---

## 🐛 Debugging

### Ver logs del servidor
```bash
# En la terminal donde corre FastAPI
✅ [AUTO-ETL] Evento pedido_creado (orders) procesado automáticamente
⚠️  [AUTO-ETL-ORDERS] Error: ...
```

### Verificar datos en BD
```bash
psql -c "SELECT COUNT(*) FROM fact_orders;"
psql -c "SELECT * FROM fact_orders ORDER BY created_at DESC LIMIT 5;"
```

### Revisar eventos sin procesar
```bash
psql -c "SELECT * FROM raw_events WHERE processed=FALSE;"
```

---

## 📞 Soporte

**¿Qué validaciones debo cumplir?**
- Incluir `order_id` y `customer_id` para orders
- Incluir `contract_id`, `user_id`, `plan_id` para subscriptions
- El `event_type` debe coincidir exactamente (case-sensitive)

**¿Qué pasa si falla el procesamiento?**
- El evento se guarda igual en `raw_events`
- Se loguea el error
- La respuesta 201 se envía al cliente (no se pierde el evento)

**¿Qué eventos nuevos quiero agregar?**
- Crear processor en `app/etl/processors/`
- Crear tabla warehouse en `app/models/warehouse/`
- Agregar import y lógica en `app/api/routes/events.py`

---

## 📚 Documentación Adicional

- [ETL_AUTOMATICO.md](./ETL_AUTOMATICO.md) - Detalles del procesamiento automático
- [ORDERS_ANALYTICS_USAGE.md](./ORDERS_ANALYTICS_USAGE.md) - Uso de endpoints de Orders
- Swagger/OpenAPI: http://localhost:8000/docs

---

## 🎯 Roadmap

- ✅ Orders Auto-ETL
- ✅ Subscriptions Auto-ETL
- ⏳ IoT Auto-ETL
- ⏳ Notifications Auto-ETL
- ⏳ Webhooks/Alertas
- ⏳ Rate Limiting
- ⏳ Autenticación JWT

---

**Última actualización:** 9 de Mayo, 2026
