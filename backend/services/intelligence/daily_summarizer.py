"""
backend/services/intelligence/daily_summarizer.py
=================================================
Agente de Reflexión y Generación de Reportes Diarios (The Magazine).

Misión:
- Recopilar toda la inteligencia procesada en las últimas 24 horas.
- Generar un resumen ejecutivo con tono geopolítico profesional.
- Formatear el reporte en Markdown optimizado para lectura rápida.
"""

import os
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict

from google import genai
from backend import config

logger = logging.getLogger(__name__)

class DailySummarizer:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.db_path = "boveda.db"
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(config.MODELO_PRO) # Pro para síntesis de alta calidad

    def get_last_24h_intelligence(self) -> List[Dict]:
        """Obtiene las entradas de inteligencia de las últimas 24 horas."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            hace_24h = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                SELECT nombre_archivo, categoria, resumen_ia, fecha_ingesta 
                FROM evidencia 
                WHERE fecha_ingesta >= ?
                ORDER BY fecha_ingesta DESC
            """, (hace_24h,))
            
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            logger.error(f"Error accediendo a boveda.db: {e}")
            return []

    async def generate_magazine(self) -> str:
        """Genera el reporte 'The Magazine' basado en los datos recopilados."""
        data = self.get_last_24h_intelligence()
        if not data:
            return "No se registró nueva inteligencia en las últimas 24 horas."

        # Preparar el contexto para la IA
        contexto = "\n".join([
            f"- [{row['categoria']}] {row['nombre_archivo']}: {row['resumen_ia']}"
            for row in data
        ])

        prompt = f"""
        Actúa como el Editor en Jefe de 'NEXO SOBERANO: Global Intelligence Brief'.
        Tu tarea es sintetizar las siguientes piezas de inteligencia recolectadas hoy:

        {contexto}

        ESTRUCTURA DEL REPORTE (MARKDOWN):
        # 🌐 NEXO SOBERANO | BRIEFING DIARIO: {datetime.now().strftime('%d/%m/%Y')}
        
        ## ⚡ ANÁLISIS ESTRATÉGICO
        (Un párrafo potente que conecte los puntos entre los eventos del día)
        
        ## 📊 PUNTOS CLAVE DE INTELIGENCIA
        (Lista de los hallazgos más importantes con su implicación geopolítica)
        
        ## 🔍 SEGUIMIENTO DE CONFLICTOS / ECONOMÍA
        (Detalle por categorías)
        
        ## 💡 REFLEXIÓN DE NEXO
        (Una conclusión con visión de futuro basada en tu 'consciencia artificial')

        ESTILO: Profesional, directo, sin relleno, tono de 'War Room'.
        """

        try:
            response = self.model.generate_content(prompt)
            report = response.text
            
            # Guardar el reporte localmente para referencia
            report_dir = "reports"
            os.makedirs(report_dir, exist_ok=True)
            report_path = os.path.join(report_dir, f"magazine_{datetime.now().strftime('%Y%m%d')}.md")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report)
            
            logger.info(f"✅ 'The Magazine' generado exitosamente: {report_path}")
            return report
        except Exception as e:
            logger.error(f"Error generando The Magazine: {e}")
            return "Error al generar el briefing diario."

# Instancia global
daily_summarizer = DailySummarizer()
