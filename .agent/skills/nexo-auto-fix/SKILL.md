---
name: nexo-auto-fix
category: engineering
summary: "Correcciones automáticas de nivel MEDIO en NEXO SOBERANO — sin intervención humana."
description: |
  SKILL de nivel 2 (medio): Antigravity ejecuta correcciones de complejidad media
  usando Gemma 4 como cerebro local ($0/consulta).
  
  Se activa cuando clasificar_tarea.py devuelve nivel=2.
  
  Capacidades:
  - Agregar endpoints simples con patrón estándar NEXO
  - Completar validaciones Pydantic faltantes
  - Agregar error handling a funciones existentes
  - Crear funciones helper/utility
  - Actualizar tests unitarios
  - Refactorizar función individual (< 50 líneas)
  - Agregar auth guard (_require_key) a rutas sin protección

trigger_phrases:
  - "agrega endpoint"
  - "añade validación"
  - "crea helper"
  - "agrega error handling"
  - "actualiza test"
  - "refactoriza función"
  - "agrega auth guard"

workflow:
  steps:
    - Leer archivo(s) involucrado(s) completamente
    - Identificar el cambio mínimo necesario
    - Generar corrección con Gemma 4 (nexo_manager.py fix)
    - Verificar con ruff antes de aplicar
    - Aplicar si pasa verificación
    - Ejecutar nexo_manager.py review para confirmar
  escalate_to_claude_code_if:
    - La corrección requiere cambios en > 3 archivos
    - Involucra autenticación, seguridad o arquitectura
    - Falla 2 veces consecutivas la verificación ruff
    - El usuario no confirma dentro de 30 segundos

commands:
  auto_fix: "python scripts/nexo_manager.py fix --file {archivo} --apply"
  review:   "python scripts/nexo_manager.py review --file {archivo}"
  classify: "python scripts/clasificar_tarea.py --tarea '{tarea}' --archivo {archivo}"
