import os
from dotenv import load_dotenv
import discord
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# carga Supervisor (usa setup() con discord.ext)
bot.load_extension("supervisor")  # si supervisor.py está en la misma carpeta

@bot.event
async def on_ready():
    log.info("Bot listo", bot.user)

bot.run(TOKEN)
