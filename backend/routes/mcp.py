"""
backend/routes/mcp.py
=======================
Endpoints REST para Docker MCP Gateway + Agent Factory.

MCP Gateway:
  GET  /api/mcp/status          — estado del gateway
  GET  /api/mcp/tools           — listar herramientas disponibles
  POST /api/mcp/call            — llamar cualquier herramienta
  POST /api/mcp/playwright/screenshot  — captura de pantalla
  POST /api/mcp/playwright/scrape      — extraer texto de URL

Agentes autónomos:
  GET  /api/agents              — listar agentes
  POST /api/agents              — crear agente
  POST /api/agents/template     — crear desde plantilla
  GET  /api/agents/templates    — plantillas disponibles
  GET  /api/agents/{id}         — detalle de agente
  POST /api/agents/{id}/run     — ejecutar ciclo manualmente
  PATCH /api/agents/{id}        — activar/desactivar
  DELETE /api/agents/{id}       — eliminar agente
"""
from __future__ import annotations

import logging
import os
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(tags=["mcp", "agents"])

API_KEY = os.getenv("NEXO_API_KEY", "NEXO_LOCAL_2026_OK")


def _auth(key=None):
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida")


def _bridge():
    from backend.services.mcp_bridge import mcp_bridge
    return mcp_bridge


def _factory():
    from backend.services.agent_factory import agent_factory
    return agent_factory


# ── MCP Gateway ───────────────────────────────────────────────────────

@router.get("/api/mcp/status")
async def mcp_status(x_api_key: str = Header(None)):
    _auth(x_api_key)
    bridge = _bridge()
    available = await bridge.is_available()
    tools = await bridge.list_tools() if available else []
    groups = await bridge.tools_by_server() if available else {}
    return {
        "gateway_url": "http://localhost:3200",
        "available": available,
        "total_tools": len(tools),
        "servers": {k: len(v) for k, v in groups.items()},
        "note": "Inicia con: pm2 start mcp-gateway" if not available else "OK",
    }


@router.get("/api/mcp/tools")
async def mcp_list_tools(x_api_key: str = Header(None)):
    _auth(x_api_key)
    tools = await _bridge().list_tools(force_refresh=True)
    return {"tools": tools, "total": len(tools)}


class MCPCallRequest(BaseModel):
    tool: str
    params: dict = {}
    timeout: float = 30.0


@router.post("/api/mcp/call")
async def mcp_call(body: MCPCallRequest, x_api_key: str = Header(None)):
    _auth(x_api_key)
    result = await _bridge().call(body.tool, body.params, timeout=body.timeout)
    return result


class ScreenshotRequest(BaseModel):
    url: str


@router.post("/api/mcp/playwright/screenshot")
async def mcp_screenshot(body: ScreenshotRequest, x_api_key: str = Header(None)):
    _auth(x_api_key)
    result = await _bridge().playwright_screenshot(body.url)
    return result


@router.post("/api/mcp/playwright/scrape")
async def mcp_scrape(body: ScreenshotRequest, x_api_key: str = Header(None)):
    _auth(x_api_key)
    result = await _bridge().call("playwright_navigate", {"url": body.url})
    if not result["ok"]:
        return result
    text_result = await _bridge().call("playwright_get_visible_text", {"random_string": "nexo"})
    return text_result


# ── Agentes autónomos ─────────────────────────────────────────────────

@router.get("/api/agents/templates")
def list_templates(x_api_key: str = Header(None)):
    _auth(x_api_key)
    from backend.services.agent_factory import AGENT_TEMPLATES
    return {"templates": list(AGENT_TEMPLATES.keys()), "details": AGENT_TEMPLATES}


@router.get("/api/agents")
def list_agents(x_api_key: str = Header(None)):
    _auth(x_api_key)
    agents = _factory().list_agents()
    return {"agents": agents, "total": len(agents)}


class CreateAgentRequest(BaseModel):
    name: str
    role: str
    tools: list[str]
    model: str = "general"
    schedule_minutes: int = 60
    trigger: str = "schedule"
    discord_channel_id: str = ""


class CreateFromTemplateRequest(BaseModel):
    template: str
    discord_channel_id: str = ""


@router.post("/api/agents")
def create_agent(body: CreateAgentRequest, x_api_key: str = Header(None)):
    _auth(x_api_key)
    agent = _factory().create(
        name=body.name, role=body.role, tools=body.tools,
        model=body.model, schedule_minutes=body.schedule_minutes,
        trigger=body.trigger, discord_channel_id=body.discord_channel_id,
    )
    return {"ok": True, "agent": agent}


@router.post("/api/agents/template")
def create_from_template(body: CreateFromTemplateRequest, x_api_key: str = Header(None)):
    _auth(x_api_key)
    agent = _factory().create_from_template(body.template, body.discord_channel_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Template '{body.template}' no existe")
    return {"ok": True, "agent": agent}


@router.get("/api/agents/{agent_id}")
def get_agent(agent_id: str, x_api_key: str = Header(None)):
    _auth(x_api_key)
    agent = _factory().get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    return agent


@router.post("/api/agents/{agent_id}/run")
async def run_agent(agent_id: str, x_api_key: str = Header(None)):
    _auth(x_api_key)
    factory = _factory()
    agent = factory.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    result = await factory.run_agent(agent)
    return result


class PatchAgentRequest(BaseModel):
    active: Optional[bool] = None
    schedule_minutes: Optional[int] = None


@router.patch("/api/agents/{agent_id}")
def patch_agent(agent_id: str, body: PatchAgentRequest, x_api_key: str = Header(None)):
    _auth(x_api_key)
    factory = _factory()
    agent = factory.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    if body.active is not None:
        factory.toggle(agent_id, body.active)
    if body.schedule_minutes is not None:
        agent["schedule_minutes"] = body.schedule_minutes
        factory._save(agent)
    return {"ok": True, "agent": factory.get(agent_id)}


@router.delete("/api/agents/{agent_id}")
def delete_agent(agent_id: str, x_api_key: str = Header(None)):
    _auth(x_api_key)
    ok = _factory().delete(agent_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    return {"ok": True}
