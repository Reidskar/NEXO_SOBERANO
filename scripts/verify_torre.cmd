@echo off
echo === NEXO SOBERANO - Verificacion Torre ===
echo.
echo [1] Git pull...
git pull origin main
echo.
echo [2] Startup test...
python -c "from main import app; print('[OK] STARTUP TORRE')"
echo.
echo [3] Docker services...
docker ps --format "table {{.Names}}\t{{.Status}}" | findstr nexo_
echo.
echo [4] MCP Logistics health...
echo {"tool": "health"} | python mcp_servers/mcp_logistics_scm.py
echo.
echo [5] Web check...
curl -s -o nul -w "HTTP Status: %%{http_code}\n" https://elanarcocapital.com
echo.
echo === Fin verificacion ===
