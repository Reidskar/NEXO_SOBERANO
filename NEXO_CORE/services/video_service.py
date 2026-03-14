import subprocess, tempfile, os
from pathlib import Path

def extract_video_content(video_path: Path) -> str:
    parts = []
    
    # Paso 1: extraer audio y transcribir con Whisper
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            audio_path = tmp.name
        subprocess.run([
            "ffmpeg", "-i", str(video_path),
            "-ar", "16000", "-ac", "1", "-f", "wav",
            audio_path, "-y", "-loglevel", "quiet"
        ], check=True, timeout=120)
        
        from faster_whisper import WhisperModel
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_path, language="es")
        transcript = " ".join(s.text for s in segments).strip()
        if transcript:
            parts.append(f"[TRANSCRIPCIÓN]\n{transcript}")
        if os.path.exists(audio_path):
            os.unlink(audio_path)
    except Exception as e:
        parts.append(f"[Audio no disponible: {e}]")
    
    # Paso 2: analizar frame del segundo 30 con Gemini Vision
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key:
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                frame_path = tmp.name
            subprocess.run([
                "ffmpeg", "-i", str(video_path),
                "-ss", "00:00:30", "-vframes", "1",
                frame_path, "-y", "-loglevel", "quiet"
            ], check=True, timeout=30)
            
            if Path(frame_path).exists():
                from google import genai
                client = genai.Client(api_key=gemini_key)
                datos = Path(frame_path).read_bytes()
                # Note: using API v1.0.0 syntax for models.generate_content
                resp = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=[
                        "Describe en 2 oraciones qué se ve en este frame de video.",
                         {"mime_type": "image/jpeg", "data": datos}
                    ]
                )
                parts.append(f"[FRAME]\n{resp.text}")
                os.unlink(frame_path)
        except Exception as e:
            import logging
            logging.error(f"Error extracting video frame with Gemini: {e}")
    
    return "\n\n".join(parts) if parts else ""
