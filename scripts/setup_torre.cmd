@echo off
title NEXO SOBERANO - Setup Torre
color 0A
echo.
echo  ==========================================
echo   NEXO SOBERANO - Setup Automatico Torre
echo  ==========================================
echo.
echo [1/7] Sincronizando repositorio...
git fetch origin
git reset --hard origin/main
git log --oneline -3
echo.
echo [2/7] Instalando dependencias Python...
pip install PyNaCl pydantic-settings aiosqlite "pydantic[email]" faster-whisper slowapi pandas matplotlib requests psutil pip-audit 2>&1 | findstr /v "already satisfied\|Requirement"
echo.
echo [3/7] Verificando startup Python...
set DATABASE_URL=sqlite+aiosqlite:///test.db
python -c "from main import app; print('[OK] STARTUP TORRE')" 2>&1 | findstr "OK\|ERROR"
echo.
echo [4/7] Verificando Docker...
docker ps >nul 2>&1
if errorlevel 1 (
    echo [!] Docker Desktop no esta corriendo.
    echo     Abrelo desde el menu inicio y espera que la ballena quede verde.
    echo     Luego vuelve a ejecutar este script.
    pause
    exit /b 1
)
docker ps --format "table {{.Names}}\t{{.Status}}" | findstr nexo_
if errorlevel 1 (
    echo Levantando servicios Docker...
    docker compose --profile dev up -d nexo_db nexo_redis nexo_qdrant
    timeout /t 15 /nobreak
    docker ps | findstr nexo_
) else (
    echo [OK] Servicios Docker corriendo.
)
echo.
echo [5/7] Verificando Ollama...
ollama --version >nul 2>&1
if errorlevel 1 (
    echo [!] Ollama NO instalado.
    echo     Descargar de: https://ollama.com/download/windows
    echo     Luego ejecutar: ollama pull gemma3:9b
) else (
    echo [OK] Ollama instalado.
    ollama list
)
echo.
echo [6/7] Verificando bot Discord...
pm2 status 2>&1 | findstr nexo-discord-bot
echo.
echo [7/7] Verificacion final...
echo --- API health ---
curl -s http://localhost:8000/api/health 2>nul || echo [!] API no responde - inicia uvicorn primero
echo.
echo --- Docker ---
docker ps --format "table {{.Names}}\t{{.Status}}"
echo.
echo --- PM2 ---
pm2 status
echo.
echo  ==========================================
echo   PENDIENTES QUE DEBES HACER MANUALMENTE:
echo  ==========================================
echo.
echo  1. TOKEN DISCORD:
echo     - discord.com/developers/applications
echo     - ElAnarcocapital - Bot - Reset Token
echo     - Pegar en: discord_bot\.env
echo     - DISCORD_TOKEN=token_nuevo_aqui
echo.
echo  2. VARIABLES .env principal:
echo     notepad C:\Users\Admn\Desktop\NEXO_SOBERANO\.env
echo     Agregar:
echo     GEMINI_API_KEY=tu_clave_de_aistudio.google.com
echo     GOOGLE_CREDENTIALS_PATH=C:\Users\Admn\Desktop\NEXO_SOBERANO\credenciales_google.json
echo     GOOGLE_DRIVE_FOLDER_ID_GEOPOLITICA=10pn6Zo5_SUTf2jlWaH98rs0wtF3W0Trx
echo.
echo  3. REINICIAR BOT (desde cmd.exe, NO PowerShell):
echo     pm2 restart nexo-discord-bot
echo     pm2 logs nexo-discord-bot --lines 20
echo.
echo  4. RAILWAY VARIABLES (desde browser):
echo     railway.app - NEXO_SOBERANO - Variables
echo     Agregar: GEMINI_API_KEY y GOOGLE_CREDENTIALS_JSON
echo.
echo  ==========================================
echo   COMANDOS DISCORD DISPONIBLES:
echo  ==========================================
echo   /nexo          - consulta con RAG
echo   /drive         - busca en Google Drive
echo   /geopolitica   - carpeta Geopolitica
echo   /social        - analisis redes sociales
echo   /status        - metricas del sistema
echo   /unirse        - bot entra a voz
echo   /salir         - bot sale de voz
echo  ==========================================
echo.
pause
