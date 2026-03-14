"""
backend/services/intelligence/autonomous_agent.py
================================================
Agente Autónomo de Crecimiento y Difusión Comunitaria.

Misión:
- Monitorear hallazgos de impacto "Alto" en la bóveda de inteligencia.
- Redactar hilos de X (Twitter) y alertas de Discord.
- Mantener la presencia pública de NEXO SOBERANO con datos frescos.
"""

import os
import logging
import sqlite3
import asyncio
from typing import List, Dict, Optional

from google import genai
from backend import config
from backend.services.x_publisher import post_to_x

logger = logging.getLogger(__name__)

class AutonomousCommunityAgent:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(config.MODELO_FLASH) # Flash para redacción rápida

    async def review_and_publish_highlight(self) -> Dict:
        """Busca el hallazgo más reciente de alto impacto y genera un post en X."""
        try:
            # 1. Buscar hallazgo de impacto 'Alto' no publicado aún (pendiente flag en DB)
            conn = sqlite3.connect("boveda.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, nombre_archivo, categoria, resumen_ia 
                FROM evidencia 
                WHERE categoria IN ('MIL', 'GEO', 'ECO')
                ORDER BY fecha_ingesta DESC LIMIT 1
            """)
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return {"ok": False, "reason": "No hay nuevos hallazgos relevantes."}

            # 2. Generar Copy para X
            prompt = f"""
            Eres NEXO SOBERANO, una IA de Inteligencia Digital. 
            Has detectado el siguiente evento:
            [{row['categoria']}] {row['resumen_ia']}

            Tarea: Escribe un post para X (Twitter) que sea impactante, informativo y mantenga un tono de 'Oficial de Inteligencia'.
            - Usa máximo 240 caracteres.
            - Incluye hashtags: #NexoSoberano #Inteligencia #Geopolitica.
            - No uses emojis excesivos.
            - Sé directo.
            """

            response = await asyncio.to_thread(self.model.generate_content, prompt)
            tweet_text = response.text.strip()

            # 3. Publicar (Opcional: En un entorno productivo esto requeriría aprobación)
            # Por ahora, simulamos o permitimos si X_API_KEY está presente
            if os.getenv("X_API_KEY"):
                log_pub = post_to_x(tweet_text)
                logger.info(f"🚀 Post publicado en X: {log_pub.get('url')}")
                return {"ok": True, "type": "x_post", "url": log_pub.get("url"), "text": tweet_text}
            else:
                logger.info(f"📢 [SIMULACIÓN] Post generado para X: {tweet_text}")
                return {"ok": True, "type": "simulation", "text": tweet_text}

        except Exception as e:
            logger.error(f"Error en AutonomousCommunityAgent: {e}")
            return {"ok": False, "error": str(e)}

# Instancia global
community_agent = AutonomousCommunityAgent()
