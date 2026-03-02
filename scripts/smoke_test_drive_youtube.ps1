param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [switch]$SkipAuthorize,
    [switch]$RunRealUpload
)

$ErrorActionPreference = "Stop"

function Step($message) {
    Write-Host "`n==> $message" -ForegroundColor Cyan
}

function Invoke-ApiJson($method, $url, $bodyObj) {
    $json = if ($null -ne $bodyObj) { $bodyObj | ConvertTo-Json -Depth 12 } else { "{}" }
    return Invoke-RestMethod -Method $method -Uri $url -ContentType "application/json" -Body $json
}

Write-Host "Smoke Test Drive + YouTube (NEXO SOBERANO)" -ForegroundColor Green

# 1) Verificar .env
Step "Validando .env"
if (-not (Test-Path ".env")) {
    throw ".env no encontrado"
}
$envRaw = Get-Content ".env" -Raw
$requiredAny = @(
    @("DRIVE_CLIENT_ID", "GOOGLE_CLIENT_ID"),
    @("DRIVE_CLIENT_SECRET", "GOOGLE_CLIENT_SECRET"),
    @("YOUTUBE_CLIENT_ID", "GOOGLE_CLIENT_ID"),
    @("YOUTUBE_CLIENT_SECRET", "GOOGLE_CLIENT_SECRET")
)
foreach ($pair in $requiredAny) {
    $ok = $false
    foreach ($k in $pair) {
        if ($envRaw -match "(?m)^\s*$k\s*=") {
            $ok = $true
            break
        }
    }
    if (-not $ok) {
        throw "Falta al menos una de estas variables en .env: $($pair -join ' o ')"
    }
}

# 2) Health backend
Step "Verificando backend health"
$health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/health"
$health | ConvertTo-Json -Depth 6 | Write-Host

# 3) Bootstrap secrets (si aplica)
Step "Bootstrap de client_secrets (Drive + YouTube)"
try {
    (Invoke-ApiJson "Post" "$BaseUrl/agente/drive/create-client-secrets" @{}) | ConvertTo-Json -Depth 6 | Write-Host
} catch {
    Write-Host "Aviso Drive client_secrets: $($_.Exception.Message)" -ForegroundColor Yellow
}
try {
    (Invoke-ApiJson "Post" "$BaseUrl/agente/youtube/create-client-secrets" @{}) | ConvertTo-Json -Depth 6 | Write-Host
} catch {
    Write-Host "Aviso YouTube client_secrets: $($_.Exception.Message)" -ForegroundColor Yellow
}

# 4) Autorizar tokens (opcional)
if (-not $SkipAuthorize) {
    Step "Autorizando Drive (puede abrir navegador)"
    (Invoke-ApiJson "Post" "$BaseUrl/agente/drive/authorize" @{ write_scope = $true }) | ConvertTo-Json -Depth 6 | Write-Host

    Step "Autorizando YouTube upload (puede abrir navegador)"
    (Invoke-ApiJson "Post" "$BaseUrl/agente/youtube/authorize" @{ upload_scope = $true }) | ConvertTo-Json -Depth 6 | Write-Host
} else {
    Step "Saltando autorización interactiva por -SkipAuthorize"
}

# 5) Crear carpeta de smoke test
Step "Asegurando carpeta de smoke test en Drive"
$folder = Invoke-ApiJson "Post" "$BaseUrl/agente/drive/ensure-folder" @{
    path_parts = @("NEXO_SOBERANO_CLASIFICADO", "SmokeTests", "DailyResume")
    parent_id = "root"
}
$folder | ConvertTo-Json -Depth 6 | Write-Host
$folderId = $folder.folder_id
if (-not $folderId) { throw "No se obtuvo folder_id" }

# 6) Subir resumen dummy con nombre compatible
Step "Subiendo resumen dummy a Drive"
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$filename = "resumen_prueba_$ts.txt"
$summaryText = @"
Resumen SIG Diario - Prueba Automática
Fecha: $(Get-Date -Format "yyyy-MM-dd HH:mm")
Indicador riesgo conflicto: 4/5
Movimientos radares detectados en zona X
Impacto económico estimado: +3.2%
Evidencia: https://example.org/evidencia-demo
"@
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($summaryText))
$upload = Invoke-ApiJson "Post" "$BaseUrl/agente/drive/upload-b64" @{
    folder_id = $folderId
    filename = $filename
    file_b64 = $b64
}
$upload | ConvertTo-Json -Depth 8 | Write-Host

# 7) Ejecutar pipeline en dry-run
Step "Ejecutando /agente/youtube/daily-resume en dry-run"
$dry = Invoke-ApiJson "Post" "$BaseUrl/agente/youtube/daily-resume" @{
    dry_run = $true
    max_scan = 100
    privacy_status = "unlisted"
}
$dry | ConvertTo-Json -Depth 10 | Write-Host

if (-not $RunRealUpload) {
    $ans = Read-Host "¿Subir video REAL a YouTube ahora? (s/n)"
    if ($ans -eq "s" -or $ans -eq "S") {
        $RunRealUpload = $true
    }
}

# 8) Ejecutar pipeline real si se solicita
if ($RunRealUpload) {
    Step "Ejecutando /agente/youtube/daily-resume REAL"
    $real = Invoke-ApiJson "Post" "$BaseUrl/agente/youtube/daily-resume" @{
        dry_run = $false
        max_scan = 100
        privacy_status = "unlisted"
    }
    $real | ConvertTo-Json -Depth 12 | Write-Host
} else {
    Step "Se mantiene en dry-run (sin upload real)"
}

Write-Host "`nSmoke test Drive + YouTube finalizado." -ForegroundColor Green
