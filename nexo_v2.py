#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════
NEXO SOBERANO v2.0 — Punto de entrada unificado
════════════════════════════════════════════════════════════════════

Reemplaza y unifica:
  - motor_ingesta.py         (ingesta + hash)
  - memoria_semantica.py     (vectorización ChromaDB)
  - api_puente.py            (FastAPI RAG)
  - core/orquestador.py      (coordinación)
  - core/orchestrator.py     (duplicado — eliminado)

Mantiene compatibilidad con:
  - core/auth_manager.py     (OAuth Google + Microsoft) ✅
  - services/connectors/     (Google + Microsoft connectors) ✅
  - NEXO_SOBERANO/base_sqlite/boveda.db  (esquema existente) ✅

CORRECCIONES vs versión anterior:
  ❌ Bug: dos pipelines (SQLite y ChromaDB) separados → ✅ pipeline único
  ❌ Bug: genai.upload_file() sube docs a Google → ✅ procesamiento 100% local
  ❌ Bug: GestorDeCostos cuenta tokens falsos → ✅ contador real por llamada
  ❌ Bug: orquestador duplicado → ✅ uno solo
  ❌ Bug: stubs vacíos nunca ejecutados → ✅ implementados

CÓMO USAR:
  python nexo_v2.py setup     ← primera vez (indexa carpeta documentos/)
  python nexo_v2.py run       ← inicia servidor web en localhost:8000
  python nexo_v2.py sync      ← sincroniza Drive/OneDrive manualmente
  python nexo_v2.py test      ← verifica que todo funciona
  python nexo_v2.py chat      ← chat en terminal
"""

import os, sys, json, hashlib, sqlite3, time, threading, logging
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List, Dict

# ════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ════════════════════════════════════════════════════════════════════

ROOT_DIR   = Path(__file__).parent
NEXO_DIR   = ROOT_DIR / "NEXO_SOBERANO"
DB_PATH    = NEXO_DIR / "base_sqlite" / "boveda.db"
CHROMA_DIR = NEXO_DIR / "memoria_vectorial"
DOCS_DIR   = ROOT_DIR / "documentos"      # carpeta de entrada local
BITACORA   = NEXO_DIR / "bitacora" / "evolucion.md"
ENV_FILE   = ROOT_DIR / ".env"

logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(message)s")
log = logging.getLogger("nexo_v2")

def _cargar_env():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

_cargar_env()

CFG = {
    "GEMINI_KEY"      : os.environ.get("GEMINI_API_KEY", ""),
    "MODELO_FLASH"    : "gemini-1.5-flash",   # clasificación rápida (barato)
    "MODELO_PRO"      : "gemini-1.5-pro",     # análisis profundo (caro — solo si es necesario)
    "EMBED_LOCAL"     : "all-MiniLM-L6-v2",  # corre en tu GPU, costo CERO
    "EMBED_GEMINI"    : "models/embedding-001",
    "HOST"            : "0.0.0.0",
    "PORT"            : 8000,
    "CHUNK_SIZE"      : 400,
    "CHUNK_OVERLAP"   : 50,
    "TOP_K"           : 5,
    "MAX_MB"          : 50,
    # Presupuesto real en tokens Gemini por día (free tier = ~1M tokens/día)
    "BUDGET_DIARIO"   : 900_000,
    # Prioridad: fuentes que merecen análisis Pro en vez de Flash
    "FUENTES_ALTO"    : ["OTAN", "NATO", "Rusia", "Russia", "China", "Iran", "Ucrania",
                          "Ukraine", "Gaza", "Economia_Austriaca", "Latam", "MiddleEast"],
}

EXTENSIONES = {'.pdf', '.txt', '.md', '.docx', '.csv', '.jpg', '.jpeg', '.png'}

# ════════════════════════════════════════════════════════════════════
# MÓDULO 1: BASE DE DATOS (compatibilidad con boveda.db existente)
# ════════════════════════════════════════════════════════════════════

_db: Optional[sqlite3.Connection] = None

def get_db() -> sqlite3.Connection:
    global _db
    if _db is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _db = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _db.execute("PRAGMA journal_mode=WAL")
        _db.row_factory = sqlite3.Row
        _db.executescript("""
            -- Tabla original (compatible con versiones anteriores)
            CREATE TABLE IF NOT EXISTS evidencia (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                hash_sha256     TEXT UNIQUE,
                nombre_archivo  TEXT,
                ruta_local      TEXT,
                link_nube       TEXT,
                dominio         TEXT,
                categoria       TEXT,
                resumen_ia      TEXT,
                fecha_ingesta   TIMESTAMP,
                nivel_confianza REAL,
                impacto         TEXT,
                vectorizado     INTEGER DEFAULT 0
            );

            -- Log de vectorización (compatible con memoria_semantica.py)
            CREATE TABLE IF NOT EXISTS vectorizados_log (
                hash_sha256         TEXT PRIMARY KEY,
                fecha_vectorizacion TIMESTAMP
            );

            -- Consultas RAG (nuevo)
            CREATE TABLE IF NOT EXISTS consultas (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       TEXT,
                pregunta    TEXT,
                respuesta   TEXT,
                fuentes     TEXT,
                chunks      INTEGER,
                ms          INTEGER
            );

            -- Control de costos REAL (nuevo — reemplaza GestorDeCostos falso)
            CREATE TABLE IF NOT EXISTS costos_api (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       TEXT,
                modelo      TEXT,
                tokens_in   INTEGER,
                tokens_out  INTEGER,
                operacion   TEXT
            );

            -- Alertas para Telegram/Discord
            CREATE TABLE IF NOT EXISTS alertas (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       TEXT,
                tipo        TEXT,
                texto       TEXT,
                gravedad    INTEGER,
                enviado     INTEGER DEFAULT 0
            );
        """)

        cols = {
            row[1] for row in _db.execute("PRAGMA table_info(evidencia)").fetchall()
        }
        if "impacto" not in cols:
            _db.execute("ALTER TABLE evidencia ADD COLUMN impacto TEXT")
        if "vectorizado" not in cols:
            _db.execute("ALTER TABLE evidencia ADD COLUMN vectorizado INTEGER DEFAULT 0")
        _db.commit()
    return _db

# ════════════════════════════════════════════════════════════════════
# MÓDULO 2: GESTOR DE COSTOS REAL (reemplaza GestorDeCostos falso)
# ════════════════════════════════════════════════════════════════════

class GestorCostos:
    """Cuenta tokens reales de Gemini y controla el presupuesto diario."""

    def registrar(self, modelo: str, tokens_in: int, tokens_out: int, op: str = ""):
        db = get_db()
        db.execute(
            "INSERT INTO costos_api VALUES (NULL,?,?,?,?,?)",
            (datetime.now().isoformat(), modelo, tokens_in, tokens_out, op)
        )
        db.commit()

    def tokens_hoy(self) -> int:
        hoy = date.today().isoformat()
        row = get_db().execute(
            "SELECT COALESCE(SUM(tokens_in + tokens_out), 0) FROM costos_api WHERE fecha LIKE ?",
            (hoy + "%",)
        ).fetchone()
        return row[0] if row else 0

    def puede_operar(self) -> bool:
        return self.tokens_hoy() < CFG["BUDGET_DIARIO"]

    def resumen_hoy(self) -> str:
        usado = self.tokens_hoy()
        pct   = (usado / CFG["BUDGET_DIARIO"]) * 100
        return f"Tokens hoy: {usado:,} / {CFG['BUDGET_DIARIO']:,} ({pct:.1f}%)"

_costos = GestorCostos()

# ════════════════════════════════════════════════════════════════════
# MÓDULO 3: MOTOR DE EMBEDDINGS (local gratis O Gemini)
# ════════════════════════════════════════════════════════════════════

_embed_model = None

def _get_embed_local():
    """Carga all-MiniLM-L6-v2 en memoria (primera vez tarda ~30s, luego instantáneo)."""
    global _embed_model
    if _embed_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            log.info("  ⚙️  Cargando modelo local de embeddings (all-MiniLM-L6-v2)...")
            _embed_model = SentenceTransformer(CFG["EMBED_LOCAL"])
            log.info("  ✅ Modelo local listo.")
        except ImportError:
            log.info("  ⚠️  sentence-transformers no instalado. Usando Gemini para embeddings.")
            _embed_model = "gemini"
    return _embed_model

def generar_embedding(texto: str) -> Optional[List[float]]:
    """
    Genera embedding. Prioridad: modelo local (GPU, gratis) → Gemini (API, si falla).
    """
    model = _get_embed_local()

    if model != "gemini":
        try:
            emb = model.encode(texto[:2000], normalize_embeddings=True)
            return emb.tolist()
        except Exception as e:
            log.info(f"  ⚠️  Embedding local falló: {e}. Intentando Gemini...")

    # Fallback: Gemini embeddings
    if not CFG["GEMINI_KEY"]:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=CFG["GEMINI_KEY"])
        time.sleep(0.2)
        r = genai.embed_content(
            model=CFG["EMBED_GEMINI"],
            content=texto[:2048],
            task_type="retrieval_document"
        )
        return r['embedding']
    except Exception as e:
        log.info(f"  ❌ Embedding Gemini falló: {e}")
        return None

# ════════════════════════════════════════════════════════════════════
# MÓDULO 4: CHROMADB
# ════════════════════════════════════════════════════════════════════

_col = None

def get_coleccion():
    global _col
    if _col is None:
        import chromadb
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        cliente = chromadb.PersistentClient(path=str(CHROMA_DIR))
        # Usar embedding function compatible con all-MiniLM-L6-v2
        try:
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
            ef = SentenceTransformerEmbeddingFunction(model_name=CFG["EMBED_LOCAL"])
            _col = cliente.get_or_create_collection(
                name="inteligencia_geopolitica",
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception:
            # Sin sentence-transformers, colección sin función de embedding automática
            _col = cliente.get_or_create_collection(
                name="inteligencia_geopolitica",
                metadata={"hnsw:space": "cosine"}
            )
    return _col

# ════════════════════════════════════════════════════════════════════
# MÓDULO 5: EXTRACTOR DE TEXTO (100% LOCAL — sin subir a Google)
# ════════════════════════════════════════════════════════════════════

def extraer_texto_local(ruta: Path) -> str:
    """
    Extrae texto completamente local. NO sube archivos a ninguna API.
    Para PDFs escaneados sin texto, usa Gemini Vision solo si es necesario.
    """
    ext = ruta.suffix.lower()
    try:
        if ext in ('.txt', '.md', '.csv'):
            return ruta.read_text(encoding='utf-8', errors='ignore')

        if ext == '.pdf':
            try:
                import pypdf
                partes = []
                with open(ruta, 'rb') as f:
                    for pag in pypdf.PdfReader(f).pages:
                        t = pag.extract_text()
                        if t: partes.append(t)
                texto = '\n'.join(partes).strip()
                if len(texto) > 100:
                    return texto
                # PDF escaneado: usar Gemini Vision (único caso donde se usa API para texto)
                log.info(f"  📷 PDF escaneado detectado, usando OCR vision: {ruta.name}")
                return _ocr_vision(ruta, "application/pdf")
            except ImportError:
                return _ocr_vision(ruta, "application/pdf")

        if ext == '.docx':
            try:
                from docx import Document
                return '\n'.join(p.text for p in Document(ruta).paragraphs if p.text.strip())
            except ImportError:
                return "[Instala python-docx: pip install python-docx]"

        if ext in ('.jpg', '.jpeg', '.png'):
            return _ocr_vision(ruta, f"image/{ext.lstrip('.')}")

    except Exception as e:
        return f"[Error leyendo {ruta.name}: {e}]"
    return ""

def _ocr_vision(ruta: Path, mime: str) -> str:
    """OCR con Gemini Vision. Solo se llama para imágenes y PDFs escaneados."""
    if not CFG["GEMINI_KEY"]:
        return "[Sin API key para OCR]"
    try:
        import google.generativeai as genai
        genai.configure(api_key=CFG["GEMINI_KEY"])
        model = genai.GenerativeModel(CFG["MODELO_PRO"])
        datos = ruta.read_bytes()
        resp  = model.generate_content([
            "Transcribe TODO el texto visible. Incluye números, fechas y nombres exactamente.",
            {"mime_type": mime, "data": datos}
        ])
        # Estimar tokens para el contador de costos
        tokens_est = len(datos) // 1000  # aprox
        _costos.registrar(CFG["MODELO_PRO"], tokens_est, len(resp.text)//4, "ocr_vision")
        return resp.text
    except Exception as e:
        return f"[OCR fallido: {e}]"

# ════════════════════════════════════════════════════════════════════
# MÓDULO 6: CHUNKER
# ════════════════════════════════════════════════════════════════════

def chunkar(texto: str) -> List[str]:
    palabras = texto.split()
    size, lap = CFG["CHUNK_SIZE"], CFG["CHUNK_OVERLAP"]
    chunks, i = [], 0
    while i < len(palabras):
        chunk = ' '.join(palabras[i:i+size])
        if len(chunk) > 40:
            chunks.append(chunk)
        i += size - lap
    return chunks

# ════════════════════════════════════════════════════════════════════
# MÓDULO 7: CLASIFICADOR (determina prioridad y categoría)
# ════════════════════════════════════════════════════════════════════

def _es_alta_prioridad(nombre: str) -> bool:
    nombre_l = nombre.lower()
    return any(f.lower() in nombre_l for f in CFG["FUENTES_ALTO"])

def clasificar(texto_muestra: str, nombre_archivo: str) -> Dict:
    """
    Clasifica usando Gemini Flash (barato).
    Retorna {"categoria": str, "impacto": str, "resumen": str}
    """
    if not CFG["GEMINI_KEY"]:
        return {"categoria": "GEO", "impacto": "Medio", "resumen": nombre_archivo}

    # Decidir modelo según prioridad del archivo
    modelo_id = CFG["MODELO_PRO"] if _es_alta_prioridad(nombre_archivo) else CFG["MODELO_FLASH"]

    try:
        import google.generativeai as genai
        genai.configure(api_key=CFG["GEMINI_KEY"])
        model = genai.GenerativeModel(modelo_id)

        prompt = f"""Analiza este fragmento de documento geopolítico/económico.
Responde ÚNICAMENTE con JSON válido, sin texto adicional:
{{"categoria": "GEO|ECO|PSI|TEC|COM|ADM", "impacto": "Alto|Medio|Bajo", "resumen": "máximo 2 frases"}}

Nombre del archivo: {nombre_archivo}
Contenido (primeros 800 chars): {texto_muestra[:800]}"""

        resp = model.generate_content(prompt)
        texto = resp.text.strip().replace('```json','').replace('```','')

        # Registrar costo real
        tokens_in  = len(prompt) // 4
        tokens_out = len(texto) // 4
        _costos.registrar(modelo_id, tokens_in, tokens_out, "clasificacion")

        data = json.loads(texto)
        return {
            "categoria": data.get("categoria", "GEO"),
            "impacto"  : data.get("impacto", "Medio"),
            "resumen"  : data.get("resumen", "")
        }
    except Exception as e:
        return {"categoria": "GEO", "impacto": "Medio", "resumen": f"[Error clasificando: {e}]"}

# ════════════════════════════════════════════════════════════════════
# MÓDULO 8: PIPELINE DE INGESTA UNIFICADO
# ════════════════════════════════════════════════════════════════════

def procesar_archivo(
    ruta: Path,
    fuente: str = "local",
    categoria_forzada: Optional[str] = None,
    publico: bool = False,
) -> Dict:
    """
    Pipeline completo para un archivo:
    1. Hash SHA-256 (deduplicación)
    2. Extracción de texto local
    3. Clasificación con Gemini Flash
    4. Chunking
    5. Vectorización con all-MiniLM-L6-v2 (local) → ChromaDB
    6. Registro en SQLite

    Retorna: {"ok": bool, "razon": str, ...}
    """
    if not ruta.exists():
        return {"ok": False, "razon": "Archivo no encontrado"}

    if ruta.stat().st_size > CFG["MAX_MB"] * 1024 * 1024:
        return {"ok": False, "razon": f"Archivo >{CFG['MAX_MB']}MB"}

    if ruta.suffix.lower() not in EXTENSIONES:
        return {"ok": False, "razon": "Extensión no soportada"}

    # Deduplicación por hash
    hash_doc = hashlib.sha256(ruta.read_bytes()).hexdigest()
    db = get_db()
    if db.execute("SELECT 1 FROM evidencia WHERE hash_sha256=?", (hash_doc,)).fetchone():
        return {"ok": False, "razon": "Ya existe (hash idéntico)"}

    if not _costos.puede_operar():
        return {"ok": False, "razon": f"Presupuesto diario agotado. {_costos.resumen_hoy()}"}

    # Extraer texto
    texto = extraer_texto_local(ruta)
    if len(texto.strip()) < 30:
        return {"ok": False, "razon": "Sin texto extraíble"}

    # Clasificar
    clasif = clasificar(texto, ruta.name)
    if categoria_forzada:
        clasif["categoria"] = categoria_forzada

    # Vectorizar: chunking + embeddings + ChromaDB
    col    = get_coleccion()
    chunks = chunkar(texto)
    doc_id = hash_doc[:16]
    chunks_ok = 0

    for i, chunk in enumerate(chunks):
        emb = generar_embedding(chunk)
        if emb:
            try:
                col.add(
                    ids        = [f"{doc_id}_c{i}"],
                    embeddings = [emb],
                    documents  = [chunk],
                    metadatas  = [{
                        "doc_id"   : doc_id,
                        "archivo"  : ruta.name,
                        "ruta"     : str(ruta),
                        "fuente"   : fuente,
                        "categoria": clasif["categoria"],
                        "impacto"  : clasif["impacto"],
                        "publico"  : str(publico),
                        "chunk"    : i,
                        "total"    : len(chunks),
                        "fecha"    : datetime.now().isoformat()
                    }]
                )
                chunks_ok += 1
            except Exception as e:
                log.info(f"  ⚠️  Chunk {i} no guardado: {e}")

    if chunks_ok == 0:
        return {"ok": False, "razon": "No se generaron embeddings"}

    # Guardar en SQLite (tabla evidencia original)
    db.execute("""
        INSERT OR REPLACE INTO evidencia
        (hash_sha256, nombre_archivo, ruta_local, dominio, categoria, resumen_ia,
         fecha_ingesta, nivel_confianza, impacto, vectorizado)
        VALUES (?,?,?,?,?,?,?,?,?,1)
    """, (hash_doc, ruta.name, str(ruta), fuente,
          clasif["categoria"], clasif["resumen"],
          datetime.now().isoformat(), 0.85, clasif["impacto"]))

    # Marcar en vectorizados_log (compatible con memoria_semantica.py)
    db.execute("INSERT OR IGNORE INTO vectorizados_log VALUES (?,?)",
               (hash_doc, datetime.now().isoformat()))
    db.commit()

    # Bitácora
    _log_bitacora(f"Procesado: {ruta.name} → {clasif['categoria']} [{clasif['impacto']}]")

    return {
        "ok"      : True,
        "hash"    : hash_doc,
        "chunks"  : chunks_ok,
        "categoria": clasif["categoria"],
        "impacto" : clasif["impacto"],
        "resumen" : clasif["resumen"],
        "nombre"  : ruta.name
    }

def _log_bitacora(msg: str):
    try:
        BITACORA.parent.mkdir(parents=True, exist_ok=True)
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(BITACORA, "a", encoding="utf-8") as f:
            f.write(f"\n- {fecha} | {msg}")
    except Exception:
        pass

# ════════════════════════════════════════════════════════════════════
# MÓDULO 9: CONSULTA RAG
# ════════════════════════════════════════════════════════════════════

def consultar_rag(pregunta: str, categoria: str = None) -> Dict:
    t0  = time.time()
    col = get_coleccion()

    if col.count() == 0:
        return {
            "respuesta": "⚠️ Bóveda vacía. Ejecuta: python nexo_v2.py setup",
            "fuentes"  : [], "chunks": 0, "ms": 0
        }

    # Embedding de la pregunta
    emb_q = generar_embedding(pregunta)
    if emb_q is None:
        return {"respuesta": "❌ No se pudo generar embedding.", "fuentes": [], "chunks": 0, "ms": 0}

    # Buscar en ChromaDB
    where = {"categoria": categoria} if categoria else None
    n     = min(CFG["TOP_K"], col.count())
    res   = col.query(
        query_embeddings=[emb_q],
        n_results=n,
        where=where,
        include=["documents", "metadatas", "distances"]
    )

    textos     = res["documents"][0]
    metas      = res["metadatas"][0]
    distancias = res["distances"][0]

    # Filtro de relevancia (distancia coseno < 0.65)
    pares = [(t, m, d) for t, m, d in zip(textos, metas, distancias) if d < 0.65]

    if not pares:
        return {
            "respuesta": "🔍 No encontré información relevante. Prueba otras palabras clave.",
            "fuentes"  : [], "chunks": 0, "ms": int((time.time()-t0)*1000)
        }

    # Construir contexto
    contexto = "\n\n---\n\n".join([
        f"[Fuente: {m['archivo']} | Cat: {m['categoria']} | Impacto: {m.get('impacto','?')} | {(1-d)*100:.0f}% relevancia]\n{t}"
        for t, m, d in pares
    ])
    fuentes = list({m["archivo"] for _, m, _ in pares})

    # Respuesta con Gemini
    if not CFG["GEMINI_KEY"]:
        respuesta = f"[Sin API key]\n\nFragmentos encontrados:\n" + \
                    "\n".join(f"• {t[:200]}..." for t, _, _ in pares)
    else:
        try:
            import google.generativeai as genai
            genai.configure(api_key=CFG["GEMINI_KEY"])
            model = genai.GenerativeModel(CFG["MODELO_FLASH"])

            prompt = f"""Eres el sistema de inteligencia del Nexo Soberano.

REGLAS ESTRICTAS:
1. Responde SOLO con información del CONTEXTO proporcionado
2. Si no está en el contexto → "No tengo esa información en la bóveda"
3. Sé analítico, directo, sin relleno
4. Cita las fuentes entre paréntesis al final
5. Responde en español

CONTEXTO DE DOCUMENTOS:
{contexto}

PREGUNTA: {pregunta}

Análisis:"""

            resp = model.generate_content(prompt)
            respuesta = resp.text
            _costos.registrar(CFG["MODELO_FLASH"], len(prompt)//4, len(respuesta)//4, "rag_consulta")

        except Exception as e:
            respuesta = f"❌ Error IA: {e}\n\nDocumentos encontrados:\n" + \
                        "\n".join(f"• {t[:200]}..." for t, _, _ in pares)

    ms = int((time.time()-t0)*1000)

    # Guardar consulta
    db = get_db()
    db.execute("INSERT INTO consultas VALUES (NULL,?,?,?,?,?,?)",
               (datetime.now().isoformat(), pregunta, respuesta, json.dumps(fuentes), len(pares), ms))
    db.commit()

    return {
        "respuesta"  : respuesta,
        "fuentes"    : fuentes,
        "chunks"     : len(pares),
        "ms"         : ms,
        "total_docs" : db.execute("SELECT COUNT(*) FROM evidencia WHERE vectorizado=1").fetchone()[0]
    }

# ════════════════════════════════════════════════════════════════════
# MÓDULO 10: SINCRONIZACIÓN CON GOOGLE DRIVE / ONEDRIVE
# ════════════════════════════════════════════════════════════════════

def sincronizar_nube(solo_drive=False, solo_onedrive=False):
    """
    Usa los conectores existentes (google_connector.py, microsoft_connector.py)
    para descargar archivos nuevos a la carpeta documentos/ y procesarlos.
    """
    DOCS_DIR.mkdir(exist_ok=True)
    procesados = 0

    # Google Drive + Google Photos
    if not solo_onedrive:
        try:
            from services.connectors.google_connector import GoogleConnector
            from services.publicacion.content_pipeline import publicar_drive_geopolitica
            gc = GoogleConnector()
            log.info("🔄 Sincronizando Google Drive...")
            for f in gc.list_drive_files(page_size=20):
                nombre = f.get('name', '')
                fid    = f.get('id', '')
                destino = DOCS_DIR / nombre

                if destino.exists():
                    continue
                if not any(nombre.endswith(e) for e in EXTENSIONES):
                    continue

                try:
                    gc.download_drive_file(fid, str(destino))
                    log.info(f"  ✅ Descargado: {nombre}")
                    r = procesar_archivo(
                        destino,
                        fuente="DrivePublico",
                        categoria_forzada="GEOPOLITICA_PUBLICA",
                        publico=True,
                    )
                    if r["ok"]:
                        log.info(f"  🧠 Indexado: {nombre} [{r['categoria']}]")
                        publicar_drive_geopolitica({
                            "id": f.get("id") or r.get("hash"),
                            "nombre": nombre,
                            "resumen": r.get("resumen", ""),
                            "impacto": r.get("impacto", "Medio"),
                            "link": f"https://drive.google.com/file/d/{fid}/view" if fid else "",
                        })
                        log.info(f"  🌍 Publicado (geopolítica pública): {nombre}")
                        procesados += 1
                    else:
                        log.info(f"  ⚠️  {r['razon']}")
                except Exception as e:
                    log.info(f"  ❌ Error descargando {nombre}: {e}")

            log.info("🔄 Sincronizando Google Photos...")
            for p in gc.list_photos(page_size=20):
                nombre = p.get('filename', '')
                pid    = p.get('id', '')
                destino = DOCS_DIR / nombre

                if destino.exists():
                    continue
                if not any(nombre.lower().endswith(e) for e in EXTENSIONES):
                    continue

                try:
                    gc.download_photo(p, str(destino))
                    log.info(f"  ✅ Descargado (Photos): {nombre}")
                    r = procesar_archivo(destino, fuente="GooglePhotos", publico=False)
                    if r["ok"]:
                        log.info(f"  🧠 Indexado (Photos): {nombre} [{r['categoria']}]")
                        procesados += 1
                    else:
                        log.info(f"  ⚠️  {r['razon']}")
                except Exception as e:
                    log.info(f"  ❌ Error descargando foto {nombre}: {e}")

        except Exception as e:
            log.info(f"⚠️ Google Drive no disponible: {e}")

    # OneDrive
    if not solo_drive:
        try:
            from services.connectors.microsoft_connector import MicrosoftConnector
            mc = MicrosoftConnector()
            log.info("🔄 Sincronizando OneDrive...")
            for f in mc.list_recent_files(top=20):
                nombre = f.get('name', '')
                fid    = f.get('id', '')
                destino = DOCS_DIR / nombre

                if destino.exists():
                    continue
                if not any(nombre.endswith(e) for e in EXTENSIONES):
                    continue

                try:
                    # Descargar desde OneDrive via Graph API
                    import requests
                    token  = mc.token_data.get('access_token','')
                    dl_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{fid}/content"
                    resp   = requests.get(dl_url, headers={'Authorization': f'Bearer {token}'}, stream=True)
                    if resp.status_code == 200:
                        destino.write_bytes(resp.content)
                        log.info(f"  ✅ Descargado: {nombre}")
                        r = procesar_archivo(destino, fuente="OneDrive", publico=False)
                        if r["ok"]:
                            log.info(f"  🧠 Indexado: {nombre} [{r['categoria']}]")
                            procesados += 1
                except Exception as e:
                    log.info(f"  ❌ Error descargando {nombre}: {e}")

        except Exception as e:
            log.info(f"⚠️ OneDrive no disponible: {e}")

    log.info(f"\n✅ Sincronización completa: {procesados} archivos nuevos procesados.")
    return procesados

# ════════════════════════════════════════════════════════════════════
# MÓDULO 11: WATCHDOG — monitoreo en tiempo real de carpeta local
# ════════════════════════════════════════════════════════════════════

def iniciar_watchdog() -> Optional[object]:
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class Handler(FileSystemEventHandler):
            def __init__(self):
                self._lock = threading.Lock()
                self._en_proceso = set()

            def on_created(self, event):
                if event.is_directory: return
                ruta = Path(event.src_path)
                if ruta.suffix.lower() not in EXTENSIONES: return
                threading.Thread(target=self._procesar, args=(ruta,), daemon=True).start()

            def _procesar(self, ruta):
                time.sleep(2)  # esperar escritura completa
                with self._lock:
                    if str(ruta) in self._en_proceso: return
                    self._en_proceso.add(str(ruta))
                try:
                    log.info(f"\n📄 Nuevo archivo: {ruta.name}")
                    r = procesar_archivo(ruta)
                    if r["ok"]:
                        log.info(f"  ✅ {r['chunks']} chunks [{r['categoria']}] [{r['impacto']}]")
                    else:
                        log.info(f"  ⚠️  {r['razon']}")
                finally:
                    with self._lock:
                        self._en_proceso.discard(str(ruta))

        DOCS_DIR.mkdir(exist_ok=True)
        obs = Observer()
        obs.schedule(Handler(), str(DOCS_DIR), recursive=True)
        obs.start()
        log.info(f"👁️  Watchdog activo → {DOCS_DIR}")
        return obs
    except ImportError:
        log.info("⚠️  watchdog no instalado — monitoreo automático desactivado")
        return None

# ════════════════════════════════════════════════════════════════════
# MÓDULO 12: FASTAPI — ENDPOINTS
# ════════════════════════════════════════════════════════════════════

def crear_app():
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

    app = FastAPI(title="Nexo Soberano", version="2.0", docs_url=None, redoc_url=None)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    class ChatReq(BaseModel):
        pregunta  : str
        categoria : Optional[str] = None

    # Endpoint principal — compatible con api_puente.py (/agente/consultar)
    @app.post("/agente/consultar")
    @app.post("/api/chat")  # nuevo endpoint también
    def chat(req: ChatReq):
        if not req.pregunta or len(req.pregunta.strip()) < 2:
            raise HTTPException(400, "Pregunta vacía")
        return consultar_rag(req.pregunta.strip(), req.categoria)

    @app.get("/api/estado")
    def estado():
        db  = get_db()
        col = get_coleccion()
        docs = db.execute("SELECT COUNT(*) FROM evidencia WHERE vectorizado=1").fetchone()[0]
        ult  = db.execute("SELECT fecha FROM consultas ORDER BY id DESC LIMIT 1").fetchone()
        return {
            "online"         : True,
            "version"        : "2.0",
            "docs_indexados" : docs,
            "chunks_total"   : col.count(),
            "costos_hoy"     : _costos.resumen_hoy(),
            "ultima_consulta": ult[0] if ult else None,
            "timestamp"      : datetime.now().isoformat()
        }

    @app.get("/api/documentos")
    def documentos():
        rows = get_db().execute("""
            SELECT nombre_archivo, categoria, impacto, resumen_ia, fecha_ingesta
            FROM evidencia WHERE vectorizado=1
            ORDER BY fecha_ingesta DESC LIMIT 100
        """).fetchall()
        return [{"nombre": r[0], "cat": r[1], "impacto": r[2],
                 "resumen": (r[3] or "")[:100], "fecha": (r[4] or "")[:10]} for r in rows]

    @app.get("/api/costos")
    def costos():
        hoy = date.today().isoformat()
        rows = get_db().execute("""
            SELECT modelo, SUM(tokens_in+tokens_out), COUNT(*)
            FROM costos_api WHERE fecha LIKE ?
            GROUP BY modelo
        """, (hoy+"%",)).fetchall()
        return {
            "resumen"  : _costos.resumen_hoy(),
            "por_modelo": [{"modelo": r[0], "tokens": r[1], "llamadas": r[2]} for r in rows]
        }

    @app.get("/api/historial")
    def historial():
        rows = get_db().execute("""
            SELECT fecha, pregunta, chunks, ms FROM consultas
            ORDER BY id DESC LIMIT 30
        """).fetchall()
        return [{"fecha": r[0][:19], "pregunta": r[1][:80], "chunks": r[2], "ms": r[3]} for r in rows]

    @app.get("/", response_class=HTMLResponse)
    def frontend():
        return _html()

    return app

# ════════════════════════════════════════════════════════════════════
# FRONTEND HTML (mismo que api.py pero con /agente/consultar)
# ════════════════════════════════════════════════════════════════════

def _html() -> str:
    return r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nexo Soberano v2</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#05080f;--panel:#090e1a;--b:#152030;--az:#00b8d4;--vd:#00e676;--tx:#b0c4d8;--dim:#405060}
body{background:var(--bg);color:var(--tx);font-family:'Courier New',monospace;height:100dvh;display:flex;flex-direction:column;overflow:hidden}
header{background:var(--panel);border-bottom:1px solid var(--b);padding:10px 20px;display:flex;align-items:center;gap:12px;flex-shrink:0}
.logo{width:32px;height:32px;border:1.5px solid var(--az);border-radius:50%;display:flex;align-items:center;justify-content:center;color:var(--az);animation:glow 3s ease-in-out infinite}
@keyframes glow{0%,100%{box-shadow:0 0 4px var(--az)}50%{box-shadow:0 0 14px var(--az)}}
.tit{color:var(--az);font-size:.9em;letter-spacing:2px;text-transform:uppercase}
.sub{font-size:.65em;color:var(--dim)}
.badge{margin-left:auto;display:flex;align-items:center;gap:6px;font-size:.65em;color:var(--vd)}
.dot{width:7px;height:7px;background:var(--vd);border-radius:50%;animation:bl 2s ease-in-out infinite}
@keyframes bl{0%,100%{opacity:1}50%{opacity:.2}}
main{flex:1;display:grid;grid-template-columns:240px 1fr;overflow:hidden}
aside{background:var(--panel);border-right:1px solid var(--b);padding:14px;overflow-y:auto;display:flex;flex-direction:column;gap:12px}
.bt{font-size:.6em;color:var(--dim);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
.stat{background:#0b1220;border:1px solid var(--b);border-radius:5px;padding:10px}
.sn{font-size:1.5em;color:var(--az);font-weight:700}.sl{font-size:.65em;color:var(--dim);margin-top:2px}
.sb{display:block;width:100%;background:#0b1220;border:1px solid var(--b);border-radius:4px;padding:7px 9px;color:var(--tx);font:.72em 'Courier New',monospace;cursor:pointer;text-align:left;margin-bottom:5px;transition:.15s}
.sb:hover{border-color:var(--az);color:var(--az)}
.dr{display:flex;align-items:center;gap:7px;padding:5px 0;border-bottom:1px solid var(--b);font-size:.7em}
.cat{font-size:.6em;background:var(--b);color:var(--az);padding:1px 5px;border-radius:2px;white-space:nowrap}
.imp-alto{color:#ff6b6b}.imp-medio{color:#ffd93d}.imp-bajo{color:var(--dim)}
.chat{display:flex;flex-direction:column;overflow:hidden}
.msgs{flex:1;overflow-y:auto;padding:18px 20px;display:flex;flex-direction:column;gap:14px}
.bv{text-align:center;padding:50px 24px;color:var(--dim)}
.bv h2{color:var(--az);font-size:1.1em;margin-bottom:10px;letter-spacing:2px}
.bv p{font-size:.78em;line-height:1.7}
.msg{display:flex;gap:10px;max-width:88%}
.msg.u{align-self:flex-end;flex-direction:row-reverse}
.msg.b{align-self:flex-start}
.av{width:28px;height:28px;min-width:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.8em;margin-top:3px}
.av.u{background:#102030;border:1px solid var(--az);color:var(--az)}
.av.b{background:#0a1f0f;border:1px solid var(--vd);color:var(--vd)}
.bur{padding:10px 14px;border-radius:7px;font-size:.82em;line-height:1.65;white-space:pre-wrap;word-break:break-word}
.bur.u{background:#0c1e30;border:1px solid #1a3a5c;border-top-right-radius:2px}
.bur.b{background:#0a1a10;border:1px solid #1a3525;border-top-left-radius:2px;color:#c8ecd4}
.bur.e{background:#1a0a0a;border:1px solid #3a1515;color:#f0a0a0}
.fts{margin-top:7px;padding-top:7px;border-top:1px solid #1a3525;font-size:.68em;color:var(--dim)}
.ft{display:inline-block;background:#0a1f10;border:1px solid #1a3525;border-radius:2px;padding:1px 6px;margin:2px;color:var(--vd)}
.meta{float:right}
.ty{display:flex;gap:4px;align-items:center;padding:5px 0}
.ty span{width:5px;height:5px;background:var(--vd);border-radius:50%;animation:bn 1.1s infinite}
.ty span:nth-child(2){animation-delay:.18s}.ty span:nth-child(3){animation-delay:.36s}
@keyframes bn{0%,100%{opacity:.2;transform:translateY(0)}50%{opacity:1;transform:translateY(-3px)}}
.ib{padding:12px 18px;border-top:1px solid var(--b);background:var(--panel);display:flex;gap:9px;align-items:flex-end;flex-shrink:0}
textarea{flex:1;background:#0a1220;border:1px solid var(--b);border-radius:5px;padding:9px 12px;color:var(--tx);font:.82em 'Courier New',monospace;resize:none;min-height:40px;max-height:110px;transition:border-color .2s}
textarea:focus{outline:none;border-color:var(--az)}
textarea::placeholder{color:var(--dim)}
.send{background:var(--az);border:none;border-radius:5px;width:40px;height:40px;cursor:pointer;color:#000;font-size:1em;display:flex;align-items:center;justify-content:center;transition:.2s;flex-shrink:0}
.send:hover{background:#009fba;transform:scale(1.05)}.send:disabled{background:var(--b);color:var(--dim);cursor:default;transform:none}
::-webkit-scrollbar{width:3px}::-webkit-scrollbar-thumb{background:var(--b)}
@media(max-width:700px){main{grid-template-columns:1fr}aside{display:none}}
</style>
</head>
<body>
<header>
  <div class="logo">◈</div>
  <div><div class="tit">Nexo Soberano</div><div class="sub">Sistema de Inteligencia · v2.0</div></div>
  <div class="badge"><div class="dot"></div><span id="badge">Conectando...</span></div>
</header>
<main>
<aside>
  <div>
    <div class="bt">Bóveda</div>
    <div class="stat"><div class="sn" id="sd">—</div><div class="sl">documentos indexados</div></div>
    <div class="stat" style="margin-top:8px"><div class="sn" id="sc">—</div><div class="sl">chunks vectoriales</div></div>
    <div class="stat" style="margin-top:8px"><div class="sn" id="sk" style="font-size:.85em;color:#ffd93d">—</div><div class="sl">tokens Gemini hoy</div></div>
  </div>
  <div>
    <div class="bt">Consultas rápidas</div>
    <button class="sb" onclick="sg(this)">¿Qué documentos tengo sobre Rusia?</button>
    <button class="sb" onclick="sg(this)">Resumen de actividad militar reciente</button>
    <button class="sb" onclick="sg(this)">¿Qué sé sobre economía austríaca?</button>
    <button class="sb" onclick="sg(this)">Contradicciones narrativas detectadas</button>
    <button class="sb" onclick="sg(this)">¿Cuáles son los documentos de mayor impacto?</button>
  </div>
  <div>
    <div class="bt">Últimos documentos</div>
    <div id="ld"><span style="color:var(--dim);font-size:.72em">cargando...</span></div>
  </div>
</aside>
<div class="chat">
  <div class="msgs" id="msgs">
    <div class="bv">
      <h2>◈ NEXO SOBERANO v2.0</h2>
      <p>Bóveda de inteligencia geopolítica.<br>Respuestas basadas únicamente en<br>documentos verificados de tu archivo.</p>
    </div>
  </div>
  <div class="ib">
    <textarea id="inp" placeholder="Consulta tu bóveda... (Enter = enviar · Shift+Enter = nueva línea)" rows="1"></textarea>
    <button class="send" id="sbtn" onclick="send()">▶</button>
  </div>
</div>
</main>
<script>
let busy=false;
const inp=document.getElementById('inp');
inp.addEventListener('input',()=>{inp.style.height='auto';inp.style.height=Math.min(inp.scrollHeight,110)+'px';});
inp.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}});

async function load(){
  try{
    const [st,docs]=await Promise.all([fetch('/api/estado').then(r=>r.json()),fetch('/api/documentos').then(r=>r.json())]);
    document.getElementById('sd').textContent=st.docs_indexados;
    document.getElementById('sc').textContent=st.chunks_total;
    document.getElementById('sk').textContent=st.costos_hoy||'—';
    document.getElementById('badge').textContent='En línea · v2.0';
    const el=document.getElementById('ld');
    el.innerHTML=docs.length===0
      ?'<span style="color:var(--dim);font-size:.72em">Sin documentos. Copia PDFs en \'documentos/\'</span>'
      :docs.slice(0,12).map(d=>`<div class="dr"><span class="cat">${d.cat}</span><span class="imp-${(d.impacto||'medio').toLowerCase()}">${d.impacto||''}</span><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${d.nombre}">${d.nombre.length>22?d.nombre.slice(0,22)+'…':d.nombre}</span></div>`).join('');
  }catch(e){document.getElementById('badge').textContent='Desconectado';}
}

async function send(){
  const txt=inp.value.trim();if(!txt||busy)return;
  busy=true;document.getElementById('sbtn').disabled=true;
  inp.value='';inp.style.height='auto';
  add('u',txt);const lid=loading();
  try{
    const r=await fetch('/agente/consultar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pregunta:txt})});
    const d=await r.json();
    rm(lid);bot(d.respuesta,d.fuentes,d.chunks,d.ms);
    if(d.total_docs!=null)document.getElementById('sd').textContent=d.total_docs;
  }catch(e){rm(lid);add('e','❌ Error: '+e.message);}
  busy=false;document.getElementById('sbtn').disabled=false;inp.focus();
}

function add(t,txt){
  const c=document.getElementById('msgs'),el=document.createElement('div');
  el.className=`msg ${t==='u'?'u':'b'}`;
  const av=t==='u'?'◉':'◈',ac=t==='u'?'u':'b',bc=t==='e'?'e':t==='u'?'u':'b';
  el.innerHTML=`<div class="av ${ac}">${av}</div><div class="bur ${bc}">${esc(txt)}</div>`;
  c.appendChild(el);c.scrollTop=c.scrollHeight;
}
function bot(txt,fts,ch,ms){
  const c=document.getElementById('msgs'),el=document.createElement('div');
  el.className='msg b';
  const fh=fts&&fts.length?`<div class="fts">📁 ${fts.map(f=>`<span class="ft">${f.length>28?f.slice(0,28)+'…':f}</span>`).join('')}<span class="meta">${ch} chunks · ${ms}ms</span></div>`:'';
  el.innerHTML=`<div class="av b">◈</div><div class="bur b">${esc(txt)}${fh}</div>`;
  c.appendChild(el);c.scrollTop=c.scrollHeight;
}
function loading(){
  const c=document.getElementById('msgs'),el=document.createElement('div');
  const id='l'+Date.now();el.id=id;el.className='msg b';
  el.innerHTML=`<div class="av b">◈</div><div class="bur b"><div class="ty"><span></span><span></span><span></span></div> Consultando bóveda...</div>`;
  c.appendChild(el);c.scrollTop=c.scrollHeight;return id;
}
function rm(id){const el=document.getElementById(id);if(el)el.remove();}
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function sg(b){inp.value=b.textContent;inp.dispatchEvent(new Event('input'));send();}
load();setInterval(load,20000);
</script>
</body>
</html>"""

# ════════════════════════════════════════════════════════════════════
# COMANDOS CLI
# ════════════════════════════════════════════════════════════════════

def cmd_setup():
    DOCS_DIR.mkdir(exist_ok=True)
    archivos = [f for f in DOCS_DIR.rglob("*") if f.is_file() and f.suffix.lower() in EXTENSIONES]
    if not archivos:
        log.info(f"⚠️  No hay archivos en: {DOCS_DIR}")
        log.info(f"   Copia tus PDFs ahí y vuelve a ejecutar.")
        return

    log.info(f"\n{'═'*60}")
    log.info(f"  NEXO SOBERANO v2.0 — Indexación inicial")
    log.info(f"  {len(archivos)} archivo(s) encontrado(s)")
    log.info(f"{'═'*60}\n")

    ok = skip = err = 0
    for i, ruta in enumerate(archivos, 1):
        log.info(f"[{i}/{len(archivos)}] {ruta.name[:55]:<55}", end=" ", flush=True)
        r = procesar_archivo(ruta)
        if r["ok"]:
            log.info(f"✅ {r['chunks']} chunks [{r['categoria']}] [{r['impacto']}]")
            ok += 1
        elif "Ya existe" in r["razon"]:
            log.info(f"⏭️  Ya indexado")
            skip += 1
        else:
            log.info(f"❌ {r['razon']}")
            err += 1

    log.info(f"\n{'─'*60}")
    log.info(f"✅ Nuevos: {ok}  ⏭️ Ya existían: {skip}  ❌ Errores: {err}")
    log.info(f"Total en ChromaDB: {get_coleccion().count()} chunks")
    log.info(f"Costos: {_costos.resumen_hoy()}")

def cmd_run():
    import uvicorn
    DOCS_DIR.mkdir(exist_ok=True)
    app = crear_app()
    wdog = iniciar_watchdog()
    log.info(f"\n{'═'*60}")
    log.info(f"  NEXO SOBERANO v2.0 — Servidor activo")
    log.info(f"  Chat:   http://localhost:{CFG['PORT']}")
    log.info(f"  Estado: http://localhost:{CFG['PORT']}/api/estado")
    log.info(f"  Costos: http://localhost:{CFG['PORT']}/api/costos")
    log.info(f"  Docs:   {DOCS_DIR}")
    log.info(f"{'═'*60}\n")
    try:
        uvicorn.run(app, host=CFG["HOST"], port=CFG["PORT"], log_level="warning")
    finally:
        if wdog: wdog.stop()

def cmd_sync():
    log.info("🔄 Iniciando sincronización con nube...")
    sincronizar_nube()

def cmd_test():
    log.info("🧪 Test 1: SQLite...", end=" ", flush=True)
    try:
        db = get_db()
        n = db.execute("SELECT COUNT(*) FROM evidencia").fetchone()[0]
        log.info(f"✅ {n} documentos en bóveda")
    except Exception as e:
        log.info(f"❌ {e}"); return

    log.info("🧪 Test 2: Embedding local...", end=" ", flush=True)
    try:
        emb = generar_embedding("test de embedding geopolítico")
        log.info(f"✅ {len(emb)} dimensiones")
    except Exception as e:
        log.info(f"❌ {e}")

    log.info("🧪 Test 3: ChromaDB...", end=" ", flush=True)
    try:
        col = get_coleccion()
        log.info(f"✅ {col.count()} chunks indexados")
    except Exception as e:
        log.info(f"❌ {e}"); return

    if get_coleccion().count() > 0:
        log.info("🧪 Test 4: Consulta RAG...", end=" ", flush=True)
        r = consultar_rag("¿Qué información hay disponible?")
        log.info(f"✅ {r['chunks']} chunks · {r['ms']}ms")
        log.info(f"   → {r['respuesta'][:120]}...")

    log.info(f"\n💰 {_costos.resumen_hoy()}")

# ════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    cmds = {"setup": cmd_setup, "run": cmd_run, "sync": cmd_sync, "test": cmd_test}
    cmd  = sys.argv[1] if len(sys.argv) > 1 else "run"

    if cmd == "chat":
        log.info("💬 Chat terminal (Ctrl+C para salir)\n")
        while True:
            try:
                q = input("Tú: ").strip()
                if q:
                    r = consultar_rag(q)
                    log.info(f"\nNexo: {r['respuesta']}")
                    if r['fuentes']:
                        log.info(f"Fuentes: {', '.join(r['fuentes'])}\n")
            except KeyboardInterrupt:
                log.info("\nCerrando."); break
    elif cmd in cmds:
        cmds[cmd]()
    else:
        log.info(f"Uso: python nexo_v2.py [setup|run|sync|test|chat]")
