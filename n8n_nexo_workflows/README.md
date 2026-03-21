# NEXO SOBERANO — n8n Workflow Templates
© 2026 elanarcocapital.com

## Workflows importados
Templates seleccionados del repo Danitilahun/n8n-workflow-templates
para automatización de NEXO SOBERANO.

## Cómo importar en n8n
1. Abrir http://localhost:5678
2. New Workflow → Import from file
3. Seleccionar el archivo .json de esta carpeta
4. Configurar credenciales (Telegram token, GitHub token)

## Workflows incluidos
- 0001_Telegram_Schedule_Automation_Scheduled.json
- 0045_Manual_Telegram_Import_Triggered.json
- 0089_Noop_Telegram_Automate_Triggered.json
- 0140_Telegram_Webhook_Automation_Webhook.json
- 0146_Functionitem_Telegram_Create_Webhook.json
- 0148_Awstextract_Telegram_Automate_Triggered.json
- 0158_Telegram_Functionitem_Create_Scheduled.json
- 0162_HTTP_Telegram_Send_Webhook.json
- 0170_Telegram_Wait_Automation_Scheduled.json
- 0188_Rssfeedread_Telegram_Create_Scheduled.json

## Variables de entorno requeridas
- TELEGRAM_TOKEN (ya en .env)
- GITHUB_TOKEN (opcional, para webhooks)
- N8N_ENCRYPTION_KEY (ya en docker-compose)
