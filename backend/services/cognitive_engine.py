"""
backend/services/cognitive_engine.py
======================================
Motor Cognitivo NEXO — Orquestación multi-modelo para conversación de voz.

Arquitectura:
  Entrada (voz transcrita)
    ↓
  IntentClassifier  ← qwen3.5 local (rápido, 0 costo)
    ↓
  Parallel Tool Runner:
    ├─ OsintProbe      ← busca datos vivos si hay contexto geopolítico
    ├─ TopicMatcher    ← vincula con temas en seguimiento
    ├─ DriveSearch     ← busca en Drive si preguntan por documentos
    ├─ DeviceAction    ← ejecuta comando en dispositivo si se requiere
    └─ MemoryRetriever ← recupera contexto de sesión previa
    ↓
  Synthesis:
    ├─ Fast (qwen3.5)  ← respuesta en ≤3s para la mayoría
    └─ Deep (Claude)   ← solo si intent=CRITICO o ESTRATEGICO
    ↓
  Respuesta + efectos secundarios (notificación, guardado, alerta)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path("exports/cognitive_sessions")
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
METACOG_FILE = Path("exports/cognitive_sessions/metacognition.json")

NEXO_URL   = os.getenv("NEXO_INTERNAL_URL", "http://127.0.0.1:8000")
NEXO_KEY   = os.getenv("NEXO_API_KEY", "NEXO_LOCAL_2026_OK")
API_HEADERS = {"x-api-key": NEXO_KEY}

# Tailscale IPs para los 3 dispositivos
DEVICES = {
    "torre":    os.getenv("TAILSCALE_TOWER",    "100.112.238.97"),   # PC principal
    "notebook": os.getenv("TAILSCALE_NOTEBOOK",  "100.121.255.125"),  # elanarcocapital-1
    "phone":    os.getenv("TAILSCALE_PHONE",     "100.83.26.14"),     # Xiaomi 14T Pro
}

# Intents reconocidos por el clasificador
INTENTS = {
    "ANALISIS":     "análisis estratégico profundo de situación",
    "COMANDO":      "ejecutar acción en dispositivo",
    "BUSQUEDA":     "buscar información en Drive/OSINT",
    "YOUTUBE":      "relacionado con stream/video de YouTube en curso",
    "ALERTA":       "evento urgente o crítico detectado",
    "MEMORIA":      "recuperar información de sesiones previas",
    "CONVERSACION": "conversación general / pregunta directa",
    "CRITICO":      "situación de alta urgencia que requiere análisis profundo",
    "CANVA":        "crear diseño visual, infografía o reporte gráfico",
}


class MetacognitionLayer:
    """
    Capa de metacognición: aprende del rendimiento propio y ajusta el routing.

    Por cada intent registra:
      - hits: número de respuestas evaluadas
      - score_sum: suma de puntuaciones (0–1)
      - model_wins: qué modelo ganó más veces
      - slow_count: cuántas veces tardó > umbral
    """

    def __init__(self):
        self._stats: dict = defaultdict(lambda: {
            "hits": 0, "score_sum": 0.0,
            "model_wins": defaultdict(int),
            "slow_count": 0,
        })
        self._load()

    # ── Persistencia ──────────────────────────────────────────────────

    def _load(self):
        try:
            if METACOG_FILE.exists():
                data = json.loads(METACOG_FILE.read_text())
                for intent, v in data.items():
                    self._stats[intent].update(v)
                    if "model_wins" in v:
                        self._stats[intent]["model_wins"] = defaultdict(int, v["model_wins"])
        except Exception:
            pass

    def _save(self):
        try:
            out = {}
            for intent, v in self._stats.items():
                out[intent] = {
                    "hits": v["hits"],
                    "score_sum": v["score_sum"],
                    "model_wins": dict(v["model_wins"]),
                    "slow_count": v["slow_count"],
                }
            METACOG_FILE.write_text(json.dumps(out, indent=2))
        except Exception:
            pass

    # ── API pública ───────────────────────────────────────────────────

    def record(self, intent: str, score: float, model: str, elapsed: float):
        """Registra resultado de un turno."""
        s = self._stats[intent]
        s["hits"] += 1
        s["score_sum"] += max(0.0, min(1.0, score))
        s["model_wins"][model] += 1
        if elapsed > 8.0:
            s["slow_count"] += 1
        self._save()

    def avg_score(self, intent: str) -> float:
        s = self._stats.get(intent)
        if not s or s["hits"] == 0:
            return 0.5
        return s["score_sum"] / s["hits"]

    def best_model(self, intent: str) -> Optional[str]:
        wins = self._stats.get(intent, {}).get("model_wins", {})
        return max(wins, key=wins.get) if wins else None

    def should_escalate(self, intent: str) -> bool:
        """Sugiere escalar a Claude si el avg_score del intent es bajo."""
        return self.avg_score(intent) < 0.45 and self._stats[intent]["hits"] >= 3

    def snapshot(self) -> dict:
        out = {}
        for intent, v in self._stats.items():
            avg = v["score_sum"] / v["hits"] if v["hits"] else 0
            out[intent] = {
                "hits": v["hits"],
                "avg_score": round(avg, 3),
                "best_model": self.best_model(intent),
                "slow_pct": round(v["slow_count"] / max(v["hits"], 1) * 100, 1),
            }
        return out


class CognitiveSession:
    """Sesión cognitiva de un canal de Discord. Mantiene contexto entre turnos."""

    def __init__(self, channel_id: str):
        self.channel_id = channel_id
        self.session_id = str(uuid.uuid4())[:8]
        self.turns: list[dict] = []          # historial de turnos
        self.active_topics: list[str] = []   # topic IDs activos en esta sesión
        self.youtube_context: dict = {}       # info del stream YouTube en curso
        self.last_osint: dict = {}           # último dato OSINT relevante
        self.created_at = time.time()
        self.last_active = time.time()

    def add_turn(self, role: str, text: str, metadata: dict = None):
        self.turns.append({
            "role": role,  # "user" | "nexo"
            "text": text,
            "ts": datetime.now(timezone.utc).isoformat(),
            "meta": metadata or {},
        })
        self.turns = self.turns[-30:]  # últimos 30 turnos en memoria
        self.last_active = time.time()

    def context_window(self, n: int = 8) -> str:
        """Últimos N turnos como contexto para el modelo."""
        recent = self.turns[-n:]
        return "\n".join([
            f"{'Usuario' if t['role']=='user' else 'NEXO'}: {t['text']}"
            for t in recent
        ])

    def is_idle(self, minutes: int = 30) -> bool:
        return (time.time() - self.last_active) > minutes * 60


class CognitiveEngine:
    """
    Orquestador cognitivo central.
    Una instancia por canal de Discord activo.
    """

    def __init__(self):
        self._sessions: dict[str, CognitiveSession] = {}
        self.metacog = MetacognitionLayer()
        logger.info("[CognitiveEngine] Motor cognitivo iniciado")

    def get_session(self, channel_id: str) -> CognitiveSession:
        if channel_id not in self._sessions or self._sessions[channel_id].is_idle():
            self._sessions[channel_id] = CognitiveSession(channel_id)
        return self._sessions[channel_id]

    # ── Pipeline principal ────────────────────────────────────────────────────

    async def process(self, text: str, channel_id: str, user_id: str = "") -> dict:
        """
        Procesa un turno de voz completo.
        Retorna: {response, intent, tools_used, streams, device_action, urgent}
        """
        t0 = time.time()
        session = self.get_session(channel_id)
        session.add_turn("user", text)

        # 1. Clasificar intent (rápido, local)
        intent = await self._classify_intent(text, session.context_window(4))

        # Metacognición: si el historial muestra score bajo para este intent, escalar a Claude
        force_deep = self.metacog.should_escalate(intent)
        if force_deep:
            logger.info(f"[Metacog] Escalando intent {intent} a Claude (avg_score bajo)")

        # 2. Ejecutar herramientas en paralelo según intent
        tools_result = await self._run_tools_parallel(text, intent, session)

        # 3. Sintetizar respuesta
        response, model_used = await self._synthesize(text, intent, tools_result, session, force_deep=force_deep)

        # 4. Metacognición: auto-evaluar la respuesta y registrar métricas
        elapsed = time.time() - t0
        score = await self._self_evaluate(text, response, intent, tools_result)
        self.metacog.record(intent, score, model_used, elapsed)
        logger.debug(f"[Metacog] intent={intent} score={score:.2f} model={model_used} t={elapsed:.1f}s")

        # 5. Efectos secundarios (guardar, alertar, vincular)
        await self._side_effects(text, intent, tools_result, session)

        session.add_turn("nexo", response, {
            "intent": intent, "tools": list(tools_result.keys()),
            "score": round(score, 3), "model": model_used, "elapsed": round(elapsed, 2),
        })

        return {
            "response":      response,
            "intent":        intent,
            "tools_used":    list(tools_result.keys()),
            "osint_data":    tools_result.get("osint"),
            "streams":       tools_result.get("streams"),
            "device_result": tools_result.get("device"),
            "topics":        tools_result.get("topics"),
            "canva":         tools_result.get("canva"),
            "urgent":        intent in ("ALERTA", "CRITICO"),
            "session_id":    session.session_id,
            "metacog":       {"score": round(score, 3), "model": model_used, "elapsed": round(elapsed, 2)},
        }

    # ── Clasificador de intents ───────────────────────────────────────────────

    async def _classify_intent(self, text: str, context: str) -> str:
        """Clasifica el intent del turno usando qwen3.5 local."""
        prompt = f"""Clasifica en UNA PALABRA el intent de este mensaje de voz en una sesión de análisis geopolítico.

Opciones: ANALISIS | COMANDO | BUSQUEDA | YOUTUBE | ALERTA | MEMORIA | CONVERSACION | CRITICO

Contexto previo:
{context or '(inicio de sesión)'}

Mensaje actual: "{text}"

Responde SOLO una de las opciones, sin explicación."""
        try:
            from NEXO_CORE.services.ollama_service import ollama_service
            resp = await ollama_service.consultar(prompt, modelo="general", temperature=0)
            word = resp.text.strip().upper().split()[0] if resp.success else "CONVERSACION"
            return word if word in INTENTS else "CONVERSACION"
        except Exception:
            return "CONVERSACION"

    # ── Runner de herramientas en paralelo ────────────────────────────────────

    async def _run_tools_parallel(self, text: str, intent: str, session: CognitiveSession) -> dict:
        """Lanza las herramientas pertinentes en paralelo."""
        tasks = {}

        # Siempre: detectar temas
        tasks["topics"] = self._probe_topics(text)

        # Si hay contexto geopolítico o análisis → buscar OSINT
        if intent in ("ANALISIS", "ALERTA", "CRITICO", "BUSQUEDA"):
            tasks["osint"] = self._probe_osint(text)

        # Si es COMANDO → ejecutar en dispositivo
        if intent == "COMANDO":
            tasks["device"] = self._probe_device(text)

        # Si hay YouTube activo → capturar contexto
        if intent == "YOUTUBE" or session.youtube_context:
            tasks["youtube"] = self._probe_youtube(text, session)

        # Buscar en Drive si pregunta sobre documentos/archivos
        if any(w in text.lower() for w in ["documento", "archivo", "drive", "video", "grabé", "guardé", "subí"]):
            tasks["drive"] = self._probe_drive(text)

        # Si piden diseño visual → Canva
        if intent == "CANVA" or any(w in text.lower() for w in ["canva", "diseño", "infografía", "visual", "poster", "gráfico"]):
            tasks["canva"] = self._probe_canva(text)

        # Ejecutar todo en paralelo con timeout
        results = {}
        if tasks:
            done = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for key, result in zip(tasks.keys(), done):
                if not isinstance(result, Exception):
                    results[key] = result
                else:
                    logger.debug(f"[CognitiveEngine] Tool {key} falló: {result}")

        return results

    async def _probe_topics(self, text: str) -> dict:
        """Detecta temas estratégicos y obtiene streams recomendados."""
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.post(
                f"{NEXO_URL}/api/topics/detect",
                json={"text": text},
                headers=API_HEADERS,
            )
            return r.json() if r.status_code == 200 else {}

    async def _probe_osint(self, text: str) -> dict:
        """Obtiene datos OSINT relevantes para el texto."""
        async with httpx.AsyncClient(timeout=15) as client:
            # Usar el caché — no forzar nuevo sweep
            r = await client.get(f"{NEXO_URL}/api/osint/sweep", headers=API_HEADERS)
            if r.status_code != 200:
                return {}
            sweep = r.json()

        # Filtrar solo fuentes relevantes según el texto
        text_lower = text.lower()
        relevant = {}
        sources = sweep.get("sources", {})

        # Siempre incluir mercados si hay contexto económico
        econ_kw = ["mercado", "bitcoin", "oro", "oil", "wti", "vix", "dólar", "inflación"]
        if any(k in text_lower for k in econ_kw) and "YFinance" in sources:
            relevant["markets"] = sources["YFinance"]

        # Vuelos si hay contexto militar/aéreo
        mil_kw = ["vuelo", "avión", "militar", "fuerza aérea", "bomber", "f-22", "su-57"]
        if any(k in text_lower for k in mil_kw) and "OpenSky" in sources:
            relevant["flights"] = sources["OpenSky"]

        # Satélites
        sat_kw = ["satélite", "orbital", "reentrada", "spy sat", "reconocimiento"]
        if any(k in text_lower for k in sat_kw) and "SkyOSINT" in sources:
            relevant["satellites"] = sources["SkyOSINT"]

        # GDELT siempre útil para contexto de eventos
        if "GDELT" in sources:
            gdelt = sources["GDELT"]
            if isinstance(gdelt, dict):
                events = (gdelt.get("events") or [])[:5]
                if events:
                    relevant["recent_events"] = events

        # CISA si hay contexto cyber
        cyber_kw = ["hack", "cve", "exploit", "ransomware", "vulnerabilidad", "ciberseguridad"]
        if any(k in text_lower for k in cyber_kw) and "CISA-KEV" in sources:
            relevant["cisa"] = sources["CISA-KEV"]

        return relevant

    async def _probe_device(self, text: str) -> dict:
        """Detecta y ejecuta comando de dispositivo."""
        from discord_bot_bridge import detect_device_intent
        # Intentar detectar qué dispositivo y qué acción
        text_lower = text.lower()

        target = "phone"  # default
        if any(w in text_lower for w in ["notebook", "laptop", "portatil", "computadora"]):
            target = "notebook"
        elif any(w in text_lower for w in ["pc", "torre", "escritorio", "computador"]):
            target = "torre"

        action = None
        if any(w in text_lower for w in ["screenshot", "captura", "foto", "pantalla"]):
            action = "screenshot"
        elif any(w in text_lower for w in ["home", "inicio", "vuelve al inicio"]):
            action = "home"
        elif any(w in text_lower for w in ["abre", "open", "lanza"]):
            action = "launch_url"
        elif any(w in text_lower for w in ["graba", "record", "grabá"]):
            action = "scrcpy_start"

        if action:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{NEXO_URL}/api/device/action",
                    json={"action": action, "params": {}},
                    headers=API_HEADERS,
                )
                return {"action": action, "target": target, "result": r.json() if r.status_code == 200 else {"error": r.text}}

        return {}

    async def _probe_youtube(self, text: str, session: CognitiveSession) -> dict:
        """Obtiene contexto del stream de YouTube activo si hay uno."""
        if not session.youtube_context:
            return {}
        return {"active_stream": session.youtube_context}

    async def _probe_drive(self, text: str) -> dict:
        """Busca en Drive archivos relacionados."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{NEXO_URL}/api/drive/contexto",
                    json={"consulta": text},
                    headers=API_HEADERS,
                )
                return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}

    async def _probe_canva(self, text: str) -> dict:
        """Prepara datos para crear un diseño en Canva."""
        token = os.getenv("CANVA_ACCESS_TOKEN", "")
        if not token:
            return {"available": False, "reason": "CANVA_ACCESS_TOKEN no configurado"}
        try:
            # Determinar tipo de diseño
            t = text.lower()
            design_type = "POSTER" if any(w in t for w in ["poster", "cartel"]) else \
                          "INFOGRAPHIC" if any(w in t for w in ["infografía", "infografia"]) else \
                          "PRESENTATION" if any(w in t for w in ["presentación", "slides"]) else \
                          "DOCUMENT"
            # Generar título
            title = f"NEXO Intel — {text[:50]}"
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    "https://api.canva.com/rest/v1/designs",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={"design_type": {"type": design_type}, "title": title},
                )
                if r.status_code in (200, 201):
                    data = r.json()
                    design_id = data.get("design", {}).get("id", "")
                    edit_url = data.get("design", {}).get("urls", {}).get("edit_url", "")
                    return {
                        "available": True,
                        "design_id": design_id,
                        "design_type": design_type,
                        "title": title,
                        "edit_url": edit_url,
                    }
                return {"available": True, "error": f"Canva API {r.status_code}: {r.text[:200]}"}
        except Exception as e:
            return {"available": True, "error": str(e)}

    # ── Auto-evaluación metacognitiva ─────────────────────────────────────────

    async def _self_evaluate(self, text: str, response: str, intent: str, tools: dict) -> float:
        """
        Puntúa la calidad de la respuesta (0–1) usando heurísticas rápidas.
        No llama a ningún LLM — es puramente local para no añadir latencia.
        """
        score = 0.5  # base

        # Respuesta vacía o error → penalizar
        if not response or len(response) < 20:
            return 0.1
        if response.startswith("Procesando") or "dame un momento" in response.lower():
            return 0.2

        # Penalizar si hay herramientas esperadas pero vacías
        if intent in ("ANALISIS", "BUSQUEDA") and not tools.get("osint"):
            score -= 0.1
        if intent == "CANVA" and not tools.get("canva", {}).get("design_id"):
            score -= 0.15

        # Premiar respuestas con datos concretos
        import re
        if re.search(r"\d+[.,]\d+|\$\d+|%\d+|\d+ (vuelo|evento|alerta)", response):
            score += 0.15

        # Penalizar respuestas muy cortas para CRITICO/ANALISIS
        if intent in ("CRITICO", "ANALISIS") and len(response) < 80:
            score -= 0.2

        # Premiar si hay tools usadas
        score += min(0.2, len(tools) * 0.05)

        # Premiar si topics fueron detectados
        if tools.get("topics", {}).get("matched_topics"):
            score += 0.1

        return max(0.0, min(1.0, score))

    # ── Síntesis multi-modelo ─────────────────────────────────────────────────

    async def _synthesize(self, text: str, intent: str, tools: dict, session: CognitiveSession, force_deep: bool = False) -> tuple[str, str]:
        """
        Sintetiza la respuesta final combinando contexto + herramientas.
        - Fast path: qwen3.5 local (intent=CONVERSACION/BUSQUEDA/COMANDO)
        - Deep path: Claude (intent=CRITICO/ANALISIS profundo)
        Retorna: (respuesta, modelo_usado)
        """
        # Construir contexto enriquecido
        context_parts = []

        # Historial de conversación
        conv_ctx = session.context_window(6)
        if conv_ctx:
            context_parts.append(f"CONVERSACIÓN PREVIA:\n{conv_ctx}")

        # Datos OSINT relevantes
        osint = tools.get("osint", {})
        if osint:
            osint_str = json.dumps(osint, ensure_ascii=False, default=str)[:1200]
            context_parts.append(f"DATOS OSINT EN TIEMPO REAL:\n{osint_str}")

        # Temas activos
        topics = tools.get("topics", {})
        if topics and topics.get("matched_topics"):
            names = [t["name"] for t in topics["matched_topics"]]
            context_parts.append(f"TEMAS EN SEGUIMIENTO DETECTADOS: {', '.join(names)}")

        # YouTube
        yt = tools.get("youtube", {})
        if yt:
            context_parts.append(f"STREAM YOUTUBE ACTIVO: {json.dumps(yt, ensure_ascii=False, default=str)[:300]}")

        # Drive
        drive = tools.get("drive", {})
        if drive:
            drive_str = json.dumps(drive, ensure_ascii=False, default=str)[:600]
            context_parts.append(f"DOCUMENTOS DRIVE RELEVANTES:\n{drive_str}")

        # Resultado de dispositivo
        device = tools.get("device", {})
        if device:
            context_parts.append(f"ACCIÓN EN DISPOSITIVO EJECUTADA: {device.get('action')} → {device.get('result', {}).get('ok', '?')}")

        # Canva
        canva = tools.get("canva", {})
        if canva and canva.get("design_id"):
            context_parts.append(f"DISEÑO CANVA CREADO: {canva.get('title')} — {canva.get('edit_url', '')}")

        context_block = "\n\n".join(context_parts)

        system_prompt = """Eres NEXO SOBERANO — analista cognitivo de inteligencia estratégica.
Estás en una conversación de voz activa. Sé CONCISO (máximo 3-4 oraciones para TTS),
analítico y directo. No uses markdown ni listas — habla como en una conversación.
Si tienes datos OSINT relevantes, cítalos con números precisos.
Si detectas urgencia, comunícala claramente.
Si se creó un diseño en Canva, menciona que está listo y el enlace."""

        user_prompt = f"""Contexto de la sesión:
{context_block}

Pregunta/comentario actual del usuario: "{text}"
Intent clasificado: {intent}

Responde de forma cognitivamente densa pero concisa para audio."""

        # Decidir modelo según intent (o si metacognición fuerza escalado)
        use_deep = force_deep or (intent in ("CRITICO", "ANALISIS") and len(text) > 40)

        if use_deep:
            response = await self._call_claude(system_prompt, user_prompt)
            if response:
                return response, "claude"

        # Fast path: Ollama local
        response = await self._call_ollama(system_prompt + "\n\n" + user_prompt)
        if response:
            return response, "ollama"

        # Fallback mínimo
        return "Procesando. Dame un momento.", "fallback"

    async def _call_ollama(self, prompt: str) -> Optional[str]:
        try:
            from NEXO_CORE.services.ollama_service import ollama_service
            resp = await ollama_service.consultar(
                prompt=prompt,
                modelo="general",
                temperature=0.15,
            )
            if resp.success:
                text = resp.text.strip()
                # Limpiar thinking tags si qwen3.5 los emite
                if "<think>" in text:
                    after = text.split("</think>")
                    text = after[-1].strip() if len(after) > 1 else text
                return text[:800]  # limitar para TTS
        except Exception as e:
            logger.warning(f"[CognitiveEngine] Ollama error: {e}")
        return None

    async def _call_claude(self, system: str, user: str) -> Optional[str]:
        try:
            import anthropic
            key = os.getenv("ANTHROPIC_API_KEY", "")
            if not key:
                return None
            client = anthropic.Anthropic(api_key=key)
            msg = client.messages.create(
                model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
                max_tokens=400,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return msg.content[0].text.strip()
        except Exception as e:
            logger.warning(f"[CognitiveEngine] Claude error: {e}")
        return None

    # ── Efectos secundarios ───────────────────────────────────────────────────

    async def _side_effects(self, text: str, intent: str, tools: dict, session: CognitiveSession):
        """Guarda, alerta, vincula — sin bloquear la respuesta principal."""
        # Vincular temas detectados a la sesión
        topics = tools.get("topics", {})
        if topics and topics.get("matched_topics"):
            for t in topics["matched_topics"]:
                if t["id"] not in session.active_topics:
                    session.active_topics.append(t["id"])

        # Guardar turno en topic tracker para cada tema activo
        if session.active_topics:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    for tid in session.active_topics[:3]:
                        await client.post(
                            f"{NEXO_URL}/api/topics/{tid}/event",
                            json={"source": "discord_voz", "text": text[:300]},
                            headers=API_HEADERS,
                        )
            except Exception:
                pass

        # Si es CRITICO → empujar a cola de dispositivo para notificación
        if intent == "CRITICO":
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.post(
                        f"{NEXO_URL}/api/device/queue/push",
                        json={"action": "wake", "params": {}, "reason": "ALERTA CRÍTICA"},
                        headers=API_HEADERS,
                    )
            except Exception:
                pass

    # ── YouTube Monitor ───────────────────────────────────────────────────────

    def set_youtube_context(self, channel_id: str, stream_info: dict):
        """Registra que hay un stream de YouTube activo en este canal."""
        session = self.get_session(channel_id)
        session.youtube_context = stream_info
        logger.info(f"[CognitiveEngine] YouTube context seteado para canal {channel_id}: {stream_info.get('title', '?')}")

    def clear_youtube_context(self, channel_id: str):
        session = self.get_session(channel_id)
        session.youtube_context = {}


# Singleton
cognitive_engine = CognitiveEngine()
