import os
import re
import discord
from discord.ext import commands
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# 1. CARGA DE ENTORNO Y CONEXIÓN
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
QDRANT_HOST = "localhost" # Tu Docker local
QDRANT_PORT = 6333

# Inicializar Qdrant y Modelo de Embeddings
q_client = QdrantClient(QDRANT_HOST, port=QDRANT_PORT)
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# 2. CONFIGURACIÓN DEL BOT (Oídos del Agente)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# REGLAS DE PATRULLA
SPAM_LINK_LIMIT = 3
NSFW_KEYWORDS = ["porn", "xxx", "gore", "violation"]

@bot.event
async def on_ready():
    log.info(f"🤖 AGENTE NEXE SOBERANO ONLINE: {bot.user}")
    log.info("🛡️ Patrulla Anti-Spam: ACTIVA")
    log.info("🧠 Memoria Geopolítica: CONECTADA")

# 3. MÓDULO DE SEGURIDAD (Automático)
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Filtro de Spam
    links = re.findall(r'(https?://[^\s]+)', message.content)
    if len(links) > SPAM_LINK_LIMIT:
        await message.delete()
        await message.channel.send(f"⚠️ {message.author.mention}, spam detectado y eliminado.")
        return

    # Filtro NSFW
    if any(word in message.content.lower() for word in NSFW_KEYWORDS):
        await message.delete()
        return

    await bot.process_commands(message)

# 4. MÓDULO DE INTELIGENCIA (Comando Consultar)
@bot.command(name="consultar")
async def consultar(ctx, *, pregunta: str):
    await ctx.send(f"🔍 Consultando archivos de la Torre sobre: *{pregunta}*...")
    
    try:
        # Convertir pregunta a vector
        query_vector = embed_model.encode(pregunta).tolist()
        
        # Buscar en Qdrant
        search_result = q_client.search_points(
            collection_name="nexo_soberano_knowledge",
            vector=query_vector,
            limit=3
        )
        
        if not search_result:
            await ctx.send("❌ No hay datos específicos en mi base de datos sobre eso.")
            return

        # Responder con las fuentes
        response = "**Resultados del Análisis Soberano:**\n\n"
        for hit in search_result:
            source = hit.payload.get("source", "Desconocido")
            text = hit.payload.get("text", "")[:350] # Limite para Discord
            response += f"📄 **Fuente:** {source}\n> {text}...\n\n"
        
        await ctx.send(response)
    except Exception as e:
        await ctx.send(f"⚠️ Error al acceder a la memoria: {e}")

# LANZAMIENTO
if __name__ == "__main__":
    if not TOKEN:
        log.info("⚠️ DISCORD_TOKEN no definido en .env. El bot no puede arrancar.")
    else:
        bot.run(TOKEN)
