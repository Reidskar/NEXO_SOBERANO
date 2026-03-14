import logging
logger = logging.getLogger(__name__)
class DiscordManager:
    def __init__(self): self._ready = False
    async def shutdown(self):
        logger.info("DiscordManager shutdown")
        self._ready = False
discord_manager = DiscordManager()
