# NEXO SOBERANO: Guía de Despliegue - Mente Global (Edge Functions)

Esta guía detalla los pasos para desplegar el pipeline de inteligencia en el Edge de Supabase.

## 📁 Archivos Implementados

- `supabase/functions/ingest_from_drive`: Gestiona OAuth y descarga proactiva de Drive.
- `supabase/functions/analyze_content`: Análisis multimodal (Visión) con Gemini y Embeddings.
- `supabase/functions/daily_summarizer`: Generación automática de "The Magazine".
- `supabase/functions/discord_bridge`: Puente de interacciones para comandos de Discord.
- `supabase/migrations/001_create_global_mind.sql`: Configura el esquema y RLS.
- `scripts/register_discord_commands.js`: Registra Slash Commands en Discord.

## 🚀 Pasos de Despliegue

### 1. Preparar Base de Datos
Ejecuta el contenido de `supabase/migrations/001_create_global_mind.sql` en el SQL Editor de tu Dashboard de Supabase.

### 2. Configurar Secretos (Secrets)
Configura las variables de entorno en Supabase (CLI o Dashboard):
```bash
supabase secrets set DISCORD_BOT_TOKEN="tu_token"
supabase secrets set DISCORD_PUBLIC_KEY="tu_clave_publica"
supabase secrets set DISCORD_APPLICATION_ID="tu_app_id"
supabase secrets set GEMINI_API_KEY="tu_llave_gemini"
supabase secrets set GOOGLE_OAUTH_CLIENT_ID="tu_client_id"
supabase secrets set GOOGLE_OAUTH_CLIENT_SECRET="tu_client_secret"
```

### 3. Desplegar Funciones
Desde la terminal del proyecto:
```bash
supabase functions deploy ingest_from_drive
supabase functions deploy analyze_content
supabase functions deploy daily_summarizer
supabase functions deploy discord_bridge
```

### 4. Registrar Comandos de Discord
Configura tu `.env` local con las credenciales de Discord y ejecuta:
```bash
node scripts/register_discord_commands.js
```

### 5. Configurar el Interacciones Endpoint
En el [Discord Developer Portal](https://discord.com/developers/applications), establece el **Interactions Endpoint URL** a:
`https://<tu-proyecto>.supabase.co/functions/v1/discord_bridge`

## ✅ Verificación
1. Inicia el flujo de OAuth en `ingest_from_drive`.
2. Sube un archivo a Drive.
3. Verifica que el archivo llegue al bucket `nexo-media` y se cree la entrada en `nexo_documentos`.
4. Prueba `/evidencia` en Discord.
