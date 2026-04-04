# ============================================================
# NEXO SOBERANO — Marketing & Community Engine v1.0
# © 2026 elanarcocapital.com
#
# Genera contenido, gestiona comunidad y expande presencia
# usando Gemma 4 ($0) + datos del sistema NEXO.
#
# Capacidades:
#   - Generación de posts X/Twitter con contexto geopolítico
#   - Calendario editorial semanal automático
#   - Análisis de audiencia y engagement
#   - Narrrativas inteligentes para eventos del globo
#   - Growth hacking con contenido técnico de alto valor
# ============================================================
from __future__ import annotations
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("NEXO.marketing")

ROOT         = Path(__file__).resolve().parents[2]
CONTENT_DIR  = ROOT / "logs" / "marketing"
CONTENT_DIR.mkdir(parents=True, exist_ok=True)

NEXO_HANDLE  = os.getenv("X_HANDLE", "@ElAnarcocapital")
BRAND_VOICE  = """
NEXO SOBERANO / El Anarcocapital — Voz de marca:
- Tono: intelectual, directo, provocador, sin filtros
- Estilo: análisis geopolítico profundo + tecnología soberana
- Audiencia: analistas, techies, libertarios, inversores
- Hashtags habituales: #Geopolitica #SoberaniaTecnologica #IA #NEXO #Anarcocapital
- Nunca: clickbait vacío, emojis en exceso, tono corporativo
- Siempre: datos reales, contexto histórico, perspectiva libertaria
"""

POST_TEMPLATES = {
    "geopolitical_alert": (
        "🌐 ALERTA GEOPOLÍTICA\n\n{headline}\n\n"
        "{analysis}\n\n"
        "Seguimiento en tiempo real: elanarcocapital.com/omniglobe\n"
        "{hashtags}"
    ),
    "tech_insight": (
        "🔧 INTELIGENCIA TECNOLÓGICA\n\n{titulo}\n\n"
        "{contenido}\n\n"
        "Sistema: NEXO SOBERANO — IA Soberana, sin dependencias cloud.\n"
        "{hashtags}"
    ),
    "thread_opener": (
        "🧵 HILO: {tema}\n\n1/ {intro}\n\n"
        "→ {punto1}\n→ {punto2}\n→ {punto3}\n\n"
        "[continúa]"
    ),
    "weekly_intel": (
        "📊 RESUMEN SEMANAL DE INTELIGENCIA\n\n"
        "Semana del {fecha}\n\n"
        "{eventos_clave}\n\n"
        "Análisis completo: elanarcocapital.com\n"
        "#NEXO #Geopolitica #InformeInteligencia"
    ),
}


class MarketingEngine:
    """
    Motor de marketing inteligente con Gemma 4.
    Genera contenido de alto valor, gestiona calendario editorial
    y coordina publicación en X y Discord.
    """

    def __init__(self):
        self._ai = None
        self._content_history: list[dict] = []

    @property
    def ai(self):
        if self._ai is None:
            from NEXO_CORE.services.ollama_service import ollama_service
            self._ai = ollama_service
        return self._ai

    # ── CONTENT GENERATION ───────────────────────────────────────────────────

    async def generar_post_geopolitico(
        self,
        evento: str,
        lat: float = 0,
        lng: float = 0,
        fuente: str = "",
    ) -> dict:
        """
        Genera un post de X para un evento geopolítico del globo.
        Contexto: evento real del OmniGlobe → Gemma 4 → post 280 chars.
        Costo: $0.
        """
        system = (
            f"{BRAND_VOICE}\n\n"
            "Genera un tweet de máximo 260 caracteres (deja espacio para URL) sobre el evento.\n"
            "Incluye: hecho concreto, contexto breve, implicación estratégica.\n"
            "NO uses emojis excesivos. SÍ usa 2-3 hashtags relevantes al final.\n"
            "Responde SOLO el texto del tweet."
        )
        geo_context = f" (lat={lat:.1f}, lng={lng:.1f})" if lat else ""
        prompt = f"Evento{geo_context}: {evento}\nFuente: {fuente or 'inteligencia NEXO'}"

        resp = await self.ai.consultar(prompt=prompt, modelo="fast", system=system, temperature=0.4, max_tokens=120)
        tweet = resp.text.strip() if resp.success else f"NEXO INTEL: {evento[:200]}"

        post = {
            "tipo": "geopolitical_alert",
            "tweet": tweet[:280],
            "evento": evento,
            "lat": lat,
            "lng": lng,
            "ts": datetime.now(timezone.utc).isoformat(),
            "fuente": fuente,
            "listo_para_publicar": False,
        }
        self._save_content(post)
        return post

    async def generar_hilo_tecnico(self, tema: str, num_tweets: int = 5) -> list[str]:
        """
        Genera un hilo técnico sobre tecnología NEXO / geopolítica.
        Costo: $0 (Gemma 4).
        """
        system = (
            f"{BRAND_VOICE}\n\n"
            f"Genera un hilo de {num_tweets} tweets sobre el tema dado.\n"
            "Cada tweet máximo 260 chars. Numerados 1/, 2/, etc.\n"
            "El hilo debe: introducir el tema, dar contexto, análisis, implicaciones, conclusión.\n"
            "Responde cada tweet en una línea separada por '---'."
        )
        resp = await self.ai.consultar(prompt=f"Tema del hilo: {tema}", modelo="general", system=system, temperature=0.5, max_tokens=800)
        if not resp.success:
            return [f"1/ {tema}"]
        tweets = [t.strip() for t in resp.text.split("---") if t.strip()][:num_tweets]
        return tweets

    async def generar_calendario_editorial(self, dias: int = 7) -> list[dict]:
        """
        Genera plan de contenido para la próxima semana.
        Mezcla: geopolítica, tecnología, OSINT, educación, comunidad.
        """
        system = (
            f"{BRAND_VOICE}\n\n"
            f"Genera un calendario editorial de {dias} días para @ElAnarcocapital.\n"
            "Por cada día incluye: fecha, tipo_contenido, tema, formato, hora_optima.\n"
            "Mezcla: análisis geopolítico (40%), tech/IA (30%), hilo educativo (20%), comunidad (10%).\n"
            "Responde SOLO JSON array:\n"
            '[{"fecha":"...","tipo":"post|hilo|encuesta","tema":"...","formato":"tweet|thread|poll","hora":"HH:MM UTC"}]'
        )
        from_date = datetime.now(timezone.utc)
        prompt = f"Fecha inicio: {from_date.strftime('%Y-%m-%d')}\nContexto actual: tensiones geopolíticas globales, IA soberana, privacidad digital"

        resp = await self.ai.consultar(prompt=prompt, modelo="general", system=system, temperature=0.6, max_tokens=600)
        try:
            import re
            m = re.search(r'\[.*\]', resp.text or "[]", re.DOTALL)
            calendario = json.loads(m.group()) if m else []
        except Exception:
            calendario = []

        result = {"dias": dias, "calendario": calendario, "generado": datetime.now(timezone.utc).isoformat()}
        (CONTENT_DIR / "calendario_editorial.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return calendario

    async def analizar_engagement(self, metricas: dict) -> str:
        """
        Analiza métricas de engagement y sugiere mejoras de estrategia.
        """
        system = (
            "Eres un experto en growth de comunidades tech/geopolítica en X.\n"
            "Analiza las métricas y da 3 recomendaciones concretas para mejorar engagement.\n"
            "Responde en español, directo y práctico."
        )
        resp = await self.ai.consultar(
            prompt=f"Métricas:\n{json.dumps(metricas, ensure_ascii=False)}",
            modelo="fast", system=system, temperature=0.3, max_tokens=300,
        )
        return resp.text if resp.success else "Métricas insuficientes para análisis"

    async def generar_narrativa_globo(self, eventos: list[dict]) -> str:
        """
        Genera narrativa geopolítica para mostrar en el OmniGlobe.
        Convierte eventos en tiempo real en inteligencia coherente.
        """
        if not eventos:
            return ""
        system = (
            "Eres el analista jefe de NEXO SOBERANO. "
            "Con base en los eventos detectados en el globo, genera una narrativa "
            "geopolítica de 2-3 oraciones para el overlay del mapa. "
            "Tono: inteligencia operacional, no alarmista. Español."
        )
        eventos_str = "\n".join(f"- {e.get('label', '')} ({e.get('source','')})" for e in eventos[:8])
        resp = await self.ai.consultar(
            prompt=f"Eventos activos:\n{eventos_str}",
            modelo="fast", system=system, temperature=0.2, max_tokens=200,
        )
        return resp.text.strip() if resp.success else ""

    # ── PUBLISHING ────────────────────────────────────────────────────────────

    async def publicar_en_x(self, texto: str, media_path: str = "") -> dict:
        """Publica en X usando x_publisher.py — requiere credenciales configuradas."""
        try:
            from backend.services.x_publisher import post_to_x
            result = post_to_x(texto, media_path or None)
            logger.info(f"X publish: {result}")
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"X publish error: {e}")
            return {"success": False, "error": str(e)}

    async def notificar_discord(self, mensaje: str, embed: dict | None = None) -> dict:
        """Envía notificación a Discord via webhook."""
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        if not webhook_url:
            return {"success": False, "error": "DISCORD_WEBHOOK_URL no configurado"}
        try:
            import aiohttp
            payload: dict = {"content": mensaje}
            if embed:
                payload["embeds"] = [embed]
            async with aiohttp.ClientSession() as s:
                async with s.post(webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    return {"success": r.status in (200, 204), "status": r.status}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── UTILS ─────────────────────────────────────────────────────────────────

    def _save_content(self, content: dict):
        self._content_history.append(content)
        ts = datetime.now().strftime("%Y%m%d")
        path = CONTENT_DIR / f"content_{ts}.json"
        history = []
        if path.exists():
            try:
                history = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        history.append(content)
        path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_pending_posts(self) -> list[dict]:
        """Posts generados pero aún no publicados."""
        return [p for p in self._content_history if not p.get("listo_para_publicar")]

    def get_stats(self) -> dict:
        return {
            "posts_generados": len(self._content_history),
            "pendientes_publicar": len(self.get_pending_posts()),
            "contenido_dir": str(CONTENT_DIR),
        }


# Instancia global
marketing_engine = MarketingEngine()
