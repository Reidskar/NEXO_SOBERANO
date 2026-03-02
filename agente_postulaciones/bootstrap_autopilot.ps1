$ErrorActionPreference = 'Stop'

Set-Location 'C:\Users\Admn\Desktop\NEXO_SOBERANO\agente_postulaciones'
$pythonExe = 'C:\Users\Admn\Desktop\NEXO_SOBERANO\.venv\Scripts\python.exe'

if (!(Test-Path $pythonExe)) {
  throw "No se encontró python del entorno: $pythonExe"
}

if (!(Test-Path '.env')) {
  Copy-Item '.env.example' '.env'
  Write-Output 'Se creó .env desde plantilla.'
}

& $pythonExe -m pip install -r requirements.txt
& $pythonExe -m playwright install chromium

powershell -ExecutionPolicy Bypass -File register_task.ps1

Write-Output 'Autopilot bootstrap completo.'
Write-Output 'Siguiente paso: completar credenciales en .env y ejecutar enable_live_mode.ps1'
