# ============================================================
# NEXO SOBERANO — Inter-Agent Message Bus
# © 2026 elanarcocapital.com
# Sistema de mensajería entre agentes via archivos JSON
# ============================================================
from __future__ import annotations
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel

logger = logging.getLogger("NEXO.inter_agent_bus")

MESSAGES_DIR = Path("inter_agent/mensajes")
MESSAGES_DIR.mkdir(parents=True, exist_ok=True)

class AgentMessage(BaseModel):
    id: str = ""
    origen: str
    destino: str
    tipo: str           # "alerta" | "info" | "tarea" | "reporte"
    urgencia: str       # "low" | "medium" | "high" | "critical"
    mensaje: str
    datos: dict = {}
    timestamp: str = ""
    leido: bool = False

    def model_post_init(self, __context):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.id:
            self.id = f"{self.origen}_{self.destino}_{self.timestamp[:19].replace(':', '')}"

class InterAgentBus:
    
    @staticmethod
    def enviar(origen: str, destino: str, mensaje: str,
               tipo: str = "info", urgencia: str = "low",
               datos: dict = {}) -> str:
        msg = AgentMessage(
            id=f"{origen}_{destino}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            origen=origen, destino=destino,
            tipo=tipo, urgencia=urgencia,
            mensaje=mensaje, datos=datos,
            timestamp=datetime.now().isoformat()
        )
        path = MESSAGES_DIR / f"{msg.id}.json"
        path.write_text(json.dumps(msg.model_dump(), indent=2, ensure_ascii=False))
        logger.info(f"Mensaje enviado: {origen} → {destino} [{urgencia}]")
        if urgencia == "critical":
            logger.critical(f"MENSAJE CRÍTICO de {origen} a {destino}: {mensaje}")
        return msg.id

    @staticmethod
    def recibir(destino: str, solo_no_leidos: bool = True) -> List[AgentMessage]:
        mensajes = []
        for f in MESSAGES_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                msg = AgentMessage(**data)
                if msg.destino == destino or msg.destino == "all":
                    if not solo_no_leidos or not msg.leido:
                        mensajes.append(msg)
            except Exception as e:
                logger.error(f"Error leyendo mensaje {f}: {e}")
        return sorted(mensajes, key=lambda m: m.timestamp)

    @staticmethod
    def marcar_leido(mensaje_id: str):
        path = MESSAGES_DIR / f"{mensaje_id}.json"
        if path.exists():
            data = json.loads(path.read_text())
            data["leido"] = True
            path.write_text(json.dumps(data, indent=2))

    @staticmethod
    def mensajes_criticos_pendientes() -> List[AgentMessage]:
        return [
            m for m in InterAgentBus.recibir("all", solo_no_leidos=True)
            if m.urgencia == "critical"
        ]

bus = InterAgentBus()
