"""
backend/services/mcp_bridge.py
================================
Puente entre NEXO y el Docker MCP Gateway.

El gateway corre en http://localhost:3200 con --transport=streaming.
Protocolo: MCP sobre HTTP (Streamable HTTP transport).

Uso básico:
  result = await mcp_bridge.call("playwright_navigate", {"url": "https://bbc.com"})
  tools  = await mcp_bridge.list_tools()
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

MCP_GATEWAY_URL = os.getenv("MCP_GATEWAY_URL", "http://localhost:3200")
MCP_GATEWAY_TOKEN = os.getenv("MCP_GATEWAY_AUTH_TOKEN", "nexo_mcp_2026_secure")

_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Authorization": f"Bearer {MCP_GATEWAY_TOKEN}",
}


class MCPBridge:
    """Cliente ligero para el Docker MCP Gateway."""

    def __init__(self):
        self._tools_cache: list[dict] | None = None

    # ── Herramientas disponibles ──────────────────────────────────────

    async def list_tools(self, force_refresh: bool = False) -> list[dict]:
        """Lista las herramientas MCP disponibles (cachea en memoria)."""
        if self._tools_cache and not force_refresh:
            return self._tools_cache
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{MCP_GATEWAY_URL}/mcp",
                    headers=_HEADERS,
                    json={
                        "jsonrpc": "2.0",
                        "id": str(uuid.uuid4()),
                        "method": "tools/list",
                        "params": {},
                    },
                )
                data = r.json()
                tools = data.get("result", {}).get("tools", [])
                self._tools_cache = tools
                return tools
        except Exception as e:
            logger.warning(f"[MCPBridge] list_tools error: {e}")
            return []

    async def tools_by_server(self) -> dict[str, list[str]]:
        """Agrupa herramientas por servidor MCP."""
        tools = await self.list_tools()
        groups: dict[str, list[str]] = {}
        for t in tools:
            name: str = t.get("name", "")
            server = name.split("_")[0] if "_" in name else "general"
            groups.setdefault(server, []).append(name)
        return groups

    # ── Llamada a una herramienta ─────────────────────────────────────

    async def call(
        self,
        tool_name: str,
        params: dict,
        timeout: float = 30.0,
    ) -> dict:
        """
        Llama a una herramienta MCP en el gateway.
        Retorna: {ok, result, error}
        """
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": params,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.post(
                    f"{MCP_GATEWAY_URL}/mcp",
                    headers=_HEADERS,
                    json=payload,
                )
                if r.status_code == 200:
                    data = r.json()
                    if "error" in data:
                        return {"ok": False, "error": data["error"]}
                    content = data.get("result", {}).get("content", [])
                    # Extraer texto plano del primer content block
                    text = ""
                    for block in content:
                        if block.get("type") == "text":
                            text += block.get("text", "")
                    return {"ok": True, "result": text, "raw": data.get("result")}
                return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}
        except httpx.ConnectError:
            return {"ok": False, "error": "MCP Gateway no disponible en localhost:3200. Inicia con: pm2 start mcp-gateway"}
        except Exception as e:
            logger.error(f"[MCPBridge] call({tool_name}) error: {e}")
            return {"ok": False, "error": str(e)}

    # ── Helpers de alto nivel ─────────────────────────────────────────

    async def playwright_screenshot(self, url: str) -> dict:
        """Toma captura de pantalla de una URL."""
        nav = await self.call("playwright_navigate", {"url": url})
        if not nav["ok"]:
            return nav
        return await self.call("playwright_screenshot", {"name": "capture", "fullPage": False})

    async def playwright_fetch(self, url: str) -> dict:
        """Obtiene el contenido de una página web."""
        return await self.call("playwright_get_visible_text", {"random_string": "fetch"})

    async def cloudflare_search_docs(self, query: str) -> dict:
        """Busca en documentación de Cloudflare."""
        return await self.call("cloudflare-docs_search", {"query": query})

    async def discord_send_message(self, channel_id: str, content: str) -> dict:
        """Envía mensaje a Discord via MCP Discord tool."""
        return await self.call("discord_send_message", {
            "channel_id": channel_id,
            "content": content,
        })

    async def is_available(self) -> bool:
        """Verifica que el gateway esté activo."""
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{MCP_GATEWAY_URL}/health", headers=_HEADERS)
                return r.status_code < 500
        except Exception:
            return False


mcp_bridge = MCPBridge()
