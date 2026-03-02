from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.agente import router as agente_router
from backend.routes.omni import router as omni_router
from backend.routes.chat import router as chat_router
from backend.routes.auth import router as auth_router
from backend.routes.health import router as health_router
from backend.routes.preferences import router as preferences_router

app = FastAPI(title="Nexo Soberano API", version="2.0")

# CORS (necesario para warroom HTML separado)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agente_router)
app.include_router(omni_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(preferences_router)

@app.get("/")
def root():
    return {"status": "Nexo Backend Activo", "version": "2.0"}

@app.get("/")
def root():
    return {"status": "Nexo Backend Activo"}
