$ErrorActionPreference = 'Continue'

$adb = 'C:\Users\Admn\AppData\Local\Microsoft\WinGet\Packages\Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe\platform-tools\adb.exe'
if (!(Test-Path $adb)) {
  Write-Output 'ADB not found. Install platform tools first.'
  exit 1
}

& $adb devices

Write-Output 'Opening Play Store pages on phone...'
& $adb shell am start -a android.intent.action.VIEW -d 'market://details?id=com.celzero.bravedns'      # RethinkDNS
& $adb shell am start -a android.intent.action.VIEW -d 'market://details?id=com.tailscale.ipn'         # Tailscale
& $adb shell am start -a android.intent.action.VIEW -d 'market://details?id=com.discord'               # Discord
& $adb shell am start -a android.intent.action.VIEW -d 'market://details?id=com.kounex.obsblade'       # OBS Blade
& $adb shell am start -a android.intent.action.VIEW -d 'market://search?q=Malwarebytes Mobile Security&c=apps'
& $adb shell am start -a android.intent.action.VIEW -d 'market://search?q=Bitdefender Mobile Security&c=apps'

Write-Output 'Verify installed packages:'
& $adb shell pm list packages com.celzero.bravedns
& $adb shell pm list packages com.tailscale.ipn
& $adb shell pm list packages com.discord
& $adb shell pm list packages com.kounex.obsblade

Write-Output 'DONE: confirm install actions in Play Store on the phone.'
