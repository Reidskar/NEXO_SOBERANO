@echo off
title NEXO SOBERANO — Torre Setup Completo
color 0A
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   NEXO SOBERANO — Torre Setup Completo  ║
echo  ╚══════════════════════════════════════════╝
echo.

:: ─── 1. Verificar Docker Desktop ─────────────────────────────────────────────
echo [1/5] Verificando Docker Desktop...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo  ⚠  Docker no está corriendo. Iniciando Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo  ⏳ Esperando que Docker Desktop levante (hasta 90s)...
    set /a tries=0
    :WAIT_DOCKER
    set /a tries+=1
    if %tries% gtr 30 (
        echo  ✗ Docker no respondió. Ábrelo manualmente y vuelve a ejecutar.
        pause
        exit /b 1
    )
    timeout /t 3 /nobreak >nul
    docker info >nul 2>&1
    if %errorlevel% neq 0 goto WAIT_DOCKER
    echo  ✓ Docker Desktop listo!
) else (
    echo  ✓ Docker ya está corriendo.
)

:: ─── 2. Verificar .env ───────────────────────────────────────────────────────
echo.
echo [2/5] Verificando .env...
if not exist ".env" (
    echo  ⚠  .env no encontrado. Copiando desde .env.example...
    copy ".env.example" ".env" >nul
    echo  ⚠  EDITA .env con tus credenciales antes de continuar.
    notepad .env
    pause
)
:: Verificar POSTGRES_PASSWORD
findstr /C:"POSTGRES_PASSWORD=" .env | findstr /v "POSTGRES_PASSWORD=$" | findstr /v "POSTGRES_PASSWORD= " >nul 2>&1
if %errorlevel% neq 0 (
    echo  ⚠  POSTGRES_PASSWORD no definida en .env
    set /p PGPASS=  Ingresa una password para PostgreSQL:
    echo POSTGRES_PASSWORD=%PGPASS%>>.env
    echo  ✓ POSTGRES_PASSWORD guardada.
) else (
    echo  ✓ .env OK
)

:: ─── 3. Levantar Docker Compose ──────────────────────────────────────────────
echo.
echo [3/5] Levantando servicios Docker (PostgreSQL + Redis + Qdrant)...
docker compose --profile dev up -d nexo_db nexo_redis nexo_qdrant
if %errorlevel% neq 0 (
    echo  ✗ Error en docker compose. Revisa los logs.
    docker compose logs --tail 20
    pause
    exit /b 1
)

:: ─── 4. Verificar 3 contenedores UP ─────────────────────────────────────────
echo.
echo [4/5] Verificando contenedores...
timeout /t 5 /nobreak >nul
docker ps --format "table {{.Names}}\t{{.Status}}" | findstr nexo_
echo.
for /f %%i in ('docker ps --filter "name=nexo_" --filter "status=running" -q ^| find /c /v ""') do set RUNNING=%%i
echo  Contenedores corriendo: %RUNNING%/3
if %RUNNING% lss 3 (
    echo  ⚠  No todos los servicios están Up. Revisando logs...
    docker compose logs nexo_db --tail 10
    docker compose logs nexo_redis --tail 5
    docker compose logs nexo_qdrant --tail 5
) else (
    echo  ✓ [OK] nexo_db  [OK] nexo_redis  [OK] nexo_qdrant
)

:: ─── 5. Verificar Python/Backend ─────────────────────────────────────────────
echo.
echo [5/5] Verificando entorno Python...
if not exist ".venv\Scripts\python.exe" (
    echo  ⚠  .venv no existe. Creando entorno virtual...
    python -m venv .venv
    echo  ⏳ Instalando dependencias (puede tardar 2-3 min)...
    .venv\Scripts\pip.exe install -r requirements.txt --quiet
    echo  ✓ Dependencias instaladas.
) else (
    echo  ✓ .venv existe.
)

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║          TORRE LISTA                     ║
echo  ║                                          ║
echo  ║  PostgreSQL  → localhost:5432            ║
echo  ║  Redis       → localhost:6379            ║
echo  ║  Qdrant      → localhost:6333            ║
echo  ║                                          ║
echo  ║  Para iniciar backend:                   ║
echo  ║  .venv\Scripts\python.exe -m uvicorn    ║
echo  ║  main:app --host 0.0.0.0 --port 8000    ║
echo  ╚══════════════════════════════════════════╝
echo.
pause
