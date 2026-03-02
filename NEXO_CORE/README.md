# NEXO_CORE

Backend consolidado para NEXO Soberano.

## Arranque

```bash
python run_backend.py
```

O directo con uvicorn:

```bash
uvicorn NEXO_CORE.main:app --host 0.0.0.0 --port 8000
```

## Endpoints nuevos

- `GET /api/health/`
- `GET /api/health/stream`
- `GET /api/stream/status`
- `POST /api/stream/status`

## Compatibilidad heredada

Se mantienen rutas de `backend.routes.agente` y `backend.routes.eventos`.
