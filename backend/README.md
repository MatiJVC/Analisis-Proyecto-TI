# 📊 Event Ingestion & Analytics API

Sistema de ingestión de eventos y análisis de KPIs en tiempo real para múltiples dominios (órdenes, suscripciones, salud, incidentes, IoT, notificaciones).

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

## 🔔 Dominio: NOTIFICATIONS

### Eventos Soportados

#### 1. **notificacion_enviada** - Notificación Enviada
```json
POST http://localhost:8000/events

{
  "source": "notifications",
  "event_type": "notificacion_enviada",
  "payload": {
    "id_notificacion": "ntf_abc123",
    "canal_usado": "email",
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
    "canal_usado": "email",
  }
}
```
**Campos obligatorios:** `id_notificacion`, `canal_usado`  
**Resultado:** Actualiza estado a `entregado`, registra `fecha_entrega`, marca éxito de entrega

---

#### 3. **fallback_activado** - Fallback Activado
```json
{
  "source": "notifications",
  "event_type": "fallback_activado",
  "payload": {
    "id_notificacion": "ntf_abc123",
    "canal_fallback": "email",
  }
}
```
**Campos obligatorios:** `id_notificacion`, `canal_fallback`    
**Resultado:** Marca `fallback_activado=TRUE`, cambia `canal_usado` al canal fallback, incrementa `intentos`

---

#### 4. **notificacion_fallida** - Notificación Fallida
```json
{
  "source": "notifications",
  "event_type": "notificacion_fallida",
  "payload": {
    "id_notificacion": "ntf_abc123",
    "canal_usado": "email",
    "intentos": 3
  }
}
```
**Campos obligatorios:** `id_notificacion`, `canal_usado`  
**Campos opcionales:** `id_api_key`, `destinatario_email`, `razon`, `intentos`  
**Resultado:** Actualiza estado a `fallido`, incrementa `intentos`, registra razón del fallo

---

## 🩺 Dominio: SALUD

> Modelo dimensional con SCD (slowly changing dimensions): primero se cargan las dimensiones (`*_upsert`) y luego los hechos (`visita_*`, `alerta_upsert`, `ficha_upsert`). Todos los IDs de negocio son **UUID**.

### Eventos Soportados

#### 1. **usuario_upsert** - Alta/actualización de Usuario (Dim)
```json
POST http://localhost:8000/events

{
  "source": "salud",
  "event_type": "usuario_upsert",
  "payload": {
    "usuario_id": "11111111-1111-1111-1111-111111111111",
    "nombres": "María",
    "apellidos": "Pérez",
    "rut": "12.345.678-9",
    "email": "maria.perez@example.com",
    "telefono": "+56 9 1234 5678",
    "activo": true
  }
}
```
**Campos obligatorios:** `usuario_id`, `nombres`, `apellidos`  
**Campos opcionales:** `rut`, `email`, `telefono`, `activo`  
**Resultado:** Crea o actualiza el registro actual (`es_actual=TRUE`) en `dim_usuarios`. Es prerequisito para `profesional_upsert` y campos de creador/actualizador en visitas y fichas.

---

#### 2. **paciente_upsert** - Alta/actualización de Paciente (Dim)
```json
{
  "source": "salud",
  "event_type": "paciente_upsert",
  "payload": {
    "paciente_id": "22222222-2222-2222-2222-222222222222",
    "nombres": "Juan",
    "apellidos": "Soto",
    "rut": "9.876.543-2",
    "fecha_nacimiento": "1985-04-12",
    "sexo": "M",
    "telefono": "+56 9 8765 4321",
    "email": "juan.soto@example.com",
    "direccion": "Av. Siempre Viva 123, Santiago"
  }
}
```
**Campos obligatorios:** `paciente_id`, `nombres`, `apellidos`  
**Campos opcionales:** `rut`, `fecha_nacimiento`, `sexo`, `telefono`, `email`, `direccion`  
**Resultado:** Crea o actualiza el registro actual en `dim_pacientes`. Prerequisito para `visita_upsert` y `alerta_upsert`.

---

#### 3. **profesional_upsert** - Alta/actualización de Profesional (Dim)
```json
{
  "source": "salud",
  "event_type": "profesional_upsert",
  "payload": {
    "profesional_id": "33333333-3333-3333-3333-333333333333",
    "usuario_id": "11111111-1111-1111-1111-111111111111",
    "nombres": "María",
    "apellidos": "Pérez",
    "profesion": "Enfermera",
    "numero_registro": "REG-001",
    "activo": true
  }
}
```
**Campos obligatorios:** `profesional_id`, `usuario_id`, `nombres`, `apellidos`  
**Campos opcionales:** `profesion`, `numero_registro`, `activo`  
**Resultado:** Crea o actualiza el registro actual en `dim_profesionales`. Requiere que el `usuario_id` exista previamente como dim actual.

---

#### 4. **zona_upsert** - Alta/actualización de Zona Geográfica (Dim)
```json
{
  "source": "salud",
  "event_type": "zona_upsert",
  "payload": {
    "zona_id": "44444444-4444-4444-4444-444444444444",
    "nombre": "Zona Norte",
    "descripcion": "Sector norte de la ciudad",
    "comuna": "Recoleta",
    "region": "Metropolitana",
    "activa": true
  }
}
```
**Campos obligatorios:** `zona_id`, `nombre`  
**Campos opcionales:** `descripcion`, `comuna`, `region`, `activa`  
**Resultado:** Crea o actualiza el registro actual en `dim_zonas`. Opcional para `visita_upsert`.

---

#### 5. **especialidad_upsert** - Alta/actualización de Especialidad (Dim)
```json
{
  "source": "salud",
  "event_type": "especialidad_upsert",
  "payload": {
    "especialidad_id": "55555555-5555-5555-5555-555555555555",
    "nombre": "Cardiología",
    "descripcion": "Atención cardiovascular"
  }
}
```
**Campos obligatorios:** `especialidad_id`, `nombre`  
**Campos opcionales:** `descripcion`  
**Resultado:** Crea o actualiza el registro actual en `dim_especialidades`.

---

#### 6. **visita_upsert** - Alta/actualización de Visita (Fact)
```json
{
  "source": "salud",
  "event_type": "visita_upsert",
  "payload": {
    "visita_id": "66666666-6666-6666-6666-666666666666",
    "paciente_id": "22222222-2222-2222-2222-222222222222",
    "profesional_id": "33333333-3333-3333-3333-333333333333",
    "zona_id": "44444444-4444-4444-4444-444444444444",
    "usuario_creador_id": "11111111-1111-1111-1111-111111111111",
    "fecha_programada": "2026-06-10",
    "hora_programada": "10:30:00",
    "fecha_inicio_real": "2026-06-10T10:35:00Z",
    "fecha_fin_real": "2026-06-10T11:15:00Z",
    "estado": "completada",
    "completada": 1,
    "puntual": 0
  }
}
```
**Campos obligatorios:** `visita_id`, `paciente_id`, `profesional_id`, `fecha_programada`, `estado`  
**Campos opcionales:** `zona_id`, `usuario_creador_id`, `hora_programada`, `fecha_inicio_real`, `fecha_fin_real`, `completada`, `puntual`  
**Resultado:** Crea o actualiza el registro en `fact_visitas`, resolviendo dimensiones a sus surrogate keys. Calcula automáticamente `duracion_minutos` y `retraso_minutos` cuando hay datos suficientes.

---

#### 7. **visita_inicio** - Inicio Real de la Visita
```json
{
  "source": "salud",
  "event_type": "visita_inicio",
  "payload": {
    "visita_id": "66666666-6666-6666-6666-666666666666",
    "fecha_inicio_real": "2026-06-10T10:35:00Z"
  }
}
```
**Campos obligatorios:** `visita_id`, `fecha_inicio_real`  
**Resultado:** Marca `fecha_inicio_real` y recalcula `duracion_minutos`/`retraso_minutos`. Requiere visita previa.

---

#### 8. **visita_fin** - Fin Real de la Visita
```json
{
  "source": "salud",
  "event_type": "visita_fin",
  "payload": {
    "visita_id": "66666666-6666-6666-6666-666666666666",
    "fecha_fin_real": "2026-06-10T11:15:00Z",
    "estado": "completada",
    "completada": 1,
    "puntual": 0
  }
}
```
**Campos obligatorios:** `visita_id`, `fecha_fin_real`  
**Campos opcionales:** `estado`, `completada` (0|1), `puntual` (0|1)  
**Resultado:** Marca `fecha_fin_real`, recalcula duración/retraso y opcionalmente actualiza `estado`, `completada`, `puntual`.

---

#### 9. **alerta_upsert** - Alta/actualización de Alerta Clínica
```json
{
  "source": "salud",
  "event_type": "alerta_upsert",
  "payload": {
    "alerta_id": "77777777-7777-7777-7777-777777777777",
    "paciente_id": "22222222-2222-2222-2222-222222222222",
    "visita_id": "66666666-6666-6666-6666-666666666666",
    "tipo": "PRESION_ALTA",
    "mensaje": "Paciente con presión sostenida sobre 160/100",
    "prioridad": "HIGH",
    "estado": "OPEN",
    "dias_abierta": 0
  }
}
```
**Campos obligatorios:** `alerta_id`, `paciente_id`, `tipo`  
**Campos opcionales:** `visita_id`, `mensaje`, `prioridad` (default `MEDIUM`), `estado` (default `OPEN`), `dias_abierta`  
**Resultado:** Crea o actualiza el registro en `fact_alertas`. Si se entrega `visita_id`, lo resuelve a `visita_dim_id`.

---

#### 10. **ficha_upsert** - Alta/actualización de Ficha Clínica
```json
{
  "source": "salud",
  "event_type": "ficha_upsert",
  "payload": {
    "ficha_id": "88888888-8888-8888-8888-888888888888",
    "visita_id": "66666666-6666-6666-6666-666666666666",
    "estado": "COMPLETED",
    "contenido": "Paciente estable, se indica control en 7 días.",
    "usuario_creador_id": "11111111-1111-1111-1111-111111111111",
    "usuario_actualizador_id": "11111111-1111-1111-1111-111111111111",
    "tiene_adjuntos": "1",
    "cantidad_adjuntos": "2"
  }
}
```
**Campos obligatorios:** `ficha_id`, `visita_id`, `estado`  
**Campos opcionales:** `contenido`, `usuario_creador_id`, `usuario_actualizador_id`, `tiene_adjuntos`, `cantidad_adjuntos`  
**Resultado:** Crea o actualiza el registro en `fact_fichas_clinicas`. Requiere que la `visita_id` exista previamente.

---

## 🚨 Dominio: INCIDENTS

> Tracking del ciclo de vida de un incidente: creación → asignación → cambio de estado → resolución. Todos los handlers son **idempotentes** y el mismo `incident_id` se puede reenviar para acumular cambios.

### Eventos Soportados

#### 1. **incident_created** - Incidente Creado
```json
POST http://localhost:8000/events

{
  "source": "incidents",
  "event_type": "incident_created",
  "payload": {
    "incident_id": "INC-1001",
    "title": "API de pagos respondiendo con 500",
    "severity": "critical",
    "status": "open",
    "assignee": "guardia-l1",
    "opened_at": "2026-06-04T09:30:00Z"
  }
}
```
**Campos obligatorios:** `incident_id`  
**Campos opcionales:** `title` (default `Incident <id>`), `severity` (`critical|high|medium|low`, default `medium`), `status` (`open|investigating|resolved`, default `open`), `assignee`, `opened_at` (default ahora)  
**Resultado:** Crea registro nuevo en `fact_incidents` o lo actualiza si ya existe ese `incident_id`. Si se proporciona `opened_at`, sobreescribe el valor previo.  
**Alias:** `incident_upsert` ejecuta exactamente el mismo handler.

---

#### 2. **incident_assigned** - Asignación de Responsable
```json
{
  "source": "incidents",
  "event_type": "incident_assigned",
  "payload": {
    "incident_id": "INC-1001",
    "assignee": "equipo-backend"
  }
}
```
**Campos obligatorios:** `incident_id`  
**Campos opcionales:** `assignee` (puede ser `null` para liberar la asignación)  
**Resultado:** Actualiza el campo `assignee` y `updated_at`. Si el incidente no existe, lo crea con valores por defecto.

---

#### 3. **incident_status_changed** - Cambio de Estado
```json
{
  "source": "incidents",
  "event_type": "incident_status_changed",
  "payload": {
    "incident_id": "INC-1001",
    "status": "investigating",
    "severity": "high",
    "assignee": "equipo-backend",
    "title": "API de pagos: degradación parcial"
  }
}
```
**Campos obligatorios:** `incident_id`  
**Campos opcionales:** `status` (`open|investigating|resolved`), `severity` (`critical|high|medium|low`), `assignee`, `title`  
**Resultado:** Aplica los campos comunes presentes (solo se aceptan valores válidos para `status` y `severity`) y actualiza `updated_at`.

---

#### 4. **incident_resolved** - Incidente Resuelto (Final)
```json
{
  "source": "incidents",
  "event_type": "incident_resolved",
  "payload": {
    "incident_id": "INC-1001",
    "resolved_at": "2026-06-04T11:45:00Z",
    "resolution_time_hours": 2.25,
    "sla_met": true,
    "assignee": "equipo-backend"
  }
}
```
**Campos obligatorios:** `incident_id`  
**Campos opcionales:** `resolved_at` (default ahora), `resolution_time_hours` (si no viene se calcula como `resolved_at - opened_at`), `sla_met`, más cualquiera de los campos comunes (`title`, `severity`, `assignee`)  
**Resultado:** 
- Fuerza `status=resolved`
- Registra `resolved_at`
- Calcula o persiste `resolution_time_hours`
- Persiste `sla_met` si viene en el payload

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
