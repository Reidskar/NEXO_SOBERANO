---
description: "Regla de enrutamiento de agentes — cuándo actúa cada herramienta"
globs: ["**/*"]
alwaysApply: true
---
# Enrutamiento de Agentes — NEXO SOBERANO

## Jerarquía de herramientas (SIEMPRE respetar)

### 🟢 NIVEL 1 — VS Code / nexo_autosupervisor (automático, sin preguntar)
**Cuándo**: Cambios simples, 1-15 líneas, sin lógica nueva
- Formateo: black, ruff --fix, isort
- Typos, docstrings, comentarios, type hints
- Agregar/renombrar imports
- Fix de sintaxis obvios
- Agregar statements de logging
- Variable renames

**Cómo**: VS Code lo hace al guardar (`formatOnSave: true`) o tarea "Fix: Formatear + lint auto"

---

### 🟡 NIVEL 2 — Antigravity / nexo_autosupervisor (semiautomático)
**Cuándo**: Cambios medianos, 15-100 líneas, lógica simple nueva
- Endpoint nuevo con patrón estándar
- Agregar validación Pydantic
- Error handling a función existente
- Funciones helper
- Tests unitarios
- Refactor de función individual (< 50 líneas)
- Auth guard faltante en ruta

**Cómo**:
```bash
python scripts/nexo_manager.py fix --file ARCHIVO --apply
# o tarea VSCode: "🤖 Antigravity: Auto-fix archivo activo"
```

---

### 🔴 NIVEL 3 — Claude Code (requiere autorización explícita del usuario)
**Cuándo**: Cambios complejos, > 100 líneas, arquitectura, múltiples archivos
- Integrar nuevo servicio externo
- Cambios de arquitectura o diseño de sistema
- Autenticación / OAuth / JWT
- Migraciones de base de datos
- Vulnerabilidades de seguridad que requieren rediseño
- Cambios en > 3 archivos simultáneamente
- Nuevas funcionalidades mayores (OmniGlobe, BigBrother, etc.)
- Deploy / infraestructura

**Cómo**: Claude Code lo hace, PERO debe comunicar claramente:
1. Nivel detectado (3 — complejo)
2. Qué archivos se modificarán
3. Impacto estimado
4. Pedir confirmación antes de proceder

## Clasificación automática
```bash
python scripts/clasificar_tarea.py --tarea "descripción" --archivo "archivo.py"
# Retorna: {"nivel": 1|2|3, "label": "simple|medio|complejo", "herramienta": "vscode|antigravity|claude_code"}
```

## Claude Code: cuándo NO actuar sin autorización
- Si `clasificar_tarea.py` devuelve nivel < 3 → sugerir herramienta apropiada, no ejecutar
- Si hay duda → clasificar y mostrar resultado al usuario, esperar confirmación
- Nunca modificar `backend/auth/`, `.env`, esquemas de DB sin autorización explícita
