# Prompt — Claude Skill Spec (Deep)

Diseña un `Agent Skill` de Claude Code para NEXO con comandos naturales:

- `/geopolitica generar_informe`
- `/economia sintetizar_fuentes`
- `/riesgo evaluar_escenario`

## Contrato de entrada

- `task`
- `domain`
- `time_range`
- `sources`
- `strict_evidence` (bool)

## Contrato de salida

- `summary`
- `findings[]`
- `citations[]`
- `confidence`
- `action_plan[]`
- `next_steps[]`

## Reglas obligatorias

1. Si `strict_evidence=true` y no hay citas, devolver `INSUFFICIENT_EVIDENCE`.
2. Toda recomendación debe incluir impacto, esfuerzo, riesgo y owner.
3. Guardar resultados en Drive y log local.
4. No ejecutar acciones destructivas sin confirmación explícita.

## Entregables

A) Especificación del Skill
B) Validadores de input/output
C) Ejemplos de ejecución
D) Manejo de errores y fallback
E) Modo ahorro (Claude decisor + Gemini fallback)
