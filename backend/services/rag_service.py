"""
RAG Service — Motor de búsqueda + respuesta IA
Extrae lógica principal de nexo_v2.py
"""

import sqlite3
import time
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend import config
from backend.services.cost_manager import get_cost_manager

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════
# INICIALIZACIÓN BD
# ════════════════════════════════════════════════════════════════════

def get_db() -> sqlite3.Connection:
    """Conexión a SQLite con WAL"""
    conn = sqlite3.connect(str(config.DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn

def ensure_db_schema():
    """Asegura que existan las tablas necesarias"""
    conn = get_db()
    conn.executescript("""
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

        CREATE TABLE IF NOT EXISTS consultas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha       TEXT,
            pregunta    TEXT,
            respuesta   TEXT,
            fuentes     TEXT,
            chunks      INTEGER,
            ms          INTEGER
        );
    """)
    conn.commit()
    conn.close()

ensure_db_schema()

# ════════════════════════════════════════════════════════════════════
# EMBEDDINGS
# ════════════════════════════════════════════════════════════════════

_embed_model = None

def get_embed_model():
    """Carga modelo de embeddings local (all-MiniLM-L6-v2)"""
    global _embed_model
    if _embed_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embed_model = SentenceTransformer(config.EMBED_LOCAL)
            logger.info("✅ Modelo de embeddings local cargado")
        except ImportError:
            logger.warning("⚠️ sentence-transformers no disponible, usando Gemini")
            _embed_model = "gemini"
    return _embed_model

def generar_embedding(texto: str) -> Optional[List[float]]:
    """Genera embedding del texto. Prioridad: local → Gemini fallback"""
    model = get_embed_model()

    if model != "gemini":
        try:
            emb = model.encode(texto[:2000], normalize_embeddings=True)
            return emb.tolist()
        except Exception as e:
            logger.warning(f"Error en embedding local: {e}, intentando Gemini...")

    # Fallback: Gemini
    if not config.GEMINI_API_KEY:
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=config.GEMINI_API_KEY)
        r = genai.embed_content(
            model=config.EMBED_GEMINI,
            content=texto[:2048],
            task_type="retrieval_document"
        )
        return r.get('embedding')
    except Exception as e:
        logger.error(f"Error en embedding Gemini: {e}")
        return None

# ════════════════════════════════════════════════════════════════════
# CHROMADB
# ════════════════════════════════════════════════════════════════════

_coleccion = None

def get_coleccion():
    """Obtiene o crea colección ChromaDB"""
    global _coleccion
    if _coleccion is None:
        try:
            import chromadb
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

            config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
            cliente = chromadb.PersistentClient(path=str(config.CHROMA_DIR))

            try:
                ef = SentenceTransformerEmbeddingFunction(model_name=config.EMBED_LOCAL)
                _coleccion = cliente.get_or_create_collection(
                    name="inteligencia_geopolitica",
                    embedding_function=ef,
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception:
                _coleccion = cliente.get_or_create_collection(
                    name="inteligencia_geopolitica",
                    metadata={"hnsw:space": "cosine"}
                )
            logger.info("✅ ChromaDB cargado")
        except Exception as e:
            logger.error(f"Error inicializando ChromaDB: {e}")
            _coleccion = None
    return _coleccion

# ════════════════════════════════════════════════════════════════════
# RAG SERVICE
# ════════════════════════════════════════════════════════════════════

class RAGService:
    """Motor unificado de RAG"""

    def __init__(self):
        self.cost_manager = get_cost_manager()

    def consultar(self, pregunta: str, categoria: Optional[str] = None) -> Dict:
        """
        Consulta la bóveda de documentosy genera respuesta con IA.
        
        Args:
            pregunta: Pregunta del usuario
            categoria: Filtro por categoría (opcional)
            
        Returns:
            {
                "respuesta": str,
                "fuentes": List[str],
                "chunks_usados": int,
                "ms": int,
                "total_docs": int,
                "presupuesto": {...}
            }
        """
        t0 = time.time()
        col = get_coleccion()

        # Sin documentos
        if col is None or col.count() == 0:
            return {
                "respuesta": "⚠️ Bóveda vacía. Ejecuta: python nexo_v2.py setup",
                "fuentes": [],
                "chunks_usados": 0,
                "ms": int((time.time() - t0) * 1000),
                "total_docs": 0,
                "presupuesto": self.cost_manager.estado(),
                "error": True,
            }

        # Generar embedding de pregunta
        emb_q = generar_embedding(pregunta)
        if emb_q is None:
            return {
                "respuesta": "❌ No se pudo generar embedding",
                "fuentes": [],
                "chunks_usados": 0,
                "ms": int((time.time() - t0) * 1000),
                "total_docs": col.count(),
                "presupuesto": self.cost_manager.estado(),
                "error": True,
            }

        # Buscar en ChromaDB
        try:
            where = {"categoria": categoria} if categoria else None
            n = min(config.TOP_K, col.count())
            res = col.query(
                query_embeddings=[emb_q],
                n_results=n,
                where=where,
                include=["documents", "metadatas", "distances"]
            )

            textos = res["documents"][0] if res["documents"] else []
            metas = res["metadatas"][0] if res["metadatas"] else []
            distancias = res["distances"][0] if res["distances"] else []
        except Exception as e:
            logger.error(f"Error en ChromaDB query: {e}")
            return {
                "respuesta": f"❌ Error en búsqueda: {str(e)}",
                "fuentes": [],
                "chunks_usados": 0,
                "ms": int((time.time() - t0) * 1000),
                "total_docs": col.count() if col else 0,
                "presupuesto": self.cost_manager.estado(),
                "error": True,
            }

        # Filtrar por relevancia
        pares = [
            (t, m, d)
            for t, m, d in zip(textos, metas, distancias)
            if d < config.RELEVANCE_THRESHOLD
        ]

        if not pares:
            return {
                "respuesta": "🔍 No encontré información relevante. Prueba otras palabras clave.",
                "fuentes": [],
                "chunks_usados": 0,
                "ms": int((time.time() - t0) * 1000),
                "total_docs": col.count() if col else 0,
                "presupuesto": self.cost_manager.estado(),
            }

        # Construir contexto
        contexto = "\n\n---\n\n".join([
            f"[Fuente: {m.get('archivo', '?')} | "
            f"Cat: {m.get('categoria', '?')} | "
            f"Impacto: {m.get('impacto', '?')} | "
            f"{(1-d)*100:.0f}% relevancia]\n{t}"
            for t, m, d in pares
        ])
        fuentes = list({m.get("archivo", "?") for _, m, _ in pares})

        # Generar respuesta
        respuesta = self._generar_respuesta(pregunta, contexto, pares)

        ms = int((time.time() - t0) * 1000)

        # Guardar consulta
        try:
            db = get_db()
            db.execute(
                "INSERT INTO consultas (fecha, pregunta, respuesta, fuentes, chunks, ms) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    datetime.now().isoformat(),
                    pregunta,
                    respuesta,
                    json.dumps(fuentes),
                    len(pares),
                    ms
                )
            )
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Error guardando consulta: {e}")

        # Obtener total de docs indexados
        try:
            db = get_db()
            total_docs = db.execute(
                "SELECT COUNT(*) FROM evidencia WHERE vectorizado=1"
            ).fetchone()[0]
            db.close()
        except Exception:
            total_docs = col.count() if col else 0

        return {
            "respuesta": respuesta,
            "fuentes": fuentes,
            "chunks_usados": len(pares),
            "ms": ms,
            "total_docs": total_docs,
            "presupuesto": self.cost_manager.estado(),
        }

    def _generar_respuesta(self, pregunta: str, contexto: str, pares: List) -> str:
        """Genera respuesta usando Gemini si está disponible"""
        
        # Sin API key
        if not config.GEMINI_API_KEY:
            fragmentos = "\n".join(
                f"• {t[:150]}..." for t, _, _ in pares
            )
            return f"[Sin Gemini API clave]\n\nFragmentos encontrados:\n{fragmentos}"

        try:
            import google.generativeai as genai
            genai.configure(api_key=config.GEMINI_API_KEY)
            model = genai.GenerativeModel(config.MODELO_FLASH)

            prompt = f"""Eres el asistente de inteligencia del Nexo Soberano.

REGLAS:
1. Responde SOLO con info del CONTEXTO
2. Si no está → "No tengo esa información en la bóveda"
3. Sé analítico, directo, sin relleno
4. Cita fuentes en paréntesis
5. Responde en español

CONTEXTO:
{contexto}

PREGUNTA: {pregunta}

Análisis:"""

            resp = model.generate_content(prompt)
            respuesta = resp.text

            # Registrar costo real
            tokens_in = len(prompt) // 4
            tokens_out = len(respuesta) // 4
            self.cost_manager.registrar(
                config.MODELO_FLASH,
                tokens_in,
                tokens_out,
                "rag_consulta"
            )

            return respuesta

        except Exception as e:
            logger.error(f"Error generando respuesta: {e}")
            fragmentos = "\n".join(
                f"• {t[:150]}..." for t, _, _ in pares
            )
            return f"❌ Error IA: {str(e)}\n\nFragmentos encontrados:\n{fragmentos}"

    def estado(self) -> Dict:
        """Estado actual del sistema"""
        col = get_coleccion()
        db = get_db()

        try:
            total_docs = db.execute(
                "SELECT COUNT(*) FROM evidencia WHERE vectorizado=1"
            ).fetchone()[0]
            total_chunks = db.execute(
                "SELECT COUNT(*) FROM evidencia WHERE vectorizado=1"
            ).fetchone()[0]  # Aproximado
        except Exception:
            total_docs = col.count() if col else 0
            total_chunks = 0

        db.close()

        return {
            "status": "ok",
            "rag_loaded": col is not None,
            "total_documentos": total_docs,
            "total_chunks": total_chunks,
            "coleccion_items": col.count() if col else 0,
            "embeddings": config.EMBED_LOCAL,
            "presupuesto": self.cost_manager.estado(),
        }


# Instancia global
_rag_service: Optional[RAGService] = None

def get_rag_service() -> RAGService:
    """Obtiene o crea el servicio RAG"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
