# ═══════════════════════════════════════════════════════════════════════════
# Script: OBTENER_DISCORD_WEBHOOK.ps1
# Propósito: Guiar la obtención de Discord Webhook URL y actualizar .env
# ═══════════════════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "  ASISTENTE: Obtener Discord Webhook URL para NEXO" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan

Write-Host "PASO 1: Ubicacion en Discord" -ForegroundColor Yellow
Write-Host "   - Abre Discord (web o app de escritorio)" -ForegroundColor White
Write-Host "   - Ve a tu servidor → Click derecho en el nombre del servidor" -ForegroundColor White
Write-Host "   - Selecciona 'Configuracion del servidor'" -ForegroundColor White
Write-Host ""

Write-Host "PASO 2: Crear/Copiar Webhook" -ForegroundColor Yellow
Write-Host "   - Ruta: Integraciones > Webhooks > Ver Webhooks / Crear Webhook" -ForegroundColor White
Write-Host "   - Si ya existe uno de GitHub u otro, podes reutilizarlo" -ForegroundColor White
Write-Host "   - Click en el webhook > 'Copiar URL del Webhook'" -ForegroundColor White
Write-Host ""

Write-Host "PASO 3: Pegar URL aqui" -ForegroundColor Yellow
Write-Host "   Ejemplo: https://discord.com/api/webhooks/123456789/AbCdEfGhIjKlMnOpQrStUvWxYz" -ForegroundColor DarkGray
Write-Host ""

$url = Read-Host "Ingresa la URL copiada (Enter vacio para cancelar)"

if ([string]::IsNullOrWhiteSpace($url)) {
    Write-Host "Cancelado. Ningun cambio." -ForegroundColor Red
    exit 0
}

$url = $url.Trim()

if ($url -notmatch '^https://discord(app)?\.com/api/webhooks/\d+/[\w\-]+$') {
    Write-Host "El formato parece incorrecto. URL esperado:" -ForegroundColor Yellow
    Write-Host "    https://discord.com/api/webhooks/<ID>/<TOKEN>" -ForegroundColor DarkGray
    Write-Host ""
    $confirm = Read-Host "Guardar de todos modos? (s/n)"
    if ($confirm -notin @('s', 'S', 'si', 'SI')) {
        Write-Host "Cancelado." -ForegroundColor Red
        exit 0
    }
}

# Actualizar .env
$envPath = "$PSScriptRoot\.env"
if (!(Test-Path $envPath)) {
    Write-Host "No se encuentra .env en $envPath" -ForegroundColor Red
    exit 1
}

$content = Get-Content $envPath -Raw
$pattern = "DISCORD_WEBHOOK_URL=.*"
$replacement = "DISCORD_WEBHOOK_URL=$url"

if ($content -match $pattern) {
    $newContent = $content -replace $pattern, $replacement
}
else {
    $newContent = "$content`n$replacement"
}

Set-Content -Path $envPath -Value $newContent -NoNewline
Write-Host "" 
Write-Host ".env actualizado con:" -ForegroundColor Green
Write-Host "   DISCORD_WEBHOOK_URL=$($url.Substring(0,[Math]::Min(60,$url.Length)))..." -ForegroundColor White
Write-Host ""
Write-Host "PROXIMO PASO:" -ForegroundColor Yellow
Write-Host "   Reiniciar backend NEXO para aplicar cambio (Ctrl+C en terminal backend y reejecutar tarea de Iniciar Backend)" -ForegroundColor White
Write-Host ""
Write-Host "Listo. Despues del reinicio el preflight deberia mostrar discord_connected=true" -ForegroundColor Cyan
Write-Host ""
