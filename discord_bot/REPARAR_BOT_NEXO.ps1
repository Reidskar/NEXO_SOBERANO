# Script PowerShell para reparar y actualizar el bot de Discord NEXO
# Ejecutar como Administrador

# Ir a la carpeta del bot
$botPath = Join-Path $PSScriptRoot 'discord_bot'
Set-Location $botPath

Write-Host "[1/5] Eliminando node_modules y package-lock.json..." -ForegroundColor Cyan
if (Test-Path node_modules) { Remove-Item -Recurse -Force node_modules }
if (Test-Path package-lock.json) { Remove-Item -Force package-lock.json }

Write-Host "[2/5] Instalando dependencias principales..." -ForegroundColor Cyan
npm install discord.js@latest @discordjs/voice@latest dotenv@latest

Write-Host "[3/5] Instalando dependencias restantes..." -ForegroundColor Cyan
npm install

Write-Host "[4/5] Reparando vulnerabilidades..." -ForegroundColor Cyan
npm audit fix

Write-Host "[5/5] Iniciando el bot..." -ForegroundColor Green
npm start

Write-Host "\nListo. Si ves errores, revisa el log anterior."
Pause
