"""
backend/services/research_guide.py
====================================
Guía de Investigación IA — NEXO SOBERANO

La IA actúa como Director de Investigación:
  1. Recibe un tema o pregunta de investigación
  2. Genera un plan estructurado (ángulos, fuentes, qué capturar)
  3. A medida que se agrega contenido, actualiza el estado
  4. Sugiere qué grabar/investigar a continuación
  5. Genera reportes y síntesis al finalizar
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

RESEARCH_DIR = Path(os.getenv("NEXO_RESEARCH_DIR", "exports/research"))
RESEARCH_DIR.mkdir(parents=True, exist_ok=True)


class ResearchGuide:

    def __init__(self):
        self._sessions: dict[str, dict] = self._load_all()

    # ── SESIONES ──────────────────────────────────────────────────────────────

    def create_session(
        self,
        topic: str,
        scope: str = "geopolitica",     # geopolitica | economia | tecnologia | general
        depth: str = "profundo",         # rapido | profundo | exhaustivo
        language: str = "es",
    ) -> dict:
        """Crea una sesión de investigación y genera el plan inicial con IA."""
        session_id = str(uuid.uuid4())[:10]
        plan = self._generate_plan(topic, scope, depth, language)
        session = {
            "id": session_id,
            "topic": topic,
            "scope": scope,
            "depth": depth,
            "language": language,
            "plan": plan,
            "captures": [],          # archivos/contenido agregado
            "findings": [],          # hallazgos clave detectados por IA
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._sessions[session_id] = session
        self._save(session_id)
        logger.info(f"[RESEARCH] Nueva sesión: {session_id} → {topic}")
        return session

    def get_session(self, session_id: str) -> Optional[dict]:
        return self._sessions.get(session_id)

    def list_sessions(self, status: str = None) -> list:
        sessions = list(self._sessions.values())
        if status:
            sessions = [s for s in sessions if s.get("status") == status]
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return sessions

    # ── AGREGAR CONTENIDO ────────────────────────────────────────────────────

    def add_capture(self, session_id: str, capture: dict) -> dict:
        """
        Agrega contenido capturado a la sesión y actualiza los hallazgos.
        capture = {
          "session_capture_id": str,
          "file_path": str,
          "transcript": str,
          "classification": dict,
          "source": "phone"|"obs"|"screen"|"file",
          "timestamp": str
        }
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"ok": False, "error": "Sesión no encontrada"}

        capture["added_at"] = datetime.now(timezone.utc).isoformat()
        session["captures"].append(capture)

        # Extraer hallazgos clave de esta captura
        finding = self._extract_finding(session, capture)
        if finding:
            session["findings"].append(finding)

        session["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save(session_id)
        return {"ok": True, "finding": finding}

    # ── GUÍA INTELIGENTE ──────────────────────────────────────────────────────

    def suggest_next(self, session_id: str) -> dict:
        """La IA sugiere qué investigar / grabar a continuación."""
        session = self._sessions.get(session_id)
        if not session:
            return {"ok": False, "error": "Sesión no encontrada"}

        findings_summary = self._summarize_findings(session)
        suggestion = self._ai_suggest_next(session["topic"], findings_summary, session["plan"])
        return {"ok": True, "suggestion": suggestion, "session_id": session_id}

    def get_insights(self, session_id: str) -> dict:
        """Síntesis de todo lo recopilado hasta ahora."""
        session = self._sessions.get(session_id)
        if not session:
            return {"ok": False, "error": "Sesión no encontrada"}

        insights = self._ai_insights(session)
        return {"ok": True, "insights": insights, "captures_count": len(session["captures"])}

    def generate_report(self, session_id: str, format: str = "markdown") -> dict:
        """Genera reporte final de investigación."""
        session = self._sessions.get(session_id)
        if not session:
            return {"ok": False, "error": "Sesión no encontrada"}

        report = self._ai_generate_report(session)
        # Guardar reporte
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = RESEARCH_DIR / f"report_{session_id}_{ts}.md"
        report_path.write_text(report, encoding="utf-8")

        session["status"] = "reported"
        session["report_path"] = str(report_path)
        session["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save(session_id)
        return {"ok": True, "report": report, "path": str(report_path)}

    def ask(self, session_id: str, question: str) -> dict:
        """Pregunta libre a la IA sobre el contexto de la investigación."""
        session = self._sessions.get(session_id)
        if not session:
            return {"ok": False, "error": "Sesión no encontrada"}

        context = self._build_context(session)
        answer = self._ai_ask(question, context, session["topic"])
        return {"ok": True, "answer": answer}

    # ── IA (Gemini → Ollama fallback) ─────────────────────────────────────────

    def _get_model(self, flash: bool = True):
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no configurada")
        genai.configure(api_key=api_key)
        model_name = "gemini-2.0-flash" if flash else "gemini-2.0-pro"
        return genai.GenerativeModel(model_name)

    def _ai_generate(self, prompt: str) -> str:
        """Genera texto con Gemini; si falla, usa Ollama local."""
        # Intento 1: Gemini
        try:
            model = self._get_model()
            resp = model.generate_content(prompt)
            return resp.text
        except Exception as e:
            logger.warning(f"[RESEARCH] Gemini falló: {e} — usando Ollama")
        # Intento 2: Ollama local
        try:
            import asyncio
            from NEXO_CORE.services.ollama_service import ollama_service
            loop = asyncio.new_event_loop()
            resp = loop.run_until_complete(
                ollama_service.consultar(prompt=prompt, modelo="general", temperature=0.1)
            )
            loop.close()
            if resp.success:
                return resp.text
        except Exception as e2:
            logger.error(f"[RESEARCH] Ollama también falló: {e2}")
        return ""

    def _generate_plan(self, topic: str, scope: str, depth: str, language: str) -> dict:
        try:
            prompt = f"""Eres NEXO SOBERANO — Director de Inteligencia Estratégica.
Crea un plan de investigación para el tema: "{topic}"
Alcance: {scope} | Profundidad: {depth} | Idioma: {language}

Responde SOLO con este JSON (sin markdown):
{{
  "objetivo": "objetivo claro de la investigación",
  "hipotesis": "hipótesis inicial",
  "angulos": ["ángulo1", "ángulo2", "ángulo3"],
  "fuentes_sugeridas": ["fuente1", "fuente2", "fuente3"],
  "que_grabar": ["qué tipo de contenido capturar primero"],
  "preguntas_clave": ["pregunta1", "pregunta2", "pregunta3"],
  "indicadores_alerta": ["qué señales confirmarían la hipótesis"],
  "timeline_estimado": "duración estimada de la investigación"
}}"""
            raw = self._ai_generate(prompt)
            raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            start = raw.find("{"); end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                raw = raw[start:end]
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"[RESEARCH] Plan generation failed: {e}")
            return {
                "objetivo": f"Investigar: {topic}",
                "hipotesis": "Por definir",
                "angulos": ["Perspectiva general"],
                "fuentes_sugeridas": [],
                "que_grabar": ["Contenido relevante sobre el tema"],
                "preguntas_clave": [f"¿Qué sabemos sobre {topic}?"],
                "indicadores_alerta": [],
                "timeline_estimado": "Variable",
            }

    def _extract_finding(self, session: dict, capture: dict) -> Optional[dict]:
        try:
            transcript = capture.get("transcript", "")[:1000]
            if not transcript:
                return None
            prompt = f"""Investigación sobre: "{session['topic']}"
Nuevo contenido capturado: {transcript}

¿Hay algún hallazgo relevante para la investigación?
Responde JSON (sin markdown) o escribe null:
{{
  "hallazgo": "descripción del hallazgo",
  "relevancia": "Alta|Media|Baja",
  "confirma_hipotesis": true,
  "accion_sugerida": "qué hacer con este hallazgo"
}}"""
            raw = self._ai_generate(prompt)
            raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            start = raw.find("{"); end = raw.rfind("}") + 1
            if raw.lower().startswith("null") or start < 0:
                return None
            raw = raw[start:end]
            finding = json.loads(raw)
            finding["capture_id"] = capture.get("session_capture_id", "")
            finding["timestamp"] = datetime.now(timezone.utc).isoformat()
            return finding
        except Exception:
            return None

    def _summarize_findings(self, session: dict) -> str:
        findings = session.get("findings", [])
        if not findings:
            return "Sin hallazgos aún."
        return "\n".join([
            f"- [{f.get('relevancia','?')}] {f.get('hallazgo','')}"
            for f in findings[-10:]
        ])

    def _ai_suggest_next(self, topic: str, findings: str, plan: dict) -> str:
        try:
            angulos = ", ".join(plan.get("angulos", []))
            prompt = f"""Investigación: "{topic}"
Ángulos del plan: {angulos}
Hallazgos hasta ahora:
{findings}

¿Qué debería investigar/grabar a continuación?
Da 3 sugerencias concretas y accionables. Sé específico."""
            result = self._ai_generate(prompt)
            return result.strip() if result else "No se pudo generar sugerencia."
        except Exception as e:
            return f"No se pudo generar sugerencia: {e}"

    def _ai_insights(self, session: dict) -> str:
        try:
            captures_text = "\n".join([
                f"[{c.get('source','')}] {c.get('transcript','')[:300]}"
                for c in session.get("captures", [])[-10:]
            ])
            prompt = f"""Investigación: "{session['topic']}"
Plan inicial: {json.dumps(session.get('plan',{}), ensure_ascii=False)[:500]}

Contenido recopilado:
{captures_text}

Genera una síntesis de inteligencia:
1. ¿Qué confirmamos?
2. ¿Qué contradice la hipótesis?
3. ¿Qué gaps quedan?
4. Conclusión preliminar."""
            result = self._ai_generate(prompt)
            return result.strip() if result else "Sin insights disponibles."
        except Exception as e:
            return f"Error generando insights: {e}"

    def _ai_generate_report(self, session: dict) -> str:
        try:
            findings_text = self._summarize_findings(session)
            captures_count = len(session.get("captures", []))
            prompt = f"""Genera un REPORTE DE INTELIGENCIA completo en Markdown.

TEMA: {session['topic']}
ALCANCE: {session['scope']}
CAPTURAS: {captures_count}

PLAN ORIGINAL:
{json.dumps(session.get('plan',{}), ensure_ascii=False, indent=2)[:600]}

HALLAZGOS:
{findings_text}

Estructura del reporte:
# [TITULO]
## Resumen Ejecutivo
## Contexto y Metodología
## Hallazgos Principales
## Análisis de Impacto
## Conclusiones
## Próximos Pasos Recomendados
---
*Generado por NEXO SOBERANO Intelligence Engine*"""
            result = self._ai_generate(prompt)
            return result.strip() if result else "# Error generando reporte"
        except Exception as e:
            return f"# Error generando reporte\n\n{e}"

    def _ai_ask(self, question: str, context: str, topic: str) -> str:
        try:
            prompt = f"""Eres NEXO SOBERANO, asistente de inteligencia estratégica.
Tema de investigación: {topic}

Contexto disponible:
{context[:2000]}

Pregunta: {question}

Responde con precisión y cita evidencia del contexto cuando sea relevante."""
            result = self._ai_generate(prompt)
            return result.strip() if result else "No se pudo generar respuesta."
        except Exception as e:
            return f"Error: {e}"

    def _build_context(self, session: dict) -> str:
        parts = [f"Tema: {session['topic']}"]
        for c in session.get("captures", [])[-5:]:
            parts.append(f"[{c.get('source','')}] {c.get('transcript','')[:400]}")
        return "\n\n".join(parts)

    # ── Persistencia ──────────────────────────────────────────────────────────

    def _session_path(self, session_id: str) -> Path:
        return RESEARCH_DIR / f"{session_id}.json"

    def _save(self, session_id: str):
        session = self._sessions[session_id]
        self._session_path(session_id).write_text(
            json.dumps(session, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8"
        )

    def _load_all(self) -> dict:
        sessions = {}
        for f in RESEARCH_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if "id" in data:
                    sessions[data["id"]] = data
            except Exception:
                pass
        return sessions


# Singleton
research_guide = ResearchGuide()
