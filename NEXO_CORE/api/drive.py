# ============================================================
# NEXO SOBERANO — Drive API Endpoints
# © 2026 elanarcocapital.com
# ============================================================
from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("NEXO.api.drive")
router = APIRouter(prefix="/api/drive", tags=["drive"])


class DriveQueryRequest(BaseModel):
    query: str
    folder_id: Optional[str] = "10pn6Zo5_SUTf2jlWaH98rs0wtF3W0Trx"
    max_resultados: Optional[int] = 5
    leer_contenido: Optional[bool] = False


class DriveContextRequest(BaseModel):
    mensaje_usuario: str
    folder_id: Optional[str] = "10pn6Zo5_SUTf2jlWaH98rs0wtF3W0Trx"


@router.get("/health")
async def drive_health():
    try:
        from NEXO_CORE.services.drive_service import drive_service
        archivos = await drive_service.listar_archivos_carpeta(max_results=1)
        return {
            "status": "ok" if archivos is not None else "sin_credenciales",
            "drive_conectado": archivos is not None
        }
    except Exception as e:
        return {"status": "error", "detalle": str(e)}


@router.post("/buscar")
async def buscar_en_drive(req: DriveQueryRequest):
    """Busca archivos en Drive y opcionalmente lee su contenido."""
    try:
        from NEXO_CORE.services.drive_service import drive_service
        archivos = await drive_service.buscar_en_drive(
            query=req.query,
            folder_id=req.folder_id
        )
        if not archivos:
            return {"resultados": [], "mensaje": "No se encontraron archivos"}

        resultados = []
        for archivo in archivos[:req.max_resultados]:
            item = {
                "nombre": archivo.get("name"),
                "tipo": archivo.get("mimeType"),
                "modificado": archivo.get("modifiedTime"),
                "id": archivo.get("id")
            }
            if req.leer_contenido:
                item["contenido"] = await drive_service.leer_archivo_texto(archivo["id"])
            resultados.append(item)

        return {"resultados": resultados, "total": len(resultados)}
    except Exception as e:
        logger.error(f"Error en /api/drive/buscar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/contexto")
async def obtener_contexto_drive(req: DriveContextRequest):
    """
    Dado un mensaje del usuario, busca contexto relevante en Drive
    y devuelve un resumen para que el bot pueda responder con conocimiento.
    """
    try:
        from NEXO_CORE.services.drive_service import drive_service

        archivos = await drive_service.buscar_en_drive(
            query=req.mensaje_usuario,
            folder_id=req.folder_id
        )

        if not archivos:
            return {
                "contexto_encontrado": False,
                "archivos": [],
                "resumen": ""
            }

        contexto_textos = []
        archivos_usados = []
        for archivo in archivos[:3]:
            contenido = await drive_service.leer_archivo_texto(archivo["id"])
            if contenido and len(contenido) > 50:
                contexto_textos.append(
                    f"[{archivo['name']}]:\n{contenido[:2000]}"
                )
                archivos_usados.append(archivo["name"])

        return {
            "contexto_encontrado": True,
            "archivos": archivos_usados,
            "contexto_raw": "\n\n---\n\n".join(contexto_textos)
        }
    except Exception as e:
        logger.error(f"Error en /api/drive/contexto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/listar")
async def listar_geopolitica(max_resultados: int = 20):
    """Lista archivos de la carpeta Geopolítica."""
    try:
        from NEXO_CORE.services.drive_service import drive_service
        archivos = await drive_service.listar_archivos_carpeta(
            max_results=max_resultados
        )
        return {
            "carpeta": "Geopolítica",
            "folder_id": "10pn6Zo5_SUTf2jlWaH98rs0wtF3W0Trx",
            "archivos": archivos,
            "total": len(archivos)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
