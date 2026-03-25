# ============================================================
# NEXO SOBERANO — Social Media API
# © 2026 elanarcocapital.com
# Torre ejecuta, Railway expone resultados
# ============================================================
from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("NEXO.api.social")
router = APIRouter(prefix="/api/social", tags=["social"])


class TweetRequest(BaseModel):
    texto: str
    responder_a: Optional[str] = None
    media_path: Optional[str] = None


class MonitorRequest(BaseModel):
    keywords: list[str]
    max_resultados: Optional[int] = 20


class SentimientoRequest(BaseModel):
    texto: str
    pais: Optional[str] = "Chile"


@router.get("/health")
async def social_health():
    """Verifica qué servicios sociales están disponibles."""
    status = {}
    try:
        from backend.services.x_publisher import post_to_x  # noqa: F401
        status["twitter_publisher"] = "disponible"
    except Exception as e:
        status["twitter_publisher"] = f"no disponible: {e}"
    try:
        from backend.services.x_monitor import _state_path  # noqa: F401
        status["twitter_monitor"] = "disponible"
    except Exception as e:
        status["twitter_monitor"] = f"no disponible: {e}"
    try:
        from backend.services.intelligence.sentiment_engine import SentimentEngine  # noqa: F401
        status["sentiment"] = "disponible"
    except Exception as e:
        status["sentiment"] = f"no disponible: {e}"
    try:
        from backend.services.intelligence.social_parasite_tracker import SocialParasiteTracker  # noqa: F401
        status["parasite_tracker"] = "disponible"
    except Exception as e:
        status["parasite_tracker"] = f"no disponible: {e}"
    return {"status": status}


@router.post("/tweet")
async def publicar_tweet(req: TweetRequest):
    """Publica tweet. Requiere X_API_KEY/X_API_SECRET/X_ACCESS_TOKEN/X_ACCESS_SECRET en env."""
    try:
        from backend.services.x_publisher import post_to_x
        result = post_to_x(
            text=req.texto,
            media_path=req.media_path,
            in_reply_to=req.responder_a
        )
        return {"publicado": True, "resultado": result}
    except ImportError:
        raise HTTPException(503, "Twitter publisher no disponible")
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        logger.error(f"Error publicando tweet: {e}")
        raise HTTPException(500, str(e))


@router.post("/monitor")
async def monitorear_twitter(req: MonitorRequest):
    """Monitorea keywords en Twitter/X y sube resultados a Drive."""
    try:
        from backend.services.x_publisher import search_x_recent
        resultados = []
        for keyword in req.keywords[:5]:
            items = search_x_recent(keyword, max_results=req.max_resultados // len(req.keywords) or 5)
            if items:
                resultados.extend(items)
        return {"resultados": resultados, "total": len(resultados)}
    except ImportError:
        raise HTTPException(503, "Twitter monitor no disponible")
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        logger.error(f"Error monitoreando: {e}")
        raise HTTPException(500, str(e))


@router.post("/analizar-sentimiento")
async def analizar_sentimiento(req: SentimientoRequest):
    """Analiza temperatura social de un texto (Le Bon + praxeología)."""
    try:
        from backend.services.intelligence.sentiment_engine import SentimentEngine
        engine = SentimentEngine()
        resultado = await engine.analyze_social_temperature(
            text_samples=[req.texto],
            country=req.pais
        )
        return {"texto": req.texto, "pais": req.pais, "sentimiento": resultado}
    except ImportError:
        raise HTTPException(503, "Sentiment engine no disponible")
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/analizar-actores")
async def analizar_actores(articulos: list[str], pais: str = "Chile"):
    """Ranking de actores sociales por índice de parasitismo (economía austríaca)."""
    try:
        from backend.services.intelligence.social_parasite_tracker import SocialParasiteTracker
        tracker = SocialParasiteTracker()
        resultado = await tracker.evaluate_entities(articles=articulos, country=pais)
        return {"pais": pais, "actores": resultado}
    except ImportError:
        raise HTTPException(503, "Parasite tracker no disponible")
    except Exception as e:
        raise HTTPException(500, str(e))
