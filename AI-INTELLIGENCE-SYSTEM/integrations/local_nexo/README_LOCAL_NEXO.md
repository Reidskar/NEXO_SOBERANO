# Local NEXO Pipeline (sin Make)

Este flujo ejecuta todo dentro del repositorio NEXO_SOBERANO, priorizando costo bajo y eficacia operativa.

## Política por defecto

- `mode`: `fast`
- `final_decider`: `claude`
- `modo_ahorro`: `true`
- fallback: `gemini`
- `openai` y `grok`: deshabilitados

## Ejecutar

Desde la raíz del repo:

```powershell
.\.venv\Scripts\python.exe AI-INTELLIGENCE-SYSTEM\scripts\run_nexo_local_video_pipeline.py --max-videos 1
```

Si quieres un archivo específico:

```powershell
.\.venv\Scripts\python.exe AI-INTELLIGENCE-SYSTEM\scripts\run_nexo_local_video_pipeline.py --video miguebaenaia-20260305-0001.mp4
```

## Validaciones runtime incluidas

- `GET /health`
- `GET /analytics`
- `GET /warroom/ai-control`
- `POST /api/ai/foda-critical` con `decisor_final=claude` y `modo_ahorro=true`

## Salidas

Por cada video genera:

- `knowledge/{slug}_system.md`
- `architectures/{slug}_architecture.md`
- `workflows/{slug}_n8n.json`
- `prompts/generated/{slug}_prompts.md`
- `database/{slug}_schema.sql`
- `implementation/{slug}_roadmap.md`

Reporte consolidado:

- `docs/reports/local_video_pipeline_YYYYMMDD_HHMMSS.json`
