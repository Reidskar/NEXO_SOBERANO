# Optimización de Procesos y Apps (IA-Aware)

Generado: 2026-03-02T20:57:49.374999+00:00

## Resumen
- Apps Android detectadas: 190
- Temperatura batería (último advisor): 39.9
- Categorías de riesgo detectadas: remote_control, finance_crypto, social_heavy

## Causas probables de sobrecarga
- Procesos con mayor carga observada:
  - 800%cpu 146%user  11%nice 311%sys 279%idle   7%iow  43%irq   4%sirq   0%host
  - 29122 u0_a311      12  -8  19G 244M 159M S  160   2.1   0:06.45 org.telegram.messenger
  - 3047 system       -2   0  23G 580M 298M S 85.7   5.1 215:02.27 com.android.systemui
  - 1257 system       -3  -8  16G 120M  98M S 53.5   1.0 465:57.27 surfaceflinger
  - 13446 u0_a307      20   0  21G 301M 182M S 39.2   2.6   2:42.06 com.whatsapp

## Reglas de optimización recomendadas
- Mantener solo una app de control remoto activa con permisos altos (evitar solapamiento AnyDesk/AirDroid).
- Aplicar perfil de background estricto a apps sociales pesadas cuando no transmites.
- Programar escaneo térmico cada 15 min durante sesiones de streaming.
- Usar DNS filtrado (AdGuard) + VPN malla (Tailscale) para reducir superficie de red.
- Ingerir este documento en el contexto RAG para recomendaciones adaptadas a apps reales.

## Integración con IA (NEXO)
- Fuente inventario: reports/security/app_inventory_*.json
- Fuente advisor: reports/security/phone_advisor_*.json
- Este documento: documentos/OPTIMIZACION_FLUJO_APPS.md