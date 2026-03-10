# NEXO Optimization Runbook

## 1) Endpoint nuevo integrado (sin servicio aparte)

Knowledge Bridge embebido en NEXO CORE:

- `GET /api/knowledge/health`
- `POST /api/knowledge/notebooks/create`
- `POST /api/knowledge/notebooks/source/add`
- `POST /api/knowledge/drive/sync-folder`
- `GET /api/knowledge/jobs/{job_id}`
- `POST /api/knowledge/summaries/generate`

Header requerido:

- `X-NEXO-API-KEY: NEXO_LOCAL_2026_OK`

## 2) Optimizador operativo

```powershell
.\.venv\Scripts\python.exe scripts\nexo_operational_optimizer.py
```

Salida:

- `logs/nexo_operational_optimizer_report.json`

## 3) Revisión multi-IA robusta

```powershell
.\.venv\Scripts\python.exe scripts\run_multi_ai_project_review.py --timeout 90 --foda-timeout 120
```

Salida:

- `logs/multi_ai_project_review.json`

Modo rápido sin FODA:

```powershell
.\.venv\Scripts\python.exe scripts\run_multi_ai_project_review.py --skip-foda
```

## 4) Secuencia recomendada diaria

1. `nexo_operational_optimizer.py`
2. Corregir acciones P1
3. `run_multi_ai_project_review.py`
4. Revisar War Room IA CTRL y `foda-status`

## 5) Límites conocidos

- OAuth Google requiere interacción de usuario (no 100% automatizable desde backend).
- OBS/Discord dependen de servicios externos en ejecución local.
