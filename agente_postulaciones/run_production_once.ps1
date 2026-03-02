$ErrorActionPreference = 'Stop'
Set-Location 'C:\Users\Admn\Desktop\NEXO_SOBERANO\agente_postulaciones'

if (!(Test-Path '.env') -and (Test-Path '.env.example')) {
  Copy-Item '.env.example' '.env'
  Write-Output 'Se creó .env desde .env.example. Completa credenciales antes de producción real.'
}

& 'C:\Users\Admn\Desktop\NEXO_SOBERANO\.venv\Scripts\python.exe' 'main.py' '--once'
