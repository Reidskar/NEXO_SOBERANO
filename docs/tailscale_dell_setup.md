# NEXO SOBERANO — Incorporar Dell Latitude al Mesh
© 2026 elanarcocapital.com

## Dispositivos actuales en el mesh
- Torre (servidor central): IP Tailscale asignada
- Xiaomi 14T Pro: 100.112.23.72 ✅

## Pasos para conectar Dell Latitude

### En el Dell Latitude:
1. Descargar Tailscale para Windows:
   https://tailscale.com/download/windows
2. Instalar y abrir Tailscale
3. Click en "Log in" → usar la misma cuenta que la Torre
4. Tailscale asignará una IP del rango 100.x.x.x automáticamente

### Verificar desde la Torre (después de conectar el Dell):
```cmd
tailscale status
ping [IP del Dell que aparezca]
```

### Acceso remoto al Dell desde la Torre:
```cmd
# RDP via Tailscale (seguro, sin exponer puertos)
mstsc /v:[IP-tailscale-del-dell]

# SSH si tienes OpenSSH instalado en Dell
ssh usuario@[IP-tailscale-del-dell]
```

### Acceso a la API de la Torre desde el Dell:
Una vez conectado al mesh, desde el Dell:
```
http://[IP-tailscale-torre]:8000/api/health
http://[IP-tailscale-torre]:8000/api/agente/consultar
http://[IP-tailscale-torre]:5678  (n8n)
```

## Comandos útiles de gestión del mesh
```cmd
tailscale status          # ver todos los nodos
tailscale ping [IP]       # verificar conectividad
tailscale ip -4           # ver IP propia
tailscale up              # conectar
tailscale down            # desconectar
```
