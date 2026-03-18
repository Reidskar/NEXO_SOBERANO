import logging
import aiohttp
from core.config import settings

logger = logging.getLogger(__name__)

class DiscordService:
    def __init__(self):
        self.webhook_url = settings.DISCORD_WEBHOOK_URL

    async def notify_new_document(self, doc_info: dict):
        if not self.webhook_url:
            logger.warning("DISCORD_WEBHOOK_URL no configurado. Saltando webhook.")
            return

        content = (
            f"🚨 **Nuevo Documento de Inteligencia** 🚨\n\n"
            f"🌍 **País:** {doc_info.get('country', 'N/A')}\n"
            f"📂 **Categoría:** {doc_info.get('category', 'N/A')}\n"
            f"🔥 **Impacto:** {doc_info.get('impact_score', 0)}/10\n\n"
            f"📝 **Resumen:**\n{doc_info.get('summary', 'Sin resumen')}\n\n"
            f"🔗 **Enlace:** [Ver en Drive]({doc_info.get('drive_url', '')})"
        )

        payload = {"content": content}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status not in (200, 204):
                        logger.error(f"Error enviando Discord Hook: código {response.status}")
        except Exception as e:
            logger.error(f"Fallo de conexión a Discord: {e}")

discord_service = DiscordService()
