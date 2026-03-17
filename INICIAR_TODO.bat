@echo off
title El Anarcocapital — Torre de Control
echo.
echo  =========================================
echo   EL ANARCOCAPITAL — Iniciando Stack GPU
echo  =========================================
echo.

:: 1. Docker + Qdrant
echo [1/4] Iniciando Qdrant (cerebro vectorial)...
docker start qdrant 2>nul || (
    docker run -d --name qdrant --restart unless-stopped ^
      -p 6333:6333 -p 6334:6334 ^
      -v "%USERPROFILE%\qdrant_storage:/qdrant/storage" ^
      qdrant/qdrant:latest 2>nul
)
echo      http://localhost:6333/dashboard

:: 2. Cloudflared tunnel
echo [2/4] Iniciando Tunnel Cloudflare (elanarcocapital.com)...
set CF="C:\Program Files (x86)\cloudflared\cloudflared.exe"
if exist %CF% (
    start "Cloudflare Tunnel" /MIN %CF% tunnel run 2205f004-b6de-4ede-a3c2-365a24afe0c2
    echo      elanarcocapital.com -> localhost:8000
) else (
    echo      cloudflared no encontrado
)

:: 3. Backend Python
echo [3/4] Iniciando backend (RTX 3060 GPU)...
cd /d "%~dp0"
start "El Anarcocapital Backend" cmd /k ".venv\Scripts\python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

:: 4. Info red
echo [4/4] Red local:
ipconfig | findstr "IPv4"
echo.
echo  Backend:    http://localhost:8000
echo  Web:        https://elanarcocapital.com
echo  API Docs:   http://localhost:8000/api/docs
echo  Qdrant:     http://localhost:6333/dashboard
echo  Torre:      http://192.168.100.38:8000
echo  Tel. IP:    192.168.100.13 (conectado via USB)
echo.
echo  Para acceder desde telefono: http://192.168.100.22:8000
echo  NOTA: En la Torre ejecutar: tailscale up
echo.

:: 5. Telegram Bot
REM start "TelegramBot" .venv\Scripts\python.exe backend/services/telegram_bot.py

:: 6. Agentes RTX 3060
REM Iniciar live_stream_analyzer.py (CUDA float16)
start "Live Stream Analyzer" .venv\Scripts\python.exe backend/services/live_stream_analyzer.py --cuda --float16
REM Iniciar semantic_classifier.py
start "Semantic Classifier" .venv\Scripts\python.exe backend/services/semantic_classifier.py
REM Iniciar psychology_engine.py
start "Psychology Engine" .venv\Scripts\python.exe backend/services/psychology_engine.py

:: 7. Rebranding global
REM Ejecutar script de rebranding
start "Rebranding" .venv\Scripts\python.exe scripts/rebranding_global.py

:: 8. Verificación de conectividad
REM Ping interno al puerto 8000
curl http://localhost:8000/api/health
REM Revisar logs del túnel
REM start "Cloudflared Logs" cloudflared.exe logs

:: 9. Corrección automática de errores
REM Ejecutar script de limpieza de procesos redundantes
start "Clean Processes" .venv\Scripts\python.exe scripts/kill_redundant_processes.py

echo.
echo  Stack completo iniciado. Presiona cualquier tecla para salir...
pause
