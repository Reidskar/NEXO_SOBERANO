# Prompt — NotebookLM Bridge (Deep)

Actúa como arquitecto principal de plataforma.

Diseña un microservicio Python (`FastAPI`) llamado `notebooklm-bridge` que exponga:

- `POST /notebooks/create`
- `POST /notebooks/{id}/sources/add`
- `POST /drive/sync-folder`
- `POST /summaries/generate`
- `GET /jobs/{job_id}`
- `GET /health`

## Requisitos

1. Debe soportar `dry-run` y `real-run`.
2. Debe registrar trazas con `request_id`, `job_id`, `source_ids`, `duration_ms`.
3. Debe implementar reintentos, idempotencia y cola simple.
4. Debe incluir contratos `Pydantic` para entrada/salida.
5. Debe poder trabajar sin API oficial (adaptador notebooklm-py/Playwright) con fallback local.

## Entregables

A) Diagrama de componentes
B) Contratos OpenAPI por endpoint
C) Estrategia de retries + dead-letter
D) Seguridad (API key + allowlist)
E) Plan de pruebas (unit + integration)
F) Riesgos y mitigaciones

## Restricciones

- Priorizar bajo costo.
- No usar servicios cerrados como dependencia obligatoria.
- Evitar lock-in: todo adaptador debe estar detrás de interfaz.
