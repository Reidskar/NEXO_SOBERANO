param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [switch]$SkipAuthorize,
    [switch]$RunRealUpload,
    [switch]$KeepDriveFile
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

Write-Host "GO-LIVE FINAL: Drive -> YouTube Automático" -ForegroundColor Green

# 1) Validar .env y credenciales
Step "Validando .env y credenciales"
if (-not (Test-Path ".env")) {
    throw ".env no encontrado"
}

$envMap = Get-DotEnvMap ".env"

$hasGoogleClient = $envMap.ContainsKey("GOOGLE_CLIENT_ID") -and $envMap.ContainsKey("GOOGLE_CLIENT_SECRET")
$hasDriveClient = $envMap.ContainsKey("DRIVE_CLIENT_ID") -and $envMap.ContainsKey("DRIVE_CLIENT_SECRET")
$hasYoutubeClient = $envMap.ContainsKey("YOUTUBE_CLIENT_ID") -and $envMap.ContainsKey("YOUTUBE_CLIENT_SECRET")

if (-not ($hasGoogleClient -or ($hasDriveClient -and $hasYoutubeClient) -or ($hasGoogleClient -and ($hasDriveClient -or $hasYoutubeClient)))) {
    throw "Faltan credenciales OAuth en .env. Define GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET o las variantes DRIVE_* y YOUTUBE_*"
}

$driveRoot = $null
if ($envMap.ContainsKey("DRIVE_ROOT_FOLDER_ID") -and $envMap["DRIVE_ROOT_FOLDER_ID"]) {
    $driveRoot = $envMap["DRIVE_ROOT_FOLDER_ID"]
}

# 2) Health backend
Step "Verificando backend health"
$health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/health"
$health | ConvertTo-Json -Depth 6 | Write-Host

# 3) Bootstrap de client_secrets
Step "Creando client_secrets desde .env (Drive + YouTube)"
try {
    (Invoke-ApiJson "Post" "$BaseUrl/agente/drive/create-client-secrets" @{}) | ConvertTo-Json -Depth 6 | Write-Host
}
catch {
    Write-Host "Aviso drive/create-client-secrets: $($_.Exception.Message)" -ForegroundColor Yellow
}

try {
    (Invoke-ApiJson "Post" "$BaseUrl/agente/youtube/create-client-secrets" @{}) | ConvertTo-Json -Depth 6 | Write-Host
}
catch {
    Write-Host "Aviso youtube/create-client-secrets: $($_.Exception.Message)" -ForegroundColor Yellow
}

# 4) Autorizar scopes
if (-not $SkipAuthorize) {
    Step "Autorizando Drive scope escritura (puede abrir navegador)"
    (Invoke-ApiJson "Post" "$BaseUrl/agente/drive/authorize" @{ write_scope = $true }) | ConvertTo-Json -Depth 8 | Write-Host

    Step "Autorizando YouTube scope upload (puede abrir navegador)"
    (Invoke-ApiJson "Post" "$BaseUrl/agente/youtube/authorize" @{ upload_scope = $true }) | ConvertTo-Json -Depth 8 | Write-Host
}
else {
    Step "Saltando autorización interactiva por -SkipAuthorize"
}

# 5) Elegir carpeta de destino en Drive
$targetFolderId = $null
if ($driveRoot) {
    Step "Usando DRIVE_ROOT_FOLDER_ID desde .env"
    $targetFolderId = $driveRoot
}
else {
    Step "DRIVE_ROOT_FOLDER_ID no definido; creando carpeta de fallback"
    $ensure = Invoke-ApiJson "Post" "$BaseUrl/agente/drive/ensure-folder" @{
        path_parts = @("NEXO_SOBERANO_CLASIFICADO", "GoLive")
        parent_id = "root"
    }
    $ensure | ConvertTo-Json -Depth 8 | Write-Host
    $targetFolderId = $ensure.folder_id
}

if (-not $targetFolderId) {
    throw "No se obtuvo folder_id de destino"
}

# 6) Subir resumen dummy a Drive (nombre compatible con pipeline)
Step "Subiendo resumen dummy a Drive"
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$driveFilename = "resumen_diario_prueba_$ts.txt"
$dummyText = @"
Resumen SIG Diario - Prueba GO-LIVE Automática
Fecha: $(Get-Date -Format "yyyy-MM-dd HH:mm")
Indicador riesgo conflicto global: 4/5
Movimientos detectados: radares zona X, satélites Y
Impacto económico estimado: +3.2% inflación proyectada
Fuente principal: https://drive.google.com/file/d/TEST_ID/view
Aporte comunidad: Telegram @usuarioZ
"@
$fileB64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($dummyText))

$upload = Invoke-ApiJson "Post" "$BaseUrl/agente/drive/upload-b64" @{
    folder_id = $targetFolderId
    filename = $driveFilename
    file_b64 = $fileB64
}
$upload | ConvertTo-Json -Depth 10 | Write-Host
$uploadedFileId = $upload.file.id

# 7) Dry-run del pipeline
Step "Ejecutando pipeline daily-resume en dry-run"
$dry = Invoke-ApiJson "Post" "$BaseUrl/agente/youtube/daily-resume" @{
    dry_run = $true
    max_scan = 100
    privacy_status = "unlisted"
}
$dry | ConvertTo-Json -Depth 12 | Write-Host

# 8) Confirmación de subida real
if (-not $RunRealUpload) {
    $confirm = Read-Host "¿Subir video REAL a YouTube ahora? (s/n)"
    if ($confirm -eq "s" -or $confirm -eq "S") {
        $RunRealUpload = $true
    }
}

if ($RunRealUpload) {
    Step "Ejecutando pipeline REAL (subida a YouTube)"
    $real = Invoke-ApiJson "Post" "$BaseUrl/agente/youtube/daily-resume" @{
        dry_run = $false
        max_scan = 100
        privacy_status = "unlisted"
    }
    $real | ConvertTo-Json -Depth 14 | Write-Host

    $videoId = $real.result.youtube.video_id
    if ($videoId) {
        Write-Host "`nVideo subido: https://youtu.be/$videoId" -ForegroundColor Green
    }
    else {
        Write-Host "`nNo se recibió video_id. Revisa respuesta/logs." -ForegroundColor Yellow
    }
}
else {
    Step "Se mantiene dry-run (sin subida real)"
}

# 9) Limpieza opcional en Drive
if (-not $KeepDriveFile -and $uploadedFileId) {
    Step "Eliminando archivo dummy en Drive"
    try {
        (Invoke-ApiJson "Post" "$BaseUrl/agente/drive/delete" @{ file_id = $uploadedFileId }) | ConvertTo-Json -Depth 6 | Write-Host
    }
    catch {
        Write-Host "No se pudo eliminar archivo dummy ($uploadedFileId): $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host "`nGO-LIVE FINAL completado." -ForegroundColor Green
Write-Host "Revisa tu canal YouTube y logs del backend." -ForegroundColor Yellow
