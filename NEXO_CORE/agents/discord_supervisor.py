import logging
logger = logging.getLogger(__name__)
class DiscordSupervisor:
    def start(self): logger.info("DiscordSupervisor started")
    async def shutdown(self): logger.info("DiscordSupervisor shutdown")
discord_supervisor = DiscordSupervisor()
