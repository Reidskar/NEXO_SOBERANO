@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
set "LOG_FILE=%CD%\logs\antigravity_install.log"

if not exist "%CD%\logs" mkdir "%CD%\logs"

echo [%date% %time%] Inicio instalacion antigravity>>"%LOG_FILE%"

if not exist "%PYTHON_EXE%" (
  echo [ERROR] No existe .venv\Scripts\python.exe
  echo Crea o repara tu entorno virtual antes de instalar.
  echo [%date% %time%] ERROR: .venv no encontrado>>"%LOG_FILE%"
  goto :end
)

echo [INFO] Instalando paquete correcto: antigravity
echo [INFO] Evita typo: antigravitty ^(con doble t^) produce "No matching distribution".
"%PYTHON_EXE%" -m pip install --upgrade pip >>"%LOG_FILE%" 2>&1
"%PYTHON_EXE%" -m pip install antigravity >>"%LOG_FILE%" 2>&1

if errorlevel 1 (
  echo [ERROR] Fallo la instalacion en el entorno virtual del proyecto.
  echo [TIP] Revisa el log: %LOG_FILE%
  echo [%date% %time%] ERROR: fallo pip install>>"%LOG_FILE%"
  goto :end
)

echo [OK] Instalacion terminada en .venv.
echo [%date% %time%] OK: instalacion completada>>"%LOG_FILE%"

if exist "%CD%\ANTIGRAVITY_SEGURO.bat" (
  echo [INFO] Abriendo Antigravity...
  start "ANTIGRAVITY_ABIERTO" cmd /k "cd /d \"%CD%\" && ANTIGRAVITY_SEGURO.bat"
  echo [%date% %time%] OK: apertura de Antigravity solicitada>>"%LOG_FILE%"
) else (
  echo [WARN] No se encontro ANTIGRAVITY_SEGURO.bat en %CD%
  echo [%date% %time%] WARN: no se encontro ANTIGRAVITY_SEGURO.bat>>"%LOG_FILE%"
)

:end
echo.
echo Presiona una tecla para cerrar...
pause >nul
endlocal
