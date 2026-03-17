@echo off
title Fix ADB — El Anarcocapital
echo.
echo [1] Cerrando AirDroid Cast (causa conflicto ADB)...
taskkill /F /IM "AirDroid Cast.exe" 2>nul
taskkill /F /IM "airdroid*.exe" 2>nul
taskkill /F /IM "adb_helper.exe" 2>nul
timeout /t 2 /nobreak > nul

echo [2] Reiniciando ADB server...
adb kill-server 2>nul
timeout /t 1 /nobreak > nul
adb start-server

echo [3] Dispositivos conectados:
adb devices

echo [4] Habilitando ADB WiFi en el telefono...
adb tcpip 5555
timeout /t 2 /nobreak > nul

echo [5] Conectando por WiFi (192.168.100.13:5555)...
adb connect 192.168.100.13:5555

echo [6] Tunel inverso: telefono accede al backend local...
adb reverse tcp:8000 tcp:8000
adb reverse tcp:6333 tcp:6333

echo.
echo === LISTO ===
echo El telefono puede acceder al backend en http://localhost:8000
echo.
adb devices
pause
