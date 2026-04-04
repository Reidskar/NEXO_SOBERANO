@echo off
title NEXO - Control Remoto Dispositivo

set ADB=C:\Users\Admn\AppData\Local\Microsoft\WinGet\Packages\Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe\scrcpy-win64-v3.3.4\adb.exe
set SCRCPY=C:\Users\Admn\AppData\Local\Microsoft\WinGet\Packages\Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe\scrcpy-win64-v3.3.4\scrcpy.exe

echo.
echo =========================================
echo   NEXO - Conectando dispositivo remoto
echo =========================================
echo.

REM Intentar Tailscale primero
echo [1/3] Conectando ADB via Tailscale...
"%ADB%" connect 100.83.26.14:5555 2>nul
if %ERRORLEVEL%==0 (
    echo      OK - Conectado via Tailscale (100.83.26.14)
    set DEVICE=100.83.26.14:5555
    goto LAUNCH_SCRCPY
)

REM Fallback Tailscale alternativo
"%ADB%" connect 100.112.23.72:5555 2>nul
if %ERRORLEVEL%==0 (
    echo      OK - Conectado via Tailscale alt (100.112.23.72)
    set DEVICE=100.112.23.72:5555
    goto LAUNCH_SCRCPY
)

REM Fallback USB
echo      Tailscale no disponible, usando USB...
set DEVICE=
echo      OK - Usando dispositivo USB

:LAUNCH_SCRCPY
echo.
echo [2/3] Lanzando espejo de pantalla (scrcpy)...
if defined DEVICE (
    start "" "%SCRCPY%" --serial %DEVICE% --window-title "NEXO | Control Remoto" --stay-awake --turn-screen-off
) else (
    start "" "%SCRCPY%" --window-title "NEXO | Control Remoto" --stay-awake --turn-screen-off
)
echo      OK - scrcpy iniciado

echo.
echo [3/3] Sistema listo.
echo.
echo =========================================
echo   Acceso NEXO desde otros dispositivos:
echo   - Notebook:  http://100.112.238.97:8000
echo   - Internet:  https://api.elanarcocapital.com
echo   - Celular:   App NEXO mobile-admin
echo =========================================
echo.
pause
