@echo off
cd /d C:\Users\Admn\Desktop\NEXO_SOBERANO

echo ==========================================
echo  NEXO - Configuracion de conectores cloud
echo ==========================================
echo.
echo 1) Google Drive/Photos:
echo    - Ejecutando asistente setup_credentials.py
echo.
C:\Users\Admn\Desktop\NEXO_SOBERANO\.venv\Scripts\python.exe setup_credentials.py

echo.
echo 2) OneDrive:
echo    - Copia credenciales_microsoft_TEMPLATE.json como credenciales_microsoft.json
echo    - Rellena client_id, client_secret, tenant_id
echo.
start "" "C:\Users\Admn\Desktop\NEXO_SOBERANO\credenciales_microsoft_TEMPLATE.json"
echo.
echo 3) Google Photos 403:
echo    - En Google Cloud agrega tu correo como TEST USER en OAuth Consent Screen
echo    - Habilita Google Photos Library API
echo.
echo Listo. Reinicia NEXO y corre Sync completo otra vez.
pause
