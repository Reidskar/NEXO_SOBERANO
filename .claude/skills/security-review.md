---
name: security-review
description: Use when adding auth, handling user input, creating API endpoints, or touching secrets. Provides NEXO-specific security checklist.
origin: affaan-m/everything-claude-code (adapted)
---

# Security Review — NEXO SOBERANO

## When to Activate
- Implementing authentication or API key validation
- New FastAPI endpoints receiving user input
- Changes to `backend/auth/`, `NEXO_CORE/middleware/`
- Integrations with external APIs (BigBrother, Ollama, Gemini, X/Twitter)
- Adding new environment variables

## Secrets Checklist
- [ ] No hardcoded API keys in `.py` files
- [ ] `backend/auth/*.json` excluded from git
- [ ] `.env` not committed
- [ ] Prod secrets set in Railway dashboard, not in code

## Input Validation Checklist
- [ ] All request bodies validated via Pydantic model
- [ ] API key headers checked with `_require_key()` helper
- [ ] File upload size limits enforced
- [ ] SQL queries use parameterized form (never f-strings)

## FastAPI Security Patterns

```python
# ✓ CORRECT: API key validation
def _require_key(x_api_key: Optional[str]):
    if x_api_key != NEXO_API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida")

# ✗ WRONG: Exposing internal errors
except Exception as e:
    return {"error": str(e), "traceback": traceback.format_exc()}  # NEVER

# ✓ CORRECT: Safe error response
except Exception as e:
    logger.error(f"Internal error: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Error interno")
```

## OSINT/BigBrother Specific
- BigBrother results must NOT be returned raw to frontend without Gemma 4 filtering
- Aircraft/person tracking endpoints require API key auth (never public)
- Dark web results must be sanitized before logging

## Run Before Merging
```bash
.venv/Scripts/python.exe -m bandit -r backend/ NEXO_CORE/ -ll -q
```
