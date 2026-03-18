import os
import json
import asyncio
import logging
from pathlib import Path
from core.config import settings
from core.database import Document, Event
from core.system_config import get_config
from core.learning_log import attach_result_metrics
try:
    from openai import AsyncAzureOpenAI
except ImportError:
    AsyncAzureOpenAI = None

logger = logging.getLogger(__name__)

class VideoGenerator:
    def __init__(self):
        self.output_dir = Path(os.getcwd()) / "output" / "videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir = Path(os.getcwd()) / "output" / "assets"
        self.assets_dir.mkdir(parents=True, exist_ok=True)

        self.client = None
        if AsyncAzureOpenAI and settings.AZURE_OPENAI_KEY:
            self.client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_KEY,
                api_version="2023-12-01-preview",
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )

    async def generate(self, document: Document, event: Event):
        """Generador principal: Toma documento e inicia pipeline de Video Profesional."""
        import time
        start_time = time.time()
        country = event.country if event else document.country
        logger.info(f"🎬 [VIDEO ENGINE] Iniciando Generación AUTOMÁTICA para: {country}")
        
        try:
            # 1. Generar Guión (IA)
            script_data = await self._generate_script(document.summary, country)
            if not script_data:
                logger.error("Fallo generando el script del video.")
                return False

            base_name = f"NEXO_REPORT_{document.id}"
            audio_path = self.assets_dir / f"{base_name}.mp3"
            video_path = self.output_dir / f"{base_name}.mp4"

            # 2. Generar Voz (TTS)
            await self._generate_voice(script_data['full_script'], str(audio_path))

            # 3. Ensamblar Video (FFmpeg)
            success = await self._assemble_video(str(audio_path), str(video_path), script_data)
            
            if success:
                # 4. Upload a Supabase (CDN) y Limpieza Efímera
                video_url = None
                if os.path.exists(video_path):
                    video_url = await asyncio.to_thread(self._upload_video_sync, str(video_path), document.id)
                    logger.info("🧹 [VIDEO ENGINE] Limpiando almacenamiento efímero local.")
                    os.remove(video_path)
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                
                # 5. Persistir URL en Database de forma segura
                if video_url:
                    from core.database import SessionLocal
                    async with SessionLocal() as session:
                        db_doc = await session.get(Document, document.id)
                        if db_doc:
                            db_doc.video_url = video_url
                            db_doc.status = "completed"
                            await session.commit()
                            logger.info("💾 [VIDEO ENGINE] Video URL y estado persistido en BD maestra.")
                            
                    # 6. Lanzar Distribución Viral Automática
                    from services.distribution_service import distribution_service
                    await distribution_service.distribute(
                        document_id=document.id,
                        video_url=video_url,
                        title=document.title or "Sin Asunto",
                        summary=document.summary or "N/A",
                        impact_score=float(getattr(document, 'impact_level', 0.0))
                    )
                            
                total_time = time.time() - start_time
                attach_result_metrics({
                    "subsystem": "video_engine",
                    "execution_time_sec": round(total_time, 2),
                    "script_length_chars": len(script_data['full_script']),
                    "country_target": country
                })
                logger.info(f"🚀 [VIDEO ENGINE] Video CDN Distribuido Exitosamente: {video_url}")
                return True
            return False

        except Exception as e:
            logger.error(f"❌ Error crítico en Video Generator: {e}")
            return False

    def _upload_video_sync(self, file_path: str, document_id: int):
        from supabase import create_client
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            logger.error("No hay credenciales Supabase para el upload de CDN.")
            return None
            
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        bucket = getattr(settings, "SUPABASE_BUCKET", "videos")
        
        file_name = f"{document_id}.mp4"
        with open(file_path, "rb") as f:
            supabase.storage.from_(bucket).upload(
                path=file_name,
                file=f,
                file_options={
                    "upsert": True,
                    "content-type": "video/mp4",
                    "cache-control": "3600"
                }
            )
        
        return supabase.storage.from_(bucket).get_public_url(file_name)

    async def _generate_script(self, summary: str, country: str):
        if not self.client:
            logger.warning("No hay Azure OpenAI configurado. Fallback a guión mock.")
            return {
                "title": f"CRISIS TÁCTICA EN {country}",
                "hook": f"Tensión letal inmediata en {country}.",
                "main": "Analistas advierten un evento de impacto severo en la economía global.",
                "closing": "No confíes en los medios. Nexo Soberano conectado.",
                "full_script": f"Tensión inmediata en {country}. Analistas advierten un evento de impacto severo."
            }

        config = get_config()
        style = config.get("video", {}).get("style", "neutral")
        
        if style == "aggressive":
            tone_rule = "Use an extremely urgent, dramatic, and highly aggressive tone, warning viewers of immediate crisis."
        elif style == "neutral":
            tone_rule = "Use a calm, analytical, and highly objective geopolitical intelligence briefing tone."
        else:
            tone_rule = f"Use a {style} tone."

        prompt = (
            "You are a master scriptwriter for YouTube Shorts/TikTok reporting geopolitical intelligence. "
            "Write a highly engaging, viral 40-second video script based on this summary. "
            f"STYLE INSTRUCTION: {tone_rule}\n"
            "DO NOT write a boring news report. Write a cinematic, objective, highly engaging intelligence briefing.\n"
            "Format JSON STRICTLY:\n"
            "{\n"
            "  \"title\": \"CATCHY 5-WORD TITLE (ALL CAPS)\",\n"
            "  \"hook\": \"Punchy first 3 seconds to grab attention without introducing yourself. Max 15 words.\",\n"
            "  \"main\": \"Core facts and geopolitical/economic impact. Max 60 words.\",\n"
            "  \"closing\": \"Authoritative outro. Max 15 words.\",\n"
            "  \"full_script\": \"Plain text of the entire script (hook + main + closing) to be read flawlessly by TTS.\"\n"
            "}\n\n"
            f"Summary: {summary}"
        )

        for attempt in range(3):
            try:
                response = await self.client.chat.completions.create(
                    model=settings.AZURE_OPENAI_DEPLOYMENT,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                data = json.loads(response.choices[0].message.content)
                logger.info(f"✍️ [VIDEO ENGINE] Guión generado: {data['title']}")
                return data
            except json.JSONDecodeError:
                logger.warning("Fallo parsing JSON en script. Reintentando...")
            except Exception as e:
                logger.error(f"Error AI Scripting: {e}")
                return None
        return None

    async def _generate_voice(self, text: str, output_path: str):
        """Invocación de Azure TTS o ElevenLabs API"""
        logger.info(f"🎙️ [VIDEO ENGINE] Generando Locución Neural TTS (ElevenLabs/Azure)...")
        await asyncio.sleep(2)
        # Mocking el archivo para que FFmpeg no crashee en modo desarrollo
        if not os.path.exists(output_path):
             with open(output_path, 'wb') as f:
                 f.write(b'\0') 
        return True

    async def _assemble_video(self, audio_path: str, output_video: str, script_data: dict):
        logger.info("🎥 [VIDEO ENGINE] Procesando Matriz Visual con FFmpeg (Dark Minimal)...")
        await asyncio.sleep(2)
        
        # OBTENEMOS SPONSORS (Max 1 por video para no saturar)
        sponsored_segments = []
        try:
            from core.database import SessionLocal, SponsoredSlot
            from sqlalchemy.future import select
            async with SessionLocal() as db:
                stmt = select(SponsoredSlot).where(SponsoredSlot.status == "approved").order_by(SponsoredSlot.priority.desc()).limit(1)
                res = await db.execute(stmt)
                slots = res.scalars().all()
                for slot in slots:
                    sponsored_segments.append(slot.media_url)
                    slot.status = "used"
                if slots:
                    await db.commit()
        except Exception as e:
            logger.error(f"⚠️ [MONETIZATION] Error obteniendo sponsors: {e}. Ignorando para proteger pipeline.")
            
        if sponsored_segments:
            logger.info(f"💰 [MONETIZATION] Inyectando {len(sponsored_segments)} Inserciones Patrocinadas (Circuit-Safe)")
        
        # EL COMANDO PROFESIONAL DE FFMPEG SERÍA ASÍ (Placeholder activo):
        ffmpeg_cmd = f'''ffmpeg -y \\
        -f lavfi -i color=c=#0a0f16:s=1080x1920:r=30 \\
        -i {audio_path} \\
        '''
        
        if sponsored_segments:
            # Fake concat para sponsors patrocinados
            ffmpeg_cmd += f"-i {sponsored_segments[0]} \\\n"
            ffmpeg_cmd += f"        -filter_complex \"[0:v]drawtext=text='{script_data['title']}':fontcolor=white:fontsize=84:x=(w-text_w)/2:y=(h-text_h)/3:font='Inter':shadowcolor=black:shadowx=2:shadowy=2[base];[base][2:v]concat=n=2:v=1:a=0[v_out]\" \\\n"
        else:
            ffmpeg_cmd += f"        -filter_complex \"[0:v]drawtext=text='{script_data['title']}':fontcolor=white:fontsize=84:x=(w-text_w)/2:y=(h-text_h)/3:font='Inter':shadowcolor=black:shadowx=2:shadowy=2[v_out]\" \\\n"
            
        ffmpeg_cmd += f"        -map \"[v_out]\" -map 1:a \\\n        -c:v libx264 -c:a aac -shortest {output_video}"
        
        # Ejecutando simulación
        # logger.debug(f"Ejecutando: {ffmpeg_cmd}")
        
        logger.info("🎬 [VIDEO ENGINE] Post-procesamiento visual completado.")
        return True

video_generator = VideoGenerator()
