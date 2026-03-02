$ErrorActionPreference = 'Continue'

Write-Output '=== NEXO Professional Tool Stack (PC) ==='

$packages = @(
  'AdGuard.AdGuardHome',
  'Tailscale.Tailscale',
  'WiresharkFoundation.Wireshark',
  'Microsoft.Sysinternals.ProcessExplorer',
  'Genymobile.scrcpy',
  'KeePassXCTeam.KeePassXC',
  'Cloudflare.Warp',
  'Proton.ProtonVPN'
)

foreach ($id in $packages) {
  Write-Output "Installing $id ..."
  winget install -e --id $id --accept-package-agreements --accept-source-agreements
}

Write-Output '--- Installed check ---'
foreach ($id in $packages) {
  winget list --id $id
}

Write-Output '--- AdGuard quick start (user mode) ---'
$agh = 'C:\Users\Admn\AppData\Local\Microsoft\WinGet\Packages\AdGuard.AdGuardHome_Microsoft.Winget.Source_8wekyb3d8bbwe\AdGuardHome\AdGuardHome.exe'
if (Test-Path $agh) {
  $wd = "$env:LOCALAPPDATA\AdGuardHomeNexo"
  New-Item -ItemType Directory -Force -Path $wd | Out-Null
  Start-Process -FilePath $agh -ArgumentList '--work-dir', $wd, '--config', "$wd\AdGuardHome.yaml", '--no-check-update' -WindowStyle Hidden
  Write-Output 'AdGuardHome started (user mode). Open: http://127.0.0.1:3000'
}

Write-Output '--- Tailscale status ---'
$ts = 'C:\Program Files\Tailscale\tailscale.exe'
if (Test-Path $ts) {
  & $ts status
  Write-Output 'If needed, run: tailscale up --accept-routes --accept-dns=false'
}

Write-Output '=== DONE ==='
