import os
import json
import logging
import asyncio
from typing import Dict, List
from google import genai

from backend import config
from backend.services.vector_db import get_pool

logger = logging.getLogger(__name__)

class SentimentEngine:
    """
    Termodinámica Social: Analiza la temperatura de un grupo basándose en Gustave Le Bon y Sigmund Freud.
    Busca polarización, pérdida de individualidad y deshumanización.
    """
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(config.MODELO_FLASH) # Usamos modelo instanciado global
        else:
            logger.error("❌ GEMINI_API_KEY no configurada. SentimentEngine necesita Gemini.")

    async def analyze_social_temperature(self, text_samples: List[str], country: str) -> Dict:
        """
        Analiza muestras de texto (ej. tweets, discursos) para medir el riesgo de estallido social.
        Devuelve un 'heat_score' de 0 a 1.
        """
        if not self.api_key:
            return {"country": country, "heat_score": 0.0, "reasoning": "API no configurada"}
            
        combined_text = "\n---\n".join(text_samples[:10]) # Evaluamos hasta 10 muestras
        
        prompt = f"""
        Actúa como un psicólogo de masas experto en Gustave Le Bon y praxeología austríaca.
        Analiza las siguientes muestras de discurso social de {country}.
        
        Debes buscar:
        1. Deshumanización del "otro" (enemigo político/clase).
        2. Pérdida de racionalidad individual a favor del "enjambre" o colectivo.
        3. Velocidad de indignación.
        
        Responde ESTRICTAMENTE con un bloque JSON con este formato:
        {{
            "heat_score": 0.85, 
            "reasoning": "Breve explicación de por qué este grupo está cerca del estallido o la calma",
            "polarization_vector": "Clase Media vs Estado"
        }}
        
        Muestras de texto:
        {combined_text}
        """
        
        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            raw_text = response.text
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0]
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0]
                
            data = json.loads(raw_text.strip())
            data['country'] = country
            return data
            
        except Exception as e:
            logger.error(f"Error en SentimentEngine para {country}: {e}")
            return {"country": country, "heat_score": 0.5, "reasoning": f"Error de análisis: {e}"}

    async def save_indicator(self, data: Dict):
        """Guarda el heat_score en Supabase conflict_indicators."""
        country = data.get('country')
        score = data.get('heat_score', 0.0)
        metadata = json.dumps({
            "reasoning": data.get('reasoning', ''),
            "polarization_vector": data.get('polarization_vector', ''),
            "source": "social_sentiment_engine"
        })
        
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO public.conflict_indicators (country, indicator_type, score, metadata)
                    VALUES ($1, $2, $3, $4::jsonb)
                """, country, 'sentiment', score, metadata)
                logger.info(f"✅ Sentiment Score: {country} registrado con {score*100}/100")
        except Exception as e:
            logger.error(f"Error guardando sentiment para {country}: {e}")

sentiment_engine = SentimentEngine()
