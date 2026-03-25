@echo off
echo === NEXO SOBERANO — Configurar variables Railway ===
echo ADVERTENCIA: Este script configura produccion.
echo Asegurate de tener railway CLI autenticado.
echo.

railway variables set OLLAMA_ENABLED=false
railway variables set NEXO_DOMAIN=elanarcocapital.com
railway variables set ENVIRONMENT=production
railway variables set PYTHONUNBUFFERED=1
railway variables set PORT=8000
echo [OK] Variables basicas configuradas.
echo.
echo Variables que debes configurar MANUALMENTE en Railway Dashboard:
echo   DATABASE_URL     (Supabase PostgreSQL)
echo   GEMINI_API_KEY   (Google AI Studio)
echo   SECRET_KEY       (string aleatorio 32+ chars)
echo   DISCORD_TOKEN    (Discord Developer Portal)
echo   TELEGRAM_TOKEN   (@BotFather)
echo   SUPABASE_URL
echo   SUPABASE_ANON_KEY
echo   SUPABASE_SERVICE_KEY
echo.
echo Para setearlas: railway variables set NOMBRE=valor
echo === Fin ===
