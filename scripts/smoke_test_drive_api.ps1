param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [switch]$SkipAuthorize
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host "\n==> $msg" -ForegroundColor Cyan
}

function Invoke-ApiJson($method, $url, $bodyObj) {
    $json = if ($null -ne $bodyObj) { $bodyObj | ConvertTo-Json -Depth 12 } else { "{}" }
    return Invoke-RestMethod -Method $method -Uri $url -ContentType "application/json" -Body $json
}

Write-Host "Smoke Test Drive API (NEXO SOBERANO)" -ForegroundColor Green

# 0) Health
Write-Step "Verificando backend health"
$health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/health"
$health | ConvertTo-Json -Depth 6 | Write-Host

# 1) Bootstrap client_secrets desde .env
Write-Step "Creando client_secrets de Drive desde .env"
try {
    $createSecrets = Invoke-ApiJson "Post" "$BaseUrl/agente/drive/create-client-secrets" @{}
    $createSecrets | ConvertTo-Json -Depth 6 | Write-Host
}
catch {
    Write-Host "No se pudo crear client_secrets automáticamente: $($_.Exception.Message)" -ForegroundColor Yellow
}

# 2) OAuth interactivo (si no se omite)
if (-not $SkipAuthorize) {
    Write-Step "Autorizando Drive (puede abrir navegador)"
    $auth = Invoke-ApiJson "Post" "$BaseUrl/agente/drive/authorize" @{ write_scope = $true }
    $auth | ConvertTo-Json -Depth 6 | Write-Host
} else {
    Write-Step "Saltando autorización interactiva por parámetro -SkipAuthorize"
}

# 3) Crear carpeta de test
Write-Step "Asegurando carpeta de prueba en Drive"
$ensure = Invoke-ApiJson "Post" "$BaseUrl/agente/drive/ensure-folder" @{
    path_parts = @("NEXO_SOBERANO_CLASIFICADO", "SmokeTests")
    parent_id = "root"
}
$ensure | ConvertTo-Json -Depth 6 | Write-Host
$folderId = $ensure.folder_id

if (-not $folderId) {
    throw "No se obtuvo folder_id para carpeta de prueba"
}

# 4) Subir archivo dummy por base64
Write-Step "Subiendo archivo dummy por /drive/upload-b64"
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$filename = "smoke_$ts.txt"
$content = "Smoke test NEXO SOBERANO - $ts"
$fileBytes = [System.Text.Encoding]::UTF8.GetBytes($content)
$fileB64 = [Convert]::ToBase64String($fileBytes)

$upload = Invoke-ApiJson "Post" "$BaseUrl/agente/drive/upload-b64" @{
    folder_id = $folderId
    filename = $filename
    file_b64 = $fileB64
}
$upload | ConvertTo-Json -Depth 8 | Write-Host
$fileId = $upload.file.id

if (-not $fileId) {
    throw "No se obtuvo file_id después de upload"
}

# 5) Listar carpeta
Write-Step "Listando carpeta de prueba"
$list = Invoke-ApiJson "Post" "$BaseUrl/agente/drive/list" @{
    folder_id = $folderId
    max_results = 10
}
$list | ConvertTo-Json -Depth 8 | Write-Host

# 6) Renombrar archivo
Write-Step "Renombrando archivo"
$newName = "renamed_$filename"
$rename = Invoke-ApiJson "Post" "$BaseUrl/agente/drive/rename" @{
    file_id = $fileId
    new_name = $newName
}
$rename | ConvertTo-Json -Depth 8 | Write-Host

# 7) Papelera y restaurar
Write-Step "Enviando a papelera"
$trash = Invoke-ApiJson "Post" "$BaseUrl/agente/drive/trash" @{
    file_id = $fileId
    trashed = $true
}
$trash | ConvertTo-Json -Depth 8 | Write-Host

Write-Step "Restaurando desde papelera"
$restore = Invoke-ApiJson "Post" "$BaseUrl/agente/drive/trash" @{
    file_id = $fileId
    trashed = $false
}
$restore | ConvertTo-Json -Depth 8 | Write-Host

# 8) Eliminación permanente
Write-Step "Eliminando archivo"
$delete = Invoke-ApiJson "Post" "$BaseUrl/agente/drive/delete" @{
    file_id = $fileId
}
$delete | ConvertTo-Json -Depth 8 | Write-Host

Write-Host "\nSmoke test Drive API completado correctamente." -ForegroundColor Green
