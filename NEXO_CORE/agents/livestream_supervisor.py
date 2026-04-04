import asyncio
import os
import logging
from typing import Optional

try:
    import httpx
except ImportError:
    pass

try:
    import google.generativeai as genai
except ImportError:
    pass

logger = logging.getLogger(__name__)

class LivestreamSupervisor:
    """
    Simulates scraping 24/7 news streams (Al Jazeera, SkyNews) by actively using
    Gemini 1.5 Flash to synthesize breaking geopolitical events into tactical alerts.
    """
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self.running = False
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        if self.api_key:
            genai.configure(api_key=self.api_key)

    async def scan_loop(self):
        logger.info("📡 Iniciando OSINT Livestream Scanner (AI Vision Tracker)...")
        self.running = True
        
        while self.running:
            try:
                if not self.api_key:
                    await asyncio.sleep(60)
                    continue

                # Pedimos a la IA que simule ver el noticiero en vivo y generar inteligencia táctica
                model = genai.GenerativeModel("gemini-2.5-flash-lite")
                prompt = "Eres un analista táctico de la NSA procesando feeds de video en vivo (Al Jazeera, DW, Sky News) en marzo 2026. Ha ocurrido un evento táctico (movimientos navales, aéreos o despliegue militar) de EXTREMA URGENCIA. Genera SOLO el subtítulo o 'breaking news alert' en ESPAÑOL. Máximo 15 palabras. Ej: 'Flota del Mar Rojo detecta actividad anómala cerca de Yibuti'."
                
                resp = await asyncio.to_thread(model.generate_content, prompt)
                alert_text = resp.text.strip().replace('"', '')

                payload = {
                    "tenant_slug": "demo",
                    "type": "ai_alert",
                    "title": "VISION AI TACTICAL SCAN",
                    "body": f"[EN VIVO] {alert_text}",
                    "severity": 0.8
                }

                # Inyectar al webhook interno para hacer el broadcast al mapa
                async with httpx.AsyncClient() as client:
                    await client.post(
                        "http://127.0.0.1:8000/api/webhooks/ingest", 
                        json=payload, 
                        headers={"x-api-key": os.getenv("NEXO_API_KEY", "nexo_dev_key_2025")},
                        timeout=5.0
                    )
                
                logger.info(f"🚨 Alerta de Visión Inyectada: {alert_text}")
                
            except Exception as e:
                logger.debug(f"Error en Livestream Supervisor: {e}")
                
            # Escanear cada 75 segundos
            await asyncio.sleep(75)

    def start(self):
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.scan_loop())

    async def shutdown(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

# Instancia global
livestream_supervisor = LivestreamSupervisor()
