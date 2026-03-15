# NEXO SOBERANO — Contexto para Claude Code

## Descripción
Plataforma de IA personal soberana multi-dispositivo.
Torre (servidor) + Notebook (consola) + Xiaomi (agente móvil).

## Stack
- Backend: FastAPI Python 3.11 en .venv
- Bot: Node.js Discord con PM2
- DB: PostgreSQL + Redis + Qdrant (Docker)
- AI: Gemini primario, Anthropic fallback
- Repo: github.com/Reidskar/NEXO_SOBERANO

## Rutas clave
- Torre: C:\Users\Admn\Desktop\NEXO_SOBERANO
- Notebook: C:\Users\estef\OneDrive\NEXO_SOBERANO
- Arrancar backend: .venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
- Docker: docker compose up -d nexo_db nexo_redis nexo_qdrant

## Reglas
- Nunca modificar main.py sin verificar imports después
- PM2 siempre desde cmd.exe, nunca PowerShell
- git pull antes de cualquier cambio
- No commitear archivos en backend/auth/*.json
- No commitear *.zip ni exports/

## Estado actual Sprint 1.3
- Backend: operativo
- Docker: tres servicios Up
- Discord slash commands: registrados
- Frontend: paleta premium aplicada
- Auth guard: conectado en main.py
