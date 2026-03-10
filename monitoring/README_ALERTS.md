# Sistema de Alertas Profesionales - NEXO

Este sistema asegura que recibas notificaciones inmediatas si el bot falla, se desconecta o experimenta errores críticos.

## 📡 Webhook Relay
El servicio `webhook-relay` (puerto 4000) centraliza todas las alertas y las distribuye a:
- **Slack**: Configura `TARGET_SLACK_WEBHOOK`.
- **Discord**: Configura `TARGET_DISCORD_WEBHOOK`.
- **PagerDuty**: Configura `PAGERDUTY_KEY` para incidentes críticos.

## 🤖 Integración en el Bot
El bot de Discord incluye un `alert_client.js` que dispara alertas automáticamente en:
- **Crashes**: Captura `uncaughtException` y envía alerta CRÍTICA.
- **Ciclo de Vida**: Notifica cuando el bot se inicia (Info) o se apaga (Warning).
- **Errores de Red**: Captura promesas fallidas y errores de conexión.

## 🔎 Monitoreo Remoto (Supabase Edge Function)
La función `bot-health-prober` en Supabase actúa como un vigía externo:
1. Intenta contactar al bot cada X tiempo (configura un Cron en Supabase).
2. Si el bot no responde (timeout) o devuelve error, dispara una alerta de "Bot Unreachable".

## 📊 Historial Persistente
Todas las alertas pueden guardarse en la tabla `public.alerts` de Supabase (ejecuta el archivo SQL en `supabase/migrations/`). Esto te permite crear dashboards en Grafana o Retool.

## 🚀 Despliegue
El sistema de alertas ya está integrado en el `docker-compose.yml`. Al ejecutar `docker-compose up -d`, el relay se levantará automáticamente.

---
*NEXO SOBERANO - Seguridad y Estabilidad Operativa*
