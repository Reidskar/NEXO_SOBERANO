"""
Clasificador Semántico — RTX 3060 GPU
Clasifica archivos en categorías de inteligencia usando SentenceTransformer local.
Categorías: Inteligencia_Mercados | Estrategia_Geopolitica | Archivo_Personal

Uso:
    from backend.services.semantic_classifier import classifier
    categoria = classifier.classify(text="texto del documento", filename="doc.pdf")
"""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Categorías de inteligencia
CATEGORIES = {
    "Inteligencia_Mercados": [
        "economía mercado finanzas inversión bolsa bitcoin crypto dólar inflación deuda",
        "trading acciones commodities petróleo oro plata reservas banco central",
        "GDP PIB recesión deflación tasas interés fed reserva federal",
        "startup empresa negocio valuación fondos venture capital silicon valley",
        "libre mercado capitalismo comercio exportaciones importaciones aranceles",
    ],
    "Estrategia_Geopolitica": [
        "geopolítica guerra conflicto militar defensa OTAN NATO ejército",
        "Israel Palestina Gaza Hamas Hezbollah Irán Rusia Ucrania China",
        "Argentina política elecciones gobierno Milei libertad soberanía",
        "Estados Unidos Europa Asia geoestrategia inteligencia espionaje OSINT",
        "anarcocapitalismo libertarismo Estado poder territorio nación soberano",
        "guerra psicológica propaganda narrativa información contrainformación",
    ],
    "Archivo_Personal": [
        "personal familiar foto video recuerdo privado diario notas",
        "salud médico doctor consulta récord personal identidad documento",
        "casa hogar vida cotidiana agenda reunión personal",
    ],
}

# Embeddings pre-computados de las categorías (lazy)
_category_embeddings: Optional[Dict] = None
_model = None


def _get_model():
    global _model
    if _model is None:
        try:
            import torch
            from sentence_transformers import SentenceTransformer
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Cargando clasificador semántico en {device}")
            _model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
        except Exception as e:
            logger.error(f"Error cargando modelo clasificador: {e}")
    return _model


def _get_category_embeddings():
    global _category_embeddings
    if _category_embeddings is not None:
        return _category_embeddings

    model = _get_model()
    if not model:
        return None

    import numpy as np
    _category_embeddings = {}
    for cat, phrases in CATEGORIES.items():
        # Promedio de embeddings de todas las frases de la categoría
        embeddings = model.encode(phrases)
        _category_embeddings[cat] = np.mean(embeddings, axis=0)

    logger.info("Embeddings de categorías pre-computados")
    return _category_embeddings


def classify_text(text: str, filename: str = "") -> Tuple[str, float]:
    """
    Clasifica texto en una categoría de inteligencia.
    Retorna (categoria, score_confianza).
    """
    if not text or len(text.strip()) < 10:
        return _classify_by_filename(filename)

    model = _get_model()
    cat_embeddings = _get_category_embeddings()

    if not model or not cat_embeddings:
        return _classify_by_filename(filename)

    try:
        import numpy as np
        # Embed el texto (truncar si muy largo)
        sample = text[:2000]
        text_emb = model.encode([sample])[0]

        # Calcular similitud coseno con cada categoría
        best_cat = "Archivo_Personal"
        best_score = -1.0
        for cat, cat_emb in cat_embeddings.items():
            # Cosine similarity
            score = float(
                np.dot(text_emb, cat_emb) /
                (np.linalg.norm(text_emb) * np.linalg.norm(cat_emb) + 1e-8)
            )
            if score > best_score:
                best_score = score
                best_cat = cat

        return best_cat, round(best_score, 3)
    except Exception as e:
        logger.error(f"Error en clasificación semántica: {e}")
        return _classify_by_filename(filename)


def _classify_by_filename(filename: str) -> Tuple[str, float]:
    """Fallback: clasificación por nombre de archivo."""
    name = filename.lower()
    if any(k in name for k in ["mercado", "btc", "crypto", "finanzas", "trading", "economia"]):
        return "Inteligencia_Mercados", 0.6
    if any(k in name for k in ["geopolit", "guerra", "israel", "rusia", "osint", "inteligencia"]):
        return "Estrategia_Geopolitica", 0.6
    return "Archivo_Personal", 0.5


def file_hash(content: bytes) -> str:
    """SHA256 del contenido del archivo para deduplicación."""
    return hashlib.sha256(content).hexdigest()


def is_duplicate_in_qdrant(file_hash_str: str, collection: str = "nexo_osint") -> bool:
    """Verifica si el hash ya existe en Qdrant."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        url = os.getenv("QDRANT_URL", "http://localhost:6333")
        client = QdrantClient(url=url, timeout=3)
        if not client.collection_exists(collection):
            return False
        results = client.scroll(
            collection_name=collection,
            scroll_filter=Filter(
                must=[FieldCondition(key="file_hash", match=MatchValue(value=file_hash_str))]
            ),
            limit=1,
            with_payload=False,
            with_vectors=False,
        )
        return len(results[0]) > 0
    except Exception:
        return False


# Instancia global
class SemanticClassifier:
    def classify(self, text: str = "", filename: str = "", content: bytes = b"") -> Dict:
        """
        Clasifica un archivo. Retorna dict con categoria, score, hash.
        """
        hash_str = file_hash(content) if content else ""

        # Deduplicación
        if hash_str and is_duplicate_in_qdrant(hash_str):
            return {
                "categoria": None,
                "score": 0.0,
                "duplicate": True,
                "hash": hash_str,
            }

        cat, score = classify_text(text, filename)
        return {
            "categoria": cat,
            "score": score,
            "duplicate": False,
            "hash": hash_str,
        }

    def get_drive_folder(self, categoria: str) -> str:
        """Retorna el nombre de carpeta en Drive para cada categoría."""
        folders = {
            "Inteligencia_Mercados": "NEXO/Inteligencia_Mercados",
            "Estrategia_Geopolitica": "NEXO/Estrategia_Geopolitica",
            "Archivo_Personal": "NEXO/Archivo_Personal",
        }
        return folders.get(categoria, "NEXO/Sin_Clasificar")


classifier = SemanticClassifier()
