# n8n workflows que sí te sirven para NEXO

Del repositorio compartido hay más de 1000 plantillas. Para NEXO conviene usar solo las que mapean a tus flujos reales (Drive/YouTube/X/Discord/alertas).

## Prioridad Alta (útiles ahora)

- `0036_Gmail_GoogleDrive_Import.json`
- `0544_Gmail_GoogleDrive_Create_Triggered.json`
- `0839_GoogleDrive_GoogleSheets_Create_Triggered.json`
- `0812_GoogleSheets_GoogleDrive_Automate_Triggered.json`
- `0476_Manual_Youtube_Create_Triggered.json`
- `0732_Form_Youtube_Update_Triggered.json`
- `0005_Manual_Twitter_Create_Triggered.json`
- `0144_HTTP_Twitter_Automation_Scheduled.json`
- `0356_Manual_Twitter_Automate_Scheduled.json`
- `0785_Openai_Twitter_Create.json`
- `0116_Graphql_Discord_Automate_Scheduled.json`
- `0270_Webhook_Discord_Automate_Webhook.json`
- `0360_Discord_Cron_Automation_Scheduled.json`
- `0966_HTTP_Discord_Import_Scheduled.json`
- `0126_Error_Slack_Automate_Triggered.json` (patrón de alerta de errores)
- `0447_Error_Slack_Send_Triggered.json` (patrón de alerta de errores)

## Cómo usarlas en NEXO (mapeo rápido)

1. **Trigger (Cron/Webhook/Manual)**
2. **HTTP Request a NEXO API** (`/agente/...`)
3. **Transformación (Code/Filter)**
4. **Salida (Discord/X/Sheets/Drive)**

## Endpoints NEXO recomendados para n8n

- `POST /agente/consultar-rag`
- `POST /agente/drive/upload-aporte`
- `POST /agente/control-center/run-drive-classification`
- `POST /agente/control-center/run-unified-sync`
- `POST /agente/x/monitor-once`
- `POST /agente/google-stitch/push`

## Flujos n8n que te recomiendo montar primero

- **Flujo 1 (cada 20:00):** Cron -> `run-unified-sync` -> `google-stitch/push` -> notificación Discord
- **Flujo 2 (cada 15 min):** Cron -> `x/monitor-once` -> si error -> alerta
- **Flujo 3 (aportes comunidad):** Webhook n8n -> `drive/upload-aporte` -> confirmación en Discord
- **Flujo 4 (reporte diario):** Cron -> `control-center/status` + `control-center/analytics` -> Google Sheets

## Nota

Las plantillas del repo son base genérica. Úsalas como estructura, pero sustituyendo nodos por tus endpoints reales de NEXO.
