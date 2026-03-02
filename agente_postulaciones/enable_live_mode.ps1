$ErrorActionPreference = 'Stop'
Set-Location 'C:\Users\Admn\Desktop\NEXO_SOBERANO\agente_postulaciones'

if (!(Test-Path '.env')) {
  Copy-Item '.env.example' '.env'
  Write-Output 'Se creó .env desde plantilla.'
}

$content = Get-Content '.env'
$map = @{}
foreach ($line in $content) {
  if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
  $parts = $line -split '=',2
  $map[$parts[0].Trim()] = $parts[1].Trim()
}

if (-not $map.ContainsKey('COMPUTRABAJO_EMAIL') -or [string]::IsNullOrWhiteSpace($map['COMPUTRABAJO_EMAIL'])) {
  throw 'Falta COMPUTRABAJO_EMAIL en .env'
}
if (-not $map.ContainsKey('COMPUTRABAJO_PASSWORD') -or [string]::IsNullOrWhiteSpace($map['COMPUTRABAJO_PASSWORD'])) {
  throw 'Falta COMPUTRABAJO_PASSWORD en .env'
}

function Set-Or-Add($key, $value) {
  $raw = Get-Content '.env'
  $found = $false
  for ($i=0; $i -lt $raw.Length; $i++) {
    if ($raw[$i] -match "^\s*$key\s*=") {
      $raw[$i] = "$key=$value"
      $found = $true
    }
  }
  if (-not $found) { $raw += "$key=$value" }
  Set-Content '.env' $raw -Encoding UTF8
}

Set-Or-Add 'DRY_RUN' 'false'
Set-Or-Add 'MAX_APPLICATIONS_PER_CYCLE' '1'
Set-Or-Add 'PLAYWRIGHT_HEADLESS' 'true'

Write-Output '✅ Modo live controlado activado: DRY_RUN=false, MAX_APPLICATIONS_PER_CYCLE=1'
Write-Output 'Ejecuta: python main.py --once'
