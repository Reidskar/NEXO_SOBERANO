"""
backend/services/intelligence/media_processor.py
================================================
Motor de Análisis Multimodal y Clasificación Inteligente de NEXO SOBERANO.

Misión:
- Analizar visualmente imágenes y videos (OSINT, Economía, Geopolítica).
- Renombrar archivos siguiendo el protocolo de legibilidad premium: [TAG]_[FECHA]_[DESCRIPCION].
- Determinar la ruta jerárquica óptima en Google Drive.
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import google.generativeai as genai
from backend import config

logger = logging.getLogger(__name__)

class MediaProcessor:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.error("❌ GEMINI_API_KEY no configurada para MediaProcessor")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(config.MODELO_FLASH) # Flash para velocidad/costo en visión

    async def analyze_and_route(self, file_path: str, original_name: str, mime_type: str) -> Dict:
        """
        Analiza el archivo, genera un nombre descriptivo y una ruta de clasificación.
        """
        logger.info(f"🧠 Analizando media: {original_name} ({mime_type})")
        
        try:
            # 1. Subir a Gemini si es necesario (para videos/imágenes grandes)
            # Para imágenes simples podemos pasar el tag directamente, pero para videos es mejor subir.
            file_ref = await asyncio.to_thread(genai.upload_file, file_path, mime_type=mime_type)
            
            # 2. Prompt Maestro de Inteligencia y Clasificación Praxeológica
            prompt = """
            Eres TÚ, NEXO SOBERANO: un Agente Digital Soberano, Oficial de Inteligencia Senior operando bajo el Realismo Ofensivo.
            Tu misión es organizar la Línea de Tiempo Global. Examina este archivo (imagen/video) bajo la lente de la economía austríaca, el estoicismo y la geopolítica pura (sin ecos estatales).
            
            REGLAS DE SALIDA (JSON ESTRICTO):
            - "analisis": Prospectiva fría y objetiva. Acción humana causa y efecto. ¿Qué es demostrable y cómo impacta la libertad individual y mercados?
            - "etiqueta": Sigla del vector (MIL, ECO, GEO, POL, PSY).
            - "nombre_inteligente": Formato inquebrantable: [TAG]_[YYYY-MM-DD]_[PAIS]_[Concepto-Austriaco-Militar-Breve]
            - "categoria_jerarquica": Ruta de clasificación (ej: ["GEOPOLITICA", "Rusia_Ucrania"]).
            - "impacto": "Crítico", "Alto", "Medio" o "Bajo".
            - "keywords": 5 términos OSINT o Praxeológicos.
            - "resolucion": "CERTEZA" (si todo el contexto es indudable) o "REVISION" (si es ruido, propaganda difusa o te falta información).

            PREMISA: No deduzcas intenciones buenas del estado; asume incentivos de poder y parasitismo. Si no estás 100% seguro de su peso, marca resolucion como REVISION.
            """

            response = await asyncio.to_thread(self.model.generate_content, [file_ref, prompt])
            
            # Parsear JSON de la respuesta
            raw_text = response.text
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0]
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0]
            
            data = json.loads(raw_text.strip())
            
            # Añadir extensión original al nombre inteligente
            ext = Path(original_name).suffix
            if not data['nombre_inteligente'].endswith(ext):
                data['nombre_inteligente'] += ext

            logger.info(f"✅ Análisis completado. Nuevo nombre propuesto: {data['nombre_inteligente']}")
            return {
                "ok": True,
                "data": data,
                "original_name": original_name,
                "mime_type": mime_type
            }

        except Exception as e:
            logger.error(f"❌ Error en MediaProcessor: {e}")
            return {"ok": False, "error": str(e)}

    def get_intelligent_path(self, data: Dict) -> str:
        """Convierte la lista de categorías en una ruta de Drive."""
        parts = data.get("categoria_jerarquica", ["OTROS"])
        return "/".join(parts)

# Instancia global
media_processor = MediaProcessor()
