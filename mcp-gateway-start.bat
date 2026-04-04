@echo off
:: NEXO SOBERANO — MCP Gateway Launcher
:: Expone 58 herramientas MCP via HTTP streaming en puerto 3200
:: Autenticacion: MCP_GATEWAY_AUTH_TOKEN=nexo_mcp_2026_secure

echo [MCP-Gateway] Iniciando Docker MCP Gateway en puerto 3200...
docker mcp gateway run --transport=streaming --port=3200 --long-lived
