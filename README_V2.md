# 🔷 NEXO SOBERANO v2.0
## Sistema de Inteligencia Geopolítica Híbrido RAG

**Status:** ✅ Operacional | **Version:** 2.0.0 | **Actualizado:** 2026-02-24

---

## ¿Qué es NEXO Soberano?

**Nexo Soberano** es una plataforma de inteligencia que:

1. **Ingesta documentos** (PDF, DOCX, TXT, imágenes) de tu computadora
2. **Los analiza** con IA (clasificación, resumen automático)
3. **Los vectoriza** (embeddings semánticos) para búsqueda inteligente
4. **Responde preguntas** basado ÚNICAMENTE en tus documentos (RAG)
5. **Controla costos** reales de la API (no estimaciones falsas)
6. **Sincroniza** con Google Drive y OneDrive
7. **Interfaz web** con chat interactivo + estadísticas

**Todo funciona con tus datos en tu computadora.** Nada se sube a la nube excepto lo que explícitamente envías a Gemini para análisis.

---

## 🚀 Quick Start (5 minutos)

### Prerequisitos
- Python 3.13 ✅ (ya instalado)
- virtual env ✅ (.venv existe)
- Dependencies ✅ (pip install -r requirements.txt pasado)

### 1. Indexar tus documentos
```bash
# Copiar PDFs a:
# documentos/
#   ├─ documento1.pdf
#   ├─ documento2.docx
#   └─ ...

python nexo_v2.py setup
```

### 2. Iniciar servidor
```bash
python nexo_v2.py run
```

### 3. Usar
```
Abrir: http://localhost:8000
Chat interactivo en navegador
```

---

## 📋 Comandos Disponibles

```bash
python nexo_v2.py setup    # Indexar documentos en carpeta local
python nexo_v2.py run      # Iniciar servidor web
python nexo_v2.py sync     # Sincronizar Google Drive + OneDrive
python nexo_v2.py test     # Verificar que todo funciona
python nexo_v2.py chat     # Chat en terminal interactivo
```

---

## 🎯 Caso de Uso: Analista Geopolítico

### Scenario
- Tienes 50 PDFs sobre conflictos, economía, geopolítica
- Necesitas responder preguntas rápidamente
- Quieres saber qué categoría de documentos tienes
- Necesitas rastrear costos de la API

### Con Nexo Soberano
```bash
# Día 1: Setup
python nexo_v2.py setup
# → Indexa 50 PDFs automáticamente
# → Clasifica en GEO/ECO/PSI/TEC/COM/ADM
# → Genera embeddings (~5 minutos)

# Día 1+: Uso
python nexo_v2.py run
# → Abre browser en http://localhost:8000
# → Preguntas instantáneas
# → Costos reales registrados

# Semana 1: Monitor
curl http://localhost:8000/api/costos
# {"resumen": "Tokens hoy: 45,230 / 900,000 (5.0%)"}
```

---

## 🏗️ Arquitectura

### Capas

```
┌──────────────────────────────────────────┐
│         Frontend (Browser)               │
│  Chat interactivo + estadísticas         │
└──────────────┬───────────────────────────┘
               │ HTTP REST
┌──────────────▼───────────────────────────┐
│       FastAPI Backend (nexo_v2.py)       │
│  Módulos 1-12, endpoints /api/*          │
└──────────────┬───────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
┌─────────────┐      ┌─────────────┐
│   SQLite    │      │   ChromaDB  │
│  (metadata) │      │  (vectores) │
└─────────────┘      └─────────────┘
    │                     │
    └──────────┬──────────┘
               │
         [Google Gemini API]  (optional, for LLM)
```

### Data Flow (Ingesta)

```
User's Computer
    │
    ├─ documentos/ (tus PDFs)
    │
    ▼
nexo_v2.py :: procesar_archivo()
    │
    ├─ Hash SHA-256 (deduplicación)
    │
    ├─ Extrae texto (local, SIN subidas)
    │
    ├─ Clasifica (Gemini Flash/Pro)
    │   Categoría: GEO/ECO/PSI/TEC/COM/ADM
    │   Impacto: Alto/Medio/Bajo
    │
    ├─ Chunks de 400 palabras
    │
    ├─ Embeddings (all-MiniLM-L6-v2, local)
    │   384 dimensiones
    │
    ├─→ ChromaDB (búsqueda semántica)
    │
    ├─→ SQLite: tabla evidencia
    │   (name, category, summary, date)
    │
    └─→ SQLite: tabla costos_api
        (modelo, tokens_in, tokens_out, operación)
```

### Data Flow (Consulta RAG)

```
User: "¿Qué sé sobre la economía austriaca?"
    │
    ▼
generar_embedding()
    │ (local, 384 dims)
    │
    ▼
ChromaDB.query()
    │ (búsqueda por cosine distance)
    │
    ▼ Find top 5 chunks where distance < 0.65
    │
    ├─ Chunk 1: "...economía austriaca está..."
    ├─ Chunk 2: "...inflación EU afecta Austria..."
    ├─ Chunk 3: "...banco central europeo..."
    │
    ▼
Gemini Flash (con contexto)
    │ Prompt: "Respondé SOLO usando estos chunks"
    │
    ▼ Respuesta
│
└─→ Guardado en tabla consultas
└─→ Costos registrados en costos_api
```

---

## 🔌 API Endpoints

### Chat RAG
```
POST /agente/consultar
POST /api/chat

{
  "pregunta": "¿Qué pasó en Rusia?",
  "categoria": "GEO"  // opcional
}

Respuesta:
{
  "respuesta": "Basado en tus documentos...",
  "fuentes": ["rusia_2024.pdf", "conflicto_2024.docx"],
  "chunks": 5,
  "ms": 1234,
  "total_docs": 42
}
```

### Estado del sistema
```
GET /api/estado

{
  "online": true,
  "version": "2.0",
  "docs_indexados": 42,
  "chunks_total": 156,
  "costos_hoy": "Tokens hoy: 45,230 / 900,000 (5.0%)",
  "ultima_consulta": "2026-02-24T12:30:45",
  "timestamp": "2026-02-24T12:31:00"
}
```

### Documentos listado
```
GET /api/documentos

[
  {
    "nombre": "rusia_2024.pdf",
    "cat": "GEO",
    "impacto": "Alto",
    "resumen": "Actividad militar en...",
    "fecha": "2026-02-24"
  }
]
```

### Costos reales
```
GET /api/costos

{
  "resumen": "Tokens hoy: 45,230 / 900,000 (5.0%)",
  "por_modelo": [
    {"modelo": "gemini-1.5-flash", "tokens": 40000, "llamadas": 15},
    {"modelo": "gemini-1.5-pro", "tokens": 5230, "llamadas": 2}
  ]
}
```

### Historial de consultas
```
GET /api/historial

[
  {
    "fecha": "2026-02-24 12:30:45",
    "pregunta": "¿Qué sé sobre Rusia?",
    "chunks": 5,
    "ms": 1234
  }
]
```

### Frontend
```
GET /

Interfaz web interactiva
Chat + sidebar con documentos
```

---

## 📊 Cómo funciona la Clasificación

### Modelo inicial (Flash — barato)
```
Archivo: economia_austriaca.docx
Contenido (primeros 800 chars): "El banco central austriaco..."

Gemini Flash analiza:
  Categoría: ECO (Economía)
  Impacto: Medio
  Resumen: "Política monetaria del banco central europeo..."

Costo: ~100 tokens (< $0.01)
```

### Modelo avanzado (Pro — para prioridad alta)
```
Archivo: OTAN_expansion_2024.pdf
Detección: "OTAN" en nombre → es ALTA PRIORIDAD

Gemini Pro analiza (modelo razonamiento profundo):
  Categoría: GEO
  Impacto: Alto
  Resumen: "Análisis geopolítico de expansión OTAN implicancias..."

Costo: ~500 tokens (< $0.05)
```

### Palabras clave de alta prioridad
```python
FUENTES_ALTO = [
    "OTAN", "NATO", "Rusia", "Russia", "China", "Iran",
    "Ucrania", "Ukraine", "Gaza", "Economia_Austriaca",
    "Latam", "MiddleEast"
]
```

Si el nombre del archivo contiene cualquiera, usa Gemini Pro.

---

## 💾 Base de datos

### SQLite: NEXO_SOBERANO/base_sqlite/boveda.db

#### Tabla: evidencia
```sql
hash_sha256         TEXT UNIQUE     -- identifier
nombre_archivo      TEXT            -- rusia_2024.pdf
ruta_local          TEXT            -- path en tu computadora
categoria           TEXT            -- GEO|ECO|PSI|TEC|COM|ADM
resumen_ia          TEXT            -- "Análisis de expansión OTAN..."
fecha_ingesta       TIMESTAMP       -- cuando se agregó
nivel_confianza     REAL            -- 0.85
impacto             TEXT            -- "Alto" | "Medio" | "Bajo"
vectorizado         INTEGER         -- 1 si está en ChromaDB
```

#### Tabla: consultas
```sql
fecha               TIMESTAMP       -- 2026-02-24 12:30:45
pregunta            TEXT            -- "¿Qué pasó en Rusia?"
respuesta           TEXT            -- "Basado en tus documentos..."
fuentes             TEXT (JSON)     -- ["rusia_2024.pdf"]
chunks              INTEGER         -- 5
ms                  INTEGER         -- 1234 ms
```

#### Tabla: costos_api
```sql
fecha               TIMESTAMP       -- 2026-02-24
modelo              TEXT            -- "gemini-1.5-flash"
tokens_in           INTEGER         -- 245
tokens_out          INTEGER         -- 89
operacion           TEXT            -- "rag_consulta" | "clasificacion"
```

### ChromaDB: NEXO_SOBERANO/memoria_vectorial/

```
Colección: inteligencia_geopolitica

Vector Store (HNSW):
  - 156 embeddings (384 dims cada uno)
  - Métrica: cosine distance
  - Threshold relevancia: < 0.65

Metadata:
  - doc_id, archivo, ruta, fuente, categoria, impacto
  - chunk número, fecha
```

---

## 🔐 Seguridad & Privacidad

### Lo que QUEDA en tu computadora
✅ Todos los PDFs/DOCX
✅ Todos los embeddings (vectors)
✅ Toda la metadata (SQLite)
✅ Todas las consultas y respuestas

### Lo que OPTIONALMENTE va a Google (Gemini)
- Títulos de archivos (para decidir Flash vs Pro)
- Primeros 800 caracteres (para clasificación)
- Top 5 chunks + pregunta (para respuesta RAG)
- Bytes de PDFs escaneados (OCR Vision, si tienes API key)

### Cómo controlar
```bash
# Si NO defines GEMINI_API_KEY en .env:
GEMINI_API_KEY=        # vacío

# Sistema funciona pero:
# - Embeddings: usa local (gratis)
# - Clasificación: sin IA (default "GEO")
# - RAG: retorna chunks sin procesamiento
# - OCR: retorna "[Sin API key]"
```

---

## 📈 Monitoreo de Costos

### Dashboard automático
```bash
python nexo_v2.py run
# Abre http://localhost:8000/api/costos
```

Muestra:
- **Tokens totales hoy**
- **% del presupuesto usado**
- **Desglose por modelo** (Flash vs Pro)
- **Número de llamadas**

### Presupuesto diario
```
Free tier Gemini: ~900K tokens/día
Contrato típico: $30/mes = 15M tokens/mes
Implementado: 900K/día (control fuerte)

Si se agota: Sistema DETIENE clasificaciones/RAG automáticamente
Mensaje: "Presupuesto diario agotado. Reinicia mañana."
```

---

## 🔄 Sync con la Nube

### Google Drive
```bash
python nexo_v2.py sync
# Descarga archivos del Drive
# Los procesa automáticamente
# Los indexa en ChromaDB
```

**Requiere:** Credenciales Google OAuth (setup_credentials.py)

### OneDrive
```bash
python nexo_v2.py sync
# Descarga archivos del OneDrive
# Los procesa automáticamente
# Los indexa en ChromaDB
```

**Requiere:** Credenciales Microsoft MSAL (setup_credentials.py)

### Watchdog (Automático)
```bash
# Mientras nexo_v2.py run está corriendo:
# Cualquier archivo nuevo en documentos/ es indexado automáticamente
# No necesitas hacer nada
```

---

## 🧪 Verificación

### Health check
```bash
curl http://localhost:8000/api/health

# Expected:
{
  "status": "online",
  "message": "✅ Nexo Soberano está operacional"
}
```

### Load test
```bash
python nexo_v2.py test

# Output:
🧪 Test 1: SQLite... ✅ 42 documentos
🧪 Test 2: Embedding... ✅ 384 dims
🧪 Test 3: ChromaDB... ✅ 156 chunks
💰 Costos: Tokens hoy: 0/900,000 (0%)
```

---

## 📚 Documentación Completa

| Documento | Propósito |
|-----------|-----------|
| [EXECUTIVE_SUMMARY_V2.md](EXECUTIVE_SUMMARY_V2.md) | Qué cambió, por qué, impacto |
| [INTEGRACION_V2.md](INTEGRACION_V2.md) | Cómo reemplaza archivos antiguos |
| [LAUNCH_GUIDE.md](LAUNCH_GUIDE.md) | Setup inicial (Node.js, frontend) |
| [STATUS.md](STATUS.md) | Estado actual del sistema |
| [QUICK_REFERENCE.txt](QUICK_REFERENCE.txt) | Tarjeta de escritorio (imprimible) |
| [README.md](README.md) | Este archivo |

---

## ⚡ Casos de Uso

### 1. Analista de Inteligencia
```bash
# Setup
python nexo_v2.py setup

# Análisis diarios
curl -X POST http://localhost:8000/api/chat \
  -d '{"pregunta": "Cambios geopolíticos la semana pasada"}'

# Reporte de costos
curl http://localhost:8000/api/costos
```

### 2. Investigador Académico
```bash
# Indexar papers
python nexo_v2.py setup

# Buscar por género
curl -X POST http://localhost:8000/api/chat \
  -d '{"pregunta": "...economia", "categoria": "ECO"}'

# Export historial de búsquedas
sqlite3 boveda.db "SELECT * FROM consultas" > research_log.csv
```

### 3. Gestor de Contenido
```bash
# Sincronizar Drive
python nexo_v2.py sync

# Ver qué se indexó
curl http://localhost:8000/api/documentos

# Verificar duplicados
sqlite3 boveda.db "SELECT COUNT(DISTINCT hash_sha256) FROM evidencia"
```

---

## 🚨 Troubleshooting

| Problem | Solution |
|---------|----------|
| Puerto 8000 ocupado | `Get-Process python \| Stop-Process -Force` |
| Embeddings no funcionan | `pip install sentence-transformers` |
| ChromaDB error | `rm -r NEXO_SOBERANO/memoria_vectorial` (rebuild) |
| API key Gemini inválida | Verifica `.env`, `echo %GEMINI_API_KEY%` |
| Base de datos corrupta | Backup + `rm boveda.db` (rebuild) |

---

## 🎓 Aprendizaje

### Conceptos clave
- **RAG:** Retrieval-Augmented Generation (búsqueda + IA)
- **Embeddings:** Representación numérica de texto (384 dimensiones)
- **ChromaDB:** Base de datos vectorial (búsqueda semántica)
- **Token:** Unidad de costo en APIs de IA (~1k tokens = 1 párrafo)

### Lecturas recomendadas
- ChromaDB docs: https://docs.trychroma.com
- Gemini API: https://ai.google.dev
- Sentence Transformers: https://www.sbert.net

---

## 📞 Soporte

### Si algo no funciona
1. Ejecutar `python nexo_v2.py test`
2. Revisar logs en `NEXO_SOBERANO/bitacora/`
3. Consultar `INTEGRACION_V2.md` (troubleshooting section)
4. Verificar `.env` config

---

## 📜 Licencia & Responsabilidad

**NEXO Soberano** es una herramienta de inteligencia local.

- Data: 100% en tu computadora
- Análisis: IA opcional (Gemini API, si lo habilitás)
- Privacidad: Tú controlas qué se envía a dónde

---

## 🔄 Changelog

### v2.0.0 (Actual)
- ✅ Pipeline unificado
- ✅ Data sovereignty (sin subidas a Google)
- ✅ Costos reales medidos
- ✅ 12 módulos integrados
- ✅ Watchdog automático
- ✅ FastAPI endpoints

### v1.x (Desinactualizado)
- ❌ 5 archivos fragmentados
- ❌ genai.upload_file() violaba privacidad
- ❌ Costos contados falsamente (1500 hardcoded)
- ❌ Orchestrators duplicados

---

**NEXO SOBERANO v2.0** — Sistema de inteligencia unificado, seguro, cost-aware.

**Listo para usar:** `python nexo_v2.py run`

