"""
NEXO SOBERANO — Drive to Kindle Sync + File Classifier
Descarga libros de Google Drive, los clasifica y los envía al Kindle.
"""
import os, io, json, shutil, logging
from pathlib import Path
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("DRIVE_KINDLE")

TOKEN_PATH   = "backend/auth/token_google_drive.json"
KINDLE_PATH  = Path(os.getenv("KINDLE_PATH", "E:/documents"))
CATALOG_PATH = Path("kindle_sync/catalog.json")

BOOK_EXTENSIONS = {".epub", ".pdf", ".mobi", ".azw3", ".txt", ".fb2"}

# ── Clasificación ──────────────────────────────────────────
CATEGORIAS = {
    "tecnico":     ["python", "code", "programming", "linux", "docker", "api", "software", "data", "ai", "ml"],
    "negocios":    ["business", "startup", "marketing", "finance", "invest", "empresa", "negocio"],
    "ciencia":     ["science", "physics", "biology", "chemistry", "math", "ciencia", "fisica"],
    "filosofia":   ["philosophy", "ethics", "logic", "filosofia", "etica"],
    "historia":    ["history", "war", "civilization", "historia", "guerra"],
    "ficcion":     ["novel", "fiction", "fantasy", "sci-fi", "thriller", "novela"],
    "otros":       []
}

def clasificar_libro(nombre: str) -> str:
    nombre_lower = nombre.lower()
    for categoria, keywords in CATEGORIAS.items():
        if any(kw in nombre_lower for kw in keywords):
            return categoria
    return "otros"

def get_drive_service():
    if not os.path.exists(TOKEN_PATH):
        raise FileNotFoundError(f"Token no encontrado en {TOKEN_PATH}")
    creds = Credentials.from_authorized_user_file(TOKEN_PATH)
    return build("drive", "v3", credentials=creds)

def listar_libros_drive(service) -> list:
    query = "trashed = false"
    results = []
    page_token = None
    while True:
        resp = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, size, modifiedTime, parents, mimeType)",
            pageSize=1000,
            pageToken=page_token
        ).execute()
        files = resp.get("files", [])
        for f in files:
            nombre = f.get("name", "").lower()
            if any(nombre.endswith(ext) for ext in BOOK_EXTENSIONS):
                results.append(f)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return results

def cargar_catalogo() -> dict:
    if CATALOG_PATH.exists():
        try:
            return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        except:
            return {}
    return {}

def guardar_catalogo(catalogo: dict):
    CATALOG_PATH.parent.mkdir(exist_ok=True)
    CATALOG_PATH.write_text(json.dumps(catalogo, indent=2, ensure_ascii=False), encoding="utf-8")

def descargar_libro(service, file_id: str, file_name: str, dest: Path) -> bool:
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        dest.write_bytes(fh.getvalue())
        return True
    except Exception as e:
        logger.error(f"Error descargando {file_name}: {e}")
        return False

def sincronizar():
    try:
        from kindle_sync.dedup_manager import analizar_duplicados, marcar_descargado
    except ImportError:
        try:
            from dedup_manager import analizar_duplicados, marcar_descargado
        except ImportError:
            # Fallback if running from root without package setup properly
            import sys
            sys.path.append(os.path.join(os.getcwd(), 'kindle_sync'))
            from dedup_manager import analizar_duplicados, marcar_descargado

    logger.info("=" * 50)
    logger.info("NEXO DRIVE→KINDLE SYNC con DEDUPLICACIÓN")

    if not KINDLE_PATH.exists():
        logger.error(f"Kindle NO montado en {KINDLE_PATH}")
        return {"ok": False, "error": "Kindle no conectado"}

    try:
        service  = get_drive_service()
    except Exception as e:
        logger.error(f"Error autenticación Drive: {e}")
        return {"ok": False, "error": str(e)}

    catalogo = cargar_catalogo()

    # 1. Obtener lista completa de Drive (1 sola llamada paginada)
    logger.info("Obteniendo lista de Drive (1 llamada API)...")
    todos = listar_libros_drive(service)

    # 2. Deduplicar ANTES de descargar — cero API calls adicionales
    resultado_dedup = analizar_duplicados(todos)
    unicos = resultado_dedup["unicos"]

    # 3. Filtrar los que ya están en catálogo local
    pendientes = [
        f for f in unicos
        if f["id"] not in catalogo and
        not (KINDLE_PATH / f["name"]).exists()
    ]

    logger.info(f"Pendientes de descarga: {len(pendientes)} archivos únicos nuevos")

    stats = {"nuevos": 0, "skip": 0, "error": 0}

    for libro in pendientes:
        nombre   = libro["name"]
        file_id  = libro["id"]
        categoria = clasificar_libro(nombre)
        dest     = KINDLE_PATH / nombre

        logger.info(f"[{categoria.upper()}] {nombre}")
        ok = descargar_libro(service, file_id, nombre, dest)

        if ok:
            catalogo[file_id] = {
                "nombre": nombre, "categoria": categoria,
                "descargado": datetime.now().isoformat(),
                "tamaño_kb": dest.stat().st_size // 1024
            }
            # Guardar catálogo después de CADA descarga
            guardar_catalogo(catalogo)
            marcar_descargado(file_id)
            stats["nuevos"] += 1
        else:
            stats["error"] += 1

    # Reporte final
    logger.info("=" * 50)
    logger.info("SYNC COMPLETO:")
    logger.info(f"  Total Drive:      {len(todos)}")
    logger.info(f"  Duplicados:       {resultado_dedup['stats']['duplicados_saltados']}")
    logger.info(f"  Personales:       {resultado_dedup['stats']['personales_saltados']}")
    logger.info(f"  Ya descargados:   {len(unicos) - len(pendientes)}")
    logger.info(f"  Nuevos hoy:       {stats['nuevos']}")
    logger.info(f"  Errores:          {stats['error']}")
    if len(todos) > 0:
        logger.info(f"  API calls usadas: ~{stats['nuevos'] + 3} (vs {len(todos)} sin dedup)")
    logger.info("=" * 50)

    return stats

if __name__ == "__main__":
    resultado = sincronizar()
