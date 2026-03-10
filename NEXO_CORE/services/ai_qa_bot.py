from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from NEXO_CORE.agents.web_ai_supervisor import web_ai_supervisor
from NEXO_CORE.core.state_manager import state_manager

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
AI_CONTEXT_JSON = ROOT / "logs" / "ai_context_status.json"
AI_CONTEXT_MD = ROOT / "documentos" / "ESTADO_CONTEXTO_IA.md"


@dataclass
class _HistoryItem:
    question: str
    answer_preview: str
    used_rag: bool
    ms: int


class AIQABot:
    def __init__(self) -> None:
        self._history: deque[_HistoryItem] = deque(maxlen=50)

    def history(self) -> list[dict[str, Any]]:
        return [
            {
                "question": item.question,
                "answer_preview": item.answer_preview,
                "used_rag": item.used_rag,
                "ms": item.ms,
            }
            for item in list(self._history)
        ]

    def _read_context_json(self) -> dict[str, Any]:
        if not AI_CONTEXT_JSON.exists():
            return {}
        try:
            return json.loads(AI_CONTEXT_JSON.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _read_context_markdown_excerpt(self, max_chars: int = 1400) -> str:
        if not AI_CONTEXT_MD.exists():
            return ""
        try:
            content = AI_CONTEXT_MD.read_text(encoding="utf-8", errors="replace")
            return content[:max_chars]
        except Exception:
            return ""

    def _fallback_answer(self, question: str, ai_growth: dict[str, Any]) -> str:
        rag = ai_growth.get("context_summary") or {}
        providers = ai_growth.get("providers") or {}
        ready = [name for name, enabled in providers.items() if enabled]
        provider_txt = ", ".join(ready) if ready else "sin proveedor externo activo"
        return (
            "No pude usar el motor RAG completo en este momento, pero sí tengo estado actualizado del sistema.\n\n"
            f"- Proveedores IA activos: {provider_txt}\n"
            f"- RAG cargado: {bool(rag.get('rag_loaded', False))}\n"
            f"- Documentos indexados: {int(rag.get('total_documentos', 0) or 0)}\n"
            f"- Chunks indexados: {int(rag.get('total_chunks', 0) or 0)}\n\n"
            f"Pregunta recibida: {question}\n"
            "Sugerencia: vuelve a consultar en unos segundos para intentar respuesta enriquecida con RAG."
        )

    def _consult_rag_sync(self, question: str, category: str | None, ai_growth: dict[str, Any]) -> dict[str, Any]:
        try:
            from backend.services.rag_service import get_rag_service

            rag = get_rag_service()
            context_json = self._read_context_json()
            context_excerpt = self._read_context_markdown_excerpt()

            prompt_parts = [
                "Responde de forma precisa y accionable usando únicamente evidencia disponible.",
                "Si no hay evidencia suficiente, dilo explícitamente.",
                f"Pregunta: {question}",
            ]

            if context_json:
                prompt_parts.append(f"Estado IA/Web actual: {json.dumps(context_json.get('rag', {}), ensure_ascii=False)}")
            if context_excerpt:
                prompt_parts.append(f"Extracto de contexto operativo:\n{context_excerpt}")

            rag_result = rag.consultar("\n\n".join(prompt_parts), category)

            answer = str(rag_result.get("respuesta") or "Sin respuesta")
            sources = list(rag_result.get("fuentes") or [])

            if "Error IA:" in answer or "[Sin API key de IA" in answer:
                clean_sources = "\n".join([f"- {source}" for source in sources[:8]]) if sources else "- (sin fuentes)"
                answer = (
                    "El motor de IA externa tuvo una incidencia, pero puedo responder con la evidencia ya indexada.\n\n"
                    f"Pregunta: {question}\n"
                    "Base documental encontrada en RAG:\n"
                    f"{clean_sources}\n\n"
                    "Si quieres, puedo responder de forma más profunda cuando el proveedor IA vuelva a estar estable."
                )

            return {
                "ok": not bool(rag_result.get("error", False)),
                "answer": answer,
                "sources": sources,
                "used_rag": True,
                "used_provider": "rag_service",
                "chunks_used": int(rag_result.get("chunks_usados", 0) or 0),
                "total_docs": int(rag_result.get("total_docs", 0) or 0),
                "ai_growth": ai_growth,
            }
        except Exception as exc:
            logger.warning("AI Q&A fallback por error RAG: %s", exc)
            return {
                "ok": True,
                "answer": self._fallback_answer(question, ai_growth),
                "sources": [],
                "used_rag": False,
                "used_provider": None,
                "chunks_used": 0,
                "total_docs": int((ai_growth.get("context_summary") or {}).get("total_documentos", 0) or 0),
                "ai_growth": ai_growth,
            }

    async def ask(self, question: str, category: str | None = None) -> dict[str, Any]:
        start = time.time()
        ai_growth = web_ai_supervisor.snapshot()
        result = await asyncio.to_thread(self._consult_rag_sync, question, category, ai_growth)
        ms = int((time.time() - start) * 1000)
        result["execution_time_ms"] = ms

        state_manager.increase_ai_requests(1)
        self._history.append(
            _HistoryItem(
                question=question,
                answer_preview=(result.get("answer") or "")[:220],
                used_rag=bool(result.get("used_rag", False)),
                ms=ms,
            )
        )
        return result


ai_qa_bot = AIQABot()
