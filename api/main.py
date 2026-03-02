import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List
from pydantic import BaseModel

# Asegurar que los imports funcionen
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

app = FastAPI(
    title="Nexo Soberano API",
    description="Plataforma de inteligencia híbrida RAG",
    version="1.0.0"
)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# The original api/main.py was a lightweight mock used by early demos.
# It has now been replaced by the real backend defined in nexo_v2.py.
# The frontend (React) still starts the server via `python nexo_v2.py run`,
# but in case somebody executes this module directly we delegate here.

import sys, os

# ensure workspace root is on sys.path so nexo_v2 can be imported
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

try:
    from nexo_v2 import crear_app
except ImportError:
    raise RuntimeError("no se pudo importar nexo_v2, ejecuta `python nexo_v2.py setup` primero")

# delegate to the application defined inside nexo_v2
app = crear_app()

# Nota: nexo_v2 already configures CORS with allow_origins=["*"]
# y **no** establece allow_credentials para evitar errores de navegador.

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
