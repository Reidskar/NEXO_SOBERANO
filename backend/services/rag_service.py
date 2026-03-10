"""
RAG Service — Motor de búsqueda + respuesta IA (Reescrito para Supabase Vector asíncrono)
"""

import sqlite3
import time
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend import config
from backend.services.cost_manager import get_cost_manager
from backend.services.unified_cost_tracker import get_cost_tracker
from backend.services.vector_db import ensure_table
from backend.services.vector_service import search as search_qdrant, ensure_collection

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

# ════════════════════════════════════════════════════════════════════
# RAG SERVICE (ASÍNCRONO)
# ════════════════════════════════════════════════════════════════════

class AsyncRAGService:
    """Motor unificado de RAG iterado para usar Supabase pgvector"""

    def __init__(self):
        self.cost_manager = get_cost_manager()
        self._initialized = False
        self._total_docs_cache = 0
        self._cache_time = 0

    async def _init(self):
        if not self._initialized:
            await ensure_table()
            self._initialized = True

    async def consultar(self, pregunta: str, tenant_slug: str = "demo", categoria: Optional[str] = None) -> Dict:
        """
        Consulta la bóveda de documentos en Qdrant y genera respuesta con IA.
        """
        t0 = time.time()
        # Asegurar colección en Qdrant
        ensure_collection(tenant_slug)

        # Buscar en Qdrant
        try:
            resultados = search_qdrant(
                tenant_slug=tenant_slug,
                query=pregunta, 
                limit=config.TOP_K
            )
        except Exception as e:
            logger.error(f"Error en Qdrant query: {e}")
            return {
                "respuesta": f"❌ Error en búsqueda vectorial: {str(e)}",
                "fuentes": [],
                "chunks_usados": 0,
                "ms": int((time.time() - t0) * 1000),
                "total_docs": 0,
                "presupuesto": self.cost_manager.estado(),
                "error": True,
            }

        # Filtrar por relevancia (Qdrant ya devuelve score de similitud coseno)
        pares = [
            (r['text'], r['metadata'], r['score'])
            for r in resultados
            if r['score'] >= (1 - config.RELEVANCE_THRESHOLD)
        ]

        if not pares:
            return {
                "respuesta": "🔍 No encontré información relevante. Prueba otras palabras clave.",
                "fuentes": [],
                "chunks_usados": 0,
                "ms": int((time.time() - t0) * 1000),
                "total_docs": len(resultados),
                "presupuesto": self.cost_manager.estado(),
            }

        # Construir contexto
        contexto = "\n\n---\n\n".join([
            f"[Fuente: {m.get('archivo', '?')} | "
            f"Cat: {m.get('categoria', '?')} | "
            f"Impacto: {m.get('impacto', '?')} | "
            f"{s*100:.0f}% relevancia]\n{t}"
            for t, m, s in pares
        ])
        fuentes = list({str(m.get("archivo", "?")) for _, m, _ in pares})

        # Generar respuesta (llamada bloqueante en un thread)
        loop = asyncio.get_running_loop()
        respuesta = await loop.run_in_executor(
            None, 
            self._generar_respuesta, 
            pregunta, 
            contexto, 
            pares
        )

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

        # Obtener total de docs indexados desde Supabase (con cache)
        if time.time() - self._cache_time > 300: # 5 min cache
            try:
                from backend.services.vector_db import get_pool
                pool = await get_pool()
                async with pool.acquire() as conn:
                    row = await conn.fetchrow("SELECT COUNT(*) FROM public.nexo_documentos")
                    self._total_docs_cache = row[0] if row else 0
                    self._cache_time = time.time()
            except Exception as e:
                logger.error(f"Error contando docs en Supabase: {e}")
        
        total_docs = self._total_docs_cache

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

        provider = config.LLM_PROVIDER if config.LLM_PROVIDER in {
            "auto", "anthropic", "gemini"
        } else "auto"

        order = {
            "auto": ["anthropic", "gemini"],
            "anthropic": ["anthropic"],
            "gemini": ["gemini"],
        }.get(provider, ["anthropic", "gemini"])

        import requests
        
        errors: List[str] = []
        for item in order:
            try:
                if item == "anthropic":
                    answer, model = self._gen_anthropic(prompt)
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
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in getattr(resp, "content", []) if getattr(block, "type", "") == "text"
        ).strip()
        if not text:
            raise RuntimeError("Claude no devolvió texto")
        
        # Track costs
        try:
            usage = getattr(resp, "usage", None)
            if usage:
                tokens_in = getattr(usage, "input_tokens", 0)
                tokens_out = getattr(usage, "output_tokens", 0)
                tracker = get_cost_tracker()
                tracker.track_ai_call("anthropic", config.CLAUDE_MODEL, tokens_in, tokens_out, "rag_consulta")
        except Exception as e:
            logger.warning(f"Error tracking Anthropic cost: {e}")
        
        return text, config.CLAUDE_MODEL

    def _gen_grok(self, prompt: str) -> tuple[str, str]:
        if not config.XAI_API_KEY:
            raise RuntimeError("XAI_API_KEY no configurada")

        import requests
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
        except Exception:
            pass
        
        return text, config.OPENAI_MODEL

    def _gen_gemini(self, prompt: str) -> tuple[str, str]:
        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY no configurada")
        import google.generativeai as genai
        from google.generativeai import GenerativeModel

        genai.configure(api_key=config.GEMINI_API_KEY)
        model = GenerativeModel(config.MODELO_FLASH)
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
        if not text:
            raise RuntimeError("Gemini no devolvió texto")
        
        # Track costs
        try:
            usage = getattr(resp, "usage_metadata", None)
            if usage:
                tokens_in = getattr(usage, "prompt_token_count", 0)
                tokens_out = getattr(usage, "candidates_token_count", 0)
            else:
                tokens_in = len(prompt) // 4
                tokens_out = len(text) // 4
            
            tracker = get_cost_tracker()
            tracker.track_ai_call("gemini", config.MODELO_FLASH, tokens_in, tokens_out, "rag_consulta")
            self.cost_manager.registrar(config.MODELO_FLASH, tokens_in, tokens_out, "rag_consulta")
        except Exception:
            pass
        
        return text, config.MODELO_FLASH

    def estado(self) -> Dict:
        """Estado actual del sistema"""
        db = get_db()
        try:
            total_docs = db.execute(
                "SELECT COUNT(*) FROM evidencia WHERE vectorizado=1"
            ).fetchone()[0]
        except Exception:
            total_docs = 0

        db.close()

        return {
            "status": "ok",
            "rag_loaded": True,
            "total_documentos": total_docs,
            "total_chunks": total_docs,
            "coleccion_items": total_docs,
            "embeddings": config.EMBED_LOCAL,
            "presupuesto": self.cost_manager.estado(),
        }

# Instancia global para fallback / compatibilidad síncrona temporal
_rag_service: Optional[AsyncRAGService] = None

def get_rag_service():
    """Obtiene o crea el servicio RAG asíncrono"""
    global _rag_service
    if _rag_service is None:
        _rag_service = AsyncRAGService()
    return _rag_service
