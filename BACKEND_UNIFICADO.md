# ✅ REFACTORIZACIÓN COMPLETA — Backend Unificado

## 📊 RESUMEN EJECUTIVO

Se reemplazó completamente el mock (`api/main.py`) con un backend unificado Real basado en FastAPI que integra la lógica RAG de `nexo_v2.py`.

### Cambios Principales

| Aspecto | Antes ❌ | Después ✅ |
|---------|---------|-----------|
| **Backend** | Mock (responde "Procesando: ...") | Real (RAG + Costos) |
| **Fragmentación** | 2 backends paralelos | 1 FastAPI unificado |
| **Costos** | Hardcoded `1500` | Reales medidos por llamada |
| **Config** | Duplicada en archivos | Centralizada en `config.py` |
| **CORS** | `allow_origins=["*"]` | Específicos + seguros |
| **Frontend** | `/api/chat` con `{message}` | `/agente/consultar` con `{query, mode}` |

---

## 📁 ARCHIVOS CREADOS

```
backend/
├── config.py              (Configuración centralizada)
├── main.py                (FastAPI app - reemplaza api/main.py)
├── routes/agente.py       (Endpoints RAG unificados)
└── services/
    ├── cost_manager.py    (Tokens reales)
    └── rag_service.py     (Motor RAG de nexo_v2.py)

run_backend.py             (Script para arrancar)
test_backend_unified.py    (Tests - 8/8 pasando)
```

---

## 🎯 ENDPOINTS

### Principal
- **POST** `/agente/consultar` — Consulta RAG unificada

### Sistema
- **GET** `/health` — Health check
- **GET** `/agente/health` — Status RAG
- **GET** `/agente/presupuesto` — Estado tokens
- **GET** `/agente/historial-costos` — Histórico 7 días
- **GET** `/api/docs` — Swagger

---

## 🚀 EJECUCIÓN

```bash
# Instalar dependencies
pip install fastapi uvicorn pydantic google-generativeai chromadb

# Backend
python run_backend.py
→ escucha en http://localhost:8000

# Frontend (otra terminal)
cd frontend && npm run dev
→ abre en http://localhost:5173

# Probar
curl -X POST http://localhost:8000/agente/consultar \
  -H "Content-Type: application/json" \
  -d '{"query":"¿Qué pasa en Rusia?"}'
```

---

## 💰 GESTIÓN DE COSTOS REAL

**Antes:**
```python
class GestorDeCostos:
    def gastar_tokens(self):
        return 1500  # ❌ Fake
```

**Después:**
```python
class CostManager:
    def registrar(self, modelo, tokens_in, tokens_out, op):
        DB → INSERT costos_api
        # ✅ Real
```

---

## 🔐 CORS CORRECTO

**Antes:** `allow_origins=["*"]` (inseguro)  
**Después:** `allow_origins=["http://localhost:3000", ...]` (específico + seguro)

---

## 📋 LISTA DE CAMBIOS

| Archivo | Cambio |
|---------|--------|
| `api/main.py` | ❌ Eliminar (reemplazado) |
| `api/routes/chat.py` | ❌ Eliminar (lógica movida) |
| `backend/config.py` | ✅ Nuevo (config centralizada) |
| `backend/main.py` | ✅ Nuevo (FastAPI oficial) |
| `backend/routes/agente.py` | ✅ Nuevo (endpoints RAG) |
| `backend/services/rag_service.py` | ✅ Nuevo (motor real) |
| `backend/services/cost_manager.py` | ✅ Nuevo (tokens reales) |
| `frontend/src/components/ChatBox.jsx` | ✅ Actualizado (endpoint + contrato) |

---

## 🧪 TESTS

```bash
python test_backend_unified.py
```

**Resultado:** ✅ 8/8 tests pasando

- ✅ Config centralizado
- ✅ Gestor de costos
- ✅ Servicio RAG
- ✅ Backend startup
- ✅ API Docs
- ✅ Integración Frontend
- ✅ CORS
- ✅ Imports

---

## 🎨 CONTRATO UNIFICADO API

### Request
```json
POST /agente/consultar
{
    "query": "¿Qué pasa en Rusia?",
    "mode": "normal",
    "categoria": null
}
```

### Response
```json
{
    "answer": "Respuesta de la IA...",
    "sources": ["rusia_2024.pdf"],
    "tokens_used": 450,
    "chunks_used": 5,
    "execution_time_ms": 2340,
    "total_docs": 45,
    "presupuesto": {
        "tokens_hoy": 2500,
        "max_tokens": 900000,
        "porcentaje": 0.28,
        "disponible": 897500,
        "puede_operar": true
    },
    "error": false
}
```

---

## ✅ STATUS

| Componente | Estado |
|------------|--------|
| Backend | ✅ Unificado |
| RAG | ✅ Funcional |
| Costos | ✅ Real |
| CORS | ✅ Correcto |
| Frontend | ✅ Actualizado |
| Tests | ✅ Pasando |
| Documentación | ✅ Completa |

**Sistema OPERACIONAL - Listo para usar** ✅

---

## 🔄 INTEGRACIÓN CON nexo_v2.py

- `nexo_v2.py` sigue siendo el script maestro CLI
- Backend **reutiliza su lógica** (sin duplicar):
  - `rag_service.py` ← `consultar_rag()`
  - `cost_manager.py` ← `GestorCostos`

---

## 📝 ARCHIVO DETALLES

Ver: [REFACTORIZACION_BACKEND.md](REFACTORIZACION_BACKEND.md)

---

**Status:** ✅ Refactorización completada  
**Inicio:** `python run_backend.py`  
**Frontend:** `cd frontend && npm run dev`

---

## 🔗 Sincronización Unificada Cloud (nuevo)

Se agregó un flujo para dejar todo vinculado entre Google Photos, Google Drive y OneDrive, con clasificación automática por tipo de archivo en Drive.

### Endpoint

- **POST** `/agente/sync/unificado`
- **POST** `/agente/youtube/recent`
- **POST** `/agente/youtube/transcript`
- **POST** `/agente/youtube/upload-summary`
- **POST** `/agente/youtube/upload-summary-file`
- **POST** `/agente/youtube/authorize`
- **POST** `/agente/youtube/create-client-secrets`
- **POST** `/agente/youtube/daily-resume`
- **POST** `/agente/drive/create-client-secrets`
- **POST** `/agente/drive/authorize`
- **POST** `/agente/drive/list`
- **POST** `/agente/drive/ensure-folder`
- **POST** `/agente/drive/upload`
- **POST** `/agente/drive/upload-b64`
- **POST** `/agente/drive/move`
- **POST** `/agente/drive/rename`
- **POST** `/agente/drive/trash`
- **POST** `/agente/drive/delete`

### Request ejemplo

```json
{
    "dry_run": true,
    "photos_limit": 20,
    "drive_limit": 50,
    "onedrive_limit": 20,
    "onedrive_max_mb": 20,
    "youtube_per_channel": 10,
    "youtube_channels": ["UC_x5XG1OV2P6uZZ5FSM9Ttw"]
}
```

### Qué hace

1. Importa fotos recientes de Google Photos a Drive.
2. Clasifica archivos recientes de Google Drive en carpetas por tipo.
3. Importa archivos recientes de OneDrive hacia Drive (con límite de tamaño).
4. Guarda metadatos en `appProperties` para evitar duplicados entre corridas.
5. Monitorea canales de YouTube y guarda transcripciones en `documentos/` para indexación RAG.

### Estructura en Drive

`
NEXO_SOBERANO_CLASIFICADO/
    GooglePhotos/{IMAGENES|VIDEOS|DOCUMENTOS|AUDIOS|COMPRIMIDOS|OTROS}
    GoogleDrive/{IMAGENES|VIDEOS|DOCUMENTOS|AUDIOS|COMPRIMIDOS|OTROS}
    OneDrive/{IMAGENES|VIDEOS|DOCUMENTOS|AUDIOS|COMPRIMIDOS|OTROS}
`

### Recomendación operativa

- Ejecuta primero con `dry_run: true` para validar acceso y volúmenes.
- Luego repite con `dry_run: false` para aplicar cambios reales.

### Endpoints YouTube

#### 1) Videos recientes de canal

`POST /agente/youtube/recent`

```json
{
    "channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
    "max_results": 10
}
```

#### 2) Transcripción para análisis/RAG

`POST /agente/youtube/transcript`

```json
{
    "video_id": "dQw4w9WgXcQ",
    "languages": ["es", "en"],
    "save_to_documentos": true
}
```

#### 3) Subida automática de resumen diario

`POST /agente/youtube/upload-summary`

```json
{
    "title": "Resumen geopolítico diario",
    "description": "Resumen automático NEXO",
    "file_b64": "<mp4_en_base64>",
    "filename": "resumen.mp4",
    "privacy_status": "unlisted"
}
```

#### 4) Bootstrap OAuth YouTube (una sola vez)

`POST /agente/youtube/authorize`

```json
{
    "upload_scope": true
}
```

Úsalo para generar tokens persistentes antes del primer uso de lectura/subida. Así el backend evita abrir flujos interactivos dentro de requests logísticos.

#### 7) Pipeline diario Drive -> YouTube

`POST /agente/youtube/daily-resume`

```json
{
    "dry_run": true,
    "max_scan": 50,
    "privacy_status": "unlisted"
}
```

Comportamiento:

1. Busca en Drive un archivo reciente con nombre que contenga `resumen`/`summary`.
2. Descarga el contenido de texto.
3. En `dry_run=true`, devuelve preview sin subir video.
4. En `dry_run=false`, genera clip simple con `moviepy` y lo sube a YouTube.

#### 5) Crear `client_secrets` desde `.env`

`POST /agente/youtube/create-client-secrets`

Variables requeridas en entorno:

- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- opcional: `YOUTUBE_PROJECT_ID`

Este endpoint genera `backend/auth/client_secrets_youtube.json` para usar OAuth de YouTube sin editar archivos manualmente.

#### 6) Subida de resumen por archivo (multipart)

`POST /agente/youtube/upload-summary-file`

`multipart/form-data`:

- `file` (mp4)
- `title`
- `description` (opcional)
- `tags` (opcional, separadas por coma)
- `privacy_status` (`public|unlisted|private`)
- `category_id` (default `25`)

Este endpoint evita el overhead de codificar MP4 en base64.

---

## 🗂️ OAuth + Gestión Completa de Google Drive

### Variables de entorno para bootstrap Drive

- `DRIVE_CLIENT_ID`
- `DRIVE_CLIENT_SECRET`
- opcional: `DRIVE_PROJECT_ID`

### Crear `drive_client_secrets.json` desde `.env`

`POST /agente/drive/create-client-secrets`

Genera automáticamente:

- `backend/auth/drive_client_secrets.json`

### Autorizar Drive (OAuth interactivo)

`POST /agente/drive/authorize`

```json
{
    "write_scope": true
}
```

Con `write_scope=true` usa scope completo: `https://www.googleapis.com/auth/drive`.

### Operaciones Drive disponibles por API

1. **Listar carpeta** — `POST /agente/drive/list`

```json
{
    "folder_id": "<drive_folder_id>",
    "max_results": 50
}
```

2. **Subir archivo** — `POST /agente/drive/upload` (`multipart/form-data`)

- `file`
- `folder_id`
- `name` (opcional)

3. **Subir archivo por base64** — `POST /agente/drive/upload-b64`

```json
{
    "folder_id": "<folder_id>",
    "filename": "prueba.txt",
    "file_b64": "<contenido_base64>"
}
```

4. **Asegurar carpeta (crear si no existe)** — `POST /agente/drive/ensure-folder`

```json
{
    "path_parts": ["NEXO_SOBERANO_CLASIFICADO", "SmokeTests"],
    "parent_id": "root"
}
```

5. **Mover archivo** — `POST /agente/drive/move`

```json
{
    "file_id": "<file_id>",
    "target_folder_id": "<folder_id>"
}
```

6. **Renombrar archivo** — `POST /agente/drive/rename`

```json
{
    "file_id": "<file_id>",
    "new_name": "nuevo_nombre.ext"
}
```

7. **Enviar/restaurar papelera** — `POST /agente/drive/trash`

```json
{
    "file_id": "<file_id>",
    "trashed": true
}
```

8. **Eliminar permanente** — `POST /agente/drive/delete`

```json
{
    "file_id": "<file_id>"
}
```

### Smoke test automatizado (PowerShell)

Script incluido:

- `scripts/smoke_test_drive_api.ps1`
- `scripts/smoke_test_drive_youtube.ps1`
- `scripts/go_live_drive_youtube_final.ps1`
- `scripts/quick_go_live.ps1`

Ejemplos:

```powershell
# Con autorización interactiva (recomendado primera vez)
.\scripts\smoke_test_drive_api.ps1

# Omitir OAuth interactivo si ya tienes token
.\scripts\smoke_test_drive_api.ps1 -SkipAuthorize

# Smoke test combinado Drive -> YouTube
.\scripts\smoke_test_drive_youtube.ps1

# Smoke test combinado sin autorizar de nuevo
.\scripts\smoke_test_drive_youtube.ps1 -SkipAuthorize

# Ejecutar subida real sin prompt
.\scripts\smoke_test_drive_youtube.ps1 -RunRealUpload

# Script final go-live (Drive -> YouTube)
.\scripts\go_live_drive_youtube_final.ps1

# Final go-live sin reautorizar
.\scripts\go_live_drive_youtube_final.ps1 -SkipAuthorize

# Final go-live con subida real no interactiva
.\scripts\go_live_drive_youtube_final.ps1 -RunRealUpload

# Quick go-live (preflight + dummy + dry-run + real)
.\scripts\quick_go_live.ps1

# Quick go-live con confirmación automática
.\scripts\quick_go_live.ps1 -AutoConfirm
```

Notas:

- El script combinado sube un `resumen_prueba_*.txt` a Drive y luego llama `POST /agente/youtube/daily-resume`.
- Si no se indica `-RunRealUpload`, ejecuta `dry_run` y pregunta confirmación antes de subir a YouTube.
- Acepta credenciales compartidas en `.env`: `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`.

### Variables mínimas para go-live

- `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET` (o equivalentes `DRIVE_*` + `YOUTUBE_*`)
- opcional: `DRIVE_ROOT_FOLDER_ID` (si no existe, el script crea carpeta fallback)

### Tunables de producción (opcionales)

- `NEXO_API_DELAY_SECONDS` → pausa entre llamadas API para reducir riesgo de cuota/rate-limit (ej. `0.5`)
- `NEXO_VIDEO_BITRATE` → bitrate de salida para clips del pipeline diario (default `1000k`)
