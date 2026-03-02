@echo off
cd /d C:\Users\Admn\Desktop\NEXO_SOBERANO
start "NEXO CORE Backend" cmd /k "C:\Users\Admn\Desktop\NEXO_SOBERANO\.venv\Scripts\python.exe run_backend.py"
timeout /t 4 /nobreak >nul
start "" "http://localhost:8000/control-center"
start "" "http://localhost:8000/api/docs"
start "" "http://localhost:8000/api/health/"
start "" "http://localhost:8000/api/stream/status"
echo NEXO CORE iniciado. Se abrieron los enlaces en el navegador.
exit /b 0
