from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, JSONResponse
import logging
import tempfile
import os
import subprocess
from pathlib import Path
from backend.services.rag_service import get_rag_service

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
