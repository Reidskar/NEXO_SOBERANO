import asyncio
import os
import logging
from typing import Optional

try:
    import httpx
except ImportError:
    pass

logger = logging.getLogger(__name__)

NEXO_PORT = os.getenv("NEXO_PORT", "8080")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

async def _ollama_generate(prompt: str) -> str:
    import json as _json, urllib.request as _req
    model = os.getenv("OLLAMA_MODEL_FAST", "gemma3:1b")
    payload = _json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.5, "num_predict": 60}
    }).encode("utf-8")
    request = _req.Request(
        f"{OLLAMA_URL}/api/chat", data=payload,
        headers={"Content-Type": "application/json"}
    )
    with _req.urlopen(request, timeout=20) as r:
        d = _json.loads(r.read())
        return d.get("message", {}).get("content", "").strip()

class LivestreamSupervisor:
    """
    Simula análisis de streams de noticias 24/7 con Ollama local.
    """
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self.running = False

    async def scan_loop(self):
        logger.info("Iniciando OSINT Livestream Scanner (Ollama local)...")
        self.running = True

        while self.running:
            try:
                prompt = (
                    "Eres analista táctico. Genera UN breaking news alert geopolítico realista "
                    "en ESPAÑOL. Máximo 15 palabras. Ejemplo: 'Flota del Mar Rojo detecta "
                    "actividad anómala cerca de Yibuti'."
                )
                try:
                    alert_text = await asyncio.to_thread(_ollama_generate, prompt)
                    alert_text = alert_text.replace('"', '').split('\n')[0][:120]
                except Exception:
                    await asyncio.sleep(120)
                    continue

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
                        f"http://127.0.0.1:{NEXO_PORT}/api/webhooks/ingest", 
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
