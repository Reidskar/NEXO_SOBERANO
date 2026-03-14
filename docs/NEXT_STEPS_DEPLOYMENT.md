# Guía de Despliegue - NEXO SOBERANO

Este documento detalla los pasos necesarios para desplegar el "Cerebro" en la nube (Railway + Supabase) mientras mantenemos el "Músculo" multimedia en local.

## 1. Supabase (Cerebro de Datos)

### Edge Functions
Desplegar la función de generación de borradores sociales:
1. Instalar Supabase CLI: `scoop install supabase` o vía npm.
2. Login: `supabase login`
3. Link al proyecto: `supabase link --project-ref [TU_PROJECT_ID]`
4. Desplegar: `supabase functions deploy generate_social_drafts`

### Database Webhooks
Configurar la automatización:
1. Ir a **Database > Webhooks** en el panel de Supabase.
2. Crear un nuevo Webhook:
   - **Name**: `trigger_social_content`
   - **Table**: `alertas` (o la tabla que dispare el contenido)
   - **Events**: `INSERT`
   - **Type**: `HTTP Request`
   - **Method**: `POST`
   - **URL**: URL de tu Edge Function o flujo de n8n.

## 2. Railway (Backend API)

### Configuración del Repositorio
1. Conectar el repositorio de GitHub a Railway.
2. Configurar la variable `DOCKERFILE` a `Dockerfile.nexo_core` si no se detecta automáticamente.

### Variables de Entorno (Railway Dashboard)
Asegurarse de inyectar todas las variables del `.env.example`:
- `DATABASE_URL` (Pooler de Supabase)
- `SUPABASE_URL` y `SUPABASE_SERVICE_KEY`
- `GEMINI_API_KEY`
- `NEXO_API_KEY`

## 3. Orquestación Local (Músculo Multimedia)

### n8n (Flujos de Trabajo)
1. Importar el archivo JSON del flujo (si está disponible) o recrear el flujo `listos_para_publicar`.
2. Configurar las credenciales de X/Twitter, YouTube y Google Drive en n8n.

### Local Server
1. Configurar `NEXO_MODE=local` en el `.env` del PC.
2. Ejecutar `scripts/start_local_server.ps1` para asegurar que el motor de video esté listo.

## 4. Verificación
1. Ejecutar el comando de prueba de video: `python services/publicacion/video_factory.py --test` (una vez verificado el script).
2. Monitorear los logs en Railway y el War Room.
