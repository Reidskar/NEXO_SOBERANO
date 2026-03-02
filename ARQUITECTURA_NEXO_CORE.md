# 🏛️ NEXO CORE — Arquitectura Definitiva

**Fecha:** 2026-03-01  
**Objetivo:** Infraestructura escalable, profesional, lista para SaaS

---

## 📐 Estructura Consolidada

```
NEXO_SOBERANO/
│
├── 🔧 NEXO_CORE/                    # ← Backend unificado
│   ├── main.py                      # FastAPI entry point
│   ├── config.py                    # Configuración centralizada
│   ├── requirements.txt             # Dependencias exactas
│   │
│   ├── core/                        # Lógica central
│   │   ├── __init__.py
│   │   ├── state_manager.py        # Estado del sistema
│   │   ├── logger.py                # Logging profesional
│   │   ├── errors.py                # Error handling global
│   │   └── health.py                # Health checks
│   │
│   ├── services/                    # Servicios de negocio
│   │   ├── __init__.py
│   │   ├── agente.py                # IA / Claude
│   │   ├── rag_service.py           # RAG / ChromaDB
│   │   ├── cost_manager.py          # Control de costos
│   │   ├── obs_manager.py           # Integración OBS
│   │   └── discord_manager.py       # Integración Discord
│   │
│   ├── api/                         # Rutas HTTP
│   │   ├── __init__.py
│   │   ├── chat.py                  # /api/chat
│   │   ├── agent.py                 # /api/agent
│   │   ├── stream.py                # /api/stream (estado streaming)
│   │   ├── health.py                # /api/health
│   │   └── preferences.py           # /api/preferences
│   │
│   ├── models/                      # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── agent.py
│   │   └── stream.py
│   │
│   └── middleware/                  # Middleware HTTP
│       ├── __init__.py
│       ├── cors.py
│       ├── auth.py
│       └── rate_limit.py
│
├── 🎨 frontend/                     # Panel de control
│   ├── index.html
│   ├── warroom_v2.html
│   ├── js/
│   ├── css/
│   └── assets/
│
├── 🤖 nexo_autosupervisor.py        # Sistema de calidad
├── 📱 NEXO_STITCH_GUIA.html         # Firebase mobile/web
├── 🐳 docker-compose.yml            # Contenedores
├── 📝 requirements.txt              # Deps globales
└── 🔒 .env.example                  # Template de config

```

---

## 🎯 Principios de Diseño

### 1. **Separación de Responsabilidades**
- **API**: Solo maneja HTTP (request/response)
- **Services**: Lógica de negocio (Claude, RAG, OBS)
- **Core**: Infraestructura (logging, estado, errores)
- **Models**: Validación de datos (Pydantic)

### 2. **Estado Centralizado**
```python
# core/state_manager.py
class SystemState:
    stream_active: bool = False
    obs_connected: bool = False
    discord_connected: bool = False
    ai_requests_today: int = 0
    last_error: Optional[str] = None
    uptime_start: datetime = datetime.now()
```

### 3. **Logging Profesional**
```python
# core/logger.py
# Todos los logs van a:
# - Console (desarrollo)
# - Archivo rotativo (logs/nexo_{date}.log)
# - Sentry (producción, opcional)

import logging
from logging.handlers import RotatingFileHandler

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    ))
    logger.addHandler(console)
    
    # File handler (10MB max, 5 backups)
    file_handler = RotatingFileHandler(
        f"logs/{name}.log",
        maxBytes=10*1024*1024,
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    ))
    logger.addHandler(file_handler)
    
    return logger
```

### 4. **Error Handling Global**
```python
# core/errors.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

async def global_exception_handler(request: Request, exc: Exception):
    """Captura todos los errores no manejados"""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    
    # Actualizar estado del sistema
    from NEXO_CORE.core.state_manager import state
    state.last_error = str(exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": str(exc),
            "path": request.url.path
        }
    )
```

### 5. **Reconexión Automática**
```python
# services/obs_manager.py
import asyncio
import obsws_python as obs

class OBSManager:
    def __init__(self):
        self.client = None
        self.reconnect_task = None
        
    async def connect(self):
        """Conecta a OBS con retry automático"""
        while True:
            try:
                self.client = obs.ReqClient(host='localhost', port=4455)
                logger.info("✅ OBS connected")
                state.obs_connected = True
                break
            except Exception as e:
                logger.warning(f"⚠️ OBS connection failed: {e}")
                state.obs_connected = False
                await asyncio.sleep(5)  # Retry en 5 segundos
                
    async def ensure_connected(self):
        """Verifica conexión antes de cada operación"""
        if not state.obs_connected:
            await self.connect()
```

### 6. **Health Checks**
```python
# api/health.py
from fastapi import APIRouter
from NEXO_CORE.core.state_manager import state

router = APIRouter(prefix="/api/health", tags=["health"])

@router.get("/")
async def health_check():
    """Devuelve estado completo del sistema"""
    return {
        "status": "operational",
        "uptime_seconds": (datetime.now() - state.uptime_start).total_seconds(),
        "connections": {
            "obs": state.obs_connected,
            "discord": state.discord_connected
        },
        "metrics": {
            "ai_requests_today": state.ai_requests_today
        },
        "last_error": state.last_error
    }

@router.get("/stream")
async def stream_status():
    """Estado específico del streaming"""
    return {
        "active": state.stream_active,
        "obs_connected": state.obs_connected,
        "current_scene": await obs_manager.get_current_scene() if state.obs_connected else None
    }
```

---

## 🔥 Ventajas de NEXO_CORE

### ✅ **Para Ti (Desarrollador)**
- **Un solo backend** — No más confusión de imports
- **Logs centralizados** — Sabes exactamente qué pasó
- **Errores manejados** — El sistema no crashea, se recupera
- **Reconexión automática** — OBS/Discord se reconectan solos
- **Health checks** — Ves el estado en tiempo real

### ✅ **Para el Stream**
- **Estabilidad 24/7** — Maneja desconexiones sin intervención
- **Visibilidad total** — WarRoom muestra estado real del sistema
- **Recuperación automática** — Si algo falla, se reintenta
- **Métricas en vivo** — Cuántas requests IA, uptime, conexiones

### ✅ **Para Escalar (SaaS Futuro)**
- **Rate limiting** — Lista para multi-usuario
- **Auth middleware** — Preparada para tokens
- **Configuración por entorno** — Dev/Staging/Prod separados
- **Docker ready** — Deploy con `docker-compose up`
- **Monitoring hooks** — Listo para Sentry/Datadog

---

## 🛠️ Migración Inmediata

### Paso 1: Crear NEXO_CORE
```bash
mkdir NEXO_CORE
mkdir NEXO_CORE/core
mkdir NEXO_CORE/services
mkdir NEXO_CORE/api
mkdir NEXO_CORE/models
mkdir NEXO_CORE/middleware
```

### Paso 2: Consolidar Código
- Tomar `main.py` del `backend/` actual (más completo)
- Migrar servicios de `backend/services/` y `nexo_backend/`
- Añadir nuevos módulos (state_manager, logger, errors)

### Paso 3: Actualizar Referencias
- Cambiar todos los imports: `from backend.X` → `from NEXO_CORE.X`
- Actualizar `run_backend.py` para usar `NEXO_CORE.main:app`
- Actualizar paths en frontend (si hay)

### Paso 4: Limpiar
- **Eliminar** `nexo_backend/` completo
- **Renombrar** `backend/` → `backend_old/` (backup temporal)
- **Renombrar** `NEXO_CORE/` → `backend/` (opcionalmente)

### Paso 5: Validar
```bash
python nexo_autosupervisor.py --scan
python -m pytest tests/
uvicorn NEXO_CORE.main:app --reload
```

---

## 📊 Comparativa: Antes vs Después

| Aspecto | Backend Actual | NEXO_CORE |
|---------|----------------|-----------|
| **Duplicación** | ❌ 2 backends conflictivos | ✅ 1 backend unificado |
| **Logging** | ⚠️ print() scattered | ✅ Logger centralizado + archivos |
| **Errores** | ❌ Crashes sin control | ✅ Global exception handler |
| **Reconexión** | ❌ Manual | ✅ Automática (OBS/Discord) |
| **Estado** | ❌ Variables globales | ✅ StateManager centralizado |
| **Health Checks** | ❌ No existe | ✅ /api/health con métricas |
| **CORS** | ⚠️ Código duplicado | ✅ Middleware reutilizable |
| **Rate Limiting** | ❌ No existe | ✅ Middleware preparado |
| **Docker** | ⚠️ Básico | ✅ Multi-stage, optimizado |
| **Tests** | ⚠️ Básicos | ✅ Fixtures + mocks incluidos |

---

## 🚀 Próximos Pasos (Post-Consolidación)

1. **Cache Layer** (Redis) para RAG queries repetidas
2. **WebSocket real-time** para eventos de stream
3. **Admin Panel** (React) para configuración
4. **Métricas avanzadas** (Prometheus + Grafana)
5. **CI/CD Pipeline** (GitHub Actions)
6. **Multi-tenancy** (preparar para SaaS)

---

## 💡 Recomendación Final

**Implementar NEXO_CORE ahora** te da:
- ✅ Stream estable inmediatamente
- ✅ Base sólida para crecer
- ✅ Código limpio, auto-supervisado
- ✅ Preparado para Firebase/Stitch
- ✅ Listo para escalar cuando quieras

**Tiempo estimado de implementación:** 30-45 minutos  
**ROI:** Evitas horas de debugging futuro + tienes base profesional

---

**¿Quieres que implemente NEXO_CORE ahora mismo?**  
Puedo crear todos los archivos en una pasada y dejar el sistema operativo.
