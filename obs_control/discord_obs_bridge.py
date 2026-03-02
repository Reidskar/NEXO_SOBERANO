# Simple bridge that listens to Discord voice channel updates and writes a
# text source in OBS with the current members.
#
# Usage:
#   pip install -r requirements.txt
#   python discord_obs_bridge.py
#
# Configure the variables below before running.

import asyncio
import discord
from obswebsocket import obsws, requests

# --- configuration ------------------------------------------------
BOT_TOKEN = "TU_TOKEN_DEL_BOT_AQUI"
OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = ""  # si tienes contraseña de WebSocket
TEXT_SOURCE = "DiscordStatus"  # nombre de la fuente de texto en OBS

# ------------------------------------------------------------------

class Bridge(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.voice_states = True
        super().__init__(intents=intents)
        self.obs = obsws(OBS_HOST, OBS_PORT, OBS_PASSWORD)
        self.obs.connect()

    async def on_ready(self):
        log.info(f"Conectado a Discord como {self.user}")

    async def on_voice_state_update(self, member, before, after):
        # detecta cambios en canales de voz y actualiza la fuente de texto
        channel = after.channel or before.channel
        if channel is None:
            text = "Voice: (ninguno)"
        else:
            users = [m.name for m in channel.members]
            text = "Voice: " + ", ".join(users) if users else "Voice: (vacío)"

        try:
            self.obs.call(requests.SetTextGDIPlusProperties(source=TEXT_SOURCE, text=text))
        except Exception as e:
            log.info("Error actualizando OBS:", e)

    async def close(self):
        self.obs.disconnect()
        await super().close()


if __name__ == "__main__":
    bridge = Bridge()
    bridge.run(BOT_TOKEN)
