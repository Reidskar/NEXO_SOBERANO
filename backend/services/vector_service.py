import os
import uuid
import logging
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

from backend import config

# Cargar modelo localmente (instancia compartida) solo si estamos en modo local
model = None
if config.NEXO_MODE == "local":
    try:
        logger.info("Cargando SentenceTransformer (Modo LOCAL)...")
        model = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as e:
        logger.error(f"Error cargando modelo de embeddings: {e}")
else:
    logger.info("SentenceTransformer no cargado (Modo CLOUD)")

# Cliente Qdrant
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
try:
    client = QdrantClient(url=QDRANT_URL)
except Exception as e:
    logger.error(f"Error conectando a Qdrant en {QDRANT_URL}: {e}")
    client = None

def ensure_collection(tenant_slug: str) -> str:
    """Asegura que la colección del tenant exista en Qdrant."""
    if not client:
        return ""
    name = f"nexo_{tenant_slug.replace('-', '_')}"
    try:
        if not client.collection_exists(name):
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            logger.info(f"Colección Qdrant creada: {name}")
        return name
    except Exception as e:
        logger.error(f"Error asegurando colección Qdrant {name}: {e}")
        return ""

def upsert_document(tenant_slug: str, doc_id: str, text: str, metadata: dict):
    """Indexa un documento en Qdrant para un tenant específico."""
    if not client or not model:
        logger.error("Servicio de vectores no inicializado")
        return
    
    collection = ensure_collection(tenant_slug)
    if not collection: return

    try:
        vector = model.encode(text).tolist()
        client.upsert(
            collection_name=collection,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "doc_id": str(doc_id),
                        "text": text[:1000],  # Guardamos un snippet del texto original
                        "created_at": str(uuid.uuid1()), # Timestamp approx
                        **metadata
                    }
                )
            ]
        )
    except Exception as e:
        logger.error(f"Error en upsert Qdrant: {e}")

def search(tenant_slug: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Busca documentos similares en Qdrant para un tenant."""
    if not client or not model:
        logger.error("Servicio de vectores no inicializado")
        return []
    
    collection = f"nexo_{tenant_slug.replace('-', '_')}"
    try:
        if not client.collection_exists(collection):
            return []
        
        vector = model.encode(query).tolist()
        results = client.search(
            collection_name=collection,
            query_vector=vector,
            limit=limit
        )
        return [
            {
                "id": hit.payload.get("doc_id"),
                "score": hit.score,
                "text": hit.payload.get("text"),
                "metadata": {k: v for k, v in hit.payload.items() if k not in ["doc_id", "text"]}
            }
            for hit in results
        ]
    except Exception as e:
        logger.error(f"Error en búsqueda Qdrant: {e}")
        return []
