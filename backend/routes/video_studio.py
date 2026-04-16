"""
NEXO SOBERANO — Video Studio
Pipeline: Contenido del día → Guión → TTS multi-idioma → Video (Reel/YouTube) → Upload

Endpoints:
  GET  /api/video/daily-content     — contenido subido hoy (Drive + sesiones)
  POST /api/video/generar-guion     — genera guión a partir del contenido
  POST /api/video/traducir          — traduce guión a ES/EN/PT
  POST /api/video/sintetizar-voz    — TTS con ElevenLabs u OpenAI TTS
  POST /api/video/compilar          — ensambla video final con ffmpeg
  POST /api/video/publicar          — sube a YouTube
  GET  /api/video/jobs              — lista todos los jobs de video
  GET  /api/video/jobs/{job_id}     — estado de un job
"""

from __future__ import annotations

import os
import uuid
import json
import shutil
import logging
import tempfile
import asyncio
import subprocess
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Dict, List, Optional, Any

import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/video", tags=["video-studio"])

# ─── Config ──────────────────────────────────────────────────────────────────
OPENAI_KEY      = lambda: os.getenv("OPENAI_API_KEY", "")
ELEVEN_KEY      = lambda: os.getenv("ELEVENLABS_API_KEY", "")
ELEVEN_VOICE_ES = lambda: os.getenv("ELEVENLABS_VOICE_ES", os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB"))
ELEVEN_VOICE_EN = lambda: os.getenv("ELEVENLABS_VOICE_EN", "EXAVITQu4vr4xnSDxMaL")
ELEVEN_VOICE_PT = lambda: os.getenv("ELEVENLABS_VOICE_PT", "VR6AewLTigWG4xSOukaG")

JOBS_DIR = Path(os.getenv("NEXO_JOBS_DIR", r"C:\Users\Admn\Desktop\NEXO_SOBERANO\exports\video_jobs"))
JOBS_DIR.mkdir(parents=True, exist_ok=True)

VOICE_IDS = {"es": ELEVEN_VOICE_ES, "en": ELEVEN_VOICE_EN, "pt": ELEVEN_VOICE_PT}

IDIOMA_LABELS = {"es": "Español", "en": "English", "pt": "Português"}

# ─── Job storage (simple JSON en disco) ──────────────────────────────────────

def _job_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"

def save_job(job: Dict) -> None:
    with open(_job_path(job["id"]), "w", encoding="utf-8") as f:
        json.dump(job, f, ensure_ascii=False, indent=2, default=str)

def load_job(job_id: str) -> Optional[Dict]:
    p = _job_path(job_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def list_jobs() -> List[Dict]:
    jobs = []
    for p in sorted(JOBS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            jobs.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return jobs[:50]

def new_job(tipo: str, idiomas: List[str], formato: str, titulo: str) -> Dict:
    job_id = str(uuid.uuid4())[:8]
    job = {
        "id": job_id,
        "tipo": tipo,
        "titulo": titulo,
        "formato": formato,
        "idiomas": idiomas,
        "estado": "pendiente",
        "creado_en": datetime.now(timezone.utc).isoformat(),
        "pasos": [],
        "videos": {},  # {idioma: path_o_url}
        "guiones": {},  # {idioma: texto}
        "youtube_ids": {},  # {idioma: video_id}
        "error": None,
    }
    save_job(job)
    return job

def update_job(job_id: str, **kwargs) -> Dict:
    job = load_job(job_id)
    if not job:
        raise ValueError(f"Job {job_id} no encontrado")
    job.update(kwargs)
    save_job(job)
    return job

def add_step(job_id: str, paso: str, estado: str = "ok", detalle: str = "") -> None:
    job = load_job(job_id)
    if not job:
        return
    job.setdefault("pasos", []).append({
        "paso": paso, "estado": estado,
        "detalle": detalle,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    save_job(job)

# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _openai_chat(messages: List[Dict], max_tokens: int = 1500) -> str:
    """Genera texto con OpenAI GPT-4o; si no hay key, usa Ollama local."""
    if OPENAI_KEY():
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=OPENAI_KEY())
            resp = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"OpenAI falló: {e} — usando Ollama")
    # Fallback: Ollama local (gemma3:12b — rápido y capaz para guiones)
    import aiohttp, json as _json
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    model_name = os.getenv("OLLAMA_MODEL_VIDEO", "gemma3:12b")  # modelo específico para video
    # Construir mensajes pasando system + user por separado (mejor que concatenar)
    ollama_messages = [m for m in messages if m.get("role") in ("system", "user", "assistant")]
    if not ollama_messages:
        ollama_messages = [{"role": "user", "content": str(messages)}]
    logger.info(f"[VIDEO] Ollama guión con {model_name}, {sum(len(m['content']) for m in ollama_messages)} chars")
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{ollama_url}/api/chat", json={
                "model": model_name,
                "messages": ollama_messages,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": max_tokens}
            }, timeout=aiohttp.ClientTimeout(total=240)) as r:
                raw = await r.text(encoding="utf-8")
                d = _json.loads(raw)
                result = d.get("message", {}).get("content", "").strip()
                logger.info(f"[VIDEO] Guión generado: {len(result)} chars")
                return result
    except Exception as e:
        logger.error(f"[VIDEO] Ollama guión falló: {e}")
        return ""


async def _tts_elevenlabs(text: str, idioma: str, output_path: str) -> bool:
    key = ELEVEN_KEY()
    if not key:
        return False
    voice_id = VOICE_IDS.get(idioma, VOICE_IDS["es"])()
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
    }
    headers = {"xi-api-key": key, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code == 200:
                Path(output_path).write_bytes(r.content)
                return True
        logger.warning(f"ElevenLabs error {r.status_code}: {r.text[:200]}")
    except Exception as e:
        logger.error(f"ElevenLabs TTS error: {e}")
    return False


async def _tts_openai(text: str, output_path: str) -> bool:
    key = OPENAI_KEY()
    if not key:
        return False
    try:
        import openai
        client = openai.AsyncOpenAI(api_key=key)
        resp = await client.audio.speech.create(
            model="tts-1", voice="onyx", input=text[:4096]
        )
        Path(output_path).write_bytes(resp.content)
        return True
    except Exception as e:
        logger.error(f"OpenAI TTS error: {e}")
        return False


async def _tts_piper(text: str, idioma: str, output_path: str) -> bool:
    """
    TTS local con Piper TTS. Gratis, offline, ultra-rápido (0.05x RT).
    Sin dependencias Python — corre como subprocess.
    Voces instaladas: es_ES-davefx-medium
    """
    import asyncio, subprocess

    piper_dir  = os.getenv("PIPER_DIR",
        r"C:\Users\Admn\Desktop\NEXO_SOBERANO\tools\piper\piper")
    voices_dir = os.getenv("PIPER_VOICES_DIR",
        r"C:\Users\Admn\Desktop\NEXO_SOBERANO\tools\piper\voices")

    piper_exe = os.path.join(piper_dir, "piper.exe")
    if not Path(piper_exe).exists():
        logger.warning(f"[TTS] Piper no encontrado en {piper_exe}")
        return False

    # Mapeo de modelos por idioma
    models = {
        "es": os.path.join(voices_dir, "es_ES-davefx-medium.onnx"),
        "en": os.path.join(voices_dir, "en_US-lessac-medium.onnx"),
        "pt": os.path.join(voices_dir, "es_ES-davefx-medium.onnx"),  # fallback ES
    }
    model = models.get(idioma, models["es"])
    if not Path(model).exists():
        model = next(Path(voices_dir).glob("*.onnx"), None)
        if not model:
            logger.warning("[TTS] No hay modelos Piper en voices/")
            return False
        model = str(model)

    # Piper lee de stdin y escribe WAV a --output_file
    wav_path = output_path.replace(".mp3", ".wav")
    try:
        def _run():
            proc = subprocess.run(
                [piper_exe, "--model", model, "--output_file", wav_path],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=60,
            )
            return proc.returncode == 0 and Path(wav_path).exists()

        ok = await asyncio.to_thread(_run)
        if ok:
            # Renombrar a output_path si es .wav o convertir
            if output_path.endswith(".wav"):
                import shutil
                if wav_path != output_path:
                    shutil.move(wav_path, output_path)
            else:
                # Convertir WAV → MP3 con ffmpeg si está disponible
                import shutil as _sh
                ffmpeg = _sh.which("ffmpeg")
                if ffmpeg:
                    subprocess.run([ffmpeg, "-y", "-i", wav_path, "-b:a", "192k", output_path],
                                   capture_output=True, timeout=30)
                    Path(wav_path).unlink(missing_ok=True)
                else:
                    import shutil
                    shutil.move(wav_path, output_path)
            logger.info(f"[TTS] Piper generó audio: {output_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"[TTS] Piper error: {e}")
        return False


def _build_video_ffmpeg(
    audio_path: Optional[str],
    output_path: str,
    guion_text: str,
    formato: str = "reel",
    duration: int = 60,
) -> bool:
    """
    Ensambla video con ffmpeg:
    - Fondo oscuro premium (gradiente negro→verde oscuro)
    - Audio TTS superpuesto
    - Subtítulos generados desde el guión
    - Formato reel: 1080x1920 (9:16)  |  youtube: 1920x1080 (16:9)
    """
    ffmpeg = (
        os.getenv("FFMPEG_PATH") or
        shutil.which("ffmpeg") or
        r"C:\Users\Admn\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe"
    )
    if not ffmpeg or not Path(ffmpeg).exists():
        logger.error(f"ffmpeg no disponible en: {ffmpeg}")
        return False

    w, h = (1080, 1920) if formato == "reel" else (1920, 1080)
    tmp = Path(tempfile.mkdtemp())

    # Subtítulos SRT simples
    srt_path = str(tmp / "subs.srt")
    lines = [l.strip() for l in guion_text.split("\n") if l.strip()]
    srt_lines = []
    for i, line in enumerate(lines[:20]):
        t_start = i * (duration / max(len(lines[:20]), 1))
        t_end   = t_start + (duration / max(len(lines[:20]), 1))
        srt_lines.append(
            f"{i+1}\n"
            f"{_fmt_srt(t_start)} --> {_fmt_srt(t_end)}\n"
            f"{line[:80]}\n"
        )
    Path(srt_path).write_text("\n".join(srt_lines), encoding="utf-8")

    # Construir filtro de video
    vf_parts = [
        f"scale={w}:{h}:force_original_aspect_ratio=increase",
        f"crop={w}:{h}",
    ]
    try:
        vf_parts.append(
            f"subtitles='{srt_path}':force_style="
            f"'FontName=Courier New,FontSize=24,PrimaryColour=&H00FFFFFF,"
            f"OutlineColour=&H00000000,Outline=2,Alignment=2,MarginV=80'"
        )
    except Exception:
        pass
    vf = ",".join(vf_parts)

    # Fondo: color negro (gradiente simulado con lavfi)
    bg_filter = f"color=c=0x080808:size={w}x{h}:rate=24,format=yuv420p"

    cmd = [ffmpeg, "-y"]

    if audio_path and Path(audio_path).exists():
        # Con audio TTS
        cmd += [
            "-f", "lavfi", "-i", bg_filter,
            "-i", audio_path,
            "-shortest",
        ]
        cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k", output_path]
    else:
        # Sin audio — video solo imagen
        cmd += [
            "-f", "lavfi", "-i", bg_filter,
            "-t", str(duration),
        ]
        cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-an", output_path]

    logger.info(f"ffmpeg cmd: {' '.join(cmd[:10])}...")
    result = subprocess.run(cmd, capture_output=True, timeout=300)

    shutil.rmtree(tmp, ignore_errors=True)

    if result.returncode != 0:
        logger.error(f"ffmpeg error: {result.stderr.decode()[:500]}")
        return False
    return True


def _fmt_srt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ─── GET /api/video/daily-content ────────────────────────────────────────────

@router.get("/daily-content")
async def daily_content(max_items: int = 30):
    """Contenido del día: sesiones NEXO + archivos Drive recientes."""
    today = date.today().isoformat()
    result: Dict[str, Any] = {
        "fecha": today,
        "sesiones": [],
        "drive_files": [],
        "total": 0,
    }

    # Sesiones del día (desde backend/sesiones si está disponible)
    try:
        from backend.routes.sesiones import router as _
        # Intentar cargar directamente desde DB/sesiones
        from backend.services.rag_service import get_rag_service
        rag = get_rag_service()
        pass
    except Exception:
        pass

    # Archivos Drive recientes
    try:
        from services.connectors.google_connector import list_recent_files_detailed
        files = list_recent_files_detailed(max_results=max_items)
        result["drive_files"] = [
            {
                "id": f.get("id"),
                "nombre": f.get("name"),
                "tipo": f.get("mimeType"),
                "creado": f.get("createdTime", ""),
            }
            for f in files
        ]
    except Exception as e:
        result["drive_error"] = str(e)

    result["total"] = len(result["drive_files"]) + len(result["sesiones"])
    return result


# ─── Models ──────────────────────────────────────────────────────────────────

class GuionRequest(BaseModel):
    contenido: str = Field(..., description="Texto base (resumen del día, noticias, análisis)")
    formato: str = Field(default="reel", description="'reel' (60s) o 'youtube' (3-5 min)")
    idioma_base: str = Field(default="es", description="Idioma del contenido original")
    dominio: Optional[str] = Field(default="libre")
    titulo: Optional[str] = Field(default="")


class TraducirRequest(BaseModel):
    guion: str
    idioma_origen: str = "es"
    idiomas_destino: List[str] = Field(default=["en", "pt"])


class CompilacionRequest(BaseModel):
    job_id: Optional[str] = None
    contenido: str
    titulo: str = "NEXO SOBERANO — Análisis Diario"
    formato: str = "reel"           # reel | youtube
    idiomas: List[str] = ["es"]     # ["es", "en", "pt"]
    dominio: str = "libre"
    publicar: bool = False          # si True → intenta subir a YouTube tras compilar


class PublicarRequest(BaseModel):
    job_id: str
    idioma: str = "es"
    privacy_status: str = "public"
    titulo_override: Optional[str] = None


# ─── POST /api/video/generar-guion ───────────────────────────────────────────

@router.post("/generar-guion")
async def generar_guion(req: GuionRequest):
    """Genera guión de video a partir del contenido del día."""
    dur_label = "60 segundos (máximo 150 palabras)" if req.formato == "reel" else "3 a 5 minutos (máximo 600 palabras)"
    domain_hint = {
        "geo": "Geopolítica y relaciones internacionales",
        "conducta": "Conducta de líderes y psicología del poder",
        "masas": "Control de masas y narrativas sociales",
        "eco_aus": "Economía austríaca y libertad económica",
        "poder": "Escenarios de poder y geoestrategia",
        "osint": "Inteligencia de fuentes abiertas",
    }.get(req.dominio or "libre", "Análisis geopolítico y de inteligencia")

    system = (
        "Eres el guionista de NEXO SOBERANO, un sistema de inteligencia estratégica. "
        "Escribes guiones para videos de alto impacto con maestría en:\n"
        "- PSICOANÁLISIS: Activas el inconsciente del espectador. Usas palabras que evocan miedo, "
        "curiosidad y pertenencia. Conectas el evento externo con la experiencia interna del individuo.\n"
        "- METACOGNICIÓN: Haces que el espectador piense sobre su propio pensamiento. "
        "Cuestionas narrativas establecidas. Activas el modo crítico.\n"
        "- PSICOLOGÍA DE MASAS (Le Bon, Freud, Bernays): Entiendes que el espectador no consume solo — "
        "pertenece a una tribu. Usas lenguaje que une a 'los que ven' contra 'los que no ven'.\n"
        "- MARKETING ESTRATÉGICO: Cada oración tiene un propósito. El gancho captura. "
        "El desarrollo convence. El cierre retiene y llama a compartir.\n"
        "Tono: analítico, sobrio, con autoridad. Nunca sensacionalista. Siempre basado en datos."
    )
    user = (
        f"Escribe un guión narrado para un video de {dur_label} sobre el siguiente contenido.\n"
        f"Dominio de análisis: {domain_hint}\n"
        f"Formato: {req.formato}\n\n"
        f"CONTENIDO BASE:\n{req.contenido[:4000]}\n\n"
        "El guión debe:\n"
        "- GANCHO (1 oración): Una verdad incómoda o paradoja que active la disonancia cognitiva\n"
        "- DESARROLLO: Puntos clave con datos concretos. Conecta lo macro (geopolítica) con lo micro (impacto personal)\n"
        "- CIERRE: Conclusión que genere sensación de haber 'despertado'. Llamado implícito a compartir.\n"
        "- Estar optimizado para ser NARRADO en voz (sin listas, sin viñetas, sin emojis)\n"
        "- Párrafos cortos de 1-2 oraciones separados por salto de línea\n"
        f"- Estar en {IDIOMA_LABELS.get(req.idioma_base, 'Español')}\n\n"
        "Solo entrega el guión, sin encabezados ni explicaciones."
    )

    guion = await _openai_chat([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ], max_tokens=800 if req.formato == "reel" else 2000)

    return {
        "ok": True,
        "guion": guion,
        "formato": req.formato,
        "idioma": req.idioma_base,
        "palabras": len(guion.split()),
        "titulo_sugerido": req.titulo or f"NEXO — {domain_hint} · {date.today().isoformat()}",
    }


# ─── POST /api/video/traducir ────────────────────────────────────────────────

@router.post("/traducir")
async def traducir_guion(req: TraducirRequest):
    """Traduce un guión a múltiples idiomas manteniendo estilo y tono."""
    if not OPENAI_KEY():
        raise HTTPException(503, "OPENAI_API_KEY no configurada")

    LANG_NAMES = {"es": "Spanish", "en": "English", "pt": "Brazilian Portuguese", "fr": "French"}

    resultados = {}
    for idioma in req.idiomas_destino:
        if idioma == req.idioma_origen:
            resultados[idioma] = req.guion
            continue
        lang_name = LANG_NAMES.get(idioma, idioma)
        prompt = (
            f"Translate the following narration script to {lang_name}. "
            "Preserve the analytical tone, impact, and structure exactly. "
            "Only return the translated script, no explanations.\n\n"
            f"SCRIPT:\n{req.guion}"
        )
        try:
            traduccion = await _openai_chat([{"role": "user", "content": prompt}], max_tokens=1500)
            resultados[idioma] = traduccion
        except Exception as e:
            resultados[idioma] = f"[Error traduciendo a {idioma}: {e}]"

    return {"ok": True, "traducciones": resultados}


# ─── POST /api/video/sintetizar-voz ─────────────────────────────────────────

@router.post("/sintetizar-voz/{job_id}/{idioma}")
async def sintetizar_voz(job_id: str, idioma: str):
    """Sintetiza TTS para un idioma de un job existente. Guarda el audio en el job."""
    job = load_job(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} no encontrado")

    guion = job.get("guiones", {}).get(idioma, "")
    if not guion:
        raise HTTPException(400, f"No hay guión para idioma '{idioma}' en job {job_id}")

    audio_path = str(JOBS_DIR / f"{job_id}_{idioma}_audio.mp3")

    ok = await _tts_elevenlabs(guion, idioma, audio_path)
    if not ok:
        ok = await _tts_openai(guion, audio_path)

    if ok:
        job.setdefault("audios", {})[idioma] = audio_path
        add_step(job_id, f"TTS {idioma}", "ok", f"Audio: {audio_path}")
        save_job(job)
        return {"ok": True, "audio_path": audio_path, "idioma": idioma}
    else:
        add_step(job_id, f"TTS {idioma}", "warning", "Sin TTS disponible, video sin audio")
        return {"ok": False, "message": "TTS no disponible (configura ELEVENLABS_API_KEY u OPENAI_API_KEY)"}


# ─── Background: pipeline completo ──────────────────────────────────────────

async def _run_pipeline(job_id: str, contenido: str, publicar: bool):
    """Pipeline completo en background: guión → traducciones → TTS → video → (upload)."""
    job = load_job(job_id)
    if not job:
        return

    try:
        update_job(job_id, estado="generando_guion")
        add_step(job_id, "Inicio pipeline", "ok")

        # 1. Generar guión en idioma base (ES)
        guion_req = GuionRequest(
            contenido=contenido,
            formato=job["formato"],
            idioma_base="es",
            dominio=job.get("dominio", "libre"),
            titulo=job["titulo"],
        )
        guion_result = await generar_guion(guion_req)
        guion_es = guion_result["guion"]
        job = update_job(job_id, guiones={"es": guion_es})
        add_step(job_id, "Guión ES", "ok", f"{guion_result['palabras']} palabras")

        # 2. Traducir a otros idiomas
        otros_idiomas = [i for i in job["idiomas"] if i != "es"]
        if otros_idiomas:
            update_job(job_id, estado="traduciendo")
            trad_req = TraducirRequest(guion=guion_es, idioma_origen="es", idiomas_destino=otros_idiomas)
            trad_result = await traducir_guion(trad_req)
            guiones = {"es": guion_es, **trad_result["traducciones"]}
            job = update_job(job_id, guiones=guiones)
            for idioma in otros_idiomas:
                add_step(job_id, f"Traducción {idioma}", "ok")

        # 3. TTS para cada idioma
        # Prioridad: Kokoro (gratis/local) → ElevenLabs → OpenAI
        update_job(job_id, estado="sintetizando_voz")
        audios: Dict[str, Optional[str]] = {}
        for idioma in job["idiomas"]:
            guion_idioma = job["guiones"].get(idioma, "")
            if not guion_idioma:
                continue
            audio_ext = "wav"  # Kokoro genera WAV; ElevenLabs/OpenAI generan MP3
            audio_path = str(JOBS_DIR / f"{job_id}_{idioma}_audio.{audio_ext}")

            # Intento 1: Piper local (gratis, 0.05x realtime)
            ok = await _tts_piper(guion_idioma, idioma, audio_path)
            if not ok:
                # Intento 2: ElevenLabs
                audio_path = str(JOBS_DIR / f"{job_id}_{idioma}_audio.mp3")
                ok = await _tts_elevenlabs(guion_idioma, idioma, audio_path)
            if not ok:
                # Intento 3: OpenAI
                ok = await _tts_openai(guion_idioma, audio_path)

            audios[idioma] = audio_path if ok else None
            add_step(job_id, f"TTS {idioma}", "ok" if ok else "warning",
                     "Con audio" if ok else "Sin audio — video mudo")

        job = update_job(job_id, audios=audios)

        # 4. Compilar video para cada idioma
        update_job(job_id, estado="compilando")
        videos: Dict[str, str] = {}
        for idioma in job["idiomas"]:
            video_path = str(JOBS_DIR / f"{job_id}_{idioma}.mp4")
            guion_idioma = job["guiones"].get(idioma, "")
            audio_path = audios.get(idioma)
            dur = 60 if job["formato"] == "reel" else 180

            ok_video = _build_video_ffmpeg(
                audio_path=audio_path,
                output_path=video_path,
                guion_text=guion_idioma,
                formato=job["formato"],
                duration=dur,
            )
            if ok_video:
                videos[idioma] = video_path
                add_step(job_id, f"Video {idioma}", "ok", video_path)
            else:
                add_step(job_id, f"Video {idioma}", "error", "ffmpeg falló")

        job = update_job(job_id, videos=videos)

        # 5. Publicar en YouTube si se solicitó
        if publicar and videos:
            update_job(job_id, estado="publicando")
            youtube_ids: Dict[str, str] = {}
            for idioma, video_path in videos.items():
                try:
                    from services.comunidad.youtube_reader import upload_video_summary
                    titulo_yt = f"{job['titulo']} [{IDIOMA_LABELS.get(idioma, idioma)}]"
                    yt_result = upload_video_summary(
                        title=titulo_yt,
                        description=f"Análisis generado por NEXO SOBERANO\n\n{job['guiones'].get(idioma, '')[:500]}",
                        file_bytes=Path(video_path).read_bytes(),
                        filename=f"nexo_{job_id}_{idioma}.mp4",
                        tags=["nexo_soberano", "geopolitica", idioma],
                        privacy_status="public",
                        category_id="25",
                    )
                    yt_id = yt_result.get("video_id") or yt_result.get("id") or ""
                    youtube_ids[idioma] = yt_id
                    add_step(job_id, f"YouTube {idioma}", "ok", f"ID: {yt_id}")
                except Exception as e:
                    add_step(job_id, f"YouTube {idioma}", "error", str(e))

            update_job(job_id, youtube_ids=youtube_ids)

        update_job(job_id, estado="completado", completado_en=datetime.now(timezone.utc).isoformat())
        add_step(job_id, "Pipeline completado", "ok")

    except Exception as e:
        logger.error(f"Error en pipeline job {job_id}: {e}", exc_info=True)
        update_job(job_id, estado="error", error=str(e))
        add_step(job_id, "Error pipeline", "error", str(e))


# ─── POST /api/video/compilar ────────────────────────────────────────────────

@router.post("/compilar")
async def compilar_video(req: CompilacionRequest, background_tasks: BackgroundTasks):
    """Lanza el pipeline completo en background. Retorna job_id para tracking."""
    job = new_job(
        tipo=req.formato,
        idiomas=req.idiomas or ["es"],
        formato=req.formato,
        titulo=req.titulo,
    )
    job["dominio"] = req.dominio
    save_job(job)

    background_tasks.add_task(_run_pipeline, job["id"], req.contenido, req.publicar)

    return {
        "ok": True,
        "job_id": job["id"],
        "mensaje": f"Pipeline iniciado en background. Idiomas: {req.idiomas}. Formato: {req.formato}.",
        "track": f"/api/video/jobs/{job['id']}",
    }


# ─── POST /api/video/publicar ────────────────────────────────────────────────

@router.post("/publicar")
async def publicar_video(req: PublicarRequest):
    """Publica un video ya compilado en YouTube."""
    job = load_job(req.job_id)
    if not job:
        raise HTTPException(404, f"Job {req.job_id} no encontrado")

    video_path = job.get("videos", {}).get(req.idioma)
    if not video_path or not Path(video_path).exists():
        raise HTTPException(400, f"Video para idioma '{req.idioma}' no disponible en job {req.job_id}")

    try:
        from services.comunidad.youtube_reader import upload_video_summary
        titulo = req.titulo_override or f"{job['titulo']} [{IDIOMA_LABELS.get(req.idioma, req.idioma)}]"
        guion = job.get("guiones", {}).get(req.idioma, "")
        result = upload_video_summary(
            title=titulo,
            description=f"Análisis NEXO SOBERANO\n\n{guion[:500]}",
            file_bytes=Path(video_path).read_bytes(),
            filename=f"nexo_{req.job_id}_{req.idioma}.mp4",
            tags=["nexo_soberano", "geopolitica", req.idioma],
            privacy_status=req.privacy_status,
            category_id="25",
        )
        yt_id = result.get("video_id") or result.get("id") or ""
        job.setdefault("youtube_ids", {})[req.idioma] = yt_id
        save_job(job)
        add_step(req.job_id, f"YouTube publicado {req.idioma}", "ok", yt_id)
        return {"ok": True, "youtube_id": yt_id, "idioma": req.idioma}
    except Exception as e:
        raise HTTPException(500, f"Error publicando en YouTube: {e}")


# ─── GET /api/video/jobs ─────────────────────────────────────────────────────

@router.get("/jobs")
async def get_jobs():
    return {"jobs": list_jobs()}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = load_job(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} no encontrado")
    return job


@router.get("/jobs/{job_id}/descargar/{idioma}")
async def descargar_video(job_id: str, idioma: str):
    """Descarga el video compilado de un job."""
    job = load_job(job_id)
    if not job:
        raise HTTPException(404, "Job no encontrado")
    video_path = job.get("videos", {}).get(idioma)
    if not video_path or not Path(video_path).exists():
        raise HTTPException(404, "Video no disponible")
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=f"NEXO_{job_id}_{idioma}.mp4",
    )


# ─── POST /api/video/auto-reel ──────────────────────────────────────────────

class AutoReelRequest(BaseModel):
    formato: str = Field(default="reel", description="'reel' o 'youtube'")
    idiomas: List[str] = Field(default=["es"])
    dominio: str = Field(default="libre")
    max_drive_files: int = Field(default=10)
    publicar: bool = False
    titulo: Optional[str] = None


@router.post("/auto-reel")
async def auto_reel(req: AutoReelRequest, background_tasks: BackgroundTasks):
    """
    Pipeline automático: toma el contenido más reciente del Drive (carpetas geopolítica)
    + inteligencia del día → genera reel/youtube completo con narración y subtítulos.
    """
    # 1. Recolectar contenido del Drive
    drive_content_parts: List[str] = []

    try:
        from services.connectors.google_connector import list_recent_files_detailed
        files = list_recent_files_detailed(max_results=req.max_drive_files)
        for f in files[:req.max_drive_files]:
            nombre = f.get("name", "")
            desc = f.get("description", "") or ""
            if nombre or desc:
                drive_content_parts.append(f"• {nombre}: {desc}"[:200])
    except Exception as e:
        logger.warning(f"[AUTO-REEL] Error obteniendo Drive: {e}")

    # 2. Agregar inteligencia del día (magazine si existe)
    from pathlib import Path as _Path
    today = datetime.now().strftime("%Y%m%d")
    magazine_path = _Path(f"reports/magazine_{today}.md")
    if magazine_path.exists():
        drive_content_parts.insert(0, magazine_path.read_text(encoding="utf-8")[:3000])

    # 3. Fallback: usar últimas sesiones de la bóveda
    if not drive_content_parts:
        import sqlite3 as _sq
        try:
            conn = _sq.connect("boveda.db")
            conn.row_factory = _sq.Row
            rows = conn.execute(
                "SELECT categoria, resumen_ia FROM evidencia ORDER BY fecha_ingesta DESC LIMIT 10"
            ).fetchall()
            conn.close()
            for r in rows:
                drive_content_parts.append(f"[{r['categoria']}] {r['resumen_ia']}")
        except Exception:
            pass

    if not drive_content_parts:
        raise HTTPException(400, "No hay contenido disponible. Sube archivos al Drive primero.")

    contenido = "\n\n".join(drive_content_parts)
    titulo = req.titulo or f"NEXO SOBERANO — {datetime.now().strftime('%d/%m/%Y')}"

    # 4. Crear job y lanzar pipeline
    job = new_job(tipo=req.formato, idiomas=req.idiomas, formato=req.formato, titulo=titulo)
    job["dominio"] = req.dominio
    job["auto_generated"] = True
    save_job(job)

    background_tasks.add_task(_run_pipeline, job["id"], contenido, req.publicar)

    return {
        "ok": True,
        "job_id": job["id"],
        "contenido_preview": contenido[:500],
        "fuentes": len(drive_content_parts),
        "mensaje": f"Auto-reel iniciado. Formato: {req.formato}. Idiomas: {req.idiomas}.",
        "track": f"/api/video/jobs/{job['id']}",
    }
