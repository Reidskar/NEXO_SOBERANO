# ============================================================
# NEXO SOBERANO — File Classification API
# © 2026 elanarcocapital.com
# ============================================================
from __future__ import annotations
import logging
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

logger = logging.getLogger("NEXO.api.files")
router = APIRouter(prefix="/api/files", tags=["files"])


class ClasificarRequest(BaseModel):
    ruta: str
    recursivo: Optional[bool] = True
    ingestar_rag: Optional[bool] = False


@router.get("/health")
async def files_health():
    try:
        from NEXO_CORE.services.file_classifier_service import clasificar_archivo  # noqa: F401
        return {"status": "ok", "clasificador": "disponible"}
    except Exception as e:
        return {"status": "error", "detalle": str(e)}


@router.post("/clasificar")
async def clasificar(req: ClasificarRequest):
    """
    Clasifica archivos en una carpeta.
    La Torre lo ejecuta, el resultado va al RAG.
    """
    try:
        from NEXO_CORE.services.file_classifier_service import (
            clasificar_directorio,
            auto_ingestar_ingestables,
        )
        ruta = Path(req.ruta)
        if not ruta.exists():
            raise HTTPException(404, f"Ruta no existe: {req.ruta}")

        resultado = clasificar_directorio(str(ruta), recursivo=req.recursivo)

        if req.ingestar_rag:
            ingestado = auto_ingestar_ingestables(str(ruta))
            resultado["ingestado_rag"] = ingestado

        total = len(resultado.get("archivos", [])) if isinstance(resultado, dict) else 0
        return {"ruta": str(ruta), "clasificados": resultado, "total": total}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clasificando {req.ruta}: {e}")
        raise HTTPException(500, str(e))


@router.post("/renombrar")
async def renombrar_clasificados(ruta: str, dry_run: bool = True):
    """
    Renombra archivos según su clasificación.
    dry_run=True solo muestra qué haría sin hacer cambios.
    Torre ejecuta esto localmente.
    """
    try:
        from NEXO_CORE.services.file_classifier_service import clasificar_archivo

        directorio = Path(ruta)
        if not directorio.exists():
            raise HTTPException(404, f"Directorio no existe: {ruta}")

        cambios = []
        for archivo in directorio.rglob("*"):
            if not archivo.is_file():
                continue
            clasificacion = clasificar_archivo(str(archivo))
            if not isinstance(clasificacion, dict) or not clasificacion.get("ok"):
                continue
            tipo = clasificacion.get("tipo", "misc")
            nombre_limpio = re.sub(r"[^a-zA-Z0-9_.\-]", "_", archivo.stem)
            nuevo_nombre = f"{tipo}_{nombre_limpio}{archivo.suffix}"
            nuevo_path = archivo.parent / nuevo_nombre

            cambio = {
                "original": archivo.name,
                "nuevo": nuevo_nombre,
                "tipo": tipo,
                "renombrado": False,
            }
            if not dry_run and nuevo_path != archivo:
                archivo.rename(nuevo_path)
                cambio["renombrado"] = True

            cambios.append(cambio)

        return {"dry_run": dry_run, "cambios": cambios, "total": len(cambios)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
