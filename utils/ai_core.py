import logging
import os
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

_logger = logging.getLogger("nexo_ai_core")

# Central logger setup
def get_logger(name: str = "nexo_ai_core"):
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

# Central Gemini model setup (google.genai)
def get_gemini_model(api_key: str, model_name: str = "gemini-2.5-flash-lite"):
    if genai is None:
        raise ImportError("google-genai no instalado")
    return genai.Client(api_key=api_key), model_name

# Embedding function (legacy compat)
def get_gemini_embedding_model(api_key: str):
    if genai is None:
        raise ImportError("google-genai no instalado")
    return genai.Client(api_key=api_key)

# ── Gemini Embedding 2 ─────────────────────────────────────────────
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "text-embedding-004")
GEMINI_EMBED_DIMS = 768

def _get_genai_client(api_key: str = None):
    _key = api_key or os.getenv("GEMINI_API_KEY", "")
    if not _key or genai is None:
        return None
    return genai.Client(api_key=_key)

def _get_embed_client(api_key: str = None):
    """Cliente Gemini forzado a v1 — los embeddings no están en v1beta."""
    _key = api_key or os.getenv("GEMINI_API_KEY", "")
    if not _key or genai is None:
        return None
    try:
        from google.genai import Client as GenaiClient
        return GenaiClient(api_key=_key, http_options={"api_version": "v1"})
    except Exception:
        return genai.Client(api_key=_key)

def _embed_with_retry(client, text, max_retries=3):
    """Call embed_content with retry on 429 rate limits."""
    for attempt in range(max_retries + 1):
        try:
            result = client.models.embed_content(
                model=GEMINI_EMBED_MODEL,
                contents=text,
                config=genai_types.EmbedContentConfig(output_dimensionality=GEMINI_EMBED_DIMS),
            )
            if result and result.embeddings:
                return result.embeddings[0].values
            return None
        except Exception as e:
            err_str = str(e)
            if "429" in err_str and attempt < max_retries:
                wait = min(15 * (2 ** attempt), 90)
                _logger.info(f"Rate limited, waiting {wait}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    return None

def embed_text_gemini2(text: str, api_key: str = None) -> list[float] | None:
    """Genera embedding de documento usando google.genai v1 (embeddings solo en v1)."""
    try:
        client = _get_embed_client(api_key)
        if not client:
            return None
        return _embed_with_retry(client, text)
    except Exception as e:
        _logger.warning(f"embed_text_gemini2 error: {e}")
    return None

def embed_query_gemini2(text: str, api_key: str = None) -> list[float] | None:
    """Genera embedding de búsqueda usando google.genai v1."""
    try:
        client = _get_embed_client(api_key)
        if not client:
            return None
        return _embed_with_retry(client, text)
    except Exception as e:
        _logger.warning(f"embed_query_gemini2 error: {e}")
    return None
