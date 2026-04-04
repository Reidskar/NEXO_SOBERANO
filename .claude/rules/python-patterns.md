---
description: "Python code patterns for NEXO SOBERANO"
globs: ["**/*.py"]
alwaysApply: false
---
# Python Patterns — NEXO SOBERANO

Adapted from: affaan-m/everything-claude-code

## Pydantic Models
- Use Pydantic BaseModel for all API request/response schemas
- Use `Field(...)` for validation constraints and descriptions
- Prefer `model_dump()` over `.dict()` (Pydantic v2)

## Async Patterns
- All FastAPI route handlers must be `async def`
- Use `asyncio.gather()` for parallel I/O operations
- Never block the event loop with `time.sleep()` — use `asyncio.sleep()`
- Use `aiohttp.ClientSession()` (not `requests`) for HTTP calls from async code

## Service Layer
- Business logic lives in `services/`, NOT in route handlers
- Route handlers should be thin: validate input → call service → return response
- Services in `NEXO_CORE/services/` are shared; `backend/services/` are project-specific

## Error Handling
- Raise `HTTPException` at the route level with appropriate status codes
- Use NEXO_CORE logger: `logger = logging.getLogger("NEXO.<module>")`
- Never swallow exceptions silently — log at minimum with `logger.error()`

## Cost Tracking
- Register AI API calls in `backend/services/cost_manager.py`
- Prefer local Ollama/Gemma 4 ($0) before cloud APIs
- Check `ai_router.py` TAREAS_LOCAL list before adding new cloud calls
