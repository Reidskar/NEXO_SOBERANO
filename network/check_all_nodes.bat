@echo off
title El Anarcocapital — Estado de Nodos
echo.
echo =========================================
echo  EL ANARCOCAPITAL — RED DE DISPOSITIVOS
echo =========================================
echo.

echo [Tailscale]
tailscale status
echo.

echo [Red Local 192.168.100.x]
ping -n 1 -w 500 192.168.100.1  > nul 2>&1 && echo "  192.168.100.1  Router       ALIVE" || echo "  192.168.100.1  Router       DEAD"
ping -n 1 -w 500 192.168.100.12 > nul 2>&1 && echo "  192.168.100.12 Notebook     ALIVE" || echo "  192.168.100.12 Notebook     DEAD"
ping -n 1 -w 500 192.168.100.13 > nul 2>&1 && echo "  192.168.100.13 Telefono     ALIVE" || echo "  192.168.100.13 Telefono     DEAD"
ping -n 1 -w 500 192.168.100.22 > nul 2>&1 && echo "  192.168.100.22 Este PC      ALIVE" || echo "  192.168.100.22 Este PC      DEAD"
echo.

echo [Backend El Anarcocapital]
curl -s --max-time 3 http://127.0.0.1:8000/api/health 2>nul || echo "  Backend OFFLINE"
echo.

echo [Qdrant]
curl -s --max-time 2 http://localhost:6333/collections 2>nul | findstr "result" > nul && echo "  Qdrant ONLINE" || echo "  Qdrant OFFLINE — corre start_qdrant.bat"
echo.

echo [ADB / Telefono]
adb devices 2>nul
echo.

echo [SSH Notebook]
curl -s --max-time 2 http://192.168.100.12:22 > nul 2>&1 && echo "  SSH OPEN" || echo "  SSH CERRADO — instalar SSH en notebook"

echo.
pause
