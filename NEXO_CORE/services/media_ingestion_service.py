import os
import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional, List
# from faster_whisper import WhisperModel (Cargado lazy en propiedad model para Slim Deploy)
from backend import config

logger = logging.getLogger(__name__)

class MediaIngestionService:
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model: Optional['WhisperModel'] = None
        self.ingestion_status: Dict[str, str] = {}

    @property
    def model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                logger.info(f"Cargando modelo Whisper ({self.model_size})...")
                # Usar CPU por defecto si no hay GPU configurada o disponible de forma sencilla
                # Auto-detect GPU (RTX 3060 / CUDA)
                try:
                    import torch
                    _device = "cuda" if torch.cuda.is_available() else "cpu"
                    _compute = "float16" if _device == "cuda" else "int8"
                except Exception:
                    _device, _compute = "cpu", "int8"
                logger.info(f"Whisper device={_device}, compute={_compute}")
                self._model = WhisperModel(self.model_size, device=_device, compute_type=_compute)
            except ImportError:
                logger.warning("faster_whisper no está instalado. El servicio de ingesta multimedia no estará funcional.")
                raise RuntimeError("El modelo Whisper no está disponible en este entorno.")
        return self._model

    def _extract_audio(self, media_path: Path) -> Path:
        """Extrae audio de video usando ffmpeg si es necesario."""
        if media_path.suffix.lower() in {'.mp3', '.wav', '.m4a', '.ogg'}:
            return media_path
        
        audio_path = media_path.with_suffix('.wav')
        logger.info(f"Extrayendo audio de {media_path} -> {audio_path}")
        
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", str(media_path),
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                str(audio_path)
            ], check=True, capture_output=True)
            return audio_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Error en ffmpeg: {e.stderr.decode()}")
            raise RuntimeError(f"FFmpeg falló al extraer audio: {e.stderr.decode()}")

    def transcribir(self, file_path: str, task_id: Optional[str] = None) -> str:
        """Transcribe archivo de audio/video."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        if task_id:
            self.ingestion_status[task_id] = "procesando"

        temp_audio = None
        try:
            # 1. Asegurar que tenemos audio
            temp_audio = self._extract_audio(path)
            
            # 2. Transcribir
            logger.info(f"Iniciando transcripción de {temp_audio}")
            segments, info = self.model.transcribe(str(temp_audio), beam_size=5)
            
            full_text = " ".join([segment.text for segment in segments])
            
            if task_id:
                self.ingestion_status[task_id] = "completado"
            
            return full_text.strip()

        except Exception as e:
            logger.error(f"Error en transcripción: {e}")
            if task_id:
                self.ingestion_status[task_id] = f"error: {str(e)}"
            raise
        finally:
            # No borramos el original, pero si creamos un temp_audio que no es el original, podríamos borrarlo
            if temp_audio and temp_audio != path and temp_audio.exists():
                try:
                    os.remove(temp_audio)
                except:
                    pass

    def get_status(self, task_id: str) -> str:
        return self.ingestion_status.get(task_id, "desconocido")

# Instancia global
media_service = MediaIngestionService()
