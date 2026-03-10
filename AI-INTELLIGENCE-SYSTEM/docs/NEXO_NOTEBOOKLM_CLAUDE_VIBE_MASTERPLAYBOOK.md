# NEXO SOBERANO — Master Playbook (NotebookLM + Claude Code + Vibe Prospecting)

## 1) Objetivo realista

Construir un sistema soberano y económico con tres capas:

1. **Ingesta y memoria**: Drive -> extracción -> NotebookLM bridge (RAG operativo).
2. **Ejecución inteligente**: Claude Code Skills con contratos de entrada/salida.
3. **Expansión comercial**: Vibe Prospecting + validación de leads + seguimiento.

## 2) Restricciones duras

- Priorizar costo bajo y robustez.
- Evitar dependencia de APIs no oficiales en ruta crítica sin fallback.
- Toda salida de IA debe incluir evidencia/citas y un nivel de confianza.
- Cualquier acción externa debe dejar traza en logs y rollback definido.

## 3) Arquitectura recomendada

- `NEXO_CORE` (FastAPI): control operativo y endpoints protegidos.
- `NotebookLM Bridge API` (FastAPI local): capa anti-fragilidad para notebooklm-py/Playwright.
- `Drive Sync Worker`: consume cambios de carpeta y normaliza documentos.
- `RAG Quality Gate`: valida cobertura y evita respuestas sin evidencia.
- `Claude Skills`: consume solo APIs internas, nunca accesos directos inseguros.

## 4) Flujo de datos (alto nivel)

1. `Drive Watch` detecta nuevos archivos.
2. Clasificador NEXO categoriza y encola ingesta.
3. Bridge NotebookLM crea/actualiza libreta y fuentes.
4. Índice de contexto se actualiza y registra versión.
5. Claude Skill ejecuta consulta -> recibe resultado con citas.
6. Salida final se guarda en Drive + reporte en `logs/`.

## 5) Guardrails anti-alucinación

- Exigir `citations_count >= 1` para respuestas analíticas.
- Si no hay evidencia: respuesta debe ser `INSUFFICIENT_EVIDENCE`.
- Bloquear generación de guiones "seguros" sin fuentes verificadas.
- Añadir revisión automática de contradicciones entre fuentes.

## 6) Plan de implementación (72h)

### 0-6h
- Levantar `notebooklm_bridge_api.py` en modo `dry-run`.
- Integrar chequeos de salud y autenticación.
- Validar roundtrip de ingestión simulada.

### 6-24h
- Conectar Drive sync real (carpeta objetivo).
- Guardar mapping `drive_file_id -> notebook_source_id`.
- Activar Skill base de Claude (`/geopolitica generar_informe`).

### 24-72h
- Integrar prospección con validación de calidad de lead.
- Añadir scoring y deduplicación por dominio/email.
- Cerrar dashboard con KPI: cobertura, latencia, costo, precisión.

## 7) Qué reforzar primero (ROI alto)

1. OAuth Google (Drive/Photos) estable.
2. Corpus RAG (5 -> 50+ documentos curados).
3. Observabilidad de costos IA (tokens/requests/presupuesto).
4. Reducción de issues altos por lotes.

## 8) Checklist de salida a producción

- [ ] `GET /api/health/` estable.
- [ ] `analytics.workspace.ok == true`.
- [ ] `foda-status` con `accion_correctiva.required == true`.
- [ ] Skill Claude con contrato validado (input/output schema).
- [ ] Reporte multi-IA generado y versionado.
