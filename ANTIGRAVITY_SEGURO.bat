@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
  echo [ERROR] No existe el entorno virtual en .venv\Scripts\python.exe
  echo Ejecuta primero: .\.venv\Scripts\python.exe -m pip install -r requirements.txt
  goto :end
)

echo [1/2] Reparando Antigravity si hace falta...
"%PYTHON_EXE%" scripts\antigravity_doctor.py
if errorlevel 1 (
  echo [ERROR] Fallo en auto-reparacion. Revisa el mensaje JSON mostrado.
  goto :end
)

echo [2/2] Ejecutando catalogo Antigravity...
"%PYTHON_EXE%" scripts\catalog_antigravity_skills.py --source . --output logs\antigravity_skills_catalog.json --min-confidence 0.35
if errorlevel 1 (
  echo [ERROR] Antigravity termino con error.
  goto :end
)

echo [OK] Antigravity ejecutado correctamente.

:end
echo.
echo Presiona una tecla para cerrar...
pause >nul
endlocal
