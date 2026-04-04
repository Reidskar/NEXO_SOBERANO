---
name: feature-development
description: Flujo completo de implementación de feature en NEXO SOBERANO.
allowed_tools: ["Bash", "Read", "Write", "Edit", "Grep", "Glob"]
---

# /feature-development

## Flujo estándar

1. **Verificar estado del sistema**
   ```bash
   python scripts/nexo_manager.py status
   ```

2. **Implementar** (route → service → model Pydantic)
   - Service en `backend/services/` o `NEXO_CORE/services/`
   - Route en `backend/routes/`, registrar en `backend/main.py`
   - Si consulta AI: usar `ai_router.py` (Gemma 4 primero, cloud fallback)
   - Si hay geo data: `broadcast_command()` → OmniGlobe

3. **Revisar código**
   ```bash
   python scripts/nexo_manager.py review --file backend/routes/nueva_ruta.py
   ```

4. **Auditoría de seguridad**
   ```bash
   python scripts/nexo_manager.py security --file backend/routes/nueva_ruta.py
   ```

5. **Auto-corregir si hay issues**
   ```bash
   python scripts/nexo_manager.py fix --file backend/routes/nueva_ruta.py --apply
   ```

6. **Tests**
   ```bash
   .venv/Scripts/python.exe -m pytest tests/ -v
   ```

7. **Diagnóstico final**
   ```bash
   python scripts/nexo_manager.py diagnose
   ```

## Integración de nueva herramienta externa
1. Crear `backend/services/<herramienta>_bridge.py` (patrón: `big_brother_bridge.py`)
2. Agregar route en `backend/routes/<herramienta>.py`
3. Registrar en `backend/main.py`
4. Documentar en `.env.example`
5. Actualizar `scripts/supervisor_osint.py` si tiene servicio propio
