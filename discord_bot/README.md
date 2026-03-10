# NEXO Discord Tutor Bot

Bot Discord educativo conectado al backend FastAPI de NEXO SOBERANO.

## Comandos

- `/tutor pregunta:<texto>`: consulta evidencia vía `POST /agente/consultar-rag`.
- `/aporte contenido:<texto> archivo:<opcional>`: envía aporte comunitario vía `POST /agente/drive/upload-aporte`.
- `/autonomo modo:<on|off|status>`: controla respuestas autónomas por canal.

## Modo conversación autónoma

El bot puede responder de forma autónoma en conversaciones de canal (incluyendo varias personas) y siempre consulta a la IA central vía `POST /agente/consultar-rag`.

Disparadores de respuesta:

- Mención directa al bot.
- Mensaje que empieza con el nombre de activación (`AUTOCHAT_NAME`, por defecto `nexo`).
- Conversación activa reciente con señal de pregunta (según configuración).

Variables de entorno relevantes:

- `AUTOCHAT_ENABLED=true|false`
- `AUTOCHAT_CHANNEL_IDS=123,456` (vacío = todos los canales)
- `AUTOCHAT_MIN_INTERVAL_SECONDS=10`
- `AUTOCHAT_ACTIVE_WINDOW_SECONDS=180`
- `AUTOCHAT_MAX_CONTEXT_MESSAGES=12`
- `AUTOCHAT_ALLOW_WITHOUT_MENTION=false`
- `AUTOCHAT_NAME=nexo`

## Modo llamada siempre activa (24/7)

El bot puede mantenerse conectado permanentemente a un canal de voz al iniciar.

Variables requeridas:

- `VOICE_ALWAYS_ON=true`
- `VOICE_GUILD_ID=<id_del_servidor>`
- `VOICE_CHANNEL_ID=<id_del_canal_voz>`
- `VOICE_SELF_DEAF=true` (recomendado si no capturas audio aún)
- `VOICE_RECONNECT_SECONDS=20`

Comando de control:

- `/llamada accion:status` muestra estado de conexión
- `/llamada accion:reconnect` fuerza reconexión

## Configuración

1. Copia `.env.example` a `.env`.
2. Completa `DISCORD_TOKEN`, `DISCORD_CLIENT_ID` y `FASTAPI_URL`.
3. Opcional: define `DISCORD_GUILD_ID` para registrar comandos instantáneamente en un servidor de prueba.

## Run local

```bash
npm install
npm run start
```

## PM2 (24/7)

```bash
npm install -g pm2
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

## Requisitos backend

- `POST /agente/consultar-rag`
- `POST /agente/drive/upload-aporte`

Este repositorio ya incluye ambos endpoints en `backend/routes/agente.py`.
