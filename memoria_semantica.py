import os
import sqlite3
import chromadb
from chromadb.utils import embedding_functions

# --- CONFIGURACIÓN ESTRATÉGICA ---
BASE_PATH = "NEXO_SOBERANO"
DB_PATH = os.path.join(BASE_PATH, "base_sqlite", "boveda.db")
CHROMA_PATH = os.path.join(BASE_PATH, "memoria_vectorial")

log.info("Iniciando conexión con el lóbulo frontal (ChromaDB)...")

# Inicializamos ChromaDB en tu disco local
cliente_chroma = chromadb.PersistentClient(path=CHROMA_PATH)

# Usamos un modelo de embeddings ligero y potente que corre en tu PC gratis
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2" 
)

# Creamos o cargamos la colección de conocimiento
coleccion = cliente_chroma.get_or_create_collection(
    name="inteligencia_geopolitica", 
    embedding_function=emb_fn
)

def preparar_esquema_vectorial():
    """Crea una tabla en SQLite para recordar qué archivos ya se convirtieron en vectores."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vectorizados_log (
            hash_sha256 TEXT PRIMARY KEY,
            fecha_vectorizacion TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def asimilar_conocimiento():
    """Toma los resúmenes de Gemini en SQLite y los convierte en memoria matemática."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Buscamos archivos que Gemini ya resumió, pero que ChromaDB aún no ha vectorizado
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

    log.info(f"🧠 Asimilando {len(pendientes)} fragmentos de inteligencia en la red neuronal...")
    
    for row in pendientes:
        hash_id, nombre, cat, resumen, ruta = row
        
        try:
            # Inyección a la memoria vectorial con metadatos para la futura Web
            coleccion.add(
                documents=[resumen],
                metadatas=[{"fuente": "local", "categoria": cat, "archivo": nombre, "ruta": ruta}],
                ids=[hash_id]
            )
            
            # Marcamos en SQLite que ya lo asimilamos
            from datetime import datetime
            cursor.execute("INSERT INTO vectorizados_log (hash_sha256, fecha_vectorizacion) VALUES (?, ?)", 
                           (hash_id, datetime.now()))
            log.info(f"✅ Conocimiento asimilado: {nombre}")
            
        except Exception as e:
            log.info(f"❌ Error vectorizando {nombre}: {e}")
            
    conn.commit()
    conn.close()
    log.info("🎯 Proceso de asimilación semántica completado.")

if __name__ == "__main__":
    preparar_esquema_vectorial()
    asimilar_conocimiento()
