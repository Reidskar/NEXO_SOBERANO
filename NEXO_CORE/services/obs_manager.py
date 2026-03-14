import logging
logger = logging.getLogger(__name__)
class OBSManager:
    def start_background_reconnect(self): logger.info("OBS reconnect loop iniciado")
    async def shutdown(self): logger.info("OBSManager shutdown")
obs_manager = OBSManager()
