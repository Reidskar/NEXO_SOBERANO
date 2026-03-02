# Integración X (Twitter) + Grok en NEXO SOBERANO

## Qué quedó implementado

- Servicio backend `backend/services/x_publisher.py` con:
  - `post_to_x(text, media_path)`
  - `search_x_recent(query, limit)`
  - `fetch_mentions(limit, since_id, username)`
  - `ask_grok_via_x(question, context)`
  - `ask_grok(question, model)` (vía `XAI_API_KEY`; fallback si no existe)
- Servicio backend `backend/services/x_monitor.py` con:
  - `monitor_x_once(limit, username)`
  - `run_x_monitor_loop(interval_seconds, limit, username)`
- Endpoints FastAPI en `backend/routes/agente.py`:
  - `POST /agente/x/post`
  - `POST /agente/x/search`
  - `POST /agente/x/mentions`
  - `POST /agente/x/ingest-mentions`
  - `POST /agente/x/monitor-once`
  - `GET /agente/x/monitor-status`
  - `POST /agente/grok/consult`
- Pipeline diario `backend/services/drive_youtube_service.py`:
  - Si `NEXO_X_AUTO_PUBLISH=true`, publica automáticamente en X al subir video de YouTube.
  - Si `NEXO_X_GROK_VALIDATE=true`, hace mención previa a `@grok` para validación proxy.

## Variables de entorno

Agrega en `.env`:

```env
X_API_KEY=
X_API_SECRET=
X_ACCESS_TOKEN=
X_ACCESS_SECRET=
X_USERNAME=
X_BOT_USERNAME=
XAI_API_KEY=
XAI_API_URL=https://api.x.ai/v1/chat/completions
NEXO_X_AUTO_PUBLISH=false
NEXO_X_GROK_VALIDATE=false
X_BEARER_TOKEN=
NEXO_X_MONITOR_INTERVAL_SECONDS=900
```

## Dependencias

Se agregó `tweepy` en `requirements.txt`.

Instala:

```bash
pip install -r requirements.txt
```

## Pruebas rápidas

### Publicar en X

```bash
curl -X POST http://127.0.0.1:8000/agente/x/post \
  -H "Content-Type: application/json" \
  -d '{"text":"Resumen SIG Diario de prueba #NexoSoberano"}'
```

### Buscar en X

```bash
curl -X POST http://127.0.0.1:8000/agente/x/search \
  -H "Content-Type: application/json" \
  -d '{"query":"geopolitica OR conflicto lang:es -is:retweet","limit":10}'
```

### Leer menciones

```bash
curl -X POST http://127.0.0.1:8000/agente/x/mentions \
  -H "Content-Type: application/json" \
  -d '{"limit":10}'
```

### Ingerir menciones a cuarentena Drive

```bash
curl -X POST http://127.0.0.1:8000/agente/x/ingest-mentions \
  -H "Content-Type: application/json" \
  -d '{"limit":10}'
```

### Consultar Grok (xAI)

```bash
curl -X POST http://127.0.0.1:8000/agente/grok/consult \
  -H "Content-Type: application/json" \
  -d '{"question":"Valida consistencia factual de este resumen...","model":"grok-beta"}'
```

### Ejecutar monitor X/Grok una vez

```bash
curl -X POST http://127.0.0.1:8000/agente/x/monitor-once \
  -H "Content-Type: application/json" \
  -d '{"limit":20}'
```

### Ver estado del monitor

```bash
curl http://127.0.0.1:8000/agente/x/monitor-status
```

### Loop automático cada 15 min

```bash
C:/Users/Admn/Desktop/NEXO_SOBERANO/.venv/Scripts/python.exe scripts/run_x_monitor.py --interval 900 --limit 20
```

## Flujo bidireccional sugerido

1. `POST /agente/youtube/daily-resume` (sube video a YouTube)
2. Si `NEXO_X_AUTO_PUBLISH=true`, se publica tweet automático con URL del video
3. Si `NEXO_X_GROK_VALIDATE=true`, se emite mención a `@grok` como verificación proxy
4. Cron/worker ejecuta `scripts/run_x_monitor.py` cada 10-30 min
5. Menciones y respuestas de Grok quedan en Drive cuarentena para análisis y posterior incorporación al RAG
