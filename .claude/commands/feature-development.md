---
name: feature-development
description: Standard feature implementation workflow for NEXO SOBERANO.
allowed_tools: ["Bash", "Read", "Write", "Edit", "Grep", "Glob"]
---

# /feature-development

## Goal
Implement a new feature following NEXO SOBERANO architecture patterns.

## Sequence

1. **Understand current state** — read related files before writing anything
2. **Plan layers needed**: route → service → model (Pydantic) → tests
3. **Implement service first** in `backend/services/` or `NEXO_CORE/services/`
4. **Add route** in `backend/routes/`, register in `backend/main.py`
5. **Check cost**: does this call cloud AI? If yes, route through `ai_router.py` with local-first
6. **Globe integration**: if geo data → use `broadcast_command()` to push to OmniGlobe
7. **Run tests**: `python -m pytest tests/ -v`
8. **Security check**: run `/security-review` before committing

## Key Files
- Routes: `backend/routes/`
- Services: `backend/services/` and `NEXO_CORE/services/`
- AI routing: `NEXO_CORE/services/ai_router.py`
- Globe commands: `backend/routes/globe_control.py`
- Config/env: `NEXO_CORE/config.py`, `backend/config.py`

## Commit Format
```
feat(module): short description

Body explaining why, not what.
```
