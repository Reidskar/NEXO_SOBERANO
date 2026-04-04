"""
NEXO SOBERANO — Drive RAG Ingestion Pipeline
Indexa documentos de Google Drive en Qdrant para búsqueda semántica.

Flujo:
  Drive (archivos) → texto → embedding Gemini → Qdrant
  Consulta usuario → embedding → Qdrant nearest neighbors → contexto → IA

Colección Qdrant: "nexo_drive_docs"
"""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("NEXO.services.drive_rag")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
COLLECTION_NAME = "nexo_drive_docs"
VECTOR_SIZE = 768          # text-embedding-004 de Gemini
CHUNK_SIZE = 1500          # chars por chunk
CHUNK_OVERLAP = 200


# ════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════

def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Divide texto largo en chunks con overlap para no perder contexto."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return [c for c in chunks if len(c.strip()) > 50]


def _doc_id(file_id: str, chunk_idx: int) -> str:
    """ID único por chunk: hash(file_id + chunk_idx)"""
    raw = f"{file_id}_{chunk_idx}"
    return hashlib.md5(raw.encode()).hexdigest()


async def _embed_text(text: str) -> Optional[list[float]]:
    """Genera embedding con Gemini text-embedding-004."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        return result["embedding"]
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return None


async def _embed_query(text: str) -> Optional[list[float]]:
    """Embedding para búsqueda (task_type diferente optimiza recall)."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_query"
        )
        return result["embedding"]
    except Exception as e:
        logger.error(f"Query embedding error: {e}")
        return None


def _get_qdrant():
    """Obtiene cliente Qdrant, crea colección si no existe."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        kwargs = {"url": QDRANT_URL}
        if QDRANT_API_KEY:
            kwargs["api_key"] = QDRANT_API_KEY

        client = QdrantClient(**kwargs)

        existing = [c.name for c in client.get_collections().collections]
        if COLLECTION_NAME not in existing:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
            )
            logger.info(f"Colección '{COLLECTION_NAME}' creada en Qdrant.")

        return client
    except Exception as e:
        logger.warning(f"Qdrant no disponible: {e}")
        return None


# ════════════════════════════════════════════════════════════════════
# INGESTA
# ════════════════════════════════════════════════════════════════════

async def ingestar_archivo(file_id: str, nombre: str, contenido: str) -> int:
    """
    Indexa un archivo de Drive en Qdrant.
    Devuelve número de chunks indexados.
    """
    client = _get_qdrant()
    if not client:
        return 0

    chunks = _chunk_text(contenido)
    puntos = []

    for idx, chunk in enumerate(chunks):
        vector = await _embed_text(chunk)
        if not vector:
            continue

        from qdrant_client.models import PointStruct
        punto = PointStruct(
            id=_doc_id(file_id, idx),
            vector=vector,
            payload={
                "file_id": file_id,
                "nombre": nombre,
                "chunk_idx": idx,
                "texto": chunk,
                "ingested_at": datetime.now(timezone.utc).isoformat()
            }
        )
        puntos.append(punto)

    if puntos:
        client.upsert(collection_name=COLLECTION_NAME, points=puntos)
        logger.info(f"Drive RAG: '{nombre}' → {len(puntos)} chunks indexados.")

    return len(puntos)


async def ingestar_carpeta(folder_id: str) -> dict:
    """
    Ingesta completa de una carpeta Drive → Qdrant.
    Retorna resumen: {total_archivos, total_chunks, errores}.
    """
    from NEXO_CORE.services.drive_service import drive_service

    archivos = await drive_service.listar_archivos_carpeta(folder_id=folder_id, max_results=100)
    total_chunks = 0
    errores = []

    for archivo in archivos:
        try:
            contenido = await drive_service.leer_archivo_texto(archivo["id"])
            if not contenido or len(contenido) < 50:
                continue
            n = await ingestar_archivo(
                file_id=archivo["id"],
                nombre=archivo.get("name", "sin_nombre"),
                contenido=contenido
            )
            total_chunks += n
        except Exception as e:
            errores.append({"archivo": archivo.get("name"), "error": str(e)})

    return {
        "total_archivos": len(archivos),
        "total_chunks": total_chunks,
        "errores": errores
    }


# ════════════════════════════════════════════════════════════════════
# BÚSQUEDA SEMÁNTICA
# ════════════════════════════════════════════════════════════════════

async def buscar_semantico(query: str, top_k: int = 5, score_min: float = 0.35) -> list[dict]:
    """
    Búsqueda semántica en Qdrant.
    Retorna lista de {nombre, texto, score, file_id}.
    """
    client = _get_qdrant()
    if not client:
        return []

    vector = await _embed_query(query)
    if not vector:
        return []

    try:
        resultados = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector,
            limit=top_k,
            score_threshold=score_min,
            with_payload=True
        )
        return [
            {
                "nombre": r.payload.get("nombre"),
                "texto": r.payload.get("texto"),
                "score": round(r.score, 3),
                "file_id": r.payload.get("file_id"),
                "chunk_idx": r.payload.get("chunk_idx", 0)
            }
            for r in resultados
        ]
    except Exception as e:
        logger.error(f"Error búsqueda semántica: {e}")
        return []


async def stats_coleccion() -> dict:
    """Estadísticas de la colección Qdrant."""
    client = _get_qdrant()
    if not client:
        return {"disponible": False}
    try:
        info = client.get_collection(COLLECTION_NAME)
        return {
            "disponible": True,
            "coleccion": COLLECTION_NAME,
            "total_vectores": info.vectors_count,
            "total_puntos": info.points_count,
            "estado": str(info.status)
        }
    except Exception as e:
        return {"disponible": False, "error": str(e)}
