"""
NEXO SOBERANO — Clasificador universal de archivos
Clasifica cualquier archivo por tipo, contenido y relevancia para el RAG.
"""
import os, json, hashlib, mimetypes, logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

CLASIFICACION_MIME = {
    "documento":  ["application/pdf", "application/msword", "text/plain",
                   "application/vnd.openxmlformats-officedocument"],
    "imagen":     ["image/"],
    "video":      ["video/"],
    "audio":      ["audio/"],
    "codigo":     ["text/x-python", "application/javascript", "text/x-c",
                   "application/json", "text/x-yaml"],
    "libro":      ["application/epub", "application/x-mobipocket-ebook"],
    "datos":      ["text/csv", "application/vnd.ms-excel",
                   "application/vnd.openxmlformats-officedocument.spreadsheetml"],
    "comprimido": ["application/zip", "application/x-tar", "application/gzip"],
}

RELEVANCIA_RAG = {
    "documento": "ALTA",
    "libro":     "ALTA",
    "codigo":    "MEDIA",
    "datos":     "MEDIA",
    "audio":     "MEDIA",   # puede transcribirse
    "video":     "MEDIA",   # puede transcribirse
    "imagen":    "BAJA",
    "comprimido":"BAJA",
}

def detectar_tipo(file_path: str) -> str:
    mime, _ = mimetypes.guess_type(file_path)
    if not mime:
        return "desconocido"
    for tipo, mimes in CLASIFICACION_MIME.items():
        if any(mime.startswith(m) for m in mimes):
            return tipo
    return "otro"

def calcular_hash(file_path: str, chunk_size: int = 8192) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()[:16]

def clasificar_archivo(file_path: str) -> dict:
    """Clasifica un archivo individual."""
    path = Path(file_path)
    if not path.exists():
        return {"ok": False, "error": "Archivo no encontrado"}

    tipo     = detectar_tipo(file_path)
    tamaño   = path.stat().st_size
    relevancia = RELEVANCIA_RAG.get(tipo, "BAJA")

    resultado = {
        "ruta":       str(path),
        "nombre":     path.name,
        "extension":  path.suffix.lower(),
        "tipo":       tipo,
        "relevancia_rag": relevancia,
        "tamaño_bytes": tamaño,
        "tamaño_kb":  round(tamaño / 1024, 1),
        "hash":       calcular_hash(file_path),
        "clasificado_en": datetime.now().isoformat(),
        "ingestable": relevancia in ("ALTA", "MEDIA"),
    }
    return resultado

def clasificar_directorio(dir_path: str, recursivo: bool = True) -> dict:
    """Clasifica todos los archivos en un directorio."""
    path = Path(dir_path)
    if not path.exists():
        return {"ok": False, "error": f"Directorio no encontrado: {dir_path}"}

    patron = "**/*" if recursivo else "*"
    archivos = [f for f in path.glob(patron) if f.is_file()]
    
    resultados = []
    stats = {}
    ingestables = []

    for archivo in archivos:
        info = clasificar_archivo(str(archivo))
        resultados.append(info)
        
        tipo = info.get("tipo", "desconocido")
        stats[tipo] = stats.get(tipo, 0) + 1
        
        if info.get("ingestable"):
            ingestables.append(str(archivo))

    return {
        "ok": True,
        "directorio": str(path),
        "total_archivos": len(archivos),
        "por_tipo": stats,
        "ingestables": ingestables,
        "archivos": resultados
    }

def auto_ingestar_ingestables(dir_path: str) -> dict:
    """
    Clasifica un directorio y envía automáticamente
    los archivos ingestables al RAG pipeline.
    """
    clasificacion = clasificar_directorio(dir_path)
    if not clasificacion["ok"]:
        return clasificacion

    ingestados = []
    errores    = []

    for ruta in clasificacion["ingestables"]:
        ext = Path(ruta).suffix.lower()
        
        # Audio/video → media_ingestion_service
        if ext in {".mp3", ".mp4", ".wav", ".mkv", ".avi", ".mov", ".ogg", ".m4a"}:
            try:
                # Intentar importar servicios de ingestión si existen
                from NEXO_CORE.services.media_ingestion_service import ingestar_media
                r = ingestar_media(ruta)
                if r["ok"]:
                    ingestados.append(ruta)
                else:
                    errores.append({"ruta": ruta, "error": r["error"]})
            except Exception as e:
                errores.append({"ruta": ruta, "error": str(e)})

        # Texto/PDF/docs → rag_service directo
        elif ext in {".txt", ".md", ".pdf", ".epub"}:
            try:
                from NEXO_CORE.services.rag_service import indexar_documento
                if ext == ".txt" or ext == ".md":
                    texto = Path(ruta).read_text(errors="ignore")
                    indexar_documento(texto, {"fuente": ruta, "tipo": "texto"})
                    ingestados.append(ruta)
                # PDF/epub requieren parser — agregar en Sprint 0.8
            except Exception as e:
                errores.append({"ruta": ruta, "error": str(e)})

    return {
        "ok": True,
        "ingestados": len(ingestados),
        "errores": len(errores),
        "detalle_errores": errores,
        "archivos_ingestados": ingestados
    }
