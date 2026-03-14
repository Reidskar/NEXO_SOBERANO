"""
NEXO SOBERANO — Deduplication Manager
Detecta duplicados en Google Drive ANTES de descargar, ahorrando API calls.
Estrategia: comparar por nombre normalizado + tamaño, no por file_id.
"""
import re
import json
import logging
from pathlib import Path
from typing import Optional
from difflib import SequenceMatcher

logger = logging.getLogger("DEDUP")

DEDUP_DB_PATH = Path("kindle_sync/dedup_db.json")

# ── Normalización ──────────────────────────────────────────────────────────
def normalizar_nombre(nombre: str) -> str:
    """
    Convierte nombres de archivos a forma canónica para comparar.
    """
    n = Path(nombre).stem.lower()
    
    # Eliminar timestamps: _2025-06-21_12-09-34, _2025-07-10_12-52-44
    n = re.sub(r'_?\d{4}-\d{2}-\d{2}[_\s]\d{2}-\d{2}-\d{2}', '', n)
    n = re.sub(r'_?\d{4}-\d{2}-\d{2}', '', n)
    
    # Eliminar sufijos de copia
    n = re.sub(r'_copia\b', '', n)
    n = re.sub(r'\s*\(copia\)', '', n)
    n = re.sub(r'_copia$', '', n)
    
    # Eliminar identificadores tipo C06932208
    n = re.sub(r'\([A-Z]\d{8,}\)', '', n)
    
    # Reemplazar separadores por espacios
    n = re.sub(r'[_\-]+', ' ', n)
    
    # Eliminar caracteres especiales
    n = re.sub(r'[^\w\s]', '', n)
    
    # Colapsar espacios
    n = ' '.join(n.split())
    
    return n.strip()

def similitud(a: str, b: str) -> float:
    """Ratio de similitud entre dos strings normalizados (0.0 a 1.0)."""
    return SequenceMatcher(None, a, b).ratio()

# ── Base de datos de deduplicación ─────────────────────────────────────────
def cargar_db() -> dict:
    if DEDUP_DB_PATH.exists():
        try:
            return json.loads(DEDUP_DB_PATH.read_text(encoding='utf-8'))
        except:
            pass
    return {"canonicos": {}, "file_ids_procesados": [], "stats": {
        "total_drive": 0, "unicos": 0, "duplicados_saltados": 0,
        "personales_saltados": 0, "api_calls_ahorradas": 0
    }}

def guardar_db(db: dict):
    DEDUP_DB_PATH.parent.mkdir(exist_ok=True)
    DEDUP_DB_PATH.write_text(
        json.dumps(db, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )

# ── Filtros de archivos personales ─────────────────────────────────────────
PATRONES_PERSONAL = [
    r'^\d{3}-\d{5}',       # documentos judiciales 104-xxxxx
    r'certificado',
    r'fonasa',
    r'rptcertafi',
    r'^cv\s',
    r'^camilo\s',
    r'informe-monetario',
    r'^informe_20\d\d',
    r'7bc2c80c',
    r'afiliaci',
    r'_copia_20\d\d-\d\d-\d\d_\d\d-\d\d',  # patrón copia automática con hora
]

def es_documento_personal(nombre: str) -> bool:
    nombre_lower = nombre.lower()
    return any(re.search(p, nombre_lower) for p in PATRONES_PERSONAL)

# ── Motor principal de deduplicación ───────────────────────────────────────
UMBRAL_SIMILITUD = 0.85  # 85% similitud = duplicado

def analizar_duplicados(archivos_drive: list) -> dict:
    db = cargar_db()
    db["stats"]["total_drive"] = len(archivos_drive)
    
    canonicos: dict = {}       # nombre_canonico → mejor archivo
    personales: list = []
    duplicados: list = []
    unicos: list = []

    for archivo in archivos_drive:
        nombre   = archivo.get("name", "")
        file_id  = archivo.get("id", "")
        # Asegurarse de que el tamaño sea un entero
        try:
            tamaño = int(archivo.get("size", 0) or 0)
        except:
            tamaño = 0
            
        mod_time = archivo.get("modifiedTime", "")

        # 1. Saltar si ya fue procesado en sesión anterior
        if file_id in db.get("file_ids_procesados", []):
            db["stats"]["api_calls_ahorradas"] += 1
            continue

        # 2. Filtrar documentos personales
        if es_documento_personal(nombre):
            personales.append({"id": file_id, "nombre": nombre})
            db["stats"]["personales_saltados"] += 1
            continue

        # 3. Normalizar para comparar
        canon = normalizar_nombre(nombre)
        if not canon or len(canon) < 5:
            continue

        # 4. Buscar duplicado exacto o similar
        es_duplicado = False
        for canon_existente, info_existente in canonicos.items():
            sim = similitud(canon, canon_existente)
            if sim >= UMBRAL_SIMILITUD:
                # Duplicado encontrado — conservar el más grande (más completo)
                if tamaño > info_existente["tamaño"]:
                    logger.debug(
                        f"[REEMPLAZAR] '{nombre}' ({tamaño//1024}KB) "
                        f"> '{info_existente['nombre']}' ({info_existente['tamaño']//1024}KB)"
                    )
                    canonicos[canon_existente] = {
                        "id": file_id, "nombre": nombre,
                        "tamaño": tamaño, "mod_time": mod_time,
                        "canon": canon
                    }
                else:
                    logger.debug(
                        f"[DUPLICADO] '{nombre}' ≈ '{info_existente['nombre']}' "
                        f"(sim={sim:.0%})"
                    )
                duplicados.append({
                    "nombre": nombre,
                    "similar_a": info_existente["nombre"],
                    "similitud": round(sim, 3)
                })
                db["stats"]["duplicados_saltados"] += 1
                es_duplicado = True
                break

        if not es_duplicado:
            canonicos[canon] = {
                "id": file_id, "nombre": nombre,
                "tamaño": tamaño, "mod_time": mod_time,
                "canon": canon
            }

    # Construir lista final de únicos a descargar
    for canon, info in canonicos.items():
        unicos.append(info)

    db["stats"]["unicos"] = len(unicos)
    db["canonicos"] = canonicos
    guardar_db(db)

    # Reporte
    total = len(archivos_drive)
    logger.info("=" * 50)
    logger.info(f"ANÁLISIS DE DEDUPLICACIÓN:")
    logger.info(f"  Total en Drive:        {total}")
    logger.info(f"  Documentos personales: {len(personales)} → SALTADOS")
    logger.info(f"  Duplicados detectados: {len(duplicados)} → SALTADOS")
    logger.info(f"  Únicos a descargar:    {len(unicos)}")
    if total > 0:
        logger.info(f"  API calls ahorradas:   {total - len(unicos)}")
        logger.info(f"  Ahorro:                {((total - len(unicos)) / total * 100):.1f}%")
    logger.info("=" * 50)

    return {
        "unicos": unicos,
        "duplicados": duplicados,
        "personales": personales,
        "stats": db["stats"]
    }

def marcar_descargado(file_id: str):
    db = cargar_db()
    if file_id not in db["file_ids_procesados"]:
        db["file_ids_procesados"].append(file_id)
    guardar_db(db)

def reporte_duplicados(top_n: int = 20) -> str:
    db = cargar_db()
    lines = ["\n=== TOP DUPLICADOS DETECTADOS ==="]
    for canon, info in list(db.get("canonicos", {}).items())[:top_n]:
        lines.append(f"  [{info['tamaño']//1024}KB] {info['nombre']}")
    return "\n".join(lines)
