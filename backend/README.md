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
    "start_date": "2026-05-09",
    "status": "active",
    "renewed": true,
    "auto_service": true,
    "billing_success": true,
    "end_date": null
  }
}
```
**Campos obligatorios:** `contract_id`, `user_id`, `plan_id`  
**Campos opcionales:** `start_date`, `status`, `renewed`, `auto_service`, `billing_success`, `end_date`  
**Resultado:** Crea nuevo registro en `fact_subscriptions`. Si se proporcionan `renewed`, `auto_service` y `billing_success`, estos se persisten inmediatamente. Estos campos también pueden actualizarse posteriormente con eventos como `renewal_success`, `payment_success`, etc.

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
**Resultado:** Actualiza `renewed=TRUE` en el registro existente con ese `contract_id`

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
**Resultado:** Actualiza `renewed=FALSE` en el registro existente con ese `contract_id`

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

## 🤖 Dominio: IoT

### Eventos Soportados

#### 1. **telemetry_received** - Datos de Telemetría
```json
POST http://localhost:8000/events

{
  "source": "iot_devices",
  "event_type": "telemetry_received",
  "payload": {
    "sensor_id": "SENSOR-001",
    "asset_id": "ASSET-100",
    "sensor_type": "temperature",
    "temperature": 22.5,
    "humidity": 65.0,
    "battery": 85.0,
    "signal_strength": -45,
    "connection_status": "connected",
    "timestamp": "2026-05-28T10:30:00Z"
  }
}
```
**Campos obligatorios:** `sensor_id`, `asset_id`, `sensor_type`  
**Campos opcionales:** `temperature`, `humidity`, `acceleration`, `battery`, `signal_strength`, `connection_status`, `timestamp`  
**Resultado:** Actualiza valores de telemetría en `fact_iot`, marca sensor como online

---

#### 2. **sensor_offline** - Sensor Desconectado
```json
{
  "source": "iot_devices",
  "event_type": "sensor_offline",
  "payload": {
    "sensor_id": "SENSOR-001",
    "asset_id": "ASSET-100",
    "sensor_type": "temperature"
  }
}
```
**Campos obligatorios:** `sensor_id`, `asset_id`, `sensor_type`  
**Resultado:** Marca `is_online=FALSE`, genera anomalía, crea evento de alerta

---

#### 3. **low_battery** - Batería Baja
```json
{
  "source": "iot_devices",
  "event_type": "low_battery",
  "payload": {
    "sensor_id": "SENSOR-001",
    "asset_id": "ASSET-100",
    "sensor_type": "temperature",
    "battery": 15.0
  }
}
```
**Campos obligatorios:** `sensor_id`, `asset_id`, `sensor_type`, `battery`  
**Resultado:** Actualiza nivel de batería, marca `low_battery_alert=TRUE`, genera anomalía

---

#### 4. **out_of_range** - Lectura Fuera de Rango
```json
{
  "source": "iot_devices",
  "event_type": "out_of_range",
  "payload": {
    "sensor_id": "SENSOR-001",
    "asset_id": "ASSET-100",
    "sensor_type": "temperature",
    "current_value": 42.5
  }
}
```
**Campos obligatorios:** `sensor_id`, `asset_id`, `sensor_type`, `current_value`  
**Resultado:** Marca `has_anomaly=TRUE`, registra evento de anomalía

---

#### 5. **signal_lost** - Señal Perdida
```json
{
  "source": "iot_devices",
  "event_type": "signal_lost",
  "payload": {
    "sensor_id": "SENSOR-001",
    "asset_id": "ASSET-100",
    "sensor_type": "temperature",
    "signal_strength": -100
  }
}
```
**Campos obligatorios:** `sensor_id`, `asset_id`, `sensor_type`  
**Campos opcionales:** `signal_strength`  
**Resultado:** Actualiza fuerza de señal, marca anomalía, mantiene estado actual

---

#### 6. **gps_updated** - Ubicación Actualizada
```json
{
  "source": "iot_devices",
  "event_type": "gps_updated",
  "payload": {
    "sensor_id": "SENSOR-001",
    "asset_id": "ASSET-100",
    "sensor_type": "gps",
    "location": "40.7128,-74.0060"
  }
}
```
**Campos obligatorios:** `sensor_id`, `asset_id`, `sensor_type`, `location`  
**Resultado:** Actualiza ubicación en `fact_iot`, no marca anomalía

---

#### 7. **anomaly_detected** - Anomalía Detectada
```json
{
  "source": "iot_devices",
  "event_type": "anomaly_detected",
  "payload": {
    "sensor_id": "SENSOR-001",
    "asset_id": "ASSET-100",
    "sensor_type": "acceleration",
    "severity": "critical"
  }
}
```
**Campos obligatorios:** `sensor_id`, `asset_id`, `sensor_type`  
**Campos opcionales:** `severity` (warning|critical)  
**Resultado:** Marca `has_anomaly=TRUE`, si severity=critical marca `is_online=FALSE`

---

## � Dominio: NOTIFICATIONS

### Eventos Soportados

#### 1. **notificacion_enviada** - Notificación Enviada
```json
POST http://localhost:8000/events

{
  "source": "notifications",
  "event_type": "notificacion_enviada",
  "payload": {
    "id_notificacion": "ntf_abc123",
    "id_api_key": "key_xyz789",
    "canal_usado": "email",
    "destinatario_email": "paciente@ejemplo.com",
    "destinatario_telefono": "+56912345678",
    "mensaje_asunto": "Confirmación de visita",
    "mensaje_email": "Hola María, su visita está confirmada para el 20 de abril a las 10:00.",
    "mensaje_sms": "Visita confirmada: 20 abril 10:00.",
    "intentos": 1
  }
}
```
**Campos obligatorios:** `id_notificacion`, `canal_usado` (sms|email|push)  
**Campos opcionales:** `id_api_key`, `destinatario_email`, `destinatario_telefono`, `mensaje_asunto`, `mensaje_email`, `mensaje_sms`, `intentos`  
**Resultado:** Crea registro en `fact_notifications` con estado `enviado`

---

#### 2. **notificacion_entregada** - Notificación Entregada
```json
{
  "source": "notifications",
  "event_type": "notificacion_entregada",
  "payload": {
    "id_notificacion": "ntf_abc123",
    "id_api_key": "key_xyz789",
    "canal_usado": "email",
    "destinatario_email": "paciente@ejemplo.com",
    "timestamp": "2026-04-16T10:00:08Z"
  }
}
```
**Campos obligatorios:** `id_notificacion`, `canal_usado`  
**Campos opcionales:** `id_api_key`, `timestamp`  
**Resultado:** Actualiza estado a `entregado`, registra `fecha_entrega`, marca éxito de entrega

---

#### 3. **fallback_activado** - Fallback Activado
```json
{
  "source": "notifications",
  "event_type": "fallback_activado",
  "payload": {
    "id_notificacion": "ntf_abc123",
    "id_api_key": "key_xyz789",
    "canal_original": "sms",
    "canal_fallback": "email",
    "destinatario_email": "paciente@ejemplo.com",
    "razon": "SMS delivery failed"
  }
}
```
**Campos obligatorios:** `id_notificacion`, `canal_original`, `canal_fallback`  
**Campos opcionales:** `id_api_key`, `destinatario_email`, `razon`  
**Resultado:** Marca `fallback_activado=TRUE`, cambia `canal_usado` al canal fallback, incrementa `intentos`

---

#### 4. **notificacion_fallida** - Notificación Fallida
```json
{
  "source": "notifications",
  "event_type": "notificacion_fallida",
  "payload": {
    "id_notificacion": "ntf_abc123",
    "id_api_key": "key_xyz789",
    "canal_usado": "email",
    "destinatario_email": "paciente@ejemplo.com",
    "razon": "Invalid email address",
    "intentos": 3
  }
}
```
**Campos obligatorios:** `id_notificacion`, `canal_usado`  
**Campos opcionales:** `id_api_key`, `destinatario_email`, `razon`, `intentos`  
**Resultado:** Actualiza estado a `fallido`, incrementa `intentos`, registra razón del fallo

---

## �📊 Response Format

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
GET http://localhost:8000/kpis/subscriptions/summary?days=30
GET http://localhost:8000/kpis/subscriptions/timeline?days=30
GET http://localhost:8000/kpis/subscriptions/retention
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
