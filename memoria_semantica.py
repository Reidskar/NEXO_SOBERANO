import os
import asyncio
import sqlite3
import logging
from datetime import datetime

# Ajuste temporal para poder importar vector_db
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.vector_db import ensure_table, asimilar_documento, close_pool

# Configurar logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# --- CONFIGURACIÓN ESTRATÉGICA ---
BASE_PATH = "NEXO_SOBERANO"
DB_PATH = os.path.join(BASE_PATH, "base_sqlite", "boveda.db")

async def preparar_esquema_vectorial():
    """Asegura la tabla vectorizados en SQLite y en Supabase."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vectorizados_log (
            hash_sha256 TEXT PRIMARY KEY,
            fecha_vectorizacion TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    
    # Inicializa pgvector
    await ensure_table()

async def asimilar_conocimiento():
    """Toma los resúmenes de Gemini en SQLite y los inyecta en Supabase pgvector."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT e.hash_sha256, e.nombre_archivo, e.categoria, e.resumen_ia, e.ruta_local 
        FROM evidencia e
        LEFT JOIN vectorizados_log v ON e.hash_sha256 = v.hash_sha256
        WHERE e.resumen_ia IS NOT NULL AND v.hash_sha256 IS NULL
    """)
    pendientes = cursor.fetchall()
    
    if not pendientes:
        log.info("☕ La Memoria Semántica está al 100%. No hay datos nuevos para asimilar.")
        conn.close()
        return

    log.info(f"🧠 Asimilando {len(pendientes)} fragmentos de inteligencia en Supabase Vector...")
    
    for row in pendientes:
        hash_id, nombre, cat, resumen, ruta = row
        
        metadata = {
            "fuente": "local", 
            "categoria": cat, 
            "archivo": nombre, 
            "ruta": ruta
        }
        
        exito = await asimilar_documento(hash_id, resumen, metadata)
            
        if exito:
            cursor.execute("INSERT INTO vectorizados_log (hash_sha256, fecha_vectorizacion) VALUES (?, ?)", 
                            (hash_id, datetime.now()))
            
    conn.commit()
    conn.close()
    log.info("🎯 Proceso de asimilación semántica en la nube completado.")

async def main():
    log.info("Iniciando conexión con el lóbulo frontal (Supabase pgvector)...")
    await preparar_esquema_vectorial()
    await asimilar_conocimiento()
    await close_pool()

if __name__ == "__main__":
    # Workaround Windows ProactorEventLoop issues on exit
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main())
