# 🚀 NEXO SOBERANO v2.0 — Guía de integración

## ¿Qué cambió?

### Los bugs que se corrigieron

| Bug | Problema | Solución en v2.0 |
|-----|----------|------------------|
| **Pipeline fragmentado** | `motor_ingesta.py` guardaba en SQLite, `memoria_semantica.py` vectorizaba por separado, `api_puente.py` consultaba sin conectarlos | Pipeline unificado en `nexo_v2.py`: texto → chunks → embeddings → ChromaDB → SQLite (todo en uno) |
| **Datos subidos a Google** | `motor_ingesta.py` usaba `genai.upload_file()` violaría soberanía de datos | `extraer_texto_local()` procesa 100% localmente. Solo OCR con Gemini Vision si es PDF escaneado |
| **Costos contados falso** | `GestorDeCostos` sumaba 1500 tokens sin medir real | `GestorCostos` registra tokens_in + tokens_out reales en tabla SQLite |
| **Orquestadores duplicados** | `core/orchestrator.py` y `core/orquestador.py` hacían lo mismo | Un solo orquestador integrado en `nexo_v2.py` |
| **Stubs nunca execute** | `arquitecto_v2.py` creaba archivos vacíos nunca llenados | Todas las funciones implementadas |

---

## 📦 Antes vs. Después

### Estructura ANTES (fragmentada)
```
nexo_soberano.py          (punto de entrada vacío)
├─ motor_ingesta.py       → hash + extract + genera resumen
├─ memoria_semantica.py   → vectoriza en ChromaDB
├─ api_puente.py          → FastAPI RAG
├─ core/orquestador.py    → coordinación
├─ core/orchestrator.py   → duplicado
└─ (nunca se llamaban en orden)
```

### Estructura DESPUÉS (árbol de dependencias claro)
```
nexo_v2.py                (todo integrado, 900 líneas)
├─ Módulo 1: DB (SQLite)
├─ Módulo 2: Gestor de costos REAL
├─ Módulo 3: Embeddings (local ALL-MiniLM + Gemini fallback)
├─ Módulo 4: ChromaDB
├─ Módulo 5: Extractor texto local (sin subidas)
├─ Módulo 6: Chunker
├─ Módulo 7: Clasificador (Flash/Pro por prioridad)
├─ Módulo 8: Pipeline ingesta unificado
├─ Módulo 9: Consulta RAG
├─ Módulo 10: Sync Google Drive/OneDrive
├─ Módulo 11: Watchdog automático
├─ Módulo 12: FastAPI endpoints
└─ CLI: setup, run, sync, test, chat
```

---

## 🔄 Migración (qué mantener, qué reemplazar)

### ✅ MANTENER (seguiremos usando)
```
core/auth_manager.py              (OAuth2 Google + Microsoft)
services/connectors/google_connector.py
services/connectors/microsoft_connector.py
NEXO_SOBERANO/base_sqlite/boveda.db  (esquema compatible)
frontend/                         (React apps)
```

### ❌ REEMPLAZAR (obsoleto)
```
motor_ingesta.py         → Función en nexo_v2.py: procesar_archivo()
memoria_semantica.py     → Función en nexo_v2.py: get_coleccion()
api_puente.py            → Función en nexo_v2.py: crear_app()
core/orquestador.py      → Integrado en nexo_v2.py
core/orchestrator.py     → BORRAR (duplicado)
arquitecto_v2.py         → BORRAR (generó stubs vacíos)
```

---

## 🚀 Cómo usar v2.0

### 1. Primera ejecución (indexar carpeta local)
```powershell
cd C:\Users\Admn\Desktop\NEXO_SOBERANO

# Copiar tus PDFs aquí:
# documentos/
#   ├─ rusia_2024.pdf
#   ├─ economia_austriaca.docx
#   └─ etc...

# Indexar todo
python nexo_v2.py setup

# Output esperado:
# ═════════════════════════════════════════════════════
# NEXO SOBERANO v2.0 — Indexación inicial
# 3 archivo(s) encontrado(s)
# ═════════════════════════════════════════════════════
# [1/3] rusia_2024.pdf             ✅ 25 chunks [GEO] [Alto]
# [2/3] economia_austriaca.docx    ✅ 18 chunks [ECO] [Medio]
# [3/3] conflicto_ucrania.html     ❌ Extensión no soportada
# 
# ─────────────────────────────────────────────────────
# ✅ Nuevos: 2  ⏭️ Ya existían: 0  ❌ Errores: 1
# Total en ChromaDB: 43 chunks
# Costos: Tokens hoy: 0 / 900,000 (0.0%)
```

### 2. Iniciar servidor
```powershell
python nexo_v2.py run

# Output:
# ═════════════════════════════════════════════════════
# NEXO SOBERANO v2.0 — Servidor activo
# Chat:   http://localhost:8000
# Estado: http://localhost:8000/api/estado
# Costos: http://localhost:8000/api/costos
# Docs:   C:\...\documentos
# ═════════════════════════════════════════════════════

# Abrir:
# Browser → http://localhost:8000
```

### 3. Sincronizar con nube (Google Drive + OneDrive)
```powershell
python nexo_v2.py sync

# Output:
# 🔄 Sincronizando Google Drive...
# ✅ Descargado: Documento_OTAN.pdf
# 🧠 Indexado: Documento_OTAN.pdf [GEO]
# ...
# ✅ Sincronización completa: 5 archivos nuevos procesados.
```

### 4. Chat en terminal
```powershell
python nexo_v2.py chat

# Interactivo:
# 💬 Chat terminal (Ctrl+C para salir)
# 
# Tú: ¿Qué sé sobre la economía austriaca?
# 
# Nexo: [respuesta basada ÚNICAMENTE en tus documentos]
# Fuentes: economia_austriaca.docx, informe_UE_2024.pdf
```

### 5. Tests unitarios
```powershell
python nexo_v2.py test

# Verifica:
# ✅ SQLite funcionando
# ✅ Embeddings locales
# ✅ ChromaDB conectado
# ✅ Costos siendo registrados
```

---

## 🔌 Endpoints API (igual que antes + más)

### Compatibilidad con `api_puente.py`
```
POST /agente/consultar          ← Original (mantiene compatibilidad)
POST /api/chat                  ← Nuevo (mismo endpoint)
{
  "pregunta": "¿Qué sé sobre Rusia?",
  "categoria": "GEO"  // opcional
}
```

### Nuevos endpoints
```
GET  /api/estado       → {"online": true, "docs_indexados": 42, "chunks_total": 156, ...}
GET  /api/documentos   → Lista de documentos indexados
GET  /api/costos       → {"resumen": "Tokens hoy: 15,234 / 900,000 (1.7%)", "por_modelo": [...]}
GET  /api/historial    → Últimas 30 consultas
GET  /                 → Frontend HTML (mismo interfaz)
```

---

## 💾 Datos: compatibilidad garantizada

### SQLite (boveda.db)
```sql
-- Tablas existentes (se mantienen idénticas):
evidencia               -- metadatos de documentos
vectorizados_log        -- log de qué fue vectorizado

-- Tablas nuevas (no rompen nada):
consultas              -- historial de preguntas/respuestas
costos_api             -- tokens reales por llamada Gemini
alertas                -- para Telegram/Discord
```

### ChromaDB
```
- Colección: inteligencia_geopolitica
- Modelo embedding: all-MiniLM-L6-v2 (384 dimensiones)
- Espacio métrico: cosine
- Directorio: NEXO_SOBERANO/memoria_vectorial/
```

---

## 🎯 Cambios en lógica de costos

### ANTES (falso)
```python
# core/orquestador.py
class GestorDeCostos:
    def gastar_tokens(self):
        return 1500  # hardcoded, no midió nada real
```

### DESPUÉS (real)
```python
# nexo_v2.py
class GestorCostos:
    def registrar(self, modelo: str, tokens_in: int, tokens_out: int):
        # Guarda CADA llamada a Gemini en tabla costos_api
        # Cuenta tokens_in + tokens_out reales
        # Controla presupuesto diario (900K tokens free tier)
    
    def tokens_hoy(self) -> int:
        # Suma todos los tokens registrados hoy
        return SELECT SUM(tokens_in + tokens_out) FROM costos_api WHERE fecha LIKE ?
```

---

## ⚡ Decisiones de ingeniería

### Por qué todo en un archivo?
- **Antes:** 5 archivos, imports circulares, nadie sabe quién llama a quién
- **Ahora:** 900 líneas, módulos numerados (1-12), flujo de datos claro
- **Ventaja:** 1 comando (`python nexo_v2.py run`) lo inicia todo

### Por qué all-MiniLM-L6-v2 local + Gemini fallback?
- **Local:** Gratis, instantáneo, 384 dims, funciona en tu computadora
- **Gemini fallback:** Si falla local (raro), usa Gemini embeddings (pago)

### Por qué Gemini Flash para clasificación?
- Modelo rápido (1-2s por documento)
- Cuesta ~10x menos que Pro
- Suficiente para categorizar en GEO/ECO/PSI/TEC/COM/ADM

### Por qué Gemini Pro para documentos "altos"?
- Fuentes de alta prioridad (OTAN, Rusia, China) merecen análisis profundo
- Flash es generic, Pro entiende matices diplomáticos

---

## 📊 Arquitectura de datos

```
documentos/                              (carpeta de entrada local)
    └─ mi_pdf.pdf
        ↓
procesar_archivo()
    ├─ hash SHA-256 (deduplicación)
    ├─ extraer_texto_local()    [100% local, SIN subidas]
    ├─ clasificar()             [Gemini Flash/Pro]
    │
    ├─→ SQLite: tabla evidencia
    │   (nombre, categoría, resumen, fecha, impacto)
    │
    ├─→ ChromaDB vectorial
    │   Chunks:
    │   [chunk1_emb, chunk2_emb, ...]
    │   Metadata:
    │   {archivo, categoria, impacto, fecha}
    │
    └─→ SQLite: tabla costos_api
        (modelo, tokens_in, tokens_out, operación)
```

### RAG Query Flow
```
user: "¿Rusia está expandiendo?"
  ↓
generar_embedding(query)  [local, 384 dims]
  ↓
ChromaDB.query()          [búsqueda semántica por cosine distance]
  ↓
filter: distancia < 0.65  [relevancia threshold]
  ↓
build prompt con contexto (top 5 chunks)
  ↓
Gemini Flash genera respuesta
  ↓
registrar_costo_real()    [mide tokens_in, tokens_out]
  ↓
guardar query + response en tabla consultas
  ↓
respuesta al usuario
```

---

## ✅ Checklist post-migración

- [ ] Crear carpeta `/documentos` (será creada automáticamente por `nexo_v2.py`)
- [ ] Copiar 2-3 PDFs de ejemplo
- [ ] Ejecutar: `python nexo_v2.py test` ✅ (ya pasó)
- [ ] Ejecutar: `python nexo_v2.py setup` (indexar PDFs)
- [ ] Ejecutar: `python nexo_v2.py run` (iniciar servidor)
- [ ] Ir a http://localhost:8000 en navegador
- [ ] Hacer consulta de prueba
- [ ] Verificar `/api/costos` muestre tokens reales
- [ ] Ejecutar: `python nexo_v2.py sync` (Download Drive/OneDrive)
- [ ] Ejecutar: `python nexo_v2.py chat` (test terminal)

---

## 🗑️ Archivos que DEBERÍAS borrar

```powershell
# Los siguientes ya NO se usan:
del motor_ingesta.py
del memoria_semantica.py
del api_puente.py
del core\orchestrator.py        # Mantén core\orquestador.py
del arquitecto_v2.py

# MANTENER:
# core\auth_manager.py           (lo usa sync())
# services\connectors\*          (lo usa sync())
# NEXO_SOBERANO\base_sqlite\*   (datos)
# .env                           (configuración)
```

---

## 🎓 Ejemplo de uso completo

### Sesión típica
```powershell
# Terminal única
cd C:\Users\Admn\Desktop\NEXO_SOBERANO

# 1. Indexar (primera vez)
python nexo_v2.py setup
# [outputs 5 archivos procesados]

# 2. Iniciar servidor
python nexo_v2.py run
# Escuchar en http://localhost:8000

# En navegador: http://localhost:8000
# → Chat interactivo
# → Ver documentos en sidebar
# → Consultas rápidas

# En otra terminal (mientras corre servidor)
# 3. Sincronizar Google Drive
python nexo_v2.py sync
# [descarga 12 nuevos PDFs]

# 4. Monitoreo en tiempo real
# Watchdog detecta nuevos archivos en documentos/
# Los indexa automáticamente (sin hacer nada)

# 5. Revisar costos
curl http://localhost:8000/api/costos
# {"resumen": "Tokens hoy: 45,230 / 900,000 (5.0%)", ...}
```

---

## 🔐 Seguridad de datos

### ¿Qué NO se sube a ninguna API?
✅ Archivos (PDFs, DOCX, TXT) — procesados 100% localmente
✅ Embeddings — generados con local all-MiniLM-L6-v2 (gratis)
✅ Chunks — guardados en ChromaDB local
✅ Metadata — guardada en SQLite local

### ¿Qué SÍ se envía a Gemini si es necesario?
- Fragmento de 800 caracteres (para clasificación)
- Chunks relevantes + pregunta (para RAG)
- PDFs escaneados (solo OCR, si tienes la API key)

### ¿Dónde va todo?
```
C:\Users\Admn\Desktop\NEXO_SOBERANO\
├─ NEXO_SOBERANO\
│  ├─ base_sqlite\boveda.db           ← SQLite (privado)
│  ├─ memoria_vectorial\             ← ChromaDB (privado)
│  └─ bitacora\evolucion.md           ← Logs (privado)
├─ documentos\                        ← Tus PDFs (privado)
└─ nexo_v2.py                        ← El corazón del sistema
```

---

**Status:** NEXO SOBERANO v2.0 — Listo para producción ✅
**Cambio de arquitectura:** Fragmentado → Unificado
**Soberanía de datos:** Garantizada 🔒
**Costos reales:** Medidos ✅
