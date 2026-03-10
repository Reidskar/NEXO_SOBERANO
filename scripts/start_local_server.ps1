# start_local_server.ps1
# Script de arranque automatizado para NEXO SOBERANO (PC Local - Músculo)

$baseDir = "C:\Users\Admn\Desktop\NEXO_SOBERANO"
Set-Location $baseDir

Write-Host "🚀 Iniciando Nexo Soberano en modo LOCAL (Músculo)..." -ForegroundColor Cyan

# 1. API - Uvicorn (Puerto 8000)
Start-Process powershell -WindowStyle Minimized -ArgumentList "-Command", "cd $baseDir; .\.venv\Scripts\activate; python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"

# 2. Celery Worker
Start-Process powershell -WindowStyle Minimized -ArgumentList "-Command", "cd $baseDir; .\.venv\Scripts\activate; python -m celery -A backend.worker.celery_app worker --loglevel=info --pool=solo"

# 3. Celery Beat
Start-Process powershell -WindowStyle Minimized -ArgumentList "-Command", "cd $baseDir; .\.venv\Scripts\activate; python -m celery -A backend.worker.celery_app beat --loglevel=info"

# 4. Qdrant (Intento de arranque vía Docker Desktop si existe o mensaje)
# Si docker no está en el PATH, avisamos al usuario o probamos ruta estándar
$dockerPath = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
if (Test-Path $dockerPath) {
    Start-Process $dockerPath -ArgumentList "start qdrant" -WindowStyle Hidden
} else {
    Write-Host "⚠️ No se encontró Docker en el PATH. Asegúrate de que Qdrant esté corriendo." -ForegroundColor Yellow
}

Write-Host "✅ Stack local iniciado en segundo plano (minimizados)." -ForegroundColor Green
