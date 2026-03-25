# NEXO SOBERANO — Variables de entorno Railway
# Configurar en: railway.app → proyecto → Variables
# NUNCA subir valores reales a GitHub

## Variables requeridas en Railway Dashboard

DATABASE_URL=postgresql://...        ← Supabase connection string
GEMINI_API_KEY=...                   ← Google AI Studio
ANTHROPIC_API_KEY=...                ← Anthropic Console
SECRET_KEY=...                       ← string aleatorio 32+ chars
DISCORD_TOKEN=...                    ← Discord Developer Portal
TELEGRAM_TOKEN=...                   ← @BotFather en Telegram
SUPABASE_URL=https://rokxchapzhgshrvmuuus.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...
OLLAMA_ENABLED=false                 ← false en Railway (sin GPU)
OLLAMA_URL=                          ← vacío en Railway
NEXO_DOMAIN=elanarcocapital.com
ENVIRONMENT=production
PORT=8000

## Nota
OLLAMA_ENABLED=false en Railway porque Ollama corre solo en la Torre.
En Railway el AI Router usará Gemini como primario.
