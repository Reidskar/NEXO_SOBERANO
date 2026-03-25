@echo off
echo === NEXO SOBERANO - Verificacion Tailscale Mesh ===
echo.
echo [1] Estado Tailscale local...
tailscale status
echo.
echo [2] IP local de la Torre...
tailscale ip -4
echo.
echo [3] Ping a Xiaomi (100.112.23.72)...
ping -n 2 100.112.23.72
echo.
echo [4] Ping a Dell Latitude (si conectado)...
tailscale ping --c 2 100.112.23.72 2>nul || echo Xiaomi no disponible via Tailscale
echo.
echo === Estado del mesh ===
tailscale status --json 2>nul | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    peers = data.get('Peer', {})
    print(f'  Nodos en mesh: {len(peers)}')
    for k, v in peers.items():
        name = v.get('HostName', 'unknown')
        online = v.get('Online', False)
        ips = v.get('TailscaleIPs', [])
        ip = ips[0] if ips else 'sin IP'
        status = 'ONLINE' if online else 'OFFLINE'
        print(f'  [{status}] {name} - {ip}')
except Exception as e:
    print(f'  Error parseando: {e}')
" 2>nul
echo.
echo === Fin verificacion mesh ===
