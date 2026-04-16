"""
backend/services/agent_factory.py
====================================
Fábrica de Agentes Autónomos NEXO.

Cada agente es un objeto JSON persistido en exports/agents/.
El factory corre un loop que ejecuta los agentes según su schedule
y reporta resultados a Discord.

Definición de un agente:
{
  "id": "uuid",
  "name": "Agente Mercados",
  "role": "Monitorear mercados financieros y reportar anomalías",
  "tools": ["osint_markets", "osint_sweep", "mcp_cloudflare"],
  "model": "general",           # general | critico | code
  "schedule_minutes": 30,       # cada cuántos minutos corre
  "trigger": "schedule",        # schedule | event | manual
  "active": true,
  "discord_channel_id": "...",
  "created_at": "...",
  "last_run": null,
  "last_result": null,
  "run_count": 0
}
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

AGENTS_DIR = Path("exports/agents")
AGENTS_DIR.mkdir(parents=True, exist_ok=True)

NEXO_URL = os.getenv("NEXO_INTERNAL_URL", "http://127.0.0.1:8080")
NEXO_KEY = os.getenv("NEXO_API_KEY", "NEXO_LOCAL_2026_OK")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")
API_HEADERS = {"x-api-key": NEXO_KEY}

# Plantillas de agentes pre-definidos que el usuario puede activar
AGENT_TEMPLATES = {
    "mercados": {
        "name": "Agente Mercados",
        "role": "Monitorear mercados financieros (Bitcoin, Oil, S&P500, VIX, Gold) y alertar anomalías superiores al 2%.",
        "tools": ["osint_markets"],
        "model": "general",
        "schedule_minutes": 30,
        "trigger": "schedule",
    },
    "osint_sweep": {
        "name": "Agente OSINT",
        "role": "Barrer todas las fuentes OSINT cada hora, detectar eventos significativos y resumirlos en un briefing.",
        "tools": ["osint_sweep", "topics_detect"],
        "model": "general",
        "schedule_minutes": 60,
        "trigger": "schedule",
    },
    "vuelos": {
        "name": "Agente Vuelos Militares",
        "role": "Monitorear tráfico aéreo inusual (vuelos militares, patrones anómalos sobre zonas calientes).",
        "tools": ["osint_flights"],
        "model": "general",
        "schedule_minutes": 20,
        "trigger": "schedule",
    },
    "amenazas_cyber": {
        "name": "Agente Cyber Intel",
        "role": "Monitorear CISA KEV, nuevas vulnerabilidades y amenazas cibernéticas activas.",
        "tools": ["osint_threats"],
        "model": "critico",
        "schedule_minutes": 120,
        "trigger": "schedule",
    },
    "noticias_geopolitica": {
        "name": "Agente Geopolítica",
        "role": "Rastrear eventos geopolíticos via GDELT, priorizar por impacto y detectar escaladas.",
        "tools": ["osint_sweep", "topics_detect"],
        "model": "general",
        "schedule_minutes": 45,
        "trigger": "schedule",
    },
    "playwright_web": {
        "name": "Agente Web Monitor",
        "role": "Monitorear páginas web clave (sitios de gobierno, prensa, think tanks) y detectar cambios.",
        "tools": ["mcp_playwright"],
        "model": "general",
        "schedule_minutes": 60,
        "trigger": "schedule",
    },
}


class AgentFactory:
    """Crea, persiste y ejecuta agentes autónomos."""

    def __init__(self):
        self._agents: dict[str, dict] = {}
        self._running = False
        self._load_all()

    # ── Persistencia ──────────────────────────────────────────────────

    def _load_all(self):
        for f in AGENTS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                self._agents[data["id"]] = data
            except Exception:
                pass
        logger.info(f"[AgentFactory] {len(self._agents)} agentes cargados")

    def _save(self, agent: dict):
        path = AGENTS_DIR / f"{agent['id']}.json"
        path.write_text(json.dumps(agent, indent=2, default=str))

    # ── CRUD ─────────────────────────────────────────────────────────

    def create(
        self,
        name: str,
        role: str,
        tools: list[str],
        model: str = "general",
        schedule_minutes: int = 60,
        trigger: str = "schedule",
        discord_channel_id: str = "",
        template: str = "",
    ) -> dict:
        """Crea un nuevo agente y lo persiste."""
        if template and template in AGENT_TEMPLATES:
            base = AGENT_TEMPLATES[template].copy()
            base.update({k: v for k, v in {
                "name": name, "role": role, "tools": tools,
                "model": model, "schedule_minutes": schedule_minutes,
            }.items() if v})
        else:
            base = {
                "name": name, "role": role, "tools": tools,
                "model": model, "schedule_minutes": schedule_minutes,
                "trigger": trigger,
            }

        agent = {
            "id": str(uuid.uuid4())[:8],
            "active": True,
            "discord_channel_id": discord_channel_id or os.getenv("DISCORD_ALERT_CHANNEL_ID", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_run": None,
            "last_result": None,
            "run_count": 0,
            **base,
        }
        self._agents[agent["id"]] = agent
        self._save(agent)
        logger.info(f"[AgentFactory] Agente creado: {agent['name']} ({agent['id']})")
        return agent

    def create_from_template(self, template_id: str, channel_id: str = "") -> Optional[dict]:
        if template_id not in AGENT_TEMPLATES:
            return None
        t = AGENT_TEMPLATES[template_id]
        return self.create(
            name=t["name"], role=t["role"], tools=t["tools"],
            model=t.get("model", "general"),
            schedule_minutes=t.get("schedule_minutes", 60),
            trigger=t.get("trigger", "schedule"),
            discord_channel_id=channel_id,
        )

    def list_agents(self) -> list[dict]:
        return list(self._agents.values())

    def get(self, agent_id: str) -> Optional[dict]:
        return self._agents.get(agent_id)

    def toggle(self, agent_id: str, active: bool) -> bool:
        if agent_id not in self._agents:
            return False
        self._agents[agent_id]["active"] = active
        self._save(self._agents[agent_id])
        return True

    def delete(self, agent_id: str) -> bool:
        if agent_id not in self._agents:
            return False
        del self._agents[agent_id]
        path = AGENTS_DIR / f"{agent_id}.json"
        path.unlink(missing_ok=True)
        return True

    # ── Ejecución de ciclo ────────────────────────────────────────────

    def _needs_run(self, agent: dict) -> bool:
        if not agent.get("active"):
            return False
        if agent.get("trigger") != "schedule":
            return False
        last = agent.get("last_run")
        if not last:
            return True
        try:
            last_ts = datetime.fromisoformat(last).timestamp()
            interval = agent.get("schedule_minutes", 60) * 60
            return (time.time() - last_ts) >= interval
        except Exception:
            return True

    async def run_agent(self, agent: dict) -> dict:
        """Ejecuta un ciclo completo del agente."""
        agent_id = agent["id"]
        logger.info(f"[AgentFactory] Ejecutando: {agent['name']} ({agent_id})")
        t0 = time.time()

        # 1. Recopilar datos de las herramientas del agente
        tool_results = {}
        for tool in agent.get("tools", []):
            result = await self._call_tool(tool)
            if result:
                tool_results[tool] = result

        # 2. Sintetizar con IA
        synthesis = await self._synthesize_agent(agent, tool_results)

        # 3. Actualizar estado
        elapsed = round(time.time() - t0, 1)
        agent["last_run"] = datetime.now(timezone.utc).isoformat()
        agent["run_count"] = agent.get("run_count", 0) + 1
        agent["last_result"] = synthesis[:500] if synthesis else "Sin resultado"
        self._save(agent)

        # 4. Reportar a Discord
        if synthesis:
            await self._report_to_discord(agent, synthesis, tool_results, elapsed)

        return {"agent_id": agent_id, "synthesis": synthesis, "tools_used": list(tool_results.keys()), "elapsed": elapsed}

    async def _call_tool(self, tool_name: str) -> Optional[dict]:
        """Llama a una herramienta NEXO o MCP según el prefijo."""
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                if tool_name == "osint_sweep":
                    r = await client.get(f"{NEXO_URL}/api/osint/sweep", headers=API_HEADERS)
                elif tool_name == "osint_markets":
                    r = await client.get(f"{NEXO_URL}/api/osint/markets", headers=API_HEADERS)
                elif tool_name == "osint_flights":
                    r = await client.get(f"{NEXO_URL}/api/osint/flights", headers=API_HEADERS)
                elif tool_name == "osint_threats":
                    r = await client.get(f"{NEXO_URL}/api/osint/threats", headers=API_HEADERS)
                elif tool_name == "topics_detect":
                    r = await client.get(f"{NEXO_URL}/api/topics", headers=API_HEADERS)
                elif tool_name.startswith("mcp_"):
                    # Llamar via MCP bridge
                    from backend.services.mcp_bridge import mcp_bridge
                    mcp_tool = tool_name[4:]  # quitar prefijo "mcp_"
                    result = await mcp_bridge.call(mcp_tool, {})
                    return result if result.get("ok") else None
                else:
                    return None
                return r.json() if r.status_code == 200 else None
        except Exception as e:
            logger.debug(f"[AgentFactory] Tool {tool_name} error: {e}")
            return None

    async def _synthesize_agent(self, agent: dict, tool_results: dict) -> str:
        """Usa Ollama para sintetizar los resultados del agente."""
        if not tool_results:
            return ""
        context = json.dumps(tool_results, ensure_ascii=False, default=str)[:2000]
        prompt = f"""Eres el agente autónomo "{agent['name']}".
Tu rol: {agent['role']}

Datos recopilados:
{context}

Genera un reporte conciso (máximo 4 oraciones) destacando lo más relevante.
Si hay algo urgente o anómalo, indícalo claramente con ⚠️.
Formato: texto directo, sin markdown."""
        try:
            from NEXO_CORE.services.ollama_service import ollama_service
            resp = await ollama_service.consultar(prompt, modelo="general", temperature=0.1)
            if resp.success:
                text = resp.text.strip()
                if "<think>" in text:
                    parts = text.split("</think>")
                    text = parts[-1].strip() if len(parts) > 1 else text
                return text[:600]
        except Exception as e:
            logger.warning(f"[AgentFactory] Synthesis error: {e}")
        return ""

    async def _report_to_discord(self, agent: dict, synthesis: str, tools: dict, elapsed: float):
        """Envía reporte del agente al webhook de Discord."""
        if not DISCORD_WEBHOOK:
            return
        urgent = "⚠️" in synthesis
        color = 0xe74c3c if urgent else 0x3498db
        embed = {
            "title": f"🤖 {agent['name']}",
            "description": synthesis,
            "color": color,
            "fields": [
                {"name": "Herramientas", "value": ", ".join(tools.keys()) or "—", "inline": True},
                {"name": "Tiempo", "value": f"{elapsed}s", "inline": True},
                {"name": "Ciclo #", "value": str(agent.get("run_count", 0)), "inline": True},
            ],
            "footer": {"text": f"Agente {agent['id']} · {agent.get('schedule_minutes', 60)}min interval"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(DISCORD_WEBHOOK, json={"embeds": [embed]})
        except Exception:
            pass

    # ── Loop principal ────────────────────────────────────────────────

    async def start_loop(self):
        """Loop que ejecuta agentes según su schedule."""
        self._running = True
        logger.info("[AgentFactory] Loop de agentes iniciado")
        while self._running:
            for agent in list(self._agents.values()):
                if self._needs_run(agent):
                    try:
                        await self.run_agent(agent)
                    except Exception as e:
                        logger.error(f"[AgentFactory] Error en agente {agent['id']}: {e}")
            await asyncio.sleep(60)  # revisar cada minuto


agent_factory = AgentFactory()
