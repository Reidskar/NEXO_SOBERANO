# Ejecutar en la TORRE (elanarcocapital) como Administrador
# PowerShell: Set-ExecutionPolicy Bypass -Scope Process; .\setup_torre.ps1

param(
    [string]$TailscaleKey = ""
)

$PC_TAILSCALE = "100.112.238.97"
$BACKEND_PORT = 8000

Write-Host "=== El Anarcocapital — Setup Torre ===" -ForegroundColor Cyan

# 1. Verificar/Instalar Tailscale
if (-not (Get-Command tailscale -ErrorAction SilentlyContinue)) {
    Write-Host "[1/3] Instalando Tailscale..." -ForegroundColor Yellow
    winget install Tailscale.Tailscale -e --silent
}

# Reconectar Tailscale
if ($TailscaleKey) {
    tailscale up --authkey=$TailscaleKey --hostname="elanarcocapital"
    Write-Host "[OK] Tailscale conectado" -ForegroundColor Green
} else {
    tailscale up --hostname="elanarcocapital"
    Write-Host "[OK] Tailscale reconectado" -ForegroundColor Green
}

# 2. Habilitar SSH (OpenSSH Server)
Write-Host "[2/3] Habilitando SSH..." -ForegroundColor Yellow
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 -ErrorAction SilentlyContinue
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd
Write-Host "[OK] SSH habilitado en puerto 22" -ForegroundColor Green

# 3. Verificar acceso al backend principal
Write-Host "[3/3] Verificando red..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod "http://${PC_TAILSCALE}:${BACKEND_PORT}/api/health" -TimeoutSec 5
    Write-Host "[OK] Backend accesible: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "[!] Backend no accesible — verificar que PC principal esté corriendo" -ForegroundColor Red
}

# 4. Estado final
Write-Host ""
Write-Host "=== Estado de red ===" -ForegroundColor Cyan
tailscale status
Write-Host ""
Write-Host "Backend PC: http://${PC_TAILSCALE}:${BACKEND_PORT}" -ForegroundColor White
Write-Host "API Docs:   http://${PC_TAILSCALE}:${BACKEND_PORT}/api/docs" -ForegroundColor White
