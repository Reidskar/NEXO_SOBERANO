# Professional Tool Stack (PC + Teléfono)

## Objetivo
Seguridad, observabilidad, control remoto seguro y optimización de procesos entre PC y Android.

## Stack recomendado

### PC
- AdGuard Home (DNS filtrado local)
- Tailscale (VPN malla zero-trust)
- Wireshark (forense de red)
- Process Explorer (análisis profundo de procesos)
- scrcpy (control/depuración Android)
- KeePassXC (gestión segura de credenciales)
- Cloudflare WARP / ProtonVPN (túnel alterno)

### Teléfono
- RethinkDNS (firewall + DNS)
- Tailscale (nodo VPN malla)
- Discord (operación)
- OBS Blade (control de OBS)
- Malwarebytes o Bitdefender Mobile (EDR ligero)

## Instalación rápida

### PC
```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_pro_tools.ps1
```

### Teléfono (ADB conectado)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_phone_tools.ps1
```

## Integración con IA del proyecto
- Ejecutar inventario de apps:
```bash
python scripts/app_inventory_sync.py
```
- El contexto queda en:
  - `documentos/APP_INVENTORY_CONTEXT.md`
  - `reports/security/app_inventory_*.json`
- Optimización de procesos:
```bash
python scripts/process_optimizer_report.py
```
- Resultado:
  - `documentos/OPTIMIZACION_FLUJO_APPS.md`
