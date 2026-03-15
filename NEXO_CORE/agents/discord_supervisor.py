"""
Agente Supervisor de Discord

Monitorea la salud del webhook de Discord, recopila métricas,
maneja reconexiones inteligentes y envía alertas de estado.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, Optional

from NEXO_CORE import config
from NEXO_CORE.core.state_manager import state_manager
from NEXO_CORE.services.discord_manager import discord_manager

logger = logging.getLogger(__name__)


@dataclass
class HealthMetrics:
    """Métricas de salud del webhook Discord"""
    total_checks: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    total_messages: int = 0
    successful_messages: int = 0
    failed_messages: int = 0
    avg_response_time_ms: float = 0.0
    uptime_start: float = field(default_factory=time.time)
    last_success: Optional[float] = None
    last_failure: Optional[float] = None
    consecutive_failures: int = 0
    response_times: Deque[float] = field(default_factory=lambda: deque(maxlen=100))

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self.uptime_start

    @property
    def success_rate(self) -> float:
        total = self.total_checks + self.total_messages
        if total == 0:
            return 0.0
        successful = self.successful_checks + self.successful_messages
        return (successful / total) * 100

    @property
    def is_healthy(self) -> bool:
        """Considera saludable si tiene >95% de éxito y <3 fallos consecutivos"""
        return self.success_rate >= 95.0 and self.consecutive_failures < 3

    def record_check(self, success: bool, response_time_ms: float) -> None:
        self.total_checks += 1
        if success:
            self.successful_checks += 1
            self.consecutive_failures = 0
            self.last_success = time.time()
        else:
            self.failed_checks += 1
            self.consecutive_failures += 1
            self.last_failure = time.time()
        
        self.response_times.append(response_time_ms)
        if self.response_times:
            self.avg_response_time_ms = sum(self.response_times) / len(self.response_times)

    def record_message(self, success: bool) -> None:
        self.total_messages += 1
        if success:
            self.successful_messages += 1
            self.consecutive_failures = 0
            self.last_success = time.time()
        else:
            self.failed_messages += 1
            self.consecutive_failures += 1
            self.last_failure = time.time()


class DiscordSupervisor:
    """Supervisor inteligente para el webhook de Discord"""

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._metrics = HealthMetrics()
        self._last_status_report: float = 0.0
        self._report_interval_seconds = 3600  # Reporte cada hora
        self._last_personal_followup: float = 0.0
        self._degraded_mode = False

    @property
    def metrics(self) -> HealthMetrics:
        return self._metrics

    async def health_check_with_metrics(self) -> bool:
        """Health check que registra métricas de rendimiento"""
        if not config.DISCORD_ENABLED or not config.DISCORD_WEBHOOK_URL:
            return False

        start_time = time.time()
        try:
            ok = await discord_manager.health_check()
            response_time_ms = (time.time() - start_time) * 1000
            self._metrics.record_check(ok, response_time_ms)

            if ok and self._degraded_mode:
                logger.info("Discord webhook recovered from degraded state")
                self._degraded_mode = False
            elif not ok and not self._degraded_mode:
                logger.warning("Discord webhook entering degraded state")
                self._degraded_mode = True

            return ok
        except Exception as exc:
            response_time_ms = (time.time() - start_time) * 1000
            self._metrics.record_check(False, response_time_ms)
            logger.warning("Discord health check failed: %s", exc)
            if not self._degraded_mode:
                logger.warning("Discord webhook entering degraded state")
                self._degraded_mode = True
            return False

    async def send_rich_notification(
        self,
        title: str,
        description: str,
        color: int = 0x5865F2,  # Discord blurple
        fields: Optional[list[dict]] = None,
        timestamp: bool = True
    ) -> bool:
        """Envía notificación enriquecida con embeds"""
        if not config.DISCORD_ENABLED or not config.DISCORD_WEBHOOK_URL:
            return False

        try:
            import aiohttp

            embed = {
                "title": title,
                "description": description,
                "color": color,
                "fields": fields or [],
            }
            
            if timestamp:
                embed["timestamp"] = datetime.utcnow().isoformat()

            payload = {"embeds": [embed]}
            
            session_timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(timeout=session_timeout) as session:
                async with session.post(config.DISCORD_WEBHOOK_URL, json=payload) as response:
                    ok = response.status in (200, 204)
                    self._metrics.record_message(ok)
                    return ok
        except Exception as exc:
            self._metrics.record_message(False)
            logger.error("Failed to send rich notification: %s", exc)
            return False

    async def send_stream_notification(
        self,
        active: bool,
        scene: Optional[str] = None,
        recording: bool = False
    ) -> bool:
        """Notificación profesional de cambio de estado de stream"""
        if active:
            title = "🔴 Stream INICIADO"
            description = "El stream está ahora en vivo"
            color = 0x43B581  # Verde Discord
        else:
            title = "⚫ Stream FINALIZADO"
            description = "El stream se ha detenido"
            color = 0x747F8D  # Gris Discord

        fields = []
        if scene:
            fields.append({"name": "🎬 Escena", "value": scene, "inline": True})
        
        if recording:
            fields.append({"name": "⏺️ Grabación", "value": "Activa", "inline": True})

        fields.append({
            "name": "⏰ Timestamp",
            "value": datetime.now().strftime("%H:%M:%S"),
            "inline": True
        })

        return await self.send_rich_notification(title, description, color, fields)

    async def send_health_report(self) -> bool:
        """Envia reporte de salud del sistema"""
        uptime_hours = self._metrics.uptime_seconds / 3600
        
        title = "📊 Reporte de Salud - Discord Webhook"
        description = f"Estado: **{'🟢 Saludable' if self._metrics.is_healthy else '🟡 Degradado'}**"
        
        fields = [
            {
                "name": "✅ Tasa de éxito",
                "value": f"{self._metrics.success_rate:.1f}%",
                "inline": True
            },
            {
                "name": "⏱️ Latencia promedio",
                "value": f"{self._metrics.avg_response_time_ms:.0f}ms",
                "inline": True
            },
            {
                "name": "⏳ Uptime",
                "value": f"{uptime_hours:.1f}h",
                "inline": True
            },
            {
                "name": "📬 Mensajes totales",
                "value": f"{self._metrics.total_messages}",
                "inline": True
            },
            {
                "name": "🔍 Health checks",
                "value": f"{self._metrics.total_checks}",
                "inline": True
            },
            {
                "name": "❌ Fallos consecutivos",
                "value": f"{self._metrics.consecutive_failures}",
                "inline": True
            }
        ]

        color = 0x43B581 if self._metrics.is_healthy else 0xFAA61A  # Verde o amarillo
        return await self.send_rich_notification(title, description, color, fields)

    async def send_personal_followup(self) -> bool:
        """Seguimiento personal continuo por Discord (modo agente permanente)."""
        snapshot = state_manager.snapshot()
        owner = config.DISCORD_OWNER_NAME
        objectives = [x.strip() for x in (config.DISCORD_PERSONAL_OBJECTIVES or "").split(",") if x.strip()]

        stream_state = "Activo" if snapshot.get("stream_active") else "Inactivo"
        obs_state = "Conectado" if snapshot.get("obs_connected") else "Desconectado"
        discord_state = "Conectado" if snapshot.get("discord_connected") else "Desconectado"

        title = f"🧠 Seguimiento Estratégico · {owner}"
        description = (
            "Agente personal en modo continuo.\n"
            "Estado actual + próximos focos para mantener ejecución diaria."
        )

        fields = [
            {
                "name": "🎯 Objetivos activos",
                "value": "\n".join(f"• {item}" for item in objectives[:6]) if objectives else "No definidos",
                "inline": False,
            },
            {
                "name": "📡 Estado operativo",
                "value": (
                    f"Stream: **{stream_state}**\n"
                    f"OBS: **{obs_state}**\n"
                    f"Discord: **{discord_state}**"
                ),
                "inline": True,
            },
            {
                "name": "📈 Salud del sistema",
                "value": (
                    f"Éxito: **{self._metrics.success_rate:.1f}%**\n"
                    f"Latencia: **{self._metrics.avg_response_time_ms:.0f}ms**\n"
                    f"IA req hoy: **{snapshot.get('ai_requests_today', 0)}**"
                ),
                "inline": True,
            },
        ]

        last_error = snapshot.get("last_error")
        if last_error:
            fields.append(
                {
                    "name": "⚠️ Último bloqueo",
                    "value": str(last_error)[:300],
                    "inline": False,
                }
            )

        fields.append(
            {
                "name": "🗺 Próxima acción sugerida",
                "value": (
                    "1) Validar conectores críticos\n"
                    "2) Ejecutar ciclo autónomo IA\n"
                    "3) Priorizar top 3 decisiones de impacto"
                ),
                "inline": False,
            }
        )

        return await self.send_rich_notification(title, description, 0x5865F2, fields)

    async def supervision_loop(self) -> None:
        """Loop principal de supervisión"""
        logger.info("Discord Supervisor iniciado")
        
        while True:
            try:
                # Health check periódico
                await self.health_check_with_metrics()
                
                # Reporte de salud periódico
                now = time.time()
                if now - self._last_status_report >= self._report_interval_seconds:
                    await self.send_health_report()
                    self._last_status_report = now

                # Seguimiento personal permanente
                if config.DISCORD_PERSONAL_FOLLOWUP_ENABLED:
                    if now - self._last_personal_followup >= config.DISCORD_PERSONAL_FOLLOWUP_SECONDS:
                        await self.send_personal_followup()
                        self._last_personal_followup = now
                
                # Alertas de estado crítico
                if self._metrics.consecutive_failures >= 5:
                    logger.error(
                        "Discord webhook en estado crítico: %d fallos consecutivos",
                        self._metrics.consecutive_failures
                    )
                    await self.send_critical_alert()
                
                # Intervalo adaptativo: más frecuente si hay problemas
                if self._degraded_mode:
                    if discord_manager.is_rate_limited():
                        await asyncio.sleep(max(60, config.DISCORD_RECONNECT_SECONDS))
                    else:
                        await asyncio.sleep(max(5, config.DISCORD_RECONNECT_SECONDS // 3))
                else:
                    await asyncio.sleep(config.DISCORD_RECONNECT_SECONDS)
                    
            except asyncio.CancelledError:
                logger.info("Discord Supervisor detenido")
                raise
            except Exception as exc:
                logger.error("Error en supervision loop: %s", exc)
                await asyncio.sleep(30)

    async def send_critical_alert(self) -> None:
        """Alerta de estado crítico (usa logging como fallback)"""
        logger.critical(
            "⚠️ ALERTA CRÍTICA: Discord webhook no responde después de %d intentos",
            self._metrics.consecutive_failures
        )
        # Aquí podrías integrar otros canales de alerta (email, SMS, etc.)

    def start(self) -> None:
        """Inicia el supervisor en background"""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.supervision_loop())
            logger.info("Discord Supervisor task creada")

    async def shutdown(self) -> None:
        """Detiene el supervisor de forma limpia"""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Discord Supervisor shutdown completado")


# Instancia global del supervisor
discord_supervisor = DiscordSupervisor()
