# backend/routes/files.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
import os
import json
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/files", tags=["files"])

class ClasificarRequest(BaseModel):
    ruta: str
    recursivo: Optional[bool] = True
    auto_ingestar: Optional[bool] = False

@router.post("/clasificar")
async def clasificar(request: ClasificarRequest):
    try:
        from NEXO_CORE.services.file_classifier_service import (
            clasificar_archivo, clasificar_directorio, auto_ingestar_ingestables
        )
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Error cargando clasificador: {e}")
    
    if not os.path.exists(request.ruta):
        raise HTTPException(status_code=404, detail=f"Ruta no encontrada: {request.ruta}")
    
    if os.path.isfile(request.ruta):
        return clasificar_archivo(request.ruta)
    
    resultado = clasificar_directorio(request.ruta, request.recursivo)
    
    if request.auto_ingestar:
        ingesta = auto_ingestar_ingestables(request.ruta)
        resultado["ingesta"] = ingesta
    
    return resultado

@router.get("/kindle/catalog")
async def kindle_catalog():
    catalog_path = Path("kindle_sync/catalog.json")
    if not catalog_path.exists():
        return {"libros": [], "total": 0}
    try:
        catalogo = json.loads(catalog_path.read_text(encoding="utf-8"))
        return {
            "libros": list(catalogo.values()),
            "total": len(catalogo),
            "por_categoria": {} # Se puede expandir si es necesario
        }
    except Exception as e:
        logger.error(f"Error leyendo catalogo: {e}")
        return {"libros": [], "total": 0, "error": str(e)}

@router.post("/notebooklm/export")
async def exportar_para_notebooklm():
    """Genera el export del código para subir a NotebookLM."""
    try:
        from NEXO_CORE.services.notebooklm_sync_service import exportar_repo
        resultado = exportar_repo()
        return {
            "ok": True,
            "mensaje": f"Export generado: {resultado['archivos']} archivos, {resultado['tamaño_kb']}KB",
            "instruccion": "Sube nexo_soberano_para_notebooklm.txt a https://notebooklm.google.com/",
            **resultado
        }
    except Exception as e:
        logger.error(f"Error en exportación NotebookLM: {e}")
        raise HTTPException(status_code=500, detail=str(e))
