# Script de Verificación Post-Reinicio

$headers = @{'X-NEXO-API-KEY'='CAMBIA_ESTA_CLAVE_NEXO'}

Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  🔍 VERIFICACIÓN DEL SISTEMA NEXO" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# 1. Health Check
Write-Host "1. Backend Health..." -NoNewline
try {
    $health = Invoke-RestMethod -Uri 'http://localhost:8000/api/health' -Headers $headers -TimeoutSec 5
    Write-Host " ✅ OK ($($health.status))" -ForegroundColor Green
} catch {
    Write-Host " ❌ ERROR" -ForegroundColor Red
    Write-Host "   Backend no responde. Asegúrate de reiniciarlo." -ForegroundColor Yellow
    exit
}

# 2. Evolution Status
Write-Host "2. Evolución IA Status..." -NoNewline
try {
    $evo = Invoke-RestMethod -Uri 'http://localhost:8000/api/ai/evolution-status' -Headers $headers -TimeoutSec 5
    Write-Host " ✅ Disponible" -ForegroundColor Green
    if ($evo.has_data) {
        Write-Host "   Score: $($evo.data.quality_score)" -ForegroundColor Cyan
        Write-Host "   Críticos: $($evo.data.critical_issues)" -ForegroundColor Cyan
    }
} catch {
    Write-Host " ❌ No disponible" -ForegroundColor Red
    Write-Host "   Reinicia el backend para cargar nuevos endpoints." -ForegroundColor Yellow
}

# 3. Control Center
Write-Host "3. Control Center..." -NoNewline
try {
    $response = Invoke-WebRequest -Uri 'http://localhost:8000/control-center' -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host " ✅ Accesible" -ForegroundColor Green
    }
} catch {
    Write-Host " ❌ No accesible" -ForegroundColor Red
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  📋 PRÓXIMOS PASOS:" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Abre: http://localhost:8000/control-center" -ForegroundColor White
Write-Host "  2. Presiona F5 para recargar" -ForegroundColor White
Write-Host "  3. Click en 'Evolución IA (auto)'" -ForegroundColor White
Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
