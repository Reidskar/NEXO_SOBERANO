# AI-INTELLIGENCE-SYSTEM

Sistema operativo para convertir videos y archivos en:

- arquitectura técnica implementable
- workflows de automatización (n8n)
- esquema SQL
- librería de prompts reutilizable
- base de conocimiento publicable

## Estructura

- `videos/` videos fuente a analizar
- `files/` documentos relacionados
- `prompts/` prompts listos para Copilot/agentes
- `database/` esquema SQL base
- `workflows/` plantillas de automatización
- `architectures/` diagramas y blueprints
- `knowledge/` salida educativa estructurada
- `integrations/` conectores por plataforma
- `tools-database/` inventario de herramientas detectadas

## Uso rápido

1. Copia videos a `videos/`.
2. Ejecuta el pipeline local NEXO (sin Make):
   - `\.venv\Scripts\python.exe AI-INTELLIGENCE-SYSTEM\scripts\run_nexo_local_video_pipeline.py --max-videos 1`
3. Revisa artefactos generados en:
   - arquitectura: `architectures/`
   - workflows: `workflows/`
   - sql: `database/`
   - lecciones: `knowledge/`
   - prompts generados: `prompts/generated/`
4. Revisa reporte consolidado en `docs/reports/`.
5. Detalle de integración local: `integrations/local_nexo/README_LOCAL_NEXO.md`.

## Stack objetivo

- Frontend: Next.js o Astro
- Backend: Node.js o Python
- Automatización: n8n
- IA: Anthropic (Claude) + fallback Gemini (modo ahorro por defecto)
- Storage: Google Drive + PostgreSQL
