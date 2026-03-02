# NEXO Discord Tutor Bot

Bot Discord educativo conectado al backend FastAPI de NEXO SOBERANO.

## Comandos

- `/tutor pregunta:<texto>`: consulta evidencia vía `POST /agente/consultar-rag`.
- `/aporte contenido:<texto> archivo:<opcional>`: envía aporte comunitario vía `POST /agente/drive/upload-aporte`.

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
