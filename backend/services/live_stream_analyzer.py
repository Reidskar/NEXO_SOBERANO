"""
Live Stream AI Analyzer — RTX 3060 GPU accelerated
Captura audio del stream OBS en tiempo real, transcribe con Whisper GPU
y genera sugerencias de temas/respuestas para Discord/chat.

Uso:
    from backend.services.live_stream_analyzer import analyzer
    analyzer.start()           # inicia en background
    analyzer.get_latest()      # obtiene última transcripción + análisis
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

CHUNK_SECONDS = 10       # analizar cada N segundos de audio
SAMPLE_RATE = 16000      # Whisper requiere 16kHz
MODEL_SIZE = "medium"    # medium = buen balance velocidad/calidad en 3060


class LiveStreamAnalyzer:
    def __init__(self):
        self._whisper = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._results: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def _load_whisper(self):
        if self._whisper is not None:
            return self._whisper
        try:
            import torch
            from faster_whisper import WhisperModel
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute = "float16" if device == "cuda" else "int8"
            logger.info(f"Cargando Whisper {MODEL_SIZE} en {device} ({compute})")
            self._whisper = WhisperModel(MODEL_SIZE, device=device, compute_type=compute)
            logger.info("Whisper GPU listo para transcripción en vivo")
            return self._whisper
        except Exception as e:
            logger.error(f"Error cargando Whisper: {e}")
            return None

    def transcribe_file(self, audio_path: str) -> Dict:
        """Transcribe un archivo de audio con GPU. Retorna texto + segmentos."""
        model = self._load_whisper()
        if not model:
            return {"ok": False, "text": "", "error": "Modelo no disponible"}
        try:
            segments, info = model.transcribe(
                audio_path,
                beam_size=5,
                language="es",
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
            )
            text = " ".join(s.text.strip() for s in segments)
            return {
                "ok": True,
                "text": text,
                "language": info.language,
                "duration": round(info.duration, 1),
            }
        except Exception as e:
            logger.error(f"Error en transcripción: {e}")
            return {"ok": False, "text": "", "error": str(e)}

    def transcribe_stream_chunk(self, audio_bytes: bytes, sample_rate: int = SAMPLE_RATE) -> Dict:
        """Transcribe chunk de bytes PCM16 directamente (para OBS virtual mic)."""
        import io, tempfile, os
        model = self._load_whisper()
        if not model:
            return {"ok": False, "text": "", "error": "Modelo no disponible"}
        try:
            import numpy as np
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            segments, info = model.transcribe(
                audio_array,
                beam_size=3,
                language="es",
                vad_filter=True,
            )
            text = " ".join(s.text.strip() for s in segments)
            return {"ok": True, "text": text, "language": info.language}
        except Exception as e:
            return {"ok": False, "text": "", "error": str(e)}

    def get_latest(self, n: int = 5) -> List[Dict]:
        """Retorna las últimas N transcripciones analizadas."""
        with self._lock:
            return list(self._results[-n:])

    def get_status(self) -> Dict:
        """Estado del analizador para el health check."""
        try:
            import torch
            gpu_available = torch.cuda.is_available()
            gpu_name = torch.cuda.get_device_name(0) if gpu_available else None
        except Exception:
            gpu_available, gpu_name = False, None
        return {
            "running": self._running,
            "model_loaded": self._whisper is not None,
            "gpu_available": gpu_available,
            "gpu_name": gpu_name,
            "transcriptions": len(self._results),
        }


# Instancia global
analyzer = LiveStreamAnalyzer()
