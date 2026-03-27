@echo off
REM Script de mantenimiento para Discord Bot NEXO
REM Ejecutar como Administrador

cd /d %~dp0
cd discord_bot

REM 1. Eliminar node_modules y package-lock.json
if exist node_modules rmdir /s /q node_modules
if exist package-lock.json del /f /q package-lock.json

REM 2. Actualizar dependencias principales
call npm install discord.js@latest @discordjs/voice@latest dotenv@latest

REM 3. Instalar dependencias restantes
call npm install

REM 4. Reparar vulnerabilidades
call npm audit fix

REM 5. Iniciar el bot
call npm start

pause
