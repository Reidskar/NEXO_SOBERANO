"""
NEXO SOBERANO — OBS <-> Discord Bridge
Controla OBS remotamente desde Discord. Lee credenciales de ../.env
Uso: python discord_obs_bridge.py
"""
import os, sys, logging
from pathlib import Path
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

import discord
from discord.ext import tasks

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
log = logging.getLogger("nexo.obs-bridge")

# ═══ CONFIG (from .env) ═══
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
OBS_HOST = os.getenv("OBS_HOST", "localhost")
OBS_PORT = int(os.getenv("OBS_PORT", "4455"))
OBS_PASSWORD = os.getenv("OBS_PASSWORD", "")
STATUS_INTERVAL = int(os.getenv("OBS_STATUS_INTERVAL", "300"))

# ═══ OBS MANAGER ═══
class OBSManager:
    def __init__(self):
        self.ws = None
        self.connected = False
        self._legacy = False
        self._connect()

    def _connect(self):
        try:
            import obsws_python as obs
            self.ws = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD, timeout=5)
            self.connected = True
            self._legacy = False
            log.info(f"Connected to OBS at {OBS_HOST}:{OBS_PORT}")
        except Exception as e:
            log.warning(f"OBS not available: {e}")
            self.connected = False

    def reconnect(self):
        self.connected = False
        self._connect()

    def get_status(self) -> dict:
        if not self.connected:
            return {"streaming": False, "recording": False, "scene": "N/A", "error": "disconnected"}
        try:
            stream = self.ws.get_stream_status()
            record = self.ws.get_record_status()
            scene = self.ws.get_current_program_scene()
            return {
                "streaming": stream.output_active,
                "recording": record.output_active,
                "scene": scene.current_program_scene_name,
                "stream_time": getattr(stream, 'output_timecode', '00:00:00'),
                "error": None
            }
        except Exception as e:
            self.connected = False
            return {"streaming": False, "recording": False, "scene": "N/A", "error": str(e)}

    def start_stream(self):
        if not self.connected: self.reconnect()
        if not self.connected: return False
        try: self.ws.start_stream(); return True
        except Exception as e: log.error(f"start_stream: {e}"); return False

    def stop_stream(self):
        if not self.connected: return False
        try: self.ws.stop_stream(); return True
        except Exception as e: log.error(f"stop_stream: {e}"); return False

    def start_recording(self):
        if not self.connected: return False
        try: self.ws.start_record(); return True
        except Exception as e: log.error(f"start_record: {e}"); return False

    def stop_recording(self):
        if not self.connected: return False
        try: self.ws.stop_record(); return True
        except Exception as e: log.error(f"stop_record: {e}"); return False

    def set_scene(self, name):
        if not self.connected: return False
        try: self.ws.set_current_program_scene(name); return True
        except Exception as e: log.error(f"set_scene: {e}"); return False


# ═══ DISCORD BOT ═══
class NexoOBSBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(intents=intents)
        self.obs = OBSManager()
        self.channel = None

    async def setup_hook(self):
        self.status_loop.start()

    async def on_ready(self):
        log.info(f"Bot connected as {self.user}")
        log.info(f"Guilds: {[g.name for g in self.guilds]}")
        if CHANNEL_ID:
            try:
                self.channel = self.get_channel(CHANNEL_ID) or await self.fetch_channel(CHANNEL_ID)
                log.info(f"Canal encontrado: #{self.channel.name} (ID: {CHANNEL_ID})")
                e = discord.Embed(title="🟢 NEXO OBS Bridge Activo", description="Bot conectado. Usa `!obs help`.", color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
                e.set_footer(text="NEXO SOBERANO")
                await self.channel.send(embed=e)
                log.info("Mensaje de bienvenida enviado al canal")
            except Exception as ex:
                log.error(f"Error enviando al canal {CHANNEL_ID}: {ex}")
        else:
            log.warning("DISCORD_CHANNEL_ID no configurado")

    async def on_message(self, message):
        log.info(f"MSG recibido: author={message.author} bot={message.author.bot} content='{message.content[:50]}'")
        if message.author.bot or not message.content.startswith("!obs"):
            return
        parts = message.content.strip().split()
        cmd = parts[1] if len(parts) > 1 else "status"

        if cmd == "status":
            s = self.obs.get_status()
            e = discord.Embed(title="Estado OBS", color=discord.Color.green() if self.obs.connected else discord.Color.red(), timestamp=datetime.now(timezone.utc))
            e.add_field(name="Conexion", value="Online" if self.obs.connected else "Offline", inline=True)
            e.add_field(name="Escena", value=s["scene"], inline=True)
            e.add_field(name="Stream", value="ACTIVO" if s["streaming"] else "Inactivo", inline=True)
            e.add_field(name="Grabacion", value="ACTIVA" if s["recording"] else "Inactiva", inline=True)
            if s.get("stream_time"): e.add_field(name="Tiempo", value=s["stream_time"], inline=True)
            if s.get("error"): e.add_field(name="Error", value=s["error"], inline=False)
            e.set_footer(text="NEXO SOBERANO")
            await message.channel.send(embed=e)

        elif cmd == "start":
            ok = self.obs.start_stream()
            await message.channel.send(f"{'✅' if ok else '❌'} Stream {'iniciado' if ok else 'fallo'}.")

        elif cmd == "stop":
            ok = self.obs.stop_stream()
            await message.channel.send(f"{'✅' if ok else '❌'} Stream {'detenido' if ok else 'fallo'}.")

        elif cmd == "rec":
            sub = parts[2] if len(parts) > 2 else "start"
            if sub == "start":
                ok = self.obs.start_recording()
                await message.channel.send(f"{'🔴' if ok else '❌'} Grabacion {'iniciada' if ok else 'fallo'}.")
            else:
                ok = self.obs.stop_recording()
                await message.channel.send(f"{'⏹' if ok else '❌'} Grabacion {'detenida' if ok else 'fallo'}.")

        elif cmd == "scene":
            if len(parts) < 3:
                await message.channel.send("Uso: `!obs scene NombreEscena`")
                return
            name = " ".join(parts[2:])
            ok = self.obs.set_scene(name)
            await message.channel.send(f"{'🎬' if ok else '❌'} Escena {'cambiada a ' + name if ok else 'no encontrada'}.")

        elif cmd == "reconnect":
            self.obs.reconnect()
            await message.channel.send(f"{'✅' if self.obs.connected else '❌'} Reconexion {'OK' if self.obs.connected else 'fallida'}.")

        elif cmd == "help":
            e = discord.Embed(title="Comandos OBS", description="Control remoto de OBS", color=discord.Color.blue())
            for c, d in [("status","Ver estado"),("start","Iniciar stream"),("stop","Detener stream"),("rec start/stop","Grabacion"),("scene Nombre","Cambiar escena"),("reconnect","Reconectar OBS")]:
                e.add_field(name=f"`!obs {c}`", value=d, inline=False)
            e.set_footer(text="NEXO SOBERANO")
            await message.channel.send(embed=e)
        else:
            await message.channel.send(f"Comando desconocido: `{cmd}`. Usa `!obs help`.")

    @tasks.loop(seconds=STATUS_INTERVAL)
    async def status_loop(self):
        if not self.channel:
            if CHANNEL_ID: self.channel = self.get_channel(CHANNEL_ID)
            if not self.channel: return
        if not self.obs.connected: self.obs.reconnect()
        s = self.obs.get_status()
        if s["streaming"] or s.get("error"):
            e = discord.Embed(title="Reporte OBS", description=f"Stream: {'ACTIVO' if s['streaming'] else 'Inactivo'} | Escena: {s['scene']}", color=discord.Color.red() if s["streaming"] else discord.Color.greyple(), timestamp=datetime.now(timezone.utc))
            if s.get("stream_time"): e.add_field(name="Tiempo", value=s["stream_time"])
            if s.get("error"): e.add_field(name="Error", value=s["error"][:200])
            e.set_footer(text="NEXO SOBERANO")
            await self.channel.send(embed=e)

    @status_loop.before_loop
    async def before_status(self):
        await self.wait_until_ready()

# ═══ MAIN ═══
if __name__ == "__main__":
    if not BOT_TOKEN:
        log.error("DISCORD_BOT_TOKEN not set in .env")
        sys.exit(1)
    log.info("=== NEXO OBS <-> Discord Bridge ===")
    log.info(f"OBS: {OBS_HOST}:{OBS_PORT} | Guild: {GUILD_ID} | Canal: {CHANNEL_ID}")
    NexoOBSBot().run(BOT_TOKEN)
