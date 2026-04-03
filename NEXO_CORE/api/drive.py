# ============================================================
# NEXO SOBERANO — Drive API Endpoints
# © 2026 elanarcocapital.com
# ============================================================
from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
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
    usar_rag: Optional[bool] = True   # True: semántico Qdrant | False: keyword Drive API


class IngestarRequest(BaseModel):
    folder_id: Optional[str] = "10pn6Zo5_SUTf2jlWaH98rs0wtF3W0Trx"


# ════════════════════════════════════════════════════════════════════
# HEALTH
# ════════════════════════════════════════════════════════════════════

@router.get("/health")
async def drive_health():
    """Estado completo: Drive service + RAG Qdrant."""
    from NEXO_CORE.services.drive_service import drive_service
    from NEXO_CORE.services.drive_rag_ingestion import stats_coleccion

    drive_ok = False
    try:
        archivos = await drive_service.listar_archivos_carpeta(max_results=1)
        drive_ok = bool(archivos)
    except Exception as e:
        logger.warning(f"Drive health check: {e}")

    rag_stats = await stats_coleccion()
    vectores = rag_stats.get("total_vectores", 0) or 0

    return {
        "drive_conectado": drive_ok,
        "rag_qdrant": rag_stats,
        "modo_activo": "rag_semantico" if rag_stats.get("disponible") and vectores > 0 else "keyword_drive"
    }


# ════════════════════════════════════════════════════════════════════
# LISTAR / BUSCAR (Drive API directo)
# ════════════════════════════════════════════════════════════════════

@router.get("/listar")
async def listar_geopolitica(max_resultados: int = 20):
    """Lista archivos de la carpeta Geopolítica."""
    try:
        from NEXO_CORE.services.drive_service import drive_service
        archivos = await drive_service.listar_archivos_carpeta(max_results=max_resultados)
        return {
            "carpeta": "Geopolítica",
            "folder_id": "10pn6Zo5_SUTf2jlWaH98rs0wtF3W0Trx",
            "archivos": archivos,
            "total": len(archivos)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/buscar")
async def buscar_en_drive(req: DriveQueryRequest):
    """Busca archivos en Drive por keyword y opcionalmente lee su contenido."""
    try:
        from NEXO_CORE.services.drive_service import drive_service
        archivos = await drive_service.buscar_en_drive(query=req.query, folder_id=req.folder_id)
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


# ════════════════════════════════════════════════════════════════════
# CONTEXTO — Endpoint principal del Discord bot
# ════════════════════════════════════════════════════════════════════

@router.post("/contexto")
async def obtener_contexto_drive(req: DriveContextRequest):
    """
    Dado el mensaje del usuario, devuelve contexto relevante de Drive.

    Modo RAG (Qdrant): búsqueda semántica por embeddings → mejor calidad.
    Modo keyword (fallback): fullText Drive API → siempre disponible.

    El Discord bot (/drive y /geopolitica) consume este endpoint.
    """
    # ── Intento 1: RAG semántico (Qdrant indexado)
    if req.usar_rag:
        try:
            from NEXO_CORE.services.drive_rag_ingestion import buscar_semantico, stats_coleccion
            stats = await stats_coleccion()
            vectores = stats.get("total_vectores", 0) or 0
            if stats.get("disponible") and vectores > 0:
                resultados = await buscar_semantico(req.mensaje_usuario, top_k=4)
                if resultados:
                    contexto_textos = [
                        f"[{r['nombre']} — relevancia {r['score']}]:\n{r['texto']}"
                        for r in resultados
                    ]
                    archivos_usados = list({r["nombre"] for r in resultados})
                    return {
                        "contexto_encontrado": True,
                        "modo": "rag_semantico",
                        "archivos": archivos_usados,
                        "contexto_raw": "\n\n---\n\n".join(contexto_textos),
                        "scores": [r["score"] for r in resultados]
                    }
        except Exception as e:
            logger.warning(f"RAG no disponible, fallback keyword: {e}")

    # ── Intento 2: keyword Drive API (siempre disponible)
    try:
        from NEXO_CORE.services.drive_service import drive_service
        archivos = await drive_service.buscar_en_drive(
            query=req.mensaje_usuario,
            folder_id=req.folder_id
        )
        if not archivos:
            return {"contexto_encontrado": False, "modo": "keyword_drive", "archivos": [], "contexto_raw": ""}

        contexto_textos = []
        archivos_usados = []
        for archivo in archivos[:3]:
            contenido = await drive_service.leer_archivo_texto(archivo["id"])
            if contenido and len(contenido) > 50:
                contexto_textos.append(f"[{archivo['name']}]:\n{contenido[:2000]}")
                archivos_usados.append(archivo["name"])

        return {
            "contexto_encontrado": True,
            "modo": "keyword_drive",
            "archivos": archivos_usados,
            "contexto_raw": "\n\n---\n\n".join(contexto_textos)
        }
    except Exception as e:
        logger.error(f"Error en /api/drive/contexto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════
# INDEXAR Drive → Qdrant
# ════════════════════════════════════════════════════════════════════

@router.post("/indexar")
async def indexar_drive(req: IngestarRequest, background_tasks: BackgroundTasks):
    """
    Dispara ingesta Drive → Qdrant en background.
    Tarda 1-5 min según cantidad de documentos.
    Usa /api/drive/health para ver progreso.
    """
    from NEXO_CORE.services.drive_rag_ingestion import ingestar_carpeta

    async def _run():
        try:
            resultado = await ingestar_carpeta(req.folder_id)
            logger.info(f"Ingesta Drive completada: {resultado}")
        except Exception as e:
            logger.error(f"Error ingesta Drive background: {e}")

    background_tasks.add_task(_run)
    return {
        "status": "indexando",
        "folder_id": req.folder_id,
        "mensaje": "Ingesta iniciada. Consulta GET /api/drive/health para ver el progreso."
    }


@router.post("/indexar/sync")
async def indexar_drive_sync(req: IngestarRequest):
    """Ingesta síncrona (espera resultado). Para pruebas o carpetas pequeñas."""
    try:
        from NEXO_CORE.services.drive_rag_ingestion import ingestar_carpeta
        resultado = await ingestar_carpeta(req.folder_id)
        return {"status": "completado", **resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════
# RAG STATS + BÚSQUEDA DIRECTA
# ════════════════════════════════════════════════════════════════════

@router.get("/rag/stats")
async def rag_stats():
    """Estado de la colección semántica en Qdrant."""
    from NEXO_CORE.services.drive_rag_ingestion import stats_coleccion
    return await stats_coleccion()


@router.post("/rag/buscar")
async def rag_buscar(req: DriveQueryRequest):
    """Búsqueda semántica directa en Qdrant (sin Drive API)."""
    try:
        from NEXO_CORE.services.drive_rag_ingestion import buscar_semantico
        resultados = await buscar_semantico(req.query, top_k=req.max_resultados)
        return {"resultados": resultados, "total": len(resultados), "modo": "rag_semantico"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ════════════════════════════════════════════════════════════════════
# OSINT VISION & BI-DIRECTIONAL SYNC
# ════════════════════════════════════════════════════════════════════

from fastapi import UploadFile, File
import tempfile
import aiofiles
import os
import datetime

@router.post("/osint-ingest")
async def ingest_osint_media(file: UploadFile = File(...)):
    """
    Recibe una imagen o video, lo pasa por el Pipeline Visión AI (Gemini + Whisper),
    extrae la inteligencia táctica, deduce el país y guarda todo en Drive/Geopolítica/[País].
    """
    from NEXO_CORE.services.osint_vision_service import osint_vision
    from NEXO_CORE.services.drive_service import drive_service

    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo no proporcionado")

    temp_path = None
    try:
        # 1. Guardar archivo temporal localmente
        ext = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            temp_path = tmp.name
        
        async with aiofiles.open(temp_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)

        # 2. Pipeline de Visión AI (reconocimiento + transcripción)
        intel = osint_vision.analyze_media(temp_path)
        pais = intel.get("pais", "Desconocido")
        analisis = intel.get("analisis", "Análisis fallido.")
        tags = intel.get("tags", [])
        transcripcion = intel.get("transcripcion", "")

        # 3. Preparar Google Drive (Crear carpeta por país si no existe)
        folder_id = await drive_service.obtener_o_crear_carpeta_pais(pais)

        # 4. Construir Reporte OSINT
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        reporte_str = f"=== REPORTE OSINT NEXO ===\n"
        reporte_str += f"Fecha: {fecha}\n"
        reporte_str += f"País/Zona: {pais}\n"
        reporte_str += f"Tags: {', '.join(tags)}\n"
        reporte_str += "-"*30 + "\n"
        reporte_str += f"ANÁLISIS TÁCTICO:\n{analisis}\n\n"
        
        if transcripcion:
            reporte_str += f"TRANSCRIPCIÓN AUDIO:\n{transcripcion}\n"

        # 5. Subir a Drive: El archivo Media original + Reporte texto
        filename_base = os.path.splitext(file.filename)[0]
        
        # Subir original
        res_media = await drive_service.subir_archivo(
            file_path=temp_path,
            filename=file.filename,
            mime_type=file.content_type,
            folder_id=folder_id
        )

        # Subir texto reporte intel
        res_texto = await drive_service.subir_archivo(
            file_bytes=reporte_str.encode('utf-8'),
            filename=f"[OSINT] {filename_base}.txt",
            mime_type="text/plain",
            folder_id=folder_id
        )

        return {
            "status": "completado",
            "pais_detectado": pais,
            "inteligencia": intel,
            "drive": {
                "carpeta_id": folder_id,
                "media_url": res_media.get("webViewLink"),
                "reporte_url": res_texto.get("webViewLink")
            }
        }

    except Exception as e:
        logger.error(f"Error en OSINT Media Ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Fallo en pipeline OSINT: {e}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
