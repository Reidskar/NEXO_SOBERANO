---
description: "Python security rules for NEXO SOBERANO FastAPI backend"
globs: ["**/*.py", "**/*.pyi"]
alwaysApply: true
---
# Python Security — NEXO SOBERANO

Adapted from: affaan-m/everything-claude-code

## Secret Management
- NEVER hardcode API keys, tokens, or passwords in source code
- ALL secrets must come from environment variables via `.env` (not committed)
- Use `os.environ["KEY"]` (raises KeyError) not `os.getenv("KEY", "fallback_secret")`
- Never commit `*.json` files under `backend/auth/`
- Never commit `.env` files (only `.env.example`)

## Input Validation
- Validate all user input at API boundaries with Pydantic models
- Use `Field(min_length=..., max_length=..., pattern=...)` for strings
- Always validate `x-api-key` headers before processing admin requests
- Never interpolate user input directly into SQL queries or shell commands

## FastAPI-specific
- Rate limiting on all public endpoints via `NEXO_CORE/middleware/rate_limit.py`
- Never expose stack traces to end users (use `HTTPException` with safe messages)
- Log security events (failed auth, rate limit hits) with severity INFO or above
- Avoid `eval()`, `exec()`, `pickle.loads()`, `subprocess.run(shell=True)` with user data

## Static Security Scan
```bash
# Run before committing
.venv/Scripts/python.exe -m bandit -r backend/ NEXO_CORE/ -ll
```

## Secrets checklist (pre-commit)
- [ ] No hardcoded credentials
- [ ] `backend/auth/*.json` NOT staged
- [ ] `.env` NOT staged (only `.env.example`)
- [ ] No `*.zip` or exports staged
