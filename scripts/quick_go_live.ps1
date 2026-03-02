param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [switch]$AutoConfirm
)

$ErrorActionPreference = "Stop"

function Step($message) {
    Write-Host "`n==> $message" -ForegroundColor Cyan
}

function Get-DotEnvMap([string]$path) {
    $data = @{}
    if (-not (Test-Path $path)) { return $data }
    foreach ($line in Get-Content $path) {
        $trim = $line.Trim()
        if (-not $trim -or $trim.StartsWith("#") -or -not $trim.Contains("=")) { continue }
        $idx = $trim.IndexOf("=")
        $k = $trim.Substring(0, $idx).Trim()
        $v = $trim.Substring($idx + 1).Trim()
        if ($v.StartsWith('"') -and $v.EndsWith('"')) { $v = $v.Substring(1, $v.Length - 2) }
        if ($v.StartsWith("'") -and $v.EndsWith("'")) { $v = $v.Substring(1, $v.Length - 2) }
        $data[$k] = $v
    }
    return $data
}

function Invoke-ApiJson($method, $url, $bodyObj) {
    $json = if ($null -ne $bodyObj) { $bodyObj | ConvertTo-Json -Depth 12 } else { "{}" }
    return Invoke-RestMethod -Method $method -Uri $url -ContentType "application/json" -Body $json
}

Write-Host "Quick Go-Live Drive -> YouTube" -ForegroundColor Green

Step "Validando preflight"
$preflight = Invoke-RestMethod -Method Get -Uri "$BaseUrl/agente/go-live/preflight"
$preflight | ConvertTo-Json -Depth 10 | Write-Host

if (-not $preflight.ffmpeg.found) {
    throw "FFmpeg no está en PATH. Instálalo antes de continuar."
}
if (-not $preflight.env.google_client -or -not $preflight.env.google_secret) {
    throw "Faltan GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET (o equivalentes) en .env"
}
if (-not $preflight.files.youtube_token_upload) {
    throw "Falta token de YouTube upload. Ejecuta /agente/youtube/authorize con upload_scope=true"
}

Step "Preparando carpeta destino"
$envMap = Get-DotEnvMap ".env"
$targetFolderId = $null
if ($envMap.ContainsKey("DRIVE_ROOT_FOLDER_ID") -and $envMap["DRIVE_ROOT_FOLDER_ID"]) {
    $targetFolderId = $envMap["DRIVE_ROOT_FOLDER_ID"]
} else {
    $ensure = Invoke-ApiJson "Post" "$BaseUrl/agente/drive/ensure-folder" @{
        path_parts = @("NEXO_SOBERANO_CLASIFICADO", "QuickGoLive")
        parent_id = "root"
    }
    $targetFolderId = $ensure.folder_id
}
if (-not $targetFolderId) { throw "No se obtuvo carpeta destino en Drive" }

Step "Subiendo resumen dummy"
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$filename = "resumen_diario_rapido_$ts.txt"
$txt = @"
Resumen SIG - Prueba Rápida
Fecha: $(Get-Date -Format "yyyy-MM-dd HH:mm")
Riesgo: 4/5
Fuente: https://drive.google.com
"@
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($txt))
$upload = Invoke-ApiJson "Post" "$BaseUrl/agente/drive/upload-b64" @{
    folder_id = $targetFolderId
    filename = $filename
    file_b64 = $b64
}
$upload | ConvertTo-Json -Depth 10 | Write-Host

Step "Ejecutando dry-run"
$dry = Invoke-ApiJson "Post" "$BaseUrl/agente/youtube/daily-resume" @{
    dry_run = $true
    max_scan = 100
    privacy_status = "unlisted"
}
$dry | ConvertTo-Json -Depth 12 | Write-Host

$go = $AutoConfirm
if (-not $AutoConfirm) {
    $ans = Read-Host "¿Subir REAL ahora? (s/n)"
    $go = ($ans -eq "s" -or $ans -eq "S")
}

if (-not $go) {
    Write-Host "Se dejó en dry-run." -ForegroundColor Yellow
    exit 0
}

Step "Subiendo video REAL a YouTube"
$real = Invoke-ApiJson "Post" "$BaseUrl/agente/youtube/daily-resume" @{
    dry_run = $false
    max_scan = 100
    privacy_status = "unlisted"
}
$real | ConvertTo-Json -Depth 14 | Write-Host

$videoId = $real.result.youtube.video_id
if ($videoId) {
    Write-Host "Video subido: https://youtu.be/$videoId" -ForegroundColor Green
} else {
    Write-Host "No se recibió video_id; revisa logs." -ForegroundColor Yellow
}
