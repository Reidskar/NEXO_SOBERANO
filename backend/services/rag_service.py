
# RAG Service — Motor de búsqueda + respuesta IA
# Extrae lógica principal de nexo_v2.py

import sqlite3
import time
import json
import requests
from utils.ai_core import get_logger, get_gemini_embedding_model, embed_text_gemini2, embed_query_gemini2
from datetime import datetime
from typing import Optional, List, Dict, Mapping
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend import config
from backend.services.cost_manager import get_cost_manager
from backend.services.unified_cost_tracker import get_cost_tracker

logger = get_logger("rag_service")

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

def get_embed_model():
    """Carga modelo de embeddings usando Gemini centralizado (legacy)"""
    return get_gemini_embedding_model(config.GEMINI_API_KEY)

def generar_embedding(texto: str) -> Optional[List[float]]:
    """Genera embedding con Gemini Embedding 2 (gemini-embedding-exp-03-07)."""
    result = embed_text_gemini2(texto, api_key=config.GEMINI_API_KEY)
    if result:
        return result
    logger.warning("Gemini Embedding 2 falló — embedding no disponible")
    return None

def generar_embedding_query(texto: str) -> Optional[List[float]]:
    """Genera embedding de búsqueda (RETRIEVAL_QUERY) con Gemini Embedding 2."""
    result = embed_query_gemini2(texto, api_key=config.GEMINI_API_KEY)
    if result:
        return result
    logger.warning("Gemini Embedding 2 (query) falló — embedding no disponible")
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
                _coleccion = cliente.get_or_create_collection(
                    name="inteligencia_geopolitica",
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

        # Generar embedding de pregunta (RETRIEVAL_QUERY para mejor relevancia)
        emb_q = generar_embedding_query(pregunta)
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
            where: Mapping[str, str | int | float | bool] = None
            if categoria:
                where = {"categoria": categoria}
            n = min(config.TOP_K, col.count())
            res = col.query(
                query_embeddings=[emb_q],
                n_results=n,
                where=where,
                include=["documents", "metadatas", "distances"]
            )

            textos = (res.get("documents") or [[]])[0] if res.get("documents") else []
            metas = (res.get("metadatas") or [[]])[0] if res.get("metadatas") else []
            distancias = (res.get("distances") or [[]])[0] if res.get("distances") else []
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
        fuentes = list({str(m.get("archivo", "?")) for _, m, _ in pares})

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
        """Genera respuesta con router IA: Claude y Gemini."""
        fragmentos = "\n".join(
            f"• {t[:150]}..." for t, _, _ in pares
        )

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

        force_local = getattr(config, 'FORCE_LOCAL_AI', False)
        provider = config.LLM_PROVIDER if config.LLM_PROVIDER in {
            "auto", "anthropic", "gemini", "gemma", "ollama"
        } else "auto"

        if force_local:
            provider = "ollama"

        order = {
            "auto": ["ollama", "gemini", "anthropic", "gemma"],
            "ollama": ["ollama"],
            "anthropic": ["anthropic"],
            "gemini": ["gemini"],
            "gemma": ["gemma"],
        }.get(provider, ["ollama", "gemini", "anthropic", "gemma"])

        errors: List[str] = []
        for item in order:
            try:
                if item == "ollama":
                    answer, model = self._gen_ollama(prompt)
                elif item == "anthropic":
                    answer, model = self._gen_anthropic(prompt)
                elif item == "gemma":
                    answer, model = self._gen_gemma_local(prompt)
                elif item == "gemini":
                    answer, model = self._gen_gemini(prompt)
                elif item == "grok":
                    answer, model = self._gen_grok(prompt)
                elif item == "openai":
                    answer, model = self._gen_openai_or_copilot(prompt)
                else:
                    answer, model = self._gen_gemini(prompt)
                tokens_in = len(prompt) // 4
                tokens_out = len(answer) // 4
                self.cost_manager.registrar(model, tokens_in, tokens_out, "rag_consulta")
                return answer
            except Exception as exc:
                errors.append(f"{item}: {exc}")
                logger.warning("Proveedor %s falló: %s", item, exc)

        if not any([config.ANTHROPIC_API_KEY, config.GEMINI_API_KEY]):
            return f"[Sin API key de IA: configura ANTHROPIC_API_KEY o GEMINI_API_KEY]\n\nFragmentos encontrados:\n{fragmentos}"

        return f"❌ Error IA: {' | '.join(errors)}\n\nFragmentos encontrados:\n{fragmentos}"

    def _gen_anthropic(self, prompt: str) -> tuple[str, str]:
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY no configurada")
        import anthropic

        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = (resp.content[0].text if resp.content else "").strip()
        if not text:
            raise RuntimeError("Anthropic no devolvió texto")
        
        # Track costs
        try:
            usage = getattr(resp, "usage", None)
            if usage:
                tokens_in = getattr(usage, "prompt_tokens", 0)
                tokens_out = getattr(usage, "completion_tokens", 0)
                tracker = get_cost_tracker()
                tracker.track_ai_call("anthropic", config.CLAUDE_MODEL, tokens_in, tokens_out, "rag_consulta")
        except Exception as e:
            logger.warning(f"Error tracking Anthropic cost: {e}")
        
        return text, config.CLAUDE_MODEL

    def _gen_grok(self, prompt: str) -> tuple[str, str]:
        if not config.XAI_API_KEY:
            raise RuntimeError("XAI_API_KEY no configurada")

        payload = {
            "model": config.XAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {config.XAI_API_KEY}",
            "Content-Type": "application/json",
        }
        resp = requests.post(config.XAI_API_URL, json=payload, headers=headers, timeout=45)
        resp.raise_for_status()
        data = resp.json()
        text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        ).strip()
        if not text:
            raise RuntimeError("Grok no devolvió texto")
        
        # Track costs
        try:
            usage = data.get("usage", {})
            tokens_in = usage.get("prompt_tokens", len(prompt) // 4)
            tokens_out = usage.get("completion_tokens", len(text) // 4)
            tracker = get_cost_tracker()
            tracker.track_ai_call("grok", config.XAI_MODEL, tokens_in, tokens_out, "rag_consulta")
        except Exception as e:
            logger.warning(f"Error tracking Grok cost: {e}")
        
        return text, config.XAI_MODEL

    def _gen_openai_or_copilot(self, prompt: str) -> tuple[str, str]:
        if not config.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY no configurada")
        from openai import OpenAI

        if config.OPENAI_BASE_URL:
            client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)
        else:
            client = OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        text = (response.choices[0].message.content or "").strip()
        if not text:
            raise RuntimeError("OpenAI/Copilot no devolvió texto")
        
        # Track costs
        try:
            usage = getattr(response, "usage", None)
            if usage:
                tokens_in = getattr(usage, "prompt_tokens", 0)
                tokens_out = getattr(usage, "completion_tokens", 0)
                tracker = get_cost_tracker()
                tracker.track_ai_call("openai", config.OPENAI_MODEL, tokens_in, tokens_out, "rag_consulta")
        except Exception as e:
            logger.warning(f"Error tracking OpenAI cost: {e}")
        
        return text, config.OPENAI_MODEL

    def _gen_gemini(self, prompt: str) -> tuple[str, str]:
        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY no configurada")
        from google import genai as new_genai

        client = new_genai.Client(api_key=config.GEMINI_API_KEY)
        resp = client.models.generate_content(
            model=config.MODELO_FLASH,
            contents=prompt,
        )
        text = (resp.text or "").strip() if hasattr(resp, "text") else ""
        if not text:
            raise RuntimeError("Gemini no devolvió texto")
        
        # Track costs
        try:
            usage = getattr(resp, "usage_metadata", None)
            if usage:
                tokens_in = getattr(usage, "prompt_token_count", 0)
                tokens_out = getattr(usage, "candidates_token_count", 0)
            else:
                # Estimación fallback
                tokens_in = len(prompt) // 4
                tokens_out = len(text) // 4
            
            tracker = get_cost_tracker()
            tracker.track_ai_call("gemini", config.MODELO_FLASH, tokens_in, tokens_out, "rag_consulta")
            
            # También registrar en el cost_manager viejo para compatibilidad
            self.cost_manager.registrar(config.MODELO_FLASH, tokens_in, tokens_out, "rag_consulta")
        except Exception as e:
            logger.warning(f"Error tracking Gemini cost: {e}")
        
        return text, config.MODELO_FLASH

    def _gen_ollama(self, prompt: str) -> tuple[str, str]:
        """Genera respuesta con Ollama local (Gemma 4 / Gemma 3) usando /api/chat."""
        if not getattr(config, 'OLLAMA_ENABLED', False):
            raise RuntimeError("Ollama desactivado en config")
        import requests as _req
        ollama_url = getattr(config, 'OLLAMA_URL', 'http://localhost:11434')
        model_name = getattr(config, 'OLLAMA_MODEL_RAG', 'gemma3:12b')
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "Eres NEXO SOBERANO, un Oficial de Inteligencia. Responde de forma precisa y concisa."},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {"temperature": 0.1}
        }
        resp = _req.post(f"{ollama_url}/api/chat", json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()
        text = data.get("message", {}).get("content", "").strip()
        if not text:
            raise RuntimeError("Ollama no devolvió texto")
        tokens_out = data.get("eval_count", len(text) // 4)
        tokens_in = data.get("prompt_eval_count", len(prompt) // 4)
        try:
            get_cost_tracker().track_ai_call(
                "ollama_local", model_name, tokens_in, tokens_out, "rag_consulta"
            )
        except Exception:
            pass
        return text, model_name

    def _gen_gemma_local(self, prompt: str) -> tuple[str, str]:
        """Genera respuesta con Gemma 4 local — delega al GemmaService compartido."""
        from NEXO_CORE.services.gemma_service import gemma_service
        text = gemma_service.consultar(prompt)
        model_name = gemma_service.model_id.split("/")[-1]
        try:
            get_cost_tracker().track_ai_call(
                "gemma_local", model_name, len(prompt) // 4, len(text) // 4, "rag_consulta"
            )
        except Exception:
            pass
        return text, model_name

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
