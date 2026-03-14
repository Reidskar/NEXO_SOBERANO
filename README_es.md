# NEXO SOBERANO: Mente Global (Supabase Edge Functions) - Manual de Despliegue

Este paquete contiene la infraestructura serverless para la evolución proactiva de NEXO SOBERANO.

## 📦 Contenido del Paquete

- `functions/`: Código Deno para Edge Functions (Drive Ingest, Vision Analysis, Summarizer, Discord Bridge).
- `sql/`: Migraciones para configurar el esquema, tablas y RLS.
- `scripts/`: Herramientas para registrar slash commands.

## 🔑 Secretos Requeridos (Supabase)

Configurar en `Settings > Edge Functions > Secrets`:
- `SUPABASE_SERVICE_ROLE_KEY`
- `DISCORD_BOT_TOKEN`, `DISCORD_PUBLIC_KEY`, `DISCORD_APPLICATION_ID`
- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`
- `GEMINI_API_KEY`
- `BUCKET_NAME` (Default: `nexo-media`)

## 🛠️ Instalación

1. **SQL**: Pegar/ejecutar el contenido de `sql/migrations/001_create_global_mind.sql` en el SQL Editor de Supabase.
2. **Bucket**: Asegurarse de que existe un bucket llamado `nexo-media` (privado).
3. **Deploy**:
   ```bash
   supabase functions deploy ingest_from_drive
   supabase functions deploy analyze_content
   supabase functions deploy daily_summarizer
   supabase functions deploy discord_bridge
   supabase functions deploy publish_queue
   ```
### 4. Configurar Google OAuth
Para que Nexo acceda a tu Drive:
1. Ve a [Google Cloud Console](https://console.cloud.google.com/).
2. Crea un proyecto y habilita la **Google Drive API**.
3. En **Pantalla de Consentimiento OAuth**, configura como "Externo" y añade tu email como usuario de prueba.
4. En **Credenciales**, crea un **ID de cliente de OAuth 2.0** (Tipo: Aplicación Web).
5. Añade la URI de redirección: `https://<tu-id-proyecto>.supabase.co/functions/v1/ingest_from_drive/callback`.
6. Copia el `Client ID` y `Client Secret` a tus secretos de Supabase.

### 5. Registrar Comandos de Discord
Configura tu `.env` local con las credenciales de Discord y ejecuta:
```bash
node scripts/register_discord_commands.js
```

## 🤖 Uso
- Apunta el **Interactions Endpoint URL** de tu app de Discord a la URL de la función `discord_bridge`.
- Visita la URL de `ingest_from_drive` para iniciar el flujo de OAuth de Google.
