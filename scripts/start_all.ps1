Write-Host "Iniciando infraestructura de NEXO SOBERANO v1.0.1..." -ForegroundColor Cyan

$baseDir = "C:\Users\Admn\Desktop\NEXO_SOBERANO"

# 1. API - Uvicorn
Start-Process powershell -ArgumentList "-NoExit", "-Title", "'NEXO API - Uvicorn'", "-Command", "cd $baseDir; .\.venv\Scripts\activate; python -m uvicorn NEXO_CORE.main:app --reload --port 8000"

# 2. Celery Worker
Start-Process powershell -ArgumentList "-NoExit", "-Title", "'NEXO Celery Worker'", "-Command", "cd $baseDir; .\.venv\Scripts\activate; python -m celery -A backend.worker.celery_app worker --loglevel=info --pool=solo"

# 3. Celery Beat
Start-Process powershell -ArgumentList "-NoExit", "-Title", "'NEXO Celery Beat'", "-Command", "cd $baseDir; .\.venv\Scripts\activate; python -m celery -A backend.worker.celery_app beat --loglevel=info"

# 4. Discord Bot
Start-Process powershell -ArgumentList "-NoExit", "-Title", "'NEXO Discord Bot (Node)'", "-Command", "cd $baseDir\discord_bot; node bot.js"

Write-Host "======================================================" -ForegroundColor Magenta
Write-Host "✅ API, Celery Worker, Celery Beat y Discord Bot lanzados." -ForegroundColor Green
Write-Host "⚠️  Nota Infraestructura: Recuerda levantar Redis y Qdrant." -ForegroundColor Yellow
Write-Host "   (Si usabas Docker: cd backend\worker; docker-compose up -d)" -ForegroundColor Gray
Write-Host "======================================================" -ForegroundColor Magenta
Write-Host "Para validar el entorno completo cuando todo cargue, ejecuta:" -ForegroundColor Cyan
Write-Host ".\.venv\Scripts\python.exe scripts\smoke_test.py" -ForegroundColor White
