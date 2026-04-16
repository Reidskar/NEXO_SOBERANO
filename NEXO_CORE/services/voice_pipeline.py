import logging, tempfile, os
from pathlib import Path

logger = logging.getLogger(__name__)

async def transcribir(audio_bytes: bytes) -> str:
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cpu", compute_type="int8")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp = f.name
        segments, _ = model.transcribe(tmp, language="es")
        texto = " ".join(s.text for s in segments).strip()
        os.unlink(tmp)
        return texto
    except ImportError:
        logger.warning("faster-whisper no instalado")
        return ""
    except Exception as e:
        logger.error("STT error: %s", e)
        return ""

async def consultar_nexo(texto: str) -> str:
    try:
        import httpx
        url = os.getenv("NEXO_BACKEND_URL", "http://localhost:8080")
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{url}/api/ai/consultar",
                           json={"query": texto},
                           headers={"X-NEXO-API-KEY": os.getenv("NEXO_API_KEY","")})
            return r.json().get("answer", "Sin respuesta")
    except Exception as e:
        return f"Error: {e}"

async def sintetizar(texto: str) -> bytes:
    try:
        from gtts import gTTS
        import io
        buf = io.BytesIO()
        gTTS(text=texto, lang="es").write_to_fp(buf)
        return buf.getvalue()
    except Exception as e:
        logger.error("TTS error: %s", e)
        return b""
