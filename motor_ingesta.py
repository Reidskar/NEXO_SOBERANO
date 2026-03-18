import os
import sqlite3
import hashlib
import json
from utils.ai_core import get_logger, get_gemini_model
from dotenv import load_dotenv
from datetime import datetime

# Configurar logging
logger = get_logger("motor_ingesta")

# Cargar API Key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY") or ""
model = get_gemini_model(api_key)

# Rutas del Sistema
DB_PATH = os.path.join("NEXO_SOBERANO", "base_sqlite", "boveda.db")
BITACORA_MD = os.path.join("NEXO_SOBERANO", "bitacora", "evolucion.md")

# ---> ¡ATENCIÓN DIRECTOR! CAMBIA ESTA RUTA POR TU CARPETA REAL <---
CARPETA_ENTRADA = r"C:\Users\Admin\Desktop\NEXO_SOBERANO\Carpeta_Prueba" # Pon aquí la ruta de Entrada_Segura

def calcular_hash(ruta):
    sha256 = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            sha256.update(bloque)
    return sha256.hexdigest()

def registrar_bitacora(mensaje):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(BITACORA_MD, "a", encoding="utf-8") as f:
        f.write(f"\n- {fecha} | OPERACIÓN: {mensaje}")
    logger.info(f"📓 Bitácora actualizada: {mensaje}")

def procesar_archivos():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for raiz, _, archivos in os.walk(CARPETA_ENTRADA):
        for nombre in archivos:
            ruta = os.path.join(raiz, nombre)
            if nombre.startswith("~$") or os.path.getsize(ruta) == 0: continue
            
            h_archivo = calcular_hash(ruta)
            
            # Verificar si ya existe en la bóveda
            cursor.execute("SELECT id FROM evidencia WHERE hash_sha256 = ?", (h_archivo,))
            if cursor.fetchone():
                continue # Archivo duplicado, lo saltamos
                
            logger.info(f"\n👁️ Nuevo archivo detectado: {nombre}")
            logger.info("🧠 Solicitando análisis a Gemini...")
            
            try:
                prompt = 'Eres un analista geopolítico. Resume este documento en 2 líneas, sugiere una categoría (ej: "Rusia", "OTAN", "Economía") y define su nivel de impacto (Alto, Medio, Bajo). Responde estrictamente en JSON: {"resumen": "...", "categoria": "...", "impacto": "..."}'
                with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
                    contenido = f.read()
                respuesta = model.generate_content([contenido, prompt])
                datos_ia = json.loads(respuesta.text.replace('```json', '').replace('```', ''))
                cursor.execute("""
                    INSERT INTO evidencia (hash_sha256, nombre_archivo, ruta_local, categoria, resumen_ia, fecha_ingesta) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (h_archivo, nombre, ruta, datos_ia['categoria'], datos_ia['resumen'], datetime.now()))
                conn.commit()
                registrar_bitacora(f"Analizado y clasificado: {nombre} -> {datos_ia['categoria']}")
            except Exception as e:
                logger.info(f"❌ Error procesando {nombre}: {e}")

    conn.close()
    logger.info("\n✅ Ronda de ingesta y análisis completada.")

if __name__ == "__main__":
    if not os.path.exists(CARPETA_ENTRADA):
        logger.info(f"⚠️ Error: La carpeta {CARPETA_ENTRADA} no existe. Ajusta la ruta en el código.")
    else:
        procesar_archivos()
