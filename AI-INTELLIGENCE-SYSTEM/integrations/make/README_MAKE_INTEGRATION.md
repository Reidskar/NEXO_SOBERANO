# Make Integration Pack NEXO (económico + eficaz)

Este paquete está adaptado a NEXO_SOBERANO para operar con costo bajo, resultados útiles y validación contra endpoints reales del backend.

## Archivos

- `payloads/video_reverse_engineering_request.json`
- `payloads/auto_ingest_rule.json`
- `payloads/llm_prompt_template.txt`
- `router-rules/video_pipeline_routing.json`
- `make_variables.example.json`

## Política por defecto (recomendada)

- Decisor final IA: `claude`
- Modo ahorro: `true`
- Fallback: `gemini`
- Modo de ejecución por defecto: `fast`
- `deep` solo con aprobación manual

## Flujo recomendado en Make

1. **Google Drive Watch Files** en carpeta `videos/`.
2. **Set Variables** con `make_variables.example.json`.
3. **Router** por `mode` (`fast|standard|deep`) usando `router-rules/video_pipeline_routing.json`.
4. **HTTP - Build Prompt Payload** con `payloads/video_reverse_engineering_request.json`.
5. **HTTP - LLM Completion** con `payloads/llm_prompt_template.txt`.
6. **JSON Parse** de salida A-J.
7. **Google Drive Upload** de artefactos a carpetas objetivo.
8. **Google Docs/Markdown append** a índice de conocimiento.
9. **HTTP - Validación NEXO** (`/health`, `/analytics`, `/warroom/ai-control`, `/api/ai/foda-critical`).
10. **Discord Notify** cuando `needs_human_review=true`.

## Mapeo dinámico mínimo

- `{{video.file_name}}`, `{{video.file_id}}`, `{{video.mime_type}}`, `{{video.drive_url}}`
- `{{project_name}}`, `{{language}}`, `{{mode}}`, `{{slug}}`
- `{{final_decider}}`, `{{modo_ahorro}}`, `{{fallback_provider}}`
- `{{critical_confidence}}` para puerta de revisión humana

## Seguridad

- Guarda secretos en Vault de Make (`nexo_api_key`, `discord_webhook`, IDs de carpetas).
- No hardcodees tokens en payloads.

## Resultado esperado

Genera en cada corrida:

- `/knowledge/{{slug}}_system.md`
- `/architecture/{{slug}}_architecture.md`
- `/workflows/{{slug}}_n8n.json`
- `/prompts/{{slug}}_prompts.md`
- `/sql/{{slug}}_schema.sql`
- `/implementation/{{slug}}_roadmap.md`

## Validación de eficacia operativa

Para considerar una corrida como "útil en producción":

1. `GET /health` responde `operational`.
2. `GET /analytics` no devuelve errores críticos nuevos.
3. `GET /warroom/ai-control` mantiene `ok=true`.
4. `POST /api/ai/foda-critical` responde con `decisor_final=claude` y `modo_ahorro=true`.
