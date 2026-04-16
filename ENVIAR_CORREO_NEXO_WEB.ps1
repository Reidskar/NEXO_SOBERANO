param(
    [string]$Recipient = "estefano.solar16@gmail.com",
    [string]$ApiKey = "CAMBIA_ESTA_CLAVE_NEXO",
    [string]$BaseUrl = "http://localhost:8080"
)

$ErrorActionPreference = "Stop"

function UrlEncode([string]$value) {
    Add-Type -AssemblyName System.Web
    return [System.Web.HttpUtility]::UrlEncode($value)
}

Write-Host "Generando paquete móvil NEXO..."
$headers = @{ "X-NEXO-KEY" = $ApiKey }
$pkg = Invoke-RestMethod -Uri "$BaseUrl/agente/mobile-package" -Method GET -Headers $headers

$links = $pkg.package.links
$downloadTxt = "$BaseUrl$($pkg.download_txt)"
$downloadJson = "$BaseUrl$($pkg.download_json)"

$subject = "NEXO - Enlaces y reportes del sistema"
$body = @"
Hola,

Aquí tienes los accesos de NEXO:

- App User: $($links.app_user)
- App Admin: $($links.app_admin)
- Control Center: $($links.control_center)
- War Room: $($links.warroom)
- Dashboard Admin: $($links.admin_dashboard)

Reportes:
- TXT: $downloadTxt
- JSON: $downloadJson

Generado automáticamente por NEXO.
"@

$gmailUrl = "https://mail.google.com/mail/?view=cm&fs=1&to=$(UrlEncode $Recipient)&su=$(UrlEncode $subject)&body=$(UrlEncode $body)"
$outlookUrl = "https://outlook.live.com/mail/0/deeplink/compose?to=$(UrlEncode $Recipient)&subject=$(UrlEncode $subject)&body=$(UrlEncode $body)"

Set-Clipboard -Value $body

Write-Host ""
Write-Host "✅ Correo preparado (sin SMTP)."
Write-Host "➡ Se abrió Gmail Compose; solo presiona ENVIAR."
Write-Host "➡ También te dejo Outlook Compose por si prefieres."
Write-Host ""
Write-Host "Gmail:   $gmailUrl"
Write-Host "Outlook: $outlookUrl"
Write-Host ""
Write-Host "(El contenido también quedó copiado al portapapeles.)"

Start-Process $gmailUrl
Start-Process $outlookUrl
