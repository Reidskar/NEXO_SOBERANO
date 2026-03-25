@echo off
echo === NEXO SOBERANO — Startup Automatico ===
echo Iniciando servicios...

:: Docker services
docker compose --profile dev up -d nexo_db nexo_redis nexo_qdrant nexo_n8n
echo [OK] Docker services iniciados

:: Esperar 10 segundos
timeout /t 10 /nobreak > nul

:: API FastAPI (si no esta corriendo)
:: tasklist | find "python" > nul || start /b python -m uvicorn main:app --host 0.0.0.0 --port 8000

:: Discord bot via PM2
pm2 start ecosystem.config.js 2>nul || pm2 restart all
pm2 save
echo [OK] PM2 services iniciados

:: Verificar todo
docker ps --format "table {{.Names}}\t{{.Status}}"
pm2 status
echo === Startup completado ===
