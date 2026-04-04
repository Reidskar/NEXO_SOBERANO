---
name: classify
description: Clasifica la complejidad de una tarea y decide si la ejecuta VS Code, Antigravity o Claude Code.
allowed_tools: ["Bash"]
---

# /classify

Antes de cualquier tarea de programación, clasifica su complejidad.

## Uso

```bash
# Clasificar por descripción
python scripts/nexo_manager.py classify --tarea "agregar endpoint de health check"

# Clasificar por diff actual
python scripts/nexo_manager.py classify --diff "$(git diff --staged)"
```

## Niveles de respuesta

| Nivel | Herramienta | Acción |
|---|---|---|
| 🟢 1 Simple | **VS Code** | Automático al guardar, o tarea "Fix: Formatear + lint auto" |
| 🟡 2 Medio | **Antigravity** | `nexo_manager.py fix --apply` o tarea "🤖 Antigravity: Auto-fix" |
| 🔴 3 Complejo | **Claude Code** | Comunicar al usuario + esperar autorización explícita |

## Regla Claude Code
Si el nivel es 1 o 2, **sugerir la herramienta correcta en lugar de ejecutar directamente**.
Solo proceder con nivel 3 si el usuario confirma explícitamente.
