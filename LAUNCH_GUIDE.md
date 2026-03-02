# 🚀 NEXO SOBERANO - GUÍA DE LANZAMIENTO

## 🎯 FASE ACTUAL: BACKEND ✅ + FRONTEND ⏳

---

## ✨ LO QUE YA FUNCIONA

### Backend completamente operacional
```
✅ API on http://127.0.0.1:8000
✅ Health check: /api/health → 200 OK
✅ System status: /api/status → 200 OK
✅ Chat RAG: /api/chat → 200 OK
✅ Swagger docs: /docs → Accesible
```

### All endpoints tested & responding
| Endpoint | Method | Status |
|----------|--------|--------|
| / | GET | ✅ 200 |
| /api/health | GET | ✅ 200 |
| /api/status | GET | ✅ 200 |
| /api/chat | POST | ✅ 200 |
| /api/chat/history | GET | ✅ 200 |
| /docs | GET | ✅ 200 |

---

## 📦 PRÓXIMOS PASOS (ORDEN CRONOLÓGICO)

### PASO 1️⃣: INSTALAR NODE.JS (30 minutos)

**Windows - Opción A (GUI):**
1. Ir a: https://nodejs.org/
2. Descargar LTS (v20.x recomendado)
3. Ejecutar installer
4. Seleccionar todas opciones por defecto
5. Reiniciar PowerShell

**Windows - Opción B (Comando):**
```powershell
# Si tienes winget instalado:
winget install OpenJS.NodeJS

# O si tienes Chocolatey:
choco install nodejs
```

**Verificar instalación:**
```powershell
node --version    # Debe mostrar v20.x.x
npm --version     # Debe mostrar 10.x.x
```

---

### PASO 2️⃣: INSTALAR FRONTEND (5 minutos)

```powershell
# Navegar a frontend
cd C:\Users\Admn\Desktop\NEXO_SOBERANO\frontend

# Instalar dependencias
npm install

# Esto instalará:
# - react@18.x
# - react-dom@18.x
# - vite@5.x
# - tailwind@3.3
# - todo lo en package.json
```

---

### PASO 3️⃣: INICIAR FRONTEND (SIMULTÁNEAMENTE CON BACKEND)

**Terminal 1: Backend (ya corriendo)**
```
✅ Ya está en background escuchando en http://127.0.0.1:8000
```

**Terminal 2: Frontend**
```powershell
cd C:\Users\Admn\Desktop\NEXO_SOBERANO\frontend
npm run dev

# Output esperado:
#   VITE v5.0.0  ready in xxx ms
#   ➜ Local:   http://localhost:3000/
#   ➜ Press q + Enter to quit
```

**Terminal 3: Monitor (opcional)**
```powershell
cd C:\Users\Admn\Desktop\NEXO_SOBERANO
python test_api.py
```

---

## 🌐 ACCESO A LA APLICACIÓN

Cuando TODO esté ejecutando:

| Componente | URL | Descripción |
|-----------|-----|------------|
| Frontend UI | http://localhost:3000 | Interfaz principal |
| Backend API | http://127.0.0.1:8000 | API REST |
| Swagger Docs | http://127.0.0.1:8000/docs | Documentación interactiva |
| OpenAPI Schema | http://127.0.0.1:8000/openapi.json | JSON schema |

---

## 🔐 FASE 4️⃣: CLOUD CONNECTORS (Opcional pero recomendado)

### Google Drive Setup

1. **Ir a Google Cloud Console**
   ```
   https://console.cloud.google.com/
   ```

2. **Crear proyecto:**
   - Click en proyecto dropdown
   - "New Project"
   - Nombre: "NEXO_SOBERANO"
   - Click "Create"

3. **Habilitar APIs:**
   - Search: "Google Drive API" → Enable
   - Search: "Google Photos Library API" → Enable
   - Search: "Google People API" → Enable

4. **Crear credenciales OAuth2:**
   - Click "Create Credentials"
   - Seleccionar "OAuth 2.0 Client ID"
   - Type: "Desktop app"
   - Descargar JSON
   - Guardar como: `credenciales_google.json` en raíz

5. **Ejecutar setup:**
   ```powershell
   cd C:\Users\Admn\Desktop\NEXO_SOBERANO
   python setup_credentials.py
   ```

---

## 📊 VERIFICAR CONECTIVIDAD

### Test 1: Backend health
```powershell
$response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing
$response | ConvertFrom-Json | ConvertTo-Json
```

### Test 2: Full integration
```powershell
python test_api.py
```

### Test 3: From browser
```
http://localhost:3000
# Debería ver:
# - Header con icono verde (🟢 Online)
# - Sidebar con menu
# - ChatBox funcional
# - Dashboard con estadísticas
```

---

## 🛠️ TROUBLESHOOTING

### ❌ "npm: El término no se reconoce"
**Solución:**
```powershell
# Reinicia PowerShell después de instalar Node.js
# O verifica que Node.js vuelve a PATH:
$env:Path -split ";" | findstr "nodejs"
```

### ❌ Puerto 8000 ya en uso
**Solución:**
```powershell
# Ver qué está usando el puerto
netstat -ano | findstr ":8000"

# Matar el proceso
taskkill /PID <PID> /F

# O: matar todos los Python
Get-Process python | Stop-Process -Force

# Reiniciar backend
```

### ❌ CORS errors en frontend
**Estado:** ✅ Ya configurado en backend
- Si persiste, verificar que backend está en `http://127.0.0.1:8000`
- Frontend debe estar en `http://localhost:3000`

### ❌ Frontend no conecta al backend
**Debug:**
```powershell
# 1. Verificar backend está corriendo
Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health'

# 2. Abrir DevTools (F12 en navegador)
#    Console tab → Ver si hay CORS errors
#    Network tab → Ver que /api/chat GET response

# 3. Verificar firewall no bloquea puerto 8000
```

---

## 📈 ARQUITECTURA FINAL

```
┌─────────────────────────────────────────────┐
│  Frontend (React + Vite)                   │
│  http://localhost:3000                      │
│                                             │
│  ┌──────────┐  ┌─────────┐  ┌──────────┐  │
│  │ Header   │  │ Sidebar │  │ ChatBox  │  │
│  │ (Health) │  │ (Nav)   │  │ (Input)  │  │
│  └──────────┘  └─────────┘  └──────────┘  │
│                                             │
│  Dashboard (Stats + Connector Status)      │
└────────────┬────────────────────────────────┘
             │ HTTP POST /api/chat
             │ HTTP GET /api/health (5s polling)
             ▼
┌─────────────────────────────────────────────┐
│  Backend (FastAPI + Python)                │
│  http://127.0.0.1:8000                     │
│                                             │
│  ┌────────────────────────────────────┐   │
│  │  Api Layer                         │   │
│  │  ├─ /api/health                    │   │
│  │  ├─ /api/status                    │   │
│  │  ├─ /api/chat (POST)               │   │
│  │  └─ /api/chat/history              │   │
│  └────────────────────────────────────┘   │
│                                             │
│  ┌────────────────────────────────────┐   │
│  │  RAG Engine                        │   │
│  │  ├─ ChromaDB (Vectorization)       │   │
│  │  ├─ Sentence Transformers         │   │
│  │  └─ Gemini LLM Integration         │   │
│  └────────────────────────────────────┘   │
│                                             │
│  ┌────────────────────────────────────┐   │
│  │  Orchestrator                      │   │
│  │  ├─ Cost Manager (Token Budget)    │   │
│  │  ├─ Decision Engine                │   │
│  │  └─ Connector Sync                 │   │
│  └────────────────────────────────────┘   │
│                                             │
│  ┌────────────────────────────────────┐   │
│  │  Cloud Connectors                  │   │
│  │  ├─ Google Drive + Photos ⚡      │   │
│  │  ├─ Microsoft OneDrive ⚡         │   │
│  │  └─ Discord (Pending)              │   │
│  └────────────────────────────────────┘   │
│                                             │
│  ┌────────────────────────────────────┐   │
│  │  Data Layer                        │   │
│  │  ├─ SQLite (metadata)              │   │
│  │  ├─ ChromaDB (vectors)             │   │
│  │  └─ File system (documents)        │   │
│  └────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

---

## 🎓 CARACTERÍSTICAS PRINCIPALES

### 1. Ingesta Inteligente
- Scanea carpetas automáticamente
- Calcula hash para evitar duplicados
- Enriquece documentos con Gemini
- Almacena en SQLite con metadata

### 2. RAG (Retrieval-Augmented Generation)
- Convierte sumarios a vectores (embeddings)
- Busca semánticamente en ChromaDB
- Augmenta prompts con contexto relevante
- Responde usando Gemini API

### 3. Orquestación Inteligente
- Gestor de costos: $1,000/mes presupuesto
- Motor de decisiones: Clasifica prioridad
- High-priority: Usa Gemini (1500 tokens)
- Routine: USA embeddings locales (gratis)

### 4. Cloud Integration
- OAuth2 para Google Drive/OneDrive
- Sincronización automática
- Graceful degradation (sin credenciales)
- Modular design (add Discord/YouTube fácil)

---

## 🔄 COMANDOS DE USO DIARIO

```powershell
# ========== STARTUP ==========

# Terminal 1: Backend (si no está corriendo)
cd C:\Users\Admn\Desktop\NEXO_SOBERANO
.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Frontend
cd C:\Users\Admn\Desktop\NEXO_SOBERANO\frontend
npm run dev

# Terminal 3: Tests (opcional)
python test_api.py


# ========== VERIFICACIONES ==========

# Ver salud del API
curl http://127.0.0.1:8000/api/health

# Ver status de connectors
curl http://127.0.0.1:8000/api/status

# Test chat
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'


# ========== MANTENIMIENTO ==========

# Update dependencias Python
pip install --upgrade -r requirements.txt

# Update dependencias Node
npm update

# Limpiar caché
npm cache clean --force
pip cache purge

# Reset ChromaDB
rmdir /s base_sqlite\boveda.db

# Kill all Python processes
Get-Process python | Stop-Process -Force -ErrorAction SilentlyContinue
```

---

## 📝 PRÓXIMAS FASES (NO URGENTES)

- [ ] **Fase 5:** Discord connector
- [ ] **Fase 6:** YouTube indexer
- [ ] **Fase 7:** Automatic file watcher
- [ ] **Fase 8:** Production deployment (Vercel + Tunnel)
- [ ] **Fase 9:** Multi-tenancy SaaS
- [ ] **Fase 10:** GPU-optimized embeddings

---

##  📞 SOPORTE

Si algo falla:

1. **Backend no responde**
   ```powershell
   Get-Process python | Stop-Process -Force
   # Retry step 1 (Backend)
   ```

2. **Frontend npm install falla**
   ```powershell
   npm cache clean --force
   rm node_modules, package-lock.json
   npm install
   ```

3. **CORS issues**
   - Check backend CORS in `api/main.py` (already enabled)
   - Try clearing browser cache (Ctrl+Shift+Delete)

4. **Port conflicts**
   ```powershell
   netstat -ano | findstr ":8000"
   netstat -ano | findstr ":3000"
   ```

---

## ✅ CHECKLIST FINAL

- [ ] Node.js instalado (`node --version`)
- [ ] Backend corriendo (`http://127.0.0.1:8000/docs` accesible)
- [ ] Frontend instancias (`cd frontend && npm install` sin errores)
- [ ] Frontend dev server (`npm run dev` inicia Vite)
- [ ] Browser abre `http://localhost:3000` sin errores
- [ ] Header muestra status verde (🟢)
- [ ] ChatBox funciona (envía/recibe)
- [ ] API tests pasan (`python test_api.py`)

---

**🎉 Una vez completado todo esto, NEXO SOBERANO estará completamente operacional en tu PC local.**

**Timestamp:** 2026-02-24 01:15 UTC
**Status:** ✅ READY FOR PHASE 2
