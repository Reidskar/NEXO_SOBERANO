"""
backend/services/worldmonitor_bridge.py
========================================
Puente de integración WorldMonitor ↔ NEXO SOBERANO

Qué hace:
- Consume la API interna de WorldMonitor (señales de inteligencia global)
- Traduce eventos CII, geo-convergencia, surge militar y noticias
  al formato RAG de NEXO (chunks vectorizados en Qdrant)
- Dispara alertas personalizadas por tenant según perfil cognitivo
- Expone endpoints que el frontend de WorldMonitor puede llamar
  para enriquecer con contexto RAG del tenant

Flujo:
  WorldMonitor signals → ingest_signals() → Qdrant (por tenant)
                       → alert_router()   → Celery task → email/notif
  WorldMonitor frontend → /nexo/enrich    → RAG query   → contexto enriquecido
"""

import os
import json
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Optional
from backend.services.vector_db import ensure_table, asimilar_documento, buscar_similares

QDRANT_URL    = os.getenv("QDRANT_URL", "http://localhost:6333")
DATABASE_URL  = os.getenv("DATABASE_URL", "")
REDIS_URL     = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# URL base de WorldMonitor (su API de Edge Functions en Vercel)
WM_BASE_URL   = os.getenv("WORLDMONITOR_API_URL", "https://worldmonitor.app")
WM_API_KEY    = os.getenv("WORLDMONITOR_API_KEY", "")  # Si tienen auth

from sentence_transformers import SentenceTransformer

# Modelo local de embedding (costo $0)
_embed_model: Optional[SentenceTransformer] = None

def get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model


# ── Tipos de señal que WorldMonitor genera ─────────────────────
SIGNAL_TYPES = {
    "cii_spike":        "🚨 Spike de inestabilidad detectado",
    "geo_convergence":  "📍 Convergencia geográfica de eventos",
    "military_surge":   "⚔️  Surge militar detectado",
    "news_cluster":     "📰 Cluster de noticias relevante",
    "threat_classified":"⚠️  Amenaza clasificada",
    "ais_anomaly":      "🚢 Anomalía marítima (AIS)",
    "protest_event":    "✊ Evento de protesta / conflicto civil",
}

# Umbral de severidad para generar alerta push (0-1)
ALERT_THRESHOLD = 0.65


class WorldMonitorBridge:
    """
    Integra el stream de señales de WorldMonitor con el RAG y
    sistema de notificaciones de NEXO SOBERANO.
    """

    def __init__(self, tenant_slug: str = "demo"):
        self.tenant_slug = tenant_slug
        self.schema = f"tenant_{tenant_slug.replace('-', '_')}"
        self.tenant_slug = tenant_slug
        self.schema = f"tenant_{tenant_slug.replace('-', '_')}"

    # ── INICIALIZACIÓN ─────────────────────────────────────────

    async def ensure_collection(self):
        """Asegura tabla en Supabase."""
        await ensure_table()

    def fetch_latest_signals(self) -> list[dict]:
        """
        Simulación de fetch desde la API de WorldMonitor.
        En producción esto llamaría a WM_BASE_URL/api/signals.
        """
        # Por ahora devolvemos un mock que cumple con lo que tasks_core espera
        return [
            {
                "type": "cii_spike",
                "severity": 0.85,
                "title": "Tensión en el Estrecho de Taiwán",
                "body": "Incremento de actividad naval detectado en las últimas 24 horas.",
                "tenant_slug": "demo"
            },
            {
                "type": "news_cluster",
                "severity": 0.45,
                "title": "Acuerdo comercial Mercosur-UE",
                "body": "Nuevas rondas de negociación programadas para el próximo mes.",
                "tenant_slug": "demo"
            }
        ]

    # ── INGESTIÓN DE SEÑALES ───────────────────────────────────

    async def ingest_signal(self, signal: dict) -> str:
        """
        Ingesta una señal de WorldMonitor al RAG del tenant (Supabase).
        """
        await self.ensure_collection()

        text_parts = [
            f"[{signal.get('type', 'evento').upper()}]",
            signal.get("title", ""),
            signal.get("summary", ""),
        ]
        full_text = " | ".join(filter(None, text_parts))

        import hashlib
        point_id_str = f"{signal.get('type')}:{signal.get('country', '')}:{signal.get('timestamp', '')}"
        signal_id = hashlib.sha256(point_id_str.encode()).hexdigest()

        payload = {
            "type": signal.get("type"),
            "severity": signal.get("severity", 0.5),
            "timestamp": signal.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "source": "worldmonitor",
            "tenant": self.tenant_slug,
        }

        await asimilar_documento(
            hash_sha256=signal_id, 
            contenido=full_text, 
            metadata={**payload, "archivo": f"wm_{signal_id}"}
        )
        return f"signal:{signal_id}"

    def ingest_batch(self, signals: list[dict]) -> dict:
        """Ingesta múltiples señales en batch."""
        self.ensure_collection()
        ingested = 0
        errors = 0

        for signal in signals:
            try:
                self.ingest_signal(signal)
                ingested += 1
            except Exception as e:
                errors += 1
                log.info(f"⚠️  Error ingestando señal: {e}")

        return {"ingested": ingested, "errors": errors, "total": len(signals)}

    # ── CONSULTA RAG ENRIQUECIDA ───────────────────────────────

    async def query_intelligence(self, query: str, top_k: int = 8,
                               categoria: Optional[str] = None,
                               filter_severity_min: float = 0.0) -> list[dict]:
        """Búsqueda semántica en Supabase."""
        await self.ensure_collection()
        resultados = await buscar_similares(query, k=top_k, categoria=categoria)
        
        return [
            {
                "score": r['similarity'],
                "type": r['metadata'].get("type"),
                "severity": r['metadata'].get("severity"),
                "title": r['metadata'].get("title"),
                "summary": r['content'],
                "timestamp": r['metadata'].get("timestamp"),
            }
            for r in resultados
            if r['similarity'] >= filter_severity_min
        ]

    # ── ROUTER DE ALERTAS ─────────────────────────────────────

    def should_alert(self, signal: dict, user_prefs: dict) -> bool:
        """
        Decide si este tenant/usuario debe recibir alerta por esta señal.

        Factores:
        - Severidad de la señal vs umbral configurado por el usuario
        - Regiones de interés del tenant
        - Tipos de señal suscritos
        """
        severity = signal.get("severity", 0.5)
        user_threshold = user_prefs.get("alert_threshold", ALERT_THRESHOLD)

        if severity < user_threshold:
            return False

        # Verificar regiones de interés
        regions_of_interest = user_prefs.get("regions_of_interest", [])
        if regions_of_interest:
            signal_country = signal.get("country", "")
            signal_region  = signal.get("region", "")
            if signal_country not in regions_of_interest and \
               signal_region not in regions_of_interest:
                return False

        # Verificar tipos suscritos
        subscribed_types = user_prefs.get("signal_types", list(SIGNAL_TYPES.keys()))
        if signal.get("type") not in subscribed_types:
            return False

        return True

    def build_alert_content(self, signal: dict, cognitive_profile: dict) -> dict:
        """
        Genera el contenido de la alerta adaptado al perfil cognitivo del usuario.
        Esto reutiliza el sistema de personalización cognitiva de NEXO.
        """
        vocab = cognitive_profile.get("vocabulary", "simple")
        length = cognitive_profile.get("content_length", "200w")
        tone   = cognitive_profile.get("tone", "formal")

        # Longitud del resumen según preferencia
        max_chars = {"50w": 250, "200w": 1000, "full": 3000}.get(length, 500)
        summary   = (signal.get("summary") or "")[:max_chars]

        severity_label = {
            (0.0, 0.4): "Bajo",
            (0.4, 0.7): "Moderado",
            (0.7, 0.9): "Alto",
            (0.9, 1.1): "Crítico",
        }
        sev = signal.get("severity", 0.5)
        nivel = next((v for k, v in severity_label.items() if k[0] <= sev < k[1]), "Moderado")

        emoji = {
            "cii_spike":        "🚨",
            "geo_convergence":  "📍",
            "military_surge":   "⚔️",
            "news_cluster":     "📰",
            "threat_classified":"⚠️",
            "ais_anomaly":      "🚢",
            "protest_event":    "✊",
        }.get(signal.get("type", ""), "🔔")

        return {
            "subject": f"{emoji} [{nivel}] {signal.get('title', 'Alerta de inteligencia')}",
            "body": summary,
            "severity": nivel,
            "country": signal.get("country"),
            "type": SIGNAL_TYPES.get(signal.get("type", ""), "Evento"),
            "timestamp": signal.get("timestamp"),
            "source": "WorldMonitor",
        }


# ── ENDPOINTS FastAPI (agregar a api/worldmonitor.py) ──────────

from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/nexo/worldmonitor", tags=["WorldMonitor Integration"])


class SignalIngestionRequest(BaseModel):
    signals: list[dict]


class EnrichRequest(BaseModel):
    query: str
    country: Optional[str] = None
    severity_min: float = 0.0
    top_k: int = 8


@router.post("/ingest")
async def ingest_signals(body: SignalIngestionRequest, request: Request):
    """
    Recibe señales de WorldMonitor y las ingesta en el RAG del tenant.
    WorldMonitor puede llamar este endpoint con un webhook al detectar eventos.
    """
    tenant_slug = getattr(request.state, "tenant_slug", None)
    if not tenant_slug:
        raise HTTPException(status_code=401, detail="Tenant no identificado")

    bridge = WorldMonitorBridge(tenant_slug)
    result = bridge.ingest_batch(body.signals)
    return {"status": "ok", **result}


@router.post("/enrich")
async def enrich_context(body: EnrichRequest, request: Request):
    """
    WorldMonitor frontend puede llamar este endpoint para enriquecer
    una consulta con el contexto RAG del tenant (documentos internos,
    historial de conversaciones, preferencias).

    Ejemplo de uso desde WorldMonitor:
    - Usuario hace click en un país → WorldMonitor pide contexto
      de NEXO sobre ese país para ese tenant específico
    """
    tenant_slug = getattr(request.state, "tenant_slug", None)
    if not tenant_slug:
        raise HTTPException(status_code=401, detail="Tenant no identificado")

    bridge = WorldMonitorBridge(tenant_slug)
    results = bridge.query_intelligence(
        query=body.query,
        top_k=body.top_k,
        filter_country=body.country,
        filter_severity_min=body.severity_min,
    )

    return {
        "query": body.query,
        "tenant": tenant_slug,
        "results": results,
        "count": len(results),
    }


@router.get("/signals/latest")
async def get_latest_signals(request: Request, limit: int = 20):
    """Retorna las señales más recientes desde Supabase."""
    from backend.services.vector_db import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT content, metadata FROM public.nexo_documentos
            WHERE metadata->>'source' = 'worldmonitor'
            ORDER BY created_at DESC
            LIMIT $1
        """, limit)
    
    signals = [r['metadata'] for r in rows]
    return {"signals": signals, "count": len(signals)}


@router.get("/stats")
async def get_intelligence_stats(request: Request):
    """Dashboard de estadísticas de inteligencia para el tenant (Supabase)."""
    from backend.services.vector_db import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT COUNT(*) FROM public.nexo_documentos
            WHERE metadata->>'source' = 'worldmonitor'
        """)
    total = row[0] if row else 0

    return {
        "status": "ok",
        "total_signals": total,
        "engine": "supabase_pgvector",
        "signal_types": list(SIGNAL_TYPES.keys()),
    }
