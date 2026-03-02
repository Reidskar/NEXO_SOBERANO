@echo off
cd /d C:\Users\Admn\Desktop\NEXO_SOBERANO
where docker >nul 2>&1
if errorlevel 1 (
	echo Docker no esta instalado o no esta en PATH.
	echo Instala Docker Desktop y vuelve a ejecutar este archivo.
	exit /b 1
)

docker compose up --build
