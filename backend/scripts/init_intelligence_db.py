"""
backend/scripts/init_intelligence_db.py
======================================
Inicializa o actualiza la base de datos de inteligencia (boveda.db).
"""

import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_DIR = os.path.join("NEXO_SOBERANO", "base_sqlite")
DB_PATH = os.path.join(DB_DIR, "boveda.db")

def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Crear tabla de evidencia si no existe
    logger.info("🛠️ Configurando tabla 'evidencia'...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evidencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash_sha256 TEXT UNIQUE,
            nombre_archivo TEXT,
            ruta_local TEXT,
            categoria TEXT,
            jerarquia TEXT,
            resumen_ia TEXT,
            impacto TEXT,
            publicado_en_redes INTEGER DEFAULT 0,
            fecha_ingesta DATETIME DEFAULT CURRENT_TIMESTAMP,
            vectorizado INTEGER DEFAULT 0
        )
    """)
    
    # Verificar si necesitamos añadir columnas nuevas a una tabla existente
    cursor.execute("PRAGMA table_info(evidencia)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "jerarquia" not in columns:
        logger.info("➕ Añadiendo columna 'jerarquia'...")
        cursor.execute("ALTER TABLE evidencia ADD COLUMN jerarquia TEXT")
        
    if "impacto" not in columns:
        logger.info("➕ Añadiendo columna 'impacto'...")
        cursor.execute("ALTER TABLE evidencia ADD COLUMN impacto TEXT")

    if "publicado_en_redes" not in columns:
        logger.info("➕ Añadiendo columna 'publicado_en_redes'...")
        cursor.execute("ALTER TABLE evidencia ADD COLUMN publicado_en_redes INTEGER DEFAULT 0")

    conn.commit()
    conn.close()
    logger.info("✅ Base de datos de inteligencia lista en: " + DB_PATH)

if __name__ == "__main__":
    init_db()
