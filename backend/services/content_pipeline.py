"""
backend/services/content_pipeline.py
=====================================
Pipeline unificado: Grabación → Transcripción → Clasificación IA → Almacenamiento inteligente.

Fuentes soportadas:
  - OBS (grabación de pantalla PC via WebSocket)
  - Celular (scrcpy --record via ADB/Tailscale)
  - PC Screen directo (ffmpeg dshow/gdigrab)
  - Archivo existente (ingesta manual)

Flujo:
  1. start_capture(source, tag, research_id?)  →  session_id
  2. stop_capture(session_id)                  →  dispara pipeline async
  3. Pipeline: ffmpeg trim → Whisper → Gemini → Drive/Vault → Qdrant
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Paths & Config ────────────────────────────────────────────────────────────
VAULT_DIR   = Path(os.getenv("NEXO_VAULT_DIR", "exports/vault"))
JOBS_FILE   = Path(os.getenv("NEXO_PIPELINE_JOBS", "logs/pipeline_jobs.json"))
SCRCPY_EXE  = os.getenv("SCRCPY_PATH",
    r"C:\Users\Admn\AppData\Local\Microsoft\WinGet\Packages\Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe\scrcpy-win64-v3.3.4\scrcpy.exe")
ADB_EXE     = os.getenv("ADB_PATH",
    r"C:\Users\Admn\AppData\Local\Microsoft\WinGet\Packages\Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe\scrcpy-win64-v3.3.4\adb.exe")
TAILSCALE_PHONE = os.getenv("NEXO_PHONE_TAILSCALE", "100.83.26.14:5555")

VAULT_DIR.mkdir(parents=True, exist_ok=True)
JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)


# ── Job Store ─────────────────────────────────────────────────────────────────

def _load_jobs() -> dict:
    if JOBS_FILE.exists():
        try:
            return json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_jobs(jobs: dict):
    JOBS_FILE.write_text(json.dumps(jobs, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


# ── Pipeline ─────────────────────────────────────────────────────────────────

class ContentPipeline:
    """Orquesta captura, procesamiento y almacenamiento inteligente de contenido."""

    def __init__(self):
        self._active: dict[str, dict] = {}   # session_id → {proc, path, meta}
        self._jobs = _load_jobs()

    # ── CAPTURA ───────────────────────────────────────────────────────────────

    def start_capture(
        self,
        source: str = "phone",           # "phone" | "obs" | "screen" | "file"
        tag: str = "GEN",                # MIL, ECO, GEO, POL, PSY, GEN
        research_id: Optional[str] = None,
        file_path: Optional[str] = None, # solo para source="file"
        title: str = "",
    ) -> dict:
        session_id = str(uuid.uuid4())[:8]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_tag = tag.upper()[:6]
        out_name = f"{safe_tag}_{ts}_{session_id}.mp4"
        out_path = VAULT_DIR / "raw" / out_name
        out_path.parent.mkdir(parents=True, exist_ok=True)

        meta = {
            "id": session_id,
            "source": source,
            "tag": safe_tag,
            "research_id": research_id,
            "title": title,
            "out_path": str(out_path),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "recording",
        }

        if source == "file" and file_path:
            meta["out_path"] = file_path
            meta["status"] = "pending_process"
            self._active[session_id] = {"proc": None, "meta": meta}
            threading.Thread(target=self._run_pipeline, args=(session_id,), daemon=True).start()
            self._save_session(session_id, meta)
            return {"ok": True, "session_id": session_id, "status": "processing"}

        elif source == "phone":
            proc = self._start_scrcpy_record(str(out_path))
            if not proc:
                return {"ok": False, "error": "No se pudo iniciar scrcpy"}

        elif source == "obs":
            ok = self._start_obs_record()
            if not ok:
                return {"ok": False, "error": "OBS no disponible o no conectado"}
            proc = None  # OBS maneja su propio proceso

        elif source == "screen":
            proc = self._start_ffmpeg_screen(str(out_path))
            if not proc:
                return {"ok": False, "error": "No se pudo capturar pantalla PC"}
        else:
            return {"ok": False, "error": f"Fuente desconocida: {source}"}

        self._active[session_id] = {"proc": proc, "meta": meta}
        self._save_session(session_id, meta)
        logger.info(f"[PIPELINE] Grabación iniciada: {session_id} via {source}")
        return {"ok": True, "session_id": session_id, "out_path": str(out_path)}

    def stop_capture(self, session_id: str) -> dict:
        """Detiene la grabación y dispara el pipeline de procesamiento."""
        session = self._active.get(session_id)
        if not session:
            # Buscar en jobs guardados
            meta = self._jobs.get(session_id, {})
            if not meta:
                return {"ok": False, "error": "Sesión no encontrada"}
            session = {"proc": None, "meta": meta}

        meta = session["meta"]
        proc = session.get("proc")

        # Detener proceso
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()

        if meta["source"] == "obs":
            self._stop_obs_record()

        meta["status"] = "processing"
        meta["stopped_at"] = datetime.now(timezone.utc).isoformat()
        self._save_session(session_id, meta)

        # Lanzar pipeline async en thread
        threading.Thread(target=self._run_pipeline, args=(session_id,), daemon=True).start()
        logger.info(f"[PIPELINE] Grabación detenida: {session_id}. Procesando...")
        return {"ok": True, "session_id": session_id, "status": "processing"}

    # ── GRABADORES ────────────────────────────────────────────────────────────

    def _start_scrcpy_record(self, out_path: str) -> Optional[subprocess.Popen]:
        try:
            cmd = [
                SCRCPY_EXE,
                "--serial", TAILSCALE_PHONE,
                "--record", out_path,
                "--no-display",
                "--stay-awake",
            ]
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return proc
        except Exception as e:
            logger.error(f"[PIPELINE] scrcpy record error: {e}")
            return None

    def _start_ffmpeg_screen(self, out_path: str) -> Optional[subprocess.Popen]:
        """Captura pantalla PC via ffmpeg gdigrab."""
        try:
            cmd = [
                "ffmpeg", "-y",
                "-f", "gdigrab", "-framerate", "30",
                "-i", "desktop",
                "-f", "dshow", "-i", "audio=Mezcla estéreo (Realtek(R) Audio)",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-c:a", "aac",
                out_path
            ]
            proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return proc
        except Exception as e:
            logger.error(f"[PIPELINE] ffmpeg screen record error: {e}")
            return None

    def _start_obs_record(self) -> bool:
        try:
            import obsws_python as obs
            from NEXO_CORE import config as core_config
            client = obs.ReqClient(
                host=core_config.OBS_HOST, port=core_config.OBS_PORT,
                password=core_config.OBS_PASSWORD, timeout=3
            )
            client.start_record()
            return True
        except Exception as e:
            logger.warning(f"[PIPELINE] OBS record start failed: {e}")
            return False

    def _stop_obs_record(self):
        try:
            import obsws_python as obs
            from NEXO_CORE import config as core_config
            client = obs.ReqClient(
                host=core_config.OBS_HOST, port=core_config.OBS_PORT,
                password=core_config.OBS_PASSWORD, timeout=3
            )
            resp = client.stop_record()
            # OBS retorna la ruta del archivo grabado
            saved = getattr(resp, "output_path", None)
            return saved
        except Exception as e:
            logger.warning(f"[PIPELINE] OBS record stop failed: {e}")
            return None

    # ── PIPELINE DE PROCESAMIENTO ─────────────────────────────────────────────

    def _run_pipeline(self, session_id: str):
        """Transcribe → Clasifica → Almacena. Corre en thread separado."""
        meta = self._jobs.get(session_id, {})
        if not meta and session_id in self._active:
            meta = self._active[session_id]["meta"]

        file_path = Path(meta.get("out_path", ""))
        if not file_path.exists():
            logger.error(f"[PIPELINE] Archivo no encontrado: {file_path}")
            meta["status"] = "error"
            meta["error"] = f"Archivo no encontrado: {file_path}"
            self._save_session(session_id, meta)
            return

        try:
            # 1. Transcripción con Whisper
            logger.info(f"[PIPELINE] Transcribiendo: {file_path.name}")
            transcript = self._transcribe(file_path)
            meta["transcript"] = transcript[:2000]  # guardar primeros 2000 chars

            # 2. Clasificación IA con Gemini
            logger.info(f"[PIPELINE] Clasificando con Gemini...")
            classification = self._classify(file_path, transcript, meta.get("tag", "GEN"))
            meta["classification"] = classification

            # 3. Mover a carpeta clasificada en vault
            category = classification.get("categoria_jerarquica", [meta.get("tag", "GEN")])
            category_str = "/".join(category) if isinstance(category, list) else str(category)
            dest_dir = VAULT_DIR / category_str.replace(" ", "_")
            dest_dir.mkdir(parents=True, exist_ok=True)

            smart_name = classification.get("nombre_inteligente", file_path.name)
            dest = dest_dir / f"{smart_name}{file_path.suffix}"
            file_path.rename(dest)
            meta["final_path"] = str(dest)

            # 4. Guardar resumen en JSON junto al video
            summary_path = dest.with_suffix(".json")
            summary_path.write_text(
                json.dumps({
                    "session_id": session_id,
                    "title": meta.get("title", ""),
                    "transcript": transcript[:3000],
                    "analysis": classification.get("analisis", ""),
                    "keywords": classification.get("keywords", []),
                    "impact": classification.get("impacto", ""),
                    "research_id": meta.get("research_id"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            # 5. Indexar en Qdrant para búsqueda semántica
            self._index_in_qdrant(session_id, transcript, classification, meta)

            # 6. Notificar a Discord
            self._notify_discord(meta, classification)

            meta["status"] = "completed"
            logger.info(f"[PIPELINE] ✓ {session_id} → {dest}")

        except Exception as e:
            logger.error(f"[PIPELINE] Error en pipeline {session_id}: {e}", exc_info=True)
            meta["status"] = "error"
            meta["error"] = str(e)

        finally:
            self._save_session(session_id, meta)

    def _transcribe(self, file_path: Path) -> str:
        """Transcribe con Whisper GPU (faster-whisper)."""
        try:
            from backend.services.intelligence.media_processor import MediaIngestionService
            svc = MediaIngestionService(model_size="medium")
            return svc.transcribir(str(file_path))
        except Exception:
            pass
        # Fallback: ffmpeg extract + faster-whisper direct
        try:
            audio = file_path.with_suffix(".tmp_audio.wav")
            subprocess.run([
                "ffmpeg", "-y", "-i", str(file_path),
                "-ar", "16000", "-ac", "1", "-f", "wav", str(audio),
                "-loglevel", "quiet"
            ], timeout=120, check=True)
            from faster_whisper import WhisperModel
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute = "float16" if device == "cuda" else "int8"
            m = WhisperModel("medium", device=device, compute_type=compute)
            segs, _ = m.transcribe(str(audio), beam_size=5, vad_filter=True)
            text = " ".join(s.text.strip() for s in segs)
            audio.unlink(missing_ok=True)
            return text
        except Exception as e:
            logger.warning(f"[PIPELINE] Transcripción fallida: {e}")
            return ""

    def _classify(self, file_path: Path, transcript: str, tag: str) -> dict:
        """Clasifica contenido con Ollama local. Sin costo de API."""
        return self._classify_ollama(file_path, transcript, tag)

    def _classify_ollama(self, file_path: Path, transcript: str, tag: str) -> dict:
        """Fallback de clasificación usando Ollama local (qwen3.5)."""
        import asyncio, json as _json
        ts = datetime.now().strftime("%Y-%m-%d")
        prompt = f"""Eres NEXO SOBERANO, agente de inteligencia estratégica.
Analiza este contenido y responde SOLO con JSON válido (sin markdown):

TRANSCRIPT: {transcript[:1500]}
TAG_INICIAL: {tag}
FECHA: {ts}

Responde exactamente este JSON:
{{
  "analisis": "análisis breve",
  "etiqueta": "MIL|ECO|GEO|POL|PSY|GEN",
  "nombre_inteligente": "[TAG]_{ts}_Concepto",
  "categoria_jerarquica": ["CARPETA_PRINCIPAL", "Subcarpeta"],
  "impacto": "Crítico|Alto|Medio|Bajo",
  "keywords": ["kw1","kw2","kw3"],
  "resolucion": "CERTEZA|REVISION"
}}"""
        try:
            from NEXO_CORE.services.ollama_service import ollama_service
            loop = asyncio.new_event_loop()
            resp = loop.run_until_complete(
                ollama_service.consultar(prompt=prompt, modelo="general", temperature=0.05)
            )
            loop.close()
            if resp.success:
                raw = resp.text.strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                # Extraer JSON del texto si hay texto extra
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    raw = raw[start:end]
                return _json.loads(raw)
        except Exception as e2:
            logger.warning(f"[PIPELINE] Clasificación Ollama fallida: {e2}")
        return {"categoria_jerarquica": [tag], "nombre_inteligente": file_path.stem,
                "impacto": "Bajo", "keywords": []}

    def _index_in_qdrant(self, session_id: str, transcript: str, classification: dict, meta: dict):
        try:
            from backend.services.vector_db import get_vector_db
            vdb = get_vector_db()
            vdb.add_document(
                collection="nexo_content_vault",
                doc_id=session_id,
                text=transcript,
                metadata={
                    "tag": classification.get("etiqueta", "GEN"),
                    "impact": classification.get("impacto", ""),
                    "keywords": ", ".join(classification.get("keywords", [])),
                    "research_id": meta.get("research_id", ""),
                    "title": meta.get("title", ""),
                    "source": meta.get("source", ""),
                    "timestamp": meta.get("started_at", ""),
                }
            )
        except Exception as e:
            logger.warning(f"[PIPELINE] Qdrant indexing fallida: {e}")

    def _notify_discord(self, meta: dict, classification: dict):
        try:
            import httpx
            webhook = os.getenv("DISCORD_WEBHOOK_URL", "")
            if not webhook:
                return
            title = meta.get("title") or classification.get("nombre_inteligente", "Nuevo contenido")
            impact = classification.get("impacto", "")
            tag = classification.get("etiqueta", meta.get("tag", ""))
            analysis = classification.get("analisis", "")[:300]
            color = {"Crítico": 0xFF0000, "Alto": 0xFF6600, "Medio": 0xFFCC00}.get(impact, 0x00FFCC)
            httpx.post(webhook, json={"embeds": [{
                "title": f"[{tag}] {title}",
                "description": analysis,
                "color": color,
                "footer": {"text": f"Impacto: {impact} | NEXO Content Vault"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }]}, timeout=5)
        except Exception:
            pass

    # ── CONSULTA ──────────────────────────────────────────────────────────────

    def get_session(self, session_id: str) -> dict:
        return self._jobs.get(session_id, {})

    def list_sessions(self, limit: int = 20) -> list:
        jobs = list(self._jobs.values())
        jobs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        return jobs[:limit]

    def _save_session(self, session_id: str, meta: dict):
        self._jobs[session_id] = meta
        _save_jobs(self._jobs)


# Singleton
content_pipeline = ContentPipeline()
