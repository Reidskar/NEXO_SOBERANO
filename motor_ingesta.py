import os
import sqlite3
import hashlib
import json
import logging
import asyncio
import time
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno antes de importar servicios
load_dotenv()

import google.generativeai as genai

# Importar servicio de vector db
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from backend.services.vector_db import asimilar_documento

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
log = logging.getLogger(__name__)

# Cargar API Key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
modelo = genai.GenerativeModel("gemini-1.5-flash")

# Rutas del Sistema
DB_PATH = os.path.join("NEXO_SOBERANO", "base_sqlite", "boveda.db")
BITACORA_MD = os.path.join("NEXO_SOBERANO", "bitacora", "evolucion.md")

# ---> ¡ATENCIÓN DIRECTOR! <---
CARPETA_ENTRADA = os.path.join(os.path.dirname(__file__), "Carpeta_Prueba")

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
    log.info(f"📓 Bitácora actualizada: {mensaje}")

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
                
            log.info(f"\n👁️ Nuevo archivo detectado: {nombre}")
            log.info("🧠 Solicitando análisis a Gemini...")
            
            try:
                # 1. Análisis con IA (con reintentos)
                max_retries = 3
                archivo_ia = None
                for attempt in range(max_retries):
                    try:
                        archivo_ia = genai.upload_file(ruta)
                        break
                    except Exception as e:
                        if attempt == max_retries - 1: raise
                        log.warning(f"Reintentando upload ({attempt+1}/{max_retries})...")
                        time.sleep(2 ** attempt)

                prompt = 'Eres un analista geopolítico. Resume este documento en 2 líneas, sugiere una categoría (ej: "Rusia", "OTAN", "Economía") y define su nivel de impacto (Alto, Medio, Bajo). Responde estrictamente en JSON: {"resumen": "...", "categoria": "...", "impacto": "..."}'
                
                respuesta = None
                for attempt in range(max_retries):
                    try:
                        respuesta = modelo.generate_content([archivo_ia, prompt])
                        break
                    except Exception as e:
                        if attempt == max_retries - 1: raise
                        log.warning(f"Reintentando generación ({attempt+1}/{max_retries})...")
                        time.sleep(2 ** attempt)

                raw_text = respuesta.text
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0]
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0]
                
                datos_ia = json.loads(raw_text.strip())
                
                # 2. Guardar en SQLite
                cursor.execute("""
                    INSERT INTO evidencia (hash_sha256, nombre_archivo, ruta_local, categoria, resumen_ia, fecha_ingesta, vectorizado) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (h_archivo, nombre, ruta, datos_ia['categoria'], datos_ia['resumen'], datetime.now(), 0))
                
                # 3. Ingesta Vectorial (Supabase)
                log.info(f"📤 Indexando en Supabase Vector...")
                try:
                    asyncio.run(asimilar_documento(
                        contenido=f"{datos_ia['resumen']}\n\n{nombre}",
                        metadata={
                            "archivo": nombre,
                            "categoria": datos_ia['categoria'],
                            "impacto": datos_ia['impacto'],
                            "hash": h_archivo,
                            "fuente": "motor_ingesta_v2"
                        }
                    ))
                    # Marcar como vectorizado solo si salió bien
                    cursor.execute("UPDATE evidencia SET vectorizado=1 WHERE hash_sha256=?", (h_archivo,))
                    log.info("✅ Indexación vectorial exitosa.")
                except Exception as ve:
                    log.error(f"⚠️ Error en indexación vectorial: {ve}")

                conn.commit()
                registrar_bitacora(f"Analizado y clasificado: {nombre} -> {datos_ia['categoria']}")
                
            except Exception as e:
                log.error(f"❌ Error crítico procesando {nombre}: {e}")

    conn.close()
    log.info("\n✅ Ronda de ingesta y análisis completada.")

if __name__ == "__main__":
    if not os.path.exists(CARPETA_ENTRADA):
        log.info(f"⚠️ Error: La carpeta {CARPETA_ENTRADA} no existe. Ajusta la ruta en el código.")
    else:
        procesar_archivos()
