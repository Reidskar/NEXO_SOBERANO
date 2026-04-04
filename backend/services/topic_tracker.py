"""
backend/services/topic_tracker.py
===================================
Topic Tracker — Memoria progresiva de temas estratégicos.

Capacidades:
- Rastrear temas con historial de eventos, capturas, alertas
- Detectar cobertura OSINT relevante y alertar
- Vincular videos del Drive a temas activos
- Sugerir streams en vivo cuando el tema escala
- Integración con pipeline de voz de Discord: detectar temas mencionados
- Ejecutar comandos de dispositivo via cola cuando el contexto lo requiere
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

TOPICS_DIR = Path("exports/topics")
TOPICS_DIR.mkdir(parents=True, exist_ok=True)

# Streams en vivo por región/tema (mapeados desde REGIONS del mapa)
LIVE_STREAMS = {
    "iran": [
        {"label": "Al Jazeera EN", "url": "https://www.youtube.com/watch?v=GbKqRSwPKSo", "lang": "EN"},
        {"label": "BBC News Live", "url": "https://www.youtube.com/watch?v=w_Ma8oQLmSM", "lang": "EN"},
    ],
    "taiwan": [
        {"label": "NHK World", "url": "https://www.youtube.com/watch?v=OpLqNLlHmVo", "lang": "EN"},
        {"label": "Al Jazeera EN", "url": "https://www.youtube.com/watch?v=GbKqRSwPKSo", "lang": "EN"},
    ],
    "ukraine": [
        {"label": "Al Jazeera EN", "url": "https://www.youtube.com/watch?v=GbKqRSwPKSo", "lang": "EN"},
        {"label": "DW News", "url": "https://www.youtube.com/watch?v=mxMpBjFoqpE", "lang": "EN"},
    ],
    "korea": [
        {"label": "Arirang News", "url": "https://www.youtube.com/watch?v=YxlDFq2L1Es", "lang": "EN"},
        {"label": "NHK World", "url": "https://www.youtube.com/watch?v=OpLqNLlHmVo", "lang": "EN"},
    ],
    "china": [
        {"label": "CGTN Live", "url": "https://www.youtube.com/watch?v=bvdEOaNDXIE", "lang": "EN"},
        {"label": "NHK World", "url": "https://www.youtube.com/watch?v=OpLqNLlHmVo", "lang": "EN"},
    ],
    "venezuela": [
        {"label": "Al Jazeera ES", "url": "https://www.youtube.com/watch?v=GbKqRSwPKSo", "lang": "ES"},
        {"label": "DW Español", "url": "https://www.youtube.com/watch?v=iU1NFCE9eJY", "lang": "ES"},
    ],
    "general": [
        {"label": "Al Jazeera EN", "url": "https://www.youtube.com/watch?v=GbKqRSwPKSo", "lang": "EN"},
        {"label": "DW News", "url": "https://www.youtube.com/watch?v=mxMpBjFoqpE", "lang": "EN"},
        {"label": "France 24 EN", "url": "https://www.youtube.com/watch?v=h3MuIUNCCLI", "lang": "EN"},
        {"label": "DW Español", "url": "https://www.youtube.com/watch?v=iU1NFCE9eJY", "lang": "ES"},
    ],
}

# Palabras clave para detección automática en texto de voz/OSINT
TOPIC_KEYWORDS = {
    "iran": ["iran", "irak", "persa", "teherán", "irgc", "nuclear", "enrichment", "hormuz"],
    "taiwan": ["taiwan", "taiwán", "strait", "estrecho", "pla", "china", "tsmc"],
    "ukraine": ["ukraine", "ucrania", "rusia", "russia", "zelensky", "putin", "donbas", "kharkiv"],
    "korea": ["corea", "korea", "pyongyang", "kim", "dprk", "icbm"],
    "china": ["china", "xi jinping", "beijing", "pla", "scs", "mar del sur"],
    "venezuela": ["venezuela", "maduro", "pdvsa", "petroleo", "caribe"],
    "israel": ["israel", "palestina", "hamas", "gaza", "hezbolá", "hezbollah"],
    "mercados": ["vix", "mercado", "bitcoin", "btc", "oro", "gold", "wti", "oil", "inflación"],
    "ciberseguridad": ["cve", "exploit", "ransomware", "hack", "vulnerabilidad", "malware"],
}


class TopicTracker:
    """
    Motor de seguimiento progresivo de temas estratégicos.
    Persiste en disco, se actualiza con cada sweep OSINT y captura de contenido.
    """

    def __init__(self):
        self._topics: dict[str, dict] = {}
        self._load_all()
        logger.info(f"[TopicTracker] Iniciado — {len(self._topics)} temas cargados")

    # ── CRUD de Temas ─────────────────────────────────────────────────────────

    def create_topic(self, name: str, keywords: list[str], description: str = "",
                     region: str = "general", priority: str = "media") -> dict:
        """Crea un nuevo tema de seguimiento."""
        tid = str(uuid.uuid4())[:8]
        topic = {
            "id": tid,
            "name": name,
            "description": description,
            "keywords": [k.lower() for k in keywords],
            "region": region.lower(),
            "priority": priority,  # alta | media | baja
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "events": [],         # historial de eventos detectados
            "captures": [],       # videos/audios vinculados
            "drive_files": [],    # archivos de Drive asociados
            "alerts_sent": 0,
            "last_alert": None,
            "osint_hits": [],     # hits del OSINT Engine
            "summary": "",        # resumen IA progresivo
        }
        self._topics[tid] = topic
        self._save(tid)
        logger.info(f"[TopicTracker] Tema creado: {name} ({tid})")
        return topic

    def get_topic(self, topic_id: str) -> Optional[dict]:
        return self._topics.get(topic_id)

    def list_topics(self, status: str = None, priority: str = None) -> list[dict]:
        topics = list(self._topics.values())
        if status:
            topics = [t for t in topics if t["status"] == status]
        if priority:
            topics = [t for t in topics if t["priority"] == priority]
        return sorted(topics, key=lambda t: t["updated_at"], reverse=True)

    def update_topic(self, topic_id: str, **kwargs) -> Optional[dict]:
        topic = self._topics.get(topic_id)
        if not topic:
            return None
        for k, v in kwargs.items():
            if k in topic:
                topic[k] = v
        topic["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save(topic_id)
        return topic

    # ── Detección de temas en texto ───────────────────────────────────────────

    def detect_topics_in_text(self, text: str) -> list[str]:
        """
        Detecta qué temas están mencionados en un texto (voz, transcript, OSINT).
        Retorna lista de topic IDs relevantes.
        """
        text_lower = text.lower()
        matched = []

        # Primero buscar en keywords de temas personalizados
        for tid, topic in self._topics.items():
            if topic["status"] != "active":
                continue
            for kw in topic.get("keywords", []):
                if kw in text_lower:
                    matched.append(tid)
                    break

        # También detectar por categorías predefinidas
        detected_regions = []
        for region, keywords in TOPIC_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                detected_regions.append(region)

        return matched, detected_regions

    # ── Ingesta de contenido ──────────────────────────────────────────────────

    def add_event(self, topic_id: str, event: dict) -> bool:
        """Agrega un evento al historial del tema."""
        topic = self._topics.get(topic_id)
        if not topic:
            return False
        event["timestamp"] = event.get("timestamp", datetime.now(timezone.utc).isoformat())
        topic["events"].append(event)
        topic["events"] = topic["events"][-100:]  # máximo 100 eventos
        topic["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save(topic_id)
        return True

    def link_drive_file(self, topic_id: str, file_info: dict) -> bool:
        """Vincula un archivo de Google Drive a un tema."""
        topic = self._topics.get(topic_id)
        if not topic:
            return False
        file_info["linked_at"] = datetime.now(timezone.utc).isoformat()
        topic["drive_files"].append(file_info)
        topic["drive_files"] = topic["drive_files"][-50:]
        topic["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save(topic_id)
        logger.info(f"[TopicTracker] Drive file vinculado a tema {topic_id}: {file_info.get('name')}")
        return True

    def link_capture(self, topic_id: str, capture: dict) -> bool:
        """Vincula una captura de contenido (vault) a un tema."""
        topic = self._topics.get(topic_id)
        if not topic:
            return False
        topic["captures"].append({
            **capture,
            "linked_at": datetime.now(timezone.utc).isoformat()
        })
        topic["captures"] = topic["captures"][-30:]
        topic["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save(topic_id)
        return True

    def add_osint_hit(self, topic_id: str, source: str, data: dict):
        """Agrega un hit de OSINT al tema."""
        topic = self._topics.get(topic_id)
        if not topic:
            return
        topic["osint_hits"].append({
            "source": source,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        topic["osint_hits"] = topic["osint_hits"][-20:]
        topic["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save(topic_id)

    # ── OSINT Sweep → Topics ──────────────────────────────────────────────────

    def process_osint_sweep(self, sweep_result: dict) -> list[dict]:
        """
        Procesa un sweep OSINT y detecta qué temas activos tienen nueva actividad.
        Retorna lista de alertas a enviar.
        """
        alerts = []
        sources = sweep_result.get("sources", {})

        for tid, topic in self._topics.items():
            if topic["status"] != "active":
                continue

            hits = []
            keywords = [k.lower() for k in topic.get("keywords", [])]
            region = topic.get("region", "general")

            # Revisar GDELT
            gdelt = sources.get("GDELT", {})
            for event in (gdelt.get("events") or []):
                title = (event.get("title") or event.get("url") or "").lower()
                if any(kw in title for kw in keywords):
                    hits.append({"source": "GDELT", "text": event.get("title", "")[:200]})

            # Revisar WHO
            who = sources.get("WHO", {})
            for item in (who.get("alerts") or []):
                text = (item.get("title") or item.get("summary") or "").lower()
                if any(kw in text for kw in keywords):
                    hits.append({"source": "WHO", "text": item.get("title", "")[:200]})

            # Revisar ReliefWeb
            relief = sources.get("ReliefWeb", {})
            for item in (relief.get("reports") or []):
                text = (item.get("title") or "").lower()
                if any(kw in text for kw in keywords):
                    hits.append({"source": "ReliefWeb", "text": item.get("title", "")[:200]})

            if hits:
                # Verificar cooldown (no alertar más de 1x por hora por tema)
                last = topic.get("last_alert")
                cooldown_ok = not last or (time.time() - time.mktime(
                    datetime.fromisoformat(last.replace("Z", "+00:00")).timetuple()
                )) > 3600

                if cooldown_ok:
                    for h in hits[:3]:
                        self.add_osint_hit(tid, h["source"], h)

                    topic["last_alert"] = datetime.now(timezone.utc).isoformat()
                    topic["alerts_sent"] = topic.get("alerts_sent", 0) + 1
                    self._save(tid)

                    streams = self.get_live_streams_for_topic(topic)
                    alerts.append({
                        "topic_id": tid,
                        "topic_name": topic["name"],
                        "region": region,
                        "hits": hits[:5],
                        "priority": topic["priority"],
                        "live_streams": streams,
                    })

        return alerts

    # ── Streams en vivo ───────────────────────────────────────────────────────

    def get_live_streams_for_topic(self, topic: dict) -> list[dict]:
        """Retorna streams en vivo relevantes para un tema."""
        region = topic.get("region", "general").lower()
        streams = LIVE_STREAMS.get(region, LIVE_STREAMS["general"])
        return streams[:2]

    def get_streams_for_regions(self, regions: list[str]) -> list[dict]:
        """Retorna streams para una lista de regiones detectadas."""
        seen = set()
        result = []
        for r in regions:
            for s in LIVE_STREAMS.get(r, []):
                key = s["label"]
                if key not in seen:
                    seen.add(key)
                    result.append({**s, "region": r})
        if not result:
            result = LIVE_STREAMS["general"][:2]
        return result[:4]

    # ── Análisis IA progresivo ────────────────────────────────────────────────

    def generate_summary(self, topic_id: str) -> str:
        """Genera un resumen progresivo del tema usando Ollama/Gemini."""
        topic = self._topics.get(topic_id)
        if not topic:
            return ""

        events_text = "\n".join([
            f"- [{e.get('source','')}] {e.get('text', e.get('title',''))[:200]}"
            for e in topic.get("events", [])[-20:]
        ])
        captures_text = "\n".join([
            f"- {c.get('title', c.get('source',''))} ({c.get('timestamp','')[:10]})"
            for c in topic.get("captures", [])[-10:]
        ])
        osint_text = "\n".join([
            f"- [{h.get('source','')}] {json.dumps(h.get('data',{}))[:150]}"
            for h in topic.get("osint_hits", [])[-10:]
        ])

        prompt = f"""Eres NEXO SOBERANO — analista de inteligencia estratégica.
Genera un resumen progresivo actualizado sobre el tema: "{topic['name']}"
Descripción inicial: {topic['description']}

EVENTOS RECIENTES:
{events_text or 'Sin eventos registrados'}

CAPTURAS DE CONTENIDO:
{captures_text or 'Sin capturas'}

HITS OSINT:
{osint_text or 'Sin hits OSINT'}

Genera:
1. Estado actual del tema (2-3 oraciones)
2. Tendencia: ¿escalando, estable, desescalando?
3. Próximas señales a monitorear
Sé conciso y analítico."""

        try:
            from research_guide_ai import _ai_generate_standalone
            return _ai_generate_standalone(prompt)
        except Exception:
            pass

        try:
            import asyncio
            from NEXO_CORE.services.ollama_service import ollama_service
            loop = asyncio.new_event_loop()
            resp = loop.run_until_complete(
                ollama_service.consultar(prompt=prompt, modelo="general", temperature=0.1)
            )
            loop.close()
            if resp.success:
                summary = resp.text.strip()
                topic["summary"] = summary
                self._save(topic_id)
                return summary
        except Exception as e:
            logger.warning(f"[TopicTracker] Error generando summary: {e}")

        return "Sin resumen disponible."

    # ── Drive Watch ───────────────────────────────────────────────────────────

    def process_new_drive_file(self, file_info: dict) -> list[str]:
        """
        Procesa un archivo nuevo de Drive y lo vincula a temas relevantes.
        file_info: {name, id, mimeType, description, transcript?, ...}
        Retorna lista de topic_ids a los que fue vinculado.
        """
        text = " ".join([
            file_info.get("name", ""),
            file_info.get("description", ""),
            file_info.get("transcript", ""),
        ]).lower()

        linked_to = []
        for tid, topic in self._topics.items():
            if topic["status"] != "active":
                continue
            if any(kw in text for kw in topic.get("keywords", [])):
                self.link_drive_file(tid, file_info)
                linked_to.append(tid)

        if not linked_to:
            logger.info(f"[TopicTracker] Drive file '{file_info.get('name')}' no coincide con temas activos")

        return linked_to

    # ── Persistencia ─────────────────────────────────────────────────────────

    def _save(self, topic_id: str):
        topic = self._topics.get(topic_id)
        if topic:
            path = TOPICS_DIR / f"{topic_id}.json"
            path.write_text(
                json.dumps(topic, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8"
            )

    def _load_all(self):
        for f in TOPICS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                self._topics[data["id"]] = data
            except Exception as e:
                logger.warning(f"[TopicTracker] Error cargando {f}: {e}")


# Singleton
topic_tracker = TopicTracker()
