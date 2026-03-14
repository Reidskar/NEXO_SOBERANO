import os
import json
import logging
import asyncio
from typing import Dict, List
from google import genai

from backend import config
from backend.services.vector_db import get_pool

logger = logging.getLogger(__name__)

class SocialParasiteTracker:
    """
    Antropología de la Decadencia: Ranking de "Parásitos Mentales Sociales".
    Mide objetivamente el daño de actores basado en Economía Austríaca.
    """
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(config.MODELO_FLASH)
        else:
            logger.error("❌ GEMINI_API_KEY no configurada. SocialParasiteTracker necesita Gemini.")

    async def evaluate_entities(self, articles: List[str], country: str) -> List[Dict]:
        """
        Analiza las acciones o discursos de figuras públicas y genera un ranking
        basado en la entropía y dependencia colectivista.
        """
        if not self.api_key:
            return [{"actor": "Desconocido", "parasite_index": 0.0, "reasoning": "API no configurada"}]
            
        combined_text = "\n---\n".join(articles[:5])
        
        prompt = f"""
        Actúa como un Auditor de Inteligencia. Analiza las siguientes noticias/discursos de {country}.
        Identifica a 1 o 2 actores principales (políticos, medios, organizaciones).
        
        Para cada uno, calcula un 'parasite_index' (0.0 a 1.0) basado en 3 ejes:
        1. Dependencia del Colectivismo: Cuánto incentivan la sumisión al estado o al grupo en lugar de la responsabilidad individual.
        2. Factor de Distorsión: Cuánto desvían la atención de la realidad económica (inflación, emisión) hacia narrativas emocionales.
        3. Incentivo al Conflicto: Cuánto ganan o lucran (poder/dinero) creando división social.
        
        Responde ESTRICTAMENTE con una lista JSON en este formato:
        [
            {{
                "actor": "Nombre del Actor", 
                "parasite_index": 0.92, 
                "reasoning": "Breve justificación objetiva y praxeológica"
            }}
        ]
        
        Artículos:
        {combined_text}
        """
        
        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            raw_text = response.text
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0]
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0]
                
            entities = json.loads(raw_text.strip())
            return entities
            
        except Exception as e:
            logger.error(f"Error en SocialParasiteTracker para {country}: {e}")
            return [{"actor": "Error", "parasite_index": 0.5, "reasoning": str(e)}]

    async def save_indicator(self, country: str, data: Dict):
        """Guarda el parasite_index en Supabase conflict_indicators."""
        actor = data.get('actor')
        score = data.get('parasite_index', 0.0)
        metadata = json.dumps({
            "actor": actor,
            "reasoning": data.get('reasoning', ''),
            "source": "parasite_tracker"
        })
        
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO public.conflict_indicators (country, indicator_type, score, metadata)
                    VALUES ($1, $2, $3, $4::jsonb)
                """, country, 'parasite', score, metadata)
                logger.info(f"✅ Parasite Index: Actor en {country} registrado con {score*100}/100")
        except Exception as e:
            logger.error(f"Error guardando indicador de parásito para {country}: {e}")

parasite_tracker = SocialParasiteTracker()
