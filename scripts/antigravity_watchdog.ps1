$ErrorActionPreference = 'Continue'

$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo ".venv\Scripts\python.exe"
$doctor = Join-Path $repo "scripts\antigravity_doctor.py"
$logDir = Join-Path $repo "logs"
$logFile = Join-Path $logDir "antigravity_watchdog.log"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if (-not (Test-Path $python)) {
    "[$(Get-Date -Format s)] ERROR: Python .venv no encontrado en $python" | Out-File -FilePath $logFile -Append -Encoding utf8
    exit 1
}

if (-not (Test-Path $doctor)) {
    "[$(Get-Date -Format s)] ERROR: antigravity_doctor.py no encontrado en $doctor" | Out-File -FilePath $logFile -Append -Encoding utf8
    exit 1
}

"[$(Get-Date -Format s)] Watchdog iniciado" | Out-File -FilePath $logFile -Append -Encoding utf8

while ($true) {
    try {
        $json = & $python $doctor --quiet 2>&1
        "[$(Get-Date -Format s)] $json" | Out-File -FilePath $logFile -Append -Encoding utf8
    }
    catch {
        "[$(Get-Date -Format s)] ERROR: $($_.Exception.Message)" | Out-File -FilePath $logFile -Append -Encoding utf8
    }

    Start-Sleep -Seconds 180
}
