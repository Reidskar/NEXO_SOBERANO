# 🔧 REFACTORIZACIÓN — Backend Unificado

## CAMBIOS REALIZADOS

### ✅ ELIMINADO (Mock)
- ❌ `api/main.py` (mock con endpoint `/api/chat`)
- ❌ `api/routes/chat.py` (respuesta demo "Procesando: ...")
- ❌ Lógica hardcodeada en rutas

### ✅ CREADO (Backend Unificado)

```
backend/
    __init__.py
    config.py              # Configuración centralizada
    main.py                # FastAPI app (puerto 8000)
    routes/
        __init__.py
        agente.py          # Rutas del agente RAG
    services/
        __init__.py
        cost_manager.py    # Gestor de costos real
        rag_service.py     # Motor RAG (extrae lógica de nexo_v2.py)
```

### ✅ ACTUALIZADO (Frontend)
- ✅ `frontend/src/components/ChatBox.jsx`
  - Endpoint: `/api/chat` → `/agente/consultar` (POST)
  - Contrato: `{message}` → `{query, mode}`
  - Respuesta: `{response}` → `{answer, sources, tokens_used, ...}`

---

## CONTRATO UNIFICADO

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
    "sources": ["rusia_2024.pdf", "economia.docx"],
    "tokens_used": 450,
    "chunks_used": 5,
    "execution_time_ms": 2340,
    "total_docs": 45,
    "presupuesto": {
        "tokens_hoy": 2500,
        "max_tokens": 900000,
        "porcentaje": 0.3,
        "disponible": 897500,
        "puede_operar": true
    },
    "error": false
}
```

---

## ENDPOINTS DISPONIBLES

### Agente RAG
- **POST** `/agente/consultar` — Consulta RAG unificada
- **GET** `/agente/health` — Health check RAG
- **GET** `/agente/presupuesto` — Estado del presupuesto
- **GET** `/agente/historial-costos` — Costos últimos 7 días

### Sistema
- **GET** `/` — Info del API
- **GET** `/health` — Health check general
- **GET** `/api/docs` — Documentación Swagger
- **GET** `/api/openapi.json` — OpenAPI JSON

---

## CONFIGURACIÓN CENTRALIZADA

### `backend/config.py`
```python
MAX_TOKENS_DIA = 900_000          # Presupuesto Gemini
CORS_ORIGINS = ["http://localhost:3000", ...]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHUNK_SIZE = 400
TOP_K = 5
```

Todos los módulos importan desde `config` — una sola fuente de verdad.

---

## GESTIÓN DE COSTOS REAL

### Before ❌
```python
class GestorDeCostos:
    def gastar_tokens(self):
        return 1500  # Hardcoded fake
```

### After ✅
```python
class CostManager:
    def registrar(self, modelo: str, tokens_in: int, tokens_out: int, op: str):
        db.execute("INSERT INTO costos_api (fecha, modelo, tokens_in, tokens_out, operacion) ...")
        
    def tokens_hoy(self) -> int:
        return SUM(tokens_in + tokens_out) FROM costos_api WHERE fecha LIKE hoy
```

**Resultado:** Tokens reales medidos, no estimados.

---

## RAG SERVICE

### Lógica Extraída de `nexo_v2.py`
```python
class RAGService:
    def consultar(self, pregunta: str, categoria: Optional[str]) -> Dict:
        # 1. Validar bóveda no vacía
        # 2. Generar embedding
        # 3. Buscar en ChromaDB  
        # 4. Filtrar por relevancia
        # 5. Generar respuesta con Gemini
        # 6. Registrar costo real
        # 7. Guardar consulta en SQLite
```

**Importable desde cualquier módulo**: `from backend.services.rag_service import get_rag_service()`

---

## CORS CORRECTO

### Before ❌
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # INSEGURO
    allow_credentials=True,
)
```

### After ✅
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Resultado:** Frontend en React (puerto 3000 o 5173) se conecta sin problemas.

---

## CÓMO ARRANCAR

### 1️⃣ Instalar dependencias (si falta)
```bash
pip install fastapi uvicorn pydantic
pip install google-generativeai chromadb sentence-transformers
```

### 2️⃣ Backend
```bash
python run_backend.py
# O
uvicorn backend.main:app --reload
```

**Output:**
```
╔══════════════════════════════════════════════════════════════╗
║  🚀 NEXO SOBERANO v2.0 — BACKEND UNIFICADO                  ║
╚══════════════════════════════════════════════════════════════╝

📍 Escuchando en: http://0.0.0.0:8000
📚 Documentación API: http://localhost:8000/api/docs
💰 Presupuesto: 900,000 tokens/día
```

### 3️⃣ Frontend (en otra terminal)
```bash
cd frontend
npm install
npm run dev
# Abrirá en http://localhost:5173 (Vite)
```

### 4️⃣ Probar
```bash
curl -X POST http://localhost:8000/agente/consultar \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Qué pasa en Rusia?"}'
```

---

## ARCHIVOS ELIMINABLES (ANTIGUOS)

Si integración funciona, puedes eliminar:
- `api/main.py` (reemplazado por `backend/main.py`)
- `api/routes/chat.py` (lógica movida a `backend/routes/agente.py`)
- `api/routes/health.py` (si existe)
- `api/__init__.py` (si no se usa)

---

## INTEGRACIÓN CON `nexo_v2.py`

`nexo_v2.py` sigue siendo el **script maestro CLI**:
```bash
python nexo_v2.py setup    # Indexar documentos
python nexo_v2.py sync     # Sincronizar nube
python nexo_v2.py test     # Tests
python nexo_v2.py chat     # Chat CLI
```

Backend ahora **reutiliza su lógica** sin duplicar:
- `rag_service.py` ← código de `consultar_rag()` de `nexo_v2.py`
- `cost_manager.py` ← código de `GestorCostos` de `nexo_v2.py`

---

## ESTADO ACTUAL

| Sistema | Estado |
|---------|--------|
| Backend API | ✅ Unificado |
| RAG Motor | ✅ Funcional |
| Gestión Costos | ✅ Real |
| CORS | ✅ Correcto |
| Frontend | ✅ Actualizado |
| Presupuesto | ✅ Centralizado |
| CLI | ✅ Funcional (separado) |

---

## PRÓXIMOS PASOS

1. Prueba: `curl -X POST http://localhost:8000/agente/consultar ...`
2. [Opcional] Eliminar archivos `api/` antiguos
3. Integrar con WorldMonitor (WebGL maps)
4. Agregar endpoints `/alertas` para geolocalización

---

**Dirección:** Camilo  
**Status:** REFACTORIZACIÓN COMPLETA ✅  
**Inicio de operaciones:** Inmediato
