# Prompt — Mermaid Sequence + Guardrails

Genera un diagrama de secuencia Mermaid para este flujo:

1. Nuevo archivo detectado en Drive.
2. Clasificación automática NEXO.
3. Ingesta en NotebookLM Bridge.
4. Actualización de índice/corpus.
5. Consulta compleja desde Claude Skill.
6. Validación anti-alucinación.
7. Entrega y persistencia de resultado.

## Requisitos de control

- Punto de validación de OAuth/tokens.
- Punto de validación de citas mínimas.
- Punto de rollback si falla ingesta.
- Punto de alerta si confidence < 0.7.
- Registro de métricas (latencia, costo, éxito/fallo).

## Salida

- Bloque Mermaid listo para pegar.
- Tabla de controles por etapa (input, output, risk, mitigation).
