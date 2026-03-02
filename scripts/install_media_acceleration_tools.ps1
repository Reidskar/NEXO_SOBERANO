$ErrorActionPreference = 'Continue'

Write-Output '=== NEXO Media Acceleration Tools ==='

$ids = @(
  'aria2.aria2',
  'Genymobile.scrcpy',
  'WiresharkFoundation.Wireshark'
)

foreach ($id in $ids) {
  Write-Output "Installing $id ..."
  winget install -e --id $id --accept-package-agreements --accept-source-agreements
}

Write-Output '--- Verify binaries ---'
Get-Command aria2c -ErrorAction SilentlyContinue | Select-Object Source
Get-Command scrcpy -ErrorAction SilentlyContinue | Select-Object Source
Get-Command yt-dlp -ErrorAction SilentlyContinue | Select-Object Source
Get-Command gallery-dl -ErrorAction SilentlyContinue | Select-Object Source

Write-Output '=== DONE ==='
