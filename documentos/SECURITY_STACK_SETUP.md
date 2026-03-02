# Security Stack Setup (PC + Teléfono)

## 1) Inventario de apps para IA
- Script: `scripts/app_inventory_sync.py`
- Salidas:
  - `reports/security/app_inventory_*.json`
  - `documentos/APP_INVENTORY_CONTEXT.md`

## 2) Optimización de procesos basada en tus apps
- Script: `scripts/process_optimizer_report.py`
- Salida:
  - `documentos/OPTIMIZACION_FLUJO_APPS.md`

## 3) DNS local tipo AdGuard en PC
- Instalado: `AdGuardHome`
- UI de configuración: `http://127.0.0.1:3000`
- Si quieres fijar DNS del sistema en Windows (PowerShell **Administrador**):
  ```powershell
  Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses @("127.0.0.1","1.1.1.1")
  ```
- Revertir:
  ```powershell
  Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ResetServerAddresses
  ```

## 4) VPN malla PC ↔ Teléfono
- PC: Tailscale instalado por winget.
- Teléfono: instalar `Tailscale` desde Play Store (`com.tailscale.ipn`).
- Pasos:
  1. Abrir Tailscale en PC e iniciar sesión.
  2. Abrir Tailscale en teléfono e iniciar sesión con la misma cuenta.
  3. Confirmar que ambos aparecen en la misma tailnet.

## 5) Admin app teléfono
- Instalado: `RethinkDNS` (`com.celzero.bravedns`).
- Recomendación: activar modo DNS+Firewall y bloquear trackers en apps sociales/remote.

## 6) Rutina sugerida
- Diario: `python scripts/phone_security_scan.py --mode quick`
- Semanal: `python scripts/phone_security_scan.py --mode full`
- Post-scan: `python scripts/phone_security_advisor.py`
- Actualizar contexto IA: `python scripts/app_inventory_sync.py`
