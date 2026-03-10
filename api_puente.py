import os
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from typing import cast
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from google.generativeai.generative_models import GenerativeModel
from dotenv import load_dotenv
import logging

# --- CONFIGURACIÓN BASE ---
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
modelo = GenerativeModel("gemini-1.5-flash")
log = logging.getLogger(__name__)

app = FastAPI(title="Nexo Soberano - API de Inteligencia", version="1.0")

# --- CONEXIÓN AL LÓBULO FRONTAL (ChromaDB) ---
CHROMA_PATH = os.path.join("NEXO_SOBERANO", "memoria_vectorial")
cliente_chroma = chromadb.PersistentClient(path=CHROMA_PATH)
emb_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
coleccion = cliente_chroma.get_or_create_collection(name="inteligencia_geopolitica", embedding_function=cast(chromadb.EmbeddingFunction, emb_fn), metadata={"hnsw:space": "cosine"})

# --- MODELO DE DATOS ---
class Peticion(BaseModel):
    pregunta: str
    n_resultados: int = 3

# --- ENDPOINT TÁCTICO (Motor RAG) ---
@app.post("/agente/consultar")
async def consultar_boveda(peticion: Peticion):
    log.info(f"📡 Solicitud entrante: {peticion.pregunta}")
    
    try:
        # 1. Búsqueda Vectorial Semántica
        resultados = coleccion.query(
            query_texts=[peticion.pregunta],
            n_results=peticion.n_resultados
        )

        if not resultados['documents'] or not resultados['documents'][0]:
            return {"respuesta": "No hay evidencia en la Bóveda sobre este tema.", "fuentes": []}

        # 2. Construcción de Contexto
        evidencia_cruda = "\n---\n".join(resultados['documents'][0])
        metadatos_fuentes = resultados['metadatas'][0] if resultados['metadatas'] else []

        # 3. Razonamiento IA
        prompt_maestro = f"""
        Eres Jarvis, el Oficial de Inteligencia Adjunto del Director.
        Responde a su pregunta utilizando ÚNICAMENTE la evidencia extraída de su Bóveda personal.
        Si la evidencia no responde la pregunta, indícalo. No inventes datos.
        
        EVIDENCIA EXTRAÍDA:
        {evidencia_cruda}
        
        PREGUNTA DEL DIRECTOR:
        {peticion.pregunta}
        """

        respuesta_ia = modelo.generate_content(prompt_maestro)
        
        # 4. Respuesta Estructurada
        return {
            "estado": "exito",
            "respuesta": respuesta_ia.text,
            "evidencia_utilizada": metadatos_fuentes
        }

    except Exception as e:
        log.info(f"❌ Error en el puente API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Para ejecutar: uvicorn api_puente:app --reload
