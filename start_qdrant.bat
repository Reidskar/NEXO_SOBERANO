@echo off
echo [NEXO] Iniciando Qdrant via Docker...
docker run -d ^
  --name qdrant ^
  --restart unless-stopped ^
  -p 6333:6333 ^
  -p 6334:6334 ^
  -v "%USERPROFILE%\qdrant_storage:/qdrant/storage" ^
  qdrant/qdrant:latest

if %ERRORLEVEL% EQU 0 (
    echo [OK] Qdrant corriendo en http://localhost:6333
) else (
    echo [INFO] Qdrant ya estaba corriendo o hubo un error. Verificando...
    docker start qdrant 2>nul && echo [OK] Qdrant reiniciado
)
echo.
echo Dashboard: http://localhost:6333/dashboard
pause
