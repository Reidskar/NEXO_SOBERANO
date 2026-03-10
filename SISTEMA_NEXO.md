# 🚀 NEXO SOBERANO - Sistema Integrado

Sistema profesional de control de streaming con integración OBS + Discord + Automatización

## 📋 Tabla de Contenidos

- [Características](#características)
- [Requisitos](#requisitos)
- [Inicio Rápido](#inicio-rápido)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Componentes](#componentes)
- [API Endpoints](#api-endpoints)
- [Configuración](#configuración)
- [Automatización](#automatización)

## ✨ Características

### 🎮 Control de Streaming
- **Control remoto de OBS** via WebSocket
- **Notificaciones Discord** con embeds enriquecidos
- **Cambio de escenas** automatizado
- **Grabación** sincronizada con stream

### 🤖 Agentes Inteligentes
- **Discord Supervisor**: Monitoreo continuo del webhook
  - Health checks automáticos
  - Métricas de rendimiento (latencia, uptime, tasa de éxito)
  - Auto-recuperación en caso de fallos
  - Reportes de salud periódicos

### 🔧 Automatización
- **Orquestador Maestro**: Inicia y monitorea todos los componentes
- **Reinicio automático** de servicios no saludables
- **Configurador OBS**: Aplica perfiles profesionales automáticamente

### 📊 Monitoreo
- **Estado en tiempo real** de todos los servicios
- **Logs estructurados** con niveles de severidad
- **Alertas automáticas** de estado crítico

## 📦 Requisitos

### Software
- **Python 3.11+**
- **OBS Studio 30+** con WebSocket habilitado
- **Discord Webhook** configurado

### Paquetes Python
```bash
pip install -r requirements.txt
```

Principales:
- `fastapi` - Backend API
- `uvicorn` - Servidor ASGI
- `obsws-python` - Cliente OBS WebSocket
- `aiohttp` - Cliente HTTP asíncrono

## 🚀 Inicio Rápido

### 1️⃣ Configuración Inicial

```bash
# 1. Clonar o descargar el proyecto
cd NEXO_SOBERANO

# 2. Instalar dependencias
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. Configurar variables de entorno (.env)
# Editar .env y configurar:
#   - DISCORD_WEBHOOK_URL
#   - OBS_WS_PASSWORD
#   - NEXO_API_KEY
```

### 2️⃣ Configurar OBS

```bash
# Opción A: Configuración automática
.\.venv\Scripts\python.exe obs_control\configure_obs.py

# Opción B: Manual
# 1. Abrir OBS Studio
# 2. Tools > WebSocket Server Settings
# 3. Habilitar WebSocket
# 4. Puerto: 4455
# 5. Password: 9AWj1VCvnTyO8vJP
```

### 3️⃣ Iniciar Sistema

```bash
# Opción A: Inicio automático (recomendado)
.\.venv\Scripts\python.exe nexo_orchestrator.py

# Opción B: Inicio manual
# Terminal 1: OBS Studio
# Terminal 2:
.\.venv\Scripts\python.exe run_backend.py
```

### 4️⃣ Verificar Estado

```powershell
# Verificar preflight
$headers = @{"X-NEXO-KEY" = "CAMBIA_ESTA_CLAVE_NEXO"}
Invoke-RestMethod -Uri "http://localhost:8000/api/stream/preflight" -Headers $headers
```

Respuesta esperada:
```json
{
  "ok": true,
  "obs_connected": true,
  "discord_connected": true,
  "blockers": [],
  "warnings": []
}
```

## 📁 Estructura del Proyecto

```
NEXO_SOBERANO/
│
├── 🎯 INICIO RÁPIDO
│   ├── nexo_orchestrator.py          # Orquestador maestro (inicio automático)
│   ├── run_backend.py                 # Iniciar backend manualmente
│   └── START_HERE.py                  # Guía de inicio
│
├── ⚙️ CONFIGURACIÓN
│   ├── .env                           # Variables de entorno (EDITAR)
│   ├── .env.example                   # Plantilla de configuración
│   └── requirements.txt               # Dependencias Python
│
├── 🔧 OBS CONTROL
│   └── obs_control/
│       ├── configure_obs.py           # Configurador automático OBS
│       └── obs_professional_profile.json  # Perfil profesional OBS
│
├── 🏗️ NEXO CORE (Backend)
│   └── NEXO_CORE/
│       ├── api/                       # Endpoints REST
│       │   ├── health.py             # Health checks
│       │   ├── stream.py             # Control de streaming
│       │   └── legacy.py             # Endpoints legacy
│       │
│       ├── agents/                    # Agentes autónomos
│       │   └── discord_supervisor.py # Supervisor Discord (nuevo)
│       │
│       ├── services/                  # Servicios del sistema
│       │   ├── obs_manager.py        # Manager OBS WebSocket
│       │   └── discord_manager.py    # Manager Discord Webhook
│       │
│       ├── core/                      # Core del sistema
│       │   ├── state_manager.py      # Estado global
│       │   ├── logger.py             # Logging
│       │   └── errors.py             # Manejo de errores
│       │
│       ├── middleware/                # Middlewares
│       │   ├── rate_limit.py         # Rate limiting
│       │   └── cors.py               # CORS
│       │
│       ├── models/                    # Modelos de datos
│       │   └── stream.py             # Modelos de stream
│       │
│       ├── config.py                  # Configuración centralizada
│       └── main.py                    # Punto de entrada FastAPI
│
├── 📊 FRONTEND
│   ├── NEXO_SOBERANO_v3.html          # War Room principal
│   ├── warroom_v2.html                # War Room v2
│   └── admin_dashboard.html           # Dashboard admin
│
├── 📝 DOCUMENTACIÓN
│   ├── SISTEMA_NEXO.md                # Este archivo
│   ├── README.md                      # README principal
│   ├── ARQUITECTURA_NEXO_CORE.md      # Arquitectura del sistema
│   └── QUICK_REFERENCE.txt            # Referencia rápida
│
└── 📦 OTROS MÓDULOS
    ├── agente_postulaciones/          # Bot de postulaciones
    ├── discord_bot/                   # Bot Discord
    └── scripts/                       # Scripts utilitarios
```

## 🧩 Componentes

### 1. Backend NEXO (FastAPI)

**Ubicación**: `NEXO_CORE/main.py`

**Puerto**: 8000

**Endpoints principales**:
- `/api/health` - Estado del sistema
- `/api/stream/status` - Estado del stream
- `/api/stream/preflight` - Verificación pre-vuelo
- `/api/stream/sync` - Sincronizar conectores
- `/api/docs` - Documentación Swagger

**Autenticación**: Header `X-NEXO-KEY`

### 2. OBS Manager

**Ubicación**: `NEXO_CORE/services/obs_manager.py`

**Funciones**:
- Conexión WebSocket a OBS
- Control de stream (start/stop)
- Cambio de escenas
- Obtención de estado

**Configuración**:
```env
OBS_ENABLED=true
OBS_WS_HOST=localhost
OBS_WS_PORT=4455
OBS_WS_PASSWORD=9AWj1VCvnTyO8vJP
```

### 3. Discord Manager

**Ubicación**: `NEXO_CORE/services/discord_manager.py`

**Funciones**:
- Envío de webhooks
- Notificaciones enriquecidas (embeds)
- Health checks del webhook
- Mensajes de estado de stream

**Configuración**:
```env
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
DISCORD_RECONNECT_SECONDS=15
```

### 4. Discord Supervisor (NUEVO)

**Ubicación**: `NEXO_CORE/agents/discord_supervisor.py`

**Características**:
- **Monitoreo continuo** del webhook Discord
- **Métricas de salud**:
  - Tasa de éxito (%)
  - Latencia promedio (ms)
  - Uptime
  - Fallos consecutivos
- **Auto-recuperación**: Reintentos inteligentes
- **Reportes periódicos**: Estado cada hora
- **Alertas críticas**: Notifica cuando hay 5+ fallos consecutivos

**Métricas disponibles**:
```python
from NEXO_CORE.agents.discord_supervisor import discord_supervisor

metrics = discord_supervisor.metrics
print(f"Tasa de éxito: {metrics.success_rate:.1f}%")
print(f"Latencia: {metrics.avg_response_time_ms:.0f}ms")
print(f"Uptime: {metrics.uptime_seconds / 3600:.1f}h")
```

### 5. Orquestador Maestro

**Ubicación**: `nexo_orchestrator.py`

**Funciones**:
- Inicio automático de OBS y Backend
- Monitoreo de salud de componentes
- Reinicio automático en caso de fallo
- Logs consolidados

**Uso**:
```bash
python nexo_orchestrator.py
```

## 🌐 API Endpoints

### Health Check
```http
GET /api/health
X-NEXO-KEY: your-api-key

Response:
{
  "status": "healthy",
  "version": "3.0.0",
  "uptime_seconds": 3600
}
```

### Stream Status
```http
GET /api/stream/status
X-NEXO-KEY: your-api-key

Response:
{
  "active": false,
  "obs_connected": true,
  "discord_connected": true,
  "current_scene": "Escena Principal"
}
```

### Control Stream
```http
POST /api/stream/status
X-NEXO-KEY: your-api-key
Content-Type: application/json

{
  "active": true
}

Response:
{
  "ok": true,
  "stream_active": true,
  "obs_applied": true,
  "discord_notified": true,
  "current_scene": "Escena Principal"
}
```

### Preflight Check
```http
GET /api/stream/preflight
X-NEXO-KEY: your-api-key

Response:
{
  "ok": true,
  "obs_connected": true,
  "discord_connected": true,
  "blockers": [],
  "warnings": []
}
```

## ⚙️ Configuración

### Variables de Entorno (.env)

```env
# === API ===
NEXO_API_KEY=CAMBIA_ESTA_CLAVE_NEXO       # Clave de API
NEXO_PROTECTED_PATH_PREFIXES=/api/stream   # Rutas protegidas

# === OBS ===
OBS_ENABLED=true                           # Habilitar OBS
OBS_WS_HOST=localhost                      # Host WebSocket
OBS_WS_PORT=4455                           # Puerto WebSocket
OBS_WS_PASSWORD=9AWj1VCvnTyO8vJP           # Password WebSocket
OBS_RECONNECT_SECONDS=30                   # Intervalo reconexión

# === Discord ===
DISCORD_ENABLED=true                       # Habilitar Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/... # URL Webhook
DISCORD_RECONNECT_SECONDS=15               # Intervalo reconexión

# === Rate Limiting ===
RATE_LIMIT_READ_PER_MIN=120                # Límite lectura
RATE_LIMIT_WRITE_PER_MIN=60                # Límite escritura
REQUEST_MAX_BYTES=1048576                  # Tamaño máximo request

# === Logging ===
LOG_LEVEL=INFO                             # Nivel de logging
LOG_FILE=logs/nexo_core.log                # Archivo de logs
```

### Configuración OBS WebSocket

1. Abrir OBS Studio
2. **Tools** → **WebSocket Server Settings**
3. Configurar:
   - ✅ Enable WebSocket server
   - **Server Port**: 4455
   - ✅ Enable Authentication
   - **Server Password**: 9AWj1VCvnTyO8vJP
4. Click **Apply** y **OK**

### Configuración Discord Webhook

1. Abrir Discord
2. Servidor → **Configuración del Servidor**
3. **Integraciones** → **Webhooks**
4. **Crear Webhook** o seleccionar existente
5. **Copiar URL del Webhook**
6. Pegar en `.env` → `DISCORD_WEBHOOK_URL`

## 🤖 Automatización

### Script de Inicio Automático

```bash
# Iniciar todo el sistema
python nexo_orchestrator.py
```

El orquestador:
1. ✅ Verifica e inicia OBS
2. ✅ Inicia el backend NEXO
3. ✅ Monitorea salud de componentes
4. ✅ Reinicia automáticamente en caso de fallo
5. ✅ Logs consolidados

### Configuración Automática de OBS

```bash
# Aplicar perfil profesional a OBS
python obs_control/configure_obs.py
```

Crea automáticamente:
- ✅ Escena Principal (con overlay)
- ✅ Escena BRB (volveremos pronto)
- ✅ Escena Final (gracias por ver)

### Tareas Programadas (Tasks)

Disponibles en VS Code: `Ctrl+Shift+P` → `Tasks: Run Task`

- 🚀 **NEXO: Iniciar Backend**
- 🔍 **NEXO: Escaneo de código**
- 🔧 **NEXO: Auto-reparar código**
- 🧪 **NEXO: Tests del Backend**
- 📊 **NEXO: Ver último reporte**
- 🔄 **NEXO: Sync completo**
- 🌐 **NEXO: Abrir War Room**

## 📈 Monitoreo

### Logs

```bash
# Ver logs del backend
tail -f logs/nexo_core.log

# Logs en tiempo real PowerShell
Get-Content logs/nexo_core.log -Wait
```

### Métricas del Supervisor Discord

El supervisor envía reportes de salud cada hora con:
- ✅ Tasa de éxito
- ⏱️ Latencia promedio
- ⏳ Uptime
- 📬 Mensajes totales
- 🔍 Health checks realizados
- ❌ Fallos consecutivos

### Dashboard

Acceder a:
- **Swagger UI**: http://localhost:8000/api/docs
- **War Room**: Abrir `NEXO_SOBERANO_v3.html`
- **Admin Dashboard**: Abrir `admin_dashboard.html`

## 🔒 Seguridad

- **API Key requerida** para endpoints protegidos
- **Rate limiting** configurado (120 read/min, 60 write/min)
- **CORS** configurado para origenes permitidos
- **Request size limit** (1MB por defecto)

## 🛠️ Desarrollo

### Agregar nuevo endpoint

```python
# NEXO_CORE/api/my_endpoint.py
from fastapi import APIRouter, Depends
from NEXO_CORE.middleware.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/api/my", tags=["my"])

@router.get("/hello", dependencies=[Depends(enforce_rate_limit)])
async def hello():
    return {"message": "Hello from NEXO!"}
```

Registrar en `NEXO_CORE/main.py`:
```python
from NEXO_CORE.api.my_endpoint import router as my_router
app.include_router(my_router)
```

### Agregar nuevo agente

```python
# NEXO_CORE/agents/my_agent.py
import asyncio
import logging

logger = logging.getLogger(__name__)

class MyAgent:
    async def run(self):
        while True:
            logger.info("Agent working...")
            await asyncio.sleep(60)

my_agent = MyAgent()
```

Iniciar en `NEXO_CORE/main.py`:
```python
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(my_agent.run())
```

## 🐛 Troubleshooting

### OBS no conecta

1. Verificar que OBS está ejecutándose
2. Verificar WebSocket habilitado en OBS
3. Verificar puerto 4455 disponible
4. Verificar password correcto

```powershell
# Test manual
python
>>> from obsws_python import ReqClient
>>> client = ReqClient(host='localhost', port=4455, password='9AWj1VCvnTyO8vJP')
>>> client.get_version()
```

### Discord no notifica

1. Verificar webhook URL correcta
2. Test manual:
```powershell
$body = @{content="Test"} | ConvertTo-Json
Invoke-RestMethod -Uri "YOUR_WEBHOOK_URL" -Method POST -Body $body -ContentType "application/json"
```

### Backend no inicia

1. Verificar puerto 8000 disponible
2. Verificar dependencias instaladas
3. Revisar logs: `logs/nexo_core.log`

```powershell
# Verificar puerto
Get-NetTCPConnection -LocalPort 8000
```

## 📞 Soporte

Para problemas o sugerencias:
1. Revisar logs en `logs/`
2. Verificar configuración `.env`
3. Ejecutar tests: `pytest tests/`

## 📄 Licencia

Proyecto privado - Todos los derechos reservados

---

**Versión**: 3.0.0  
**Última actualización**: 2026-03-03  
**Autor**: NEXO Team
