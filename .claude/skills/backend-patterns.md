---
name: backend-patterns
description: FastAPI/Python backend patterns for NEXO SOBERANO. Activate when designing new routes, services, or middleware.
origin: affaan-m/everything-claude-code (adapted)
---

# Backend Patterns — NEXO SOBERANO

## API Design
```
GET    /api/{resource}           # list
GET    /api/{resource}/{id}      # single
POST   /api/{resource}           # create
PATCH  /api/{resource}/{id}      # update
DELETE /api/{resource}/{id}      # delete
```

## Router Pattern
```python
# backend/routes/my_feature.py
router = APIRouter(prefix="/api/my_feature", tags=["my_feature"])

@router.get("/status")              # public
async def status(): ...

@router.post("/action")             # protected
async def action(
    body: ActionRequest,
    x_api_key: Optional[str] = Header(None),
):
    _require_key(x_api_key)
    result = await my_service.do_thing(body.param)
    return result
```

## Service Layer Pattern
```python
# backend/services/my_service.py
class MyService:
    async def do_thing(self, param: str) -> dict:
        # 1. Try local Ollama first ($0)
        result = await ollama_service.consultar(param)
        # 2. Fallback to cloud if needed
        if not result.success:
            result = await ai_router.consultar(AIRequest(...))
        return result.model_dump()

my_service = MyService()   # singleton
```

## Registering in main.py
```python
from backend.routes.my_feature import router as my_router
app.include_router(my_router)
```

## Globe Integration Pattern
When a service discovers geo-located intelligence:
```python
from backend.routes.globe_control import broadcast_command
await broadcast_command({
    "type": "add_event",
    "id": "unique_id",
    "lat": lat, "lng": lng,
    "label": "Description",
    "severity": 0.7,
})
```
