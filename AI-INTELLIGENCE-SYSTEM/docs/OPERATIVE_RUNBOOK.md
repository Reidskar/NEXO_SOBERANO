# Operative Runbook

## Objetivo
Convertir videos y archivos en sistemas implementables + conocimiento publicable.

## Flujo operativo recomendado

1. **Ingesta**
   - Copiar video en `videos/`
   - Copiar material extra en `files/`

2. **Extracción de sistema**
   - Ejecutar prompt por tipo de video:
     - `prompts/01_video_enrique_rocha.md`
     - `prompts/02_video_chase_h_ai.md`
     - `prompts/03_video_revolutia_ai.md`
     - `prompts/04_video_nico_pradas.md`

3. **Modo masivo**
   - Ejecutar `prompts/05_super_prompt_reverse_engineering.md`
   - Guardar salida en:
     - `architectures/`
     - `database/`
     - `workflows/`
     - `integrations/`

4. **Modo educativo**
   - Ejecutar `prompts/06_prompt_knowledge_curator.md`
   - Publicar contenido en `knowledge/`

5. **Base de herramientas**
   - Registrar tools/APIs detectadas en `tools-database/`

## Checklist de calidad

- [ ] Arquitectura modular definida
- [ ] SQL validado para tablas core
- [ ] Endpoints REST definidos
- [ ] Workflows n8n creados
- [ ] Integración Discord/Drive especificada
- [ ] Logs y rate limiting considerados

## Fases sugeridas

- **Fase 1 (MVP):** extracción + esquema SQL + endpoint base
- **Fase 2 (Automation):** workflows n8n + integración Discord/Drive
- **Fase 3 (Scale):** multi-agentes + despliegue cloud/distribuido
