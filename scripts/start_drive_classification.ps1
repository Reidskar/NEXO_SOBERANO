param(
    [string]$PythonExe = "C:/Users/Admn/Desktop/NEXO_SOBERANO/.venv/Scripts/python.exe"
)

$ErrorActionPreference = "Stop"

Write-Host "Iniciando clasificación masiva de Drive..." -ForegroundColor Cyan

$proc = Start-Process -FilePath $PythonExe -ArgumentList "scripts/run_drive_classification_api.py" -PassThru
Write-Host "Proceso lanzado. PID: $($proc.Id)" -ForegroundColor Green
Write-Host "Reporte esperado en: logs/sync_drive_last.json" -ForegroundColor Yellow
