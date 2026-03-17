"""
OSINT YouTube Video Extractor
Ingiere videos de YouTube, extrae transcripciones y las indexa en Qdrant.
Colección: "youtube_osint" (independiente de las colecciones por tenant)
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

COLLECTION_NAME = "youtube_osint"
CHUNK_SIZE = 500       # caracteres por chunk
CHUNK_OVERLAP = 80     # overlap entre chunks


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _extract_video_id(url_or_id: str) -> str:
    """Extrae el video_id de una URL de YouTube o lo devuelve tal cual."""
    patterns = [
        r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for p in patterns:
        m = re.search(p, url_or_id)
        if m:
            return m.group(1)
    raise ValueError(f"No se pudo extraer video_id de: {url_or_id!r}")


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Divide texto en chunks con overlap."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return [c for c in chunks if c.strip()]


def _stable_point_id(video_id: str, chunk_idx: int) -> str:
    """Genera un UUID v5-like determinista a partir de video_id + chunk_idx."""
    import uuid
    namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    return str(uuid.uuid5(namespace, f"{video_id}:{chunk_idx}"))


# ---------------------------------------------------------------------------
# Qdrant helpers
# ---------------------------------------------------------------------------

def _get_client():
    """Retorna el cliente Qdrant (lazy, mismo patrón que vector_service)."""
    import os
    from qdrant_client import QdrantClient
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY") or None
    return QdrantClient(url=url, api_key=api_key)


def _ensure_collection(client) -> None:
    """Crea la colección youtube_osint si no existe."""
    from qdrant_client.models import Distance, VectorParams
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        logger.info("Colección Qdrant creada: %s", COLLECTION_NAME)


def _video_already_indexed(client, video_id: str) -> bool:
    """Verifica si video_id ya tiene puntos en Qdrant (deduplicación)."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    try:
        results = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="video_id", match=MatchValue(value=video_id))]
            ),
            limit=1,
            with_payload=False,
            with_vectors=False,
        )
        return len(results[0]) > 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Transcripción
# ---------------------------------------------------------------------------

def _get_transcript(video_id: str) -> Dict:
    """
    Obtiene transcripción con youtube_transcript_api.
    Retorna {"ok": bool, "text": str, "error": str|None}
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["es", "en"])
        text = " ".join(seg.get("text", "").strip() for seg in transcript if seg.get("text"))
        return {"ok": True, "text": text}
    except Exception as exc:
        logger.warning("youtube_transcript_api falló para %s: %s", video_id, exc)
        return {"ok": False, "text": "", "error": str(exc)}


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

_model = None

def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Cargando SentenceTransformer para OSINT extractor...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def ingest_youtube_video(
    url_or_id: str,
    topic: Optional[str] = None,
    tenant_slug: str = "osint",
) -> Dict:
    """
    Ingiere un video de YouTube y lo indexa en Qdrant.

    Returns:
        {
            "video_id": str,
            "indexed": int,        # chunks indexados
            "duplicate": bool,     # ya existía en Qdrant
            "status": str,         # "indexed" | "duplicate" | "error"
            "error": str | None,
        }
    """
    # 1. Extraer video_id
    try:
        video_id = _extract_video_id(url_or_id)
    except ValueError as e:
        return {"video_id": None, "indexed": 0, "duplicate": False, "status": "error", "error": str(e)}

    # 2. Conectar a Qdrant
    try:
        client = _get_client()
        _ensure_collection(client)
    except Exception as e:
        logger.error("Error conectando a Qdrant: %s", e)
        return {"video_id": video_id, "indexed": 0, "duplicate": False, "status": "error", "error": str(e)}

    # 3. Deduplicación
    if _video_already_indexed(client, video_id):
        logger.info("Video ya indexado, retornando sin gastar tokens: %s", video_id)
        return {"video_id": video_id, "indexed": 0, "duplicate": True, "status": "duplicate", "error": None}

    # 4. Obtener transcripción
    result = _get_transcript(video_id)
    if not result["ok"] or not result["text"].strip():
        return {
            "video_id": video_id,
            "indexed": 0,
            "duplicate": False,
            "status": "error",
            "error": result.get("error", "Transcripción vacía"),
        }

    text = result["text"]

    # 5. Chunking semántico
    chunks = _chunk_text(text)
    if not chunks:
        return {"video_id": video_id, "indexed": 0, "duplicate": False, "status": "error", "error": "Sin chunks"}

    # 6. Embeddings + indexar en Qdrant
    try:
        from qdrant_client.models import PointStruct
        model = _get_model()
        vectors = model.encode(chunks).tolist()

        points = []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            points.append(
                PointStruct(
                    id=_stable_point_id(video_id, idx),
                    vector=vector,
                    payload={
                        "video_id": video_id,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "chunk_idx": idx,
                        "text": chunk,
                        "topic": topic or "general",
                        "tenant": tenant_slug,
                    },
                )
            )

        client.upsert(collection_name=COLLECTION_NAME, points=points)
        logger.info("Video %s indexado: %d chunks en %s", video_id, len(points), COLLECTION_NAME)
        return {
            "video_id": video_id,
            "indexed": len(points),
            "duplicate": False,
            "status": "indexed",
            "error": None,
        }

    except Exception as e:
        logger.error("Error indexando en Qdrant: %s", e)
        return {"video_id": video_id, "indexed": 0, "duplicate": False, "status": "error", "error": str(e)}
