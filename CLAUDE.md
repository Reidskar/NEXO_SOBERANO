# CLAUDE.md

Este archivo proporciona contexto y guía para Claude Code (claude.ai/code) y otros agentes IA al trabajar en este repositorio.

## Proyecto: NEXO SOBERANO / El Anarcocapital

Plataforma de IA personal soberana multi-dispositivo.
Torre (servidor) + Notebook (consola) + Xiaomi (agente móvil).

### Stack principal

- Backend: FastAPI Python 3.11 en .venv
- Bot: Node.js Discord con PM2
- DB: PostgreSQL + Redis + Qdrant (Docker)
- AI: Gemini primario, Anthropic fallback
- Repo: github.com/Reidskar/NEXO_SOBERANO

### Rutas clave

- Torre: C:\Users\Admn\Desktop\NEXO_SOBERANO
- Notebook: C:\Users\estef\OneDrive\NEXO_SOBERANO
- Arrancar backend: .venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8080
- Docker: docker compose up -d nexo_db nexo_redis nexo_qdrant

### Reglas operativas

- Nunca modificar main.py sin verificar imports después
- PM2 siempre desde cmd.exe, nunca PowerShell
- git pull antes de cualquier cambio
- No commitear archivos en backend/auth/\*.json
- No commitear \*.zip ni exports/

### Estado actual Sprint 1.3

- Backend: operativo
- Docker: tres servicios Up
- Discord slash commands: registrados
- Frontend: paleta premium aplicada
- Auth guard: conectado en main.py

---

## Comandos clave

### Iniciar backend local

```powershell
.venv/Scripts/python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
```

### Instalar dependencias

```powershell
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

### Tests

```powershell
.venv/Scripts/python.exe -m pytest tests/ -v
.venv/Scripts/python.exe test_backend.py        # test integral
.venv/Scripts/python.exe scripts/validate_go_live.py --base-url http://127.0.0.1:8080
```

### Monitor X (Twitter)

```powershell
.venv/Scripts/python.exe scripts/run_x_monitor.py --once --limit 20
```

### Validar credenciales / conectores

```powershell
.venv/Scripts/python.exe backend/check_connectors.py
```

## Arquitectura

### Estructura principal

```
NEXO_SOBERANO/
├── NEXO_CORE/          # Motor central consolidado (fuente de verdad)
│   ├── config.py       # Todas las variables de entorno del core
│   ├── main.py         # Entry point del NEXO_CORE standalone
│   ├── agents/         # Supervisores IA (discord_supervisor, web_ai_supervisor)
│   ├── api/            # Routers: health, ai, knowledge, stream, dashboard, webhooks
│   ├── core/           # state_manager, errors, logger
│   ├── middleware/      # cors, rate_limit
│   └── services/       # discord_manager, obs_manager, multi_ai_service, etc.
├── backend/            # Capa backend del proyecto (envuelve NEXO_CORE)
│   ├── config.py       # Config local (rutas SQLite, Chroma, etc.)
│   ├── main.py         # FastAPI app principal — importa NEXO_CORE + backend.routes
│   ├── routes/         # agente, eventos, metrics, media, mobile, files
│   ├── services/       # cost_manager, vector_db, rag_service, x_monitor, etc.
│   └── middleware/     # TenantMiddleware, PerformanceMiddleware
├── frontend/           # App Vite/Vue (npm run dev / npm run build → dist/)
├── frontend_public/    # Páginas HTML estáticas (control_center, landing, etc.)
└── logs/               # Logs del sistema
```

### Flujo de datos

- **IA**: Gemini Flash (barato/rápido) → Gemini Pro → Claude → OpenAI/Grok. Controlado por `LLM_PROVIDER=auto` en `.env`.
- **Vectores**: Qdrant local para memoria semántica a largo plazo. ChromaDB como alternativa local.
- **BD relacional**: Supabase/PostgreSQL en producción, SQLite (`boveda.db`) en local.
- **Cache**: Upstash Redis para respuestas rápidas.
- **Discord**: Solo webhook (no bot completo). El `discord_supervisor` monitorea salud y reintenta.

### Configuración crítica en `.env`

| Variable                        | Propósito                                  |
| ------------------------------- | ------------------------------------------ |
| `DISCORD_ENABLED=true`          | Activar envío a Discord                    |
| `DISCORD_WEBHOOK_URL`           | URL del webhook de Discord                 |
| `NEXO_LLM_PROVIDER=auto`        | `auto`, `gemini`, `claude`, `openai`       |
| `NEXO_MAX_TOKENS_DIA`           | Límite duro de tokens/día (default 900000) |
| `NEXO_MODE`                     | `local` o `railway`                        |
| `QDRANT_URL` / `QDRANT_API_KEY` | Qdrant cloud o local                       |

## Patrones de código importantes

- **Imports**: Siempre importar desde `NEXO_CORE.*` para servicios del core; `backend.*` para lógica específica del proyecto.
- **Config**: `NEXO_CORE/config.py` es el config canónico del motor. `backend/config.py` extiende para rutas locales.
- **Costo API**: Usar `backend/services/cost_manager.py` para registrar llamadas. El hard-limit diario bloquea procesos excedentes.
- **Estado**: `NEXO_CORE/core/state_manager.py` es el singleton de estado del sistema (Discord, OBS, errores).

## Notas de despliegue

- **Railway**: `railway.toml` + `Procfile`. Variables en Railway dashboard.
- **Cloudflare Tunnel**: `cloudflared` expone el backend local a `elanarcocapital.com`.
- **Frontend build**: `cd frontend && npm run build` → sirve desde `frontend/dist/` (montado en FastAPI como StaticFiles).
