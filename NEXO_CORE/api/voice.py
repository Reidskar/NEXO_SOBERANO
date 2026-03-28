from fastapi import APIRouter, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, JSONResponse
import logging
import tempfile
import os
import subprocess
from pathlib import Path
from pydantic import BaseModel
from backend.services.rag_service import get_rag_service
from NEXO_CORE.services.gemini_live_service import get_live_service

router = APIRouter(prefix="/api/voice", tags=["voice"])
logger = logging.getLogger(__name__)

@router.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    user_id: str = Form(...),
):
    """
    Recibe audio de Discord, lo transcribe (o usa Whisper), y dispara el RAG.
    """
    tmp_path = ""
    try:
        content = await audio.read()
        
        # 1. Guardar PCM (suponiendo que Discord envía PCM 48kHz o similar)
        # O si Discord envía OGG Opus, dependemos del cliente.
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # 2. Convertir a WAV 16kHz para Whisper
        wav_path = tmp_path + ".wav"
        subprocess.run([
            "ffmpeg", "-i", tmp_path, "-ar", "16000", "-ac", "1", "-f", "wav", wav_path, "-y", "-loglevel", "quiet"
        ], check=True)

        # 3. Transcribir con faster-whisper
        from faster_whisper import WhisperModel
        # Carga perezosa (en RAM) para no estallar el inicio
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(wav_path, language="es")
        transcript = " ".join(s.text for s in segments).strip()

        # Limpiar
        if os.path.exists(tmp_path): os.unlink(tmp_path)
        if os.path.exists(wav_path): os.unlink(wav_path)

        if not transcript:
            return JSONResponse(status_code=400, content={"error": "Audio silencioso o ininteligible"})

        # 4. Procesar RAG
        logger.info(f"[VOZ STT] Usuario {user_id} dijo: {transcript}")
        rag = get_rag_service()
        ans = rag.consultar(transcript, mode="fast", categoria=None)

        # 5. Sintetizar respuesta (TTS) al vuelo
        from gtts import gTTS
        # get("answer") depends on rag output, if it's a model could be ans.answer
        # backend.services.rag_service returns a dict in older versions, let's just use .get if dict or .answer if pydantic
        answer_text = ans.answer if hasattr(ans, 'answer') else ans.get("answer", "Lo siento, hubo un error.")
        
        tts = gTTS(text=answer_text, lang='es')
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_mp3:
            tts.save(tmp_mp3.name)
            mp3_data = Path(tmp_mp3.name).read_bytes()
        
        os.unlink(tmp_mp3.name)

        # Devolver MP3 binario directamente al bot, con la transcripción en Headers
        response = Response(content=mp3_data, media_type="audio/mpeg")
        response.headers["X-Transcript"] = transcript.encode('utf-8').hex()
        response.headers["X-Text-Answer"] = answer_text.encode('utf-8').hex()
        return response

    except Exception as e:
        logger.error(f"[VOZ] Error procesando STT/TTS: {e}")
        if os.path.exists(tmp_path): os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=str(e))


# ── Gemini Live — conversación en tiempo real ─────────────────────────────────

@router.get("/live/status")
async def live_status() -> dict:
    """Estado del servicio Gemini Live (voz/texto en tiempo real)."""
    svc = get_live_service()
    return {
        "available": svc.available,
        "model": svc.model,
        "modalities": ["TEXT", "AUDIO"],
        "ws_endpoint": "/api/voice/live/stream",
    }


class LiveAskRequest(BaseModel):
    text: str
    modality: str = "TEXT"


@router.post("/live/ask")
async def live_ask(body: LiveAskRequest):
    """
    Pregunta rápida texto→texto via Gemini Live (sin WebSocket).
    Para respuesta en audio usa el WebSocket /api/voice/live/stream.
    """
    svc = get_live_service()
    if not svc.available:
        return JSONResponse(
            status_code=503,
            content={"error": "Gemini Live no disponible — revisa GEMINI_API_KEY"},
        )
    parts: list[str] = []
    async for chunk in svc.chat(body.text, modality="TEXT"):
        if chunk["type"] == "text":
            parts.append(chunk["content"])
        elif chunk["type"] == "error":
            return JSONResponse(status_code=500, content={"error": chunk["content"]})
    return {"response": "".join(parts), "model": svc.model}


@router.websocket("/live/stream")
async def live_stream(websocket: WebSocket) -> None:
    """
    Sesión de voz en tiempo real con Gemini Live.

    Cliente → servidor:  {"text": "pregunta", "modality": "TEXT"|"AUDIO"}
    Servidor → cliente:  {"type": "text",  "content": "..."}
                         {"type": "audio", "data": "<base64 PCM 16-bit 24kHz mono>"}
                         {"type": "done"}
                         {"type": "error", "content": "..."}
    """
    await websocket.accept()
    svc = get_live_service()

    if not svc.available:
        await websocket.send_json(
            {"type": "error", "content": "Gemini Live no disponible — revisa GEMINI_API_KEY"}
        )
        await websocket.close(code=1011)
        return

    logger.info("[Live WS] Cliente conectado")
    try:
        while True:
            data = await websocket.receive_json()
            text: str = data.get("text", "").strip()
            modality: str = data.get("modality", "TEXT").upper()
            if not text:
                continue
            if modality not in ("TEXT", "AUDIO"):
                modality = "TEXT"
            logger.info(f"[Live WS] [{modality}] {text[:80]}")
            async for chunk in svc.chat(text, modality=modality):
                await websocket.send_json(chunk)
    except WebSocketDisconnect:
        logger.info("[Live WS] Cliente desconectado")
    except Exception as exc:
        logger.error(f"[Live WS] Error: {exc}")
        try:
            await websocket.send_json({"type": "error", "content": str(exc)})
        except Exception:
            pass
