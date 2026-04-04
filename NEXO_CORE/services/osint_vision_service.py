import os
import logging
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("NEXO.services.osint_vision")

# Prompt unificado para extraer inteligencia geopolítica de medios
OSINT_VISION_PROMPT = """Eres un analista de inteligencia de código abierto (OSINT) de la plataforma NEXO SOBERANO.
Se te proporciona evidencia en forma de imagen (y posiblemente contexto de transcripción de audio).
Tu objetivo es analizar el contenido visual e identificar:
1. El país exacto o zona de conflicto principal donde ocurre o a la que pertenece esta situación (ej. "Rusia", "Ucrania", "Taiwán", "Israel", "Desconocido").
2. Un análisis táctico breve sobre qué activos, eventos militares, protestas o infraestructuras se observan.
3. Tags relevantes.

IMPORTANTE: Responde ÚNICAMENTE con un objeto JSON válido, sin delimitadores ```json ni texto adicional.
El formato debe ser EXACTAMENTE este:
{
  "pais": "Nombre_del_Pais",
  "analisis": "Tu reporte táctico y descripción de los hallazgos.",
  "tags": ["tag1", "tag2", "tag3"]
}
"""

class OsintVisionPipeline:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.model_name = "gemini-1.5-pro" # Usamos pro para mejor análisis visual si está disponible, sino flash
    
    def _call_gemini_vision(self, file_path: Path, context_text: Optional[str] = None) -> Dict[str, Any]:
        """Envía imagen a Gemini Vision con el prompt OSINT y retorna el JSON parseado."""
        if not self.gemini_key:
            raise RuntimeError("GEMINI_API_KEY no configurada.")
            
        from google import genai
        client = genai.Client(api_key=self.gemini_key)
        
        datos = file_path.read_bytes()
        mime_type = "image/jpeg" if file_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
        
        prompt = OSINT_VISION_PROMPT
        if context_text:
            prompt += f"\n\nCONTEXTO ADICIONAL (Audio Transcrito):\n{context_text}"
            
        try:
            resp = client.models.generate_content(
                model=self.model_name,
                contents=[
                    prompt,
                    {"mime_type": mime_type, "data": datos}
                ]
            )
            raw_text = resp.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:-3].strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:-3].strip()
                
            return json.loads(raw_text)
        except Exception as e:
            logger.error(f"Error parseando respuesta de Gemini Vision: {e}")
            return {
                "pais": "Desconocido",
                "analisis": f"Error procesando imagen mediante AI: {e}",
                "tags": ["error", "ia"]
            }

    def process_image(self, image_path: Path) -> Dict[str, Any]:
        """Procesa una imagen y retorna el OSINT intel."""
        logger.info(f"Analizando imagen para OSINT: {image_path.name}")
        intel = self._call_gemini_vision(image_path)
        intel["tipo_media"] = "imagen"
        return intel

    def process_video(self, video_path: Path) -> Dict[str, Any]:
        """Extrae audio -> transcribe, extrae keyframe -> Gemini Vision."""
        logger.info(f"Procesando video para OSINT: {video_path.name}")
        transcripcion = ""
        
        # 1. Extraer y Transcribir Audio
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
                audio_temp = tmp_audio.name
            
            # Extraer audio
            subprocess.run([
                "ffmpeg", "-i", str(video_path),
                "-ar", "16000", "-ac", "1", "-f", "wav",
                audio_temp, "-y", "-loglevel", "quiet"
            ], check=True, timeout=120)
            
            # Usar media_ingestion_service o fallback a faster_whisper
            try:
                from NEXO_CORE.services.media_ingestion_service import media_service
                transcripcion = media_service.transcribir(audio_temp)
            except Exception as e:
                logger.warning(f"Falla transcribe service externo, usando local: {e}")
                from faster_whisper import WhisperModel
                # Modelo ultra ligero para procesar rápido en pipeline OSINT
                model = WhisperModel("tiny", device="cpu", compute_type="int8")
                segments, _ = model.transcribe(audio_temp, language="es")
                transcripcion = " ".join(s.text for s in segments).strip()

        except Exception as e:
            logger.error(f"Error procesando audio del video OSINT: {e}")
            transcripcion = "(No se pudo transcribir audio o el video no contiene sonido)"
        finally:
            if os.path.exists(audio_temp):
                os.unlink(audio_temp)

        # 2. Extraer Keyframe central
        intel = {}
        frame_temp = None
        try:
            # Capturar duración para sacar el centro
            dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)]
            dur_out = subprocess.check_output(dur_cmd).decode("utf-8").strip()
            duration = float(dur_out) if dur_out else 30.0
            mid_point = min(duration / 2, 30.0) # Usa la mitad, o max 30 seg
            
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_img:
                frame_temp = tmp_img.name

            subprocess.run([
                "ffmpeg", "-i", str(video_path),
                "-ss", str(mid_point), "-vframes", "1",
                "-q:v", "2", frame_temp, "-y", "-loglevel", "quiet"
            ], check=True, timeout=30)
            
            intel = self._call_gemini_vision(Path(frame_temp), context_text=transcripcion)
            
        except Exception as e:
            logger.error(f"Error extrayendo frame del video: {e}")
            intel = {
                "pais": "Desconocido",
                "analisis": "Error procesando el flujo de video.",
                "tags": ["error_video"]
            }
        finally:
            if frame_temp and os.path.exists(frame_temp):
                os.unlink(frame_temp)

        intel["tipo_media"] = "video"
        if transcripcion:
            intel["transcripcion"] = transcripcion
            
        return intel

    def analyze_media(self, file_path: str) -> Dict[str, Any]:
        """Detecta tipo de archivo y lo envia al pipeline correcto."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"El archivo OSINT no existe: {file_path}")
            
        ext = path.suffix.lower()
        if ext in {".png", ".jpg", ".jpeg", ".webp"}:
            return self.process_image(path)
        elif ext in {".mp4", ".mkv", ".avi", ".mov", ".webm"}:
            return self.process_video(path)
        else:
            raise ValueError(f"Formato no soportado para análisis visual OSINT: {ext}")


osint_vision = OsintVisionPipeline()
