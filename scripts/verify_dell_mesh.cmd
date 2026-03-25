@echo off
echo === NEXO — Verificar Dell Latitude en Mesh ===
echo.
echo [1] Estado del mesh completo:
tailscale status
echo.
echo [2] IPs del mesh:
tailscale ip -4
echo.
echo [3] Intentando ping a posibles IPs del Dell...
for %%i in (100.64.0.2 100.64.0.3 100.64.0.4 100.100.0.2) do (
    ping -n 1 -w 1000 %%i >nul 2>&1
    if not errorlevel 1 echo   [RESPONDE] %%i
)
echo.
echo Ejecutar "tailscale status" para ver la IP exacta del Dell
echo === Fin ===
