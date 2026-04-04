---
name: code-review
description: Revisión de código con Gemma 4 — detecta bugs, anti-patrones y violaciones de arquitectura NEXO.
allowed_tools: ["Bash", "Read", "Grep"]
---

# /code-review

Motor: **Gemma 4 local ($0)** + ruff.

## Ejecutar

```bash
# Revisar todos los cambios actuales
python scripts/nexo_manager.py review

# Revisar archivo específico
python scripts/nexo_manager.py review --file backend/routes/mi_ruta.py

# Solo cambios staged
python scripts/nexo_manager.py review --staged
```

## Auto-fix

```bash
# Detectar y corregir automáticamente
python scripts/nexo_manager.py fix --file backend/routes/mi_ruta.py

# Aplicar corrección directamente
python scripts/nexo_manager.py fix --file backend/routes/mi_ruta.py --issue "endpoint sin auth guard" --apply
```
