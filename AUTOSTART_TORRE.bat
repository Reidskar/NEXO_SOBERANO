@echo off
:: ============================================================
::  AUTOSTART_TORRE.bat — NEXO SOBERANO Auto-Startup
::  Registers itself in Windows Task Scheduler to run on login.
::  Run once as Administrator to install; then runs automatically.
:: ============================================================

SET ROOT=%~dp0
SET ROOT=%ROOT:~0,-1%
SET PYTHON=%ROOT%\.venv\Scripts\python.exe
SET CLOUDFLARED="C:\Program Files (x86)\cloudflared\cloudflared.exe"
SET TUNNEL_ID=2205f004-b6de-4ede-a3c2-365a24afe0c2
SET TASK_NAME=NEXO_Torre_Autostart

:: ─── If called with --install, register in Task Scheduler ───
IF "%1"=="--install" GOTO :INSTALL
IF "%1"=="--uninstall" GOTO :UNINSTALL

:: ─── Normal launch (called by Task Scheduler on login) ───────
GOTO :LAUNCH

:INSTALL
echo [NEXO] Registrando tarea en Task Scheduler...
schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "\"%~f0\"" ^
  /sc ONLOGON ^
  /ru "%USERNAME%" ^
  /rl HIGHEST ^
  /delay 0000:30 ^
  /f
IF %ERRORLEVEL%==0 (
    echo [NEXO] ✓ Tarea registrada. Se ejecutará en cada inicio de sesión.
    echo [NEXO]   Nombre: %TASK_NAME%
    echo [NEXO]   Trigger: Al iniciar sesión con retraso de 30 segundos
) ELSE (
    echo [NEXO] ✗ Error al registrar tarea. Ejecuta como Administrador.
)
GOTO :EOF

:UNINSTALL
echo [NEXO] Eliminando tarea del Task Scheduler...
schtasks /delete /tn "%TASK_NAME%" /f
echo [NEXO] Tarea eliminada.
GOTO :EOF

:LAUNCH
echo [NEXO] ====================================================
echo [NEXO]  NEXO SOBERANO — Torre Startup
echo [NEXO]  %DATE% %TIME%
echo [NEXO] ====================================================

:: ─── 1. Docker services ──────────────────────────────────────
echo [NEXO] Iniciando servicios Docker...
docker compose -f "%ROOT%\docker-compose.yml" up -d nexo_db nexo_redis nexo_qdrant 2>nul
IF %ERRORLEVEL%==0 (
    echo [NEXO] ✓ Docker services up
) ELSE (
    echo [NEXO] ! Docker no disponible o ya corriendo — continuando
)

:: ─── 2. Wait for Docker to settle ────────────────────────────
timeout /t 5 /nobreak >nul

:: ─── 3. Start backend ────────────────────────────────────────
echo [NEXO] Iniciando backend FastAPI...
start "NEXO Backend" /MIN cmd /c "cd /d "%ROOT%" && "%PYTHON%" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 >> "%ROOT%\logs\backend.log" 2>&1"
timeout /t 4 /nobreak >nul

:: ─── 4. Start Cloudflare Tunnel ──────────────────────────────
echo [NEXO] Iniciando Cloudflare Tunnel...
IF EXIST %CLOUDFLARED% (
    start "NEXO Cloudflare Tunnel" /MIN cmd /c "%CLOUDFLARED% tunnel run %TUNNEL_ID% >> "%ROOT%\logs\cloudflare.log" 2>&1"
    echo [NEXO] ✓ Cloudflare Tunnel lanzado
) ELSE (
    echo [NEXO] ! cloudflared.exe no encontrado en %CLOUDFLARED%
    echo [NEXO]   Descarga: https://github.com/cloudflare/cloudflared/releases
)

:: ─── 5. Verify backend health ────────────────────────────────
timeout /t 5 /nobreak >nul
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:8000/health > "%TEMP%\nexo_health.txt" 2>nul
SET /p HEALTH_CODE=<"%TEMP%\nexo_health.txt"
IF "%HEALTH_CODE%"=="200" (
    echo [NEXO] ✓ Backend responde OK (HTTP 200)
) ELSE (
    echo [NEXO] ! Backend no responde aún (código: %HEALTH_CODE%) — puede tardar unos segundos más
)

echo [NEXO] ====================================================
echo [NEXO]  Startup completo. Dominio: elanarcocapital.com
echo [NEXO]  API local: http://127.0.0.1:8000
echo [NEXO] ====================================================

:: Keep the window open for 5 seconds then minimize
timeout /t 5 /nobreak >nul
