import logging
import google.generativeai as genai

# Central logger setup
def get_logger(name: str = "nexo_ai_core"):
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

# Central Gemini model setup
def get_gemini_model(api_key: str, model_name: str = "gemini-pro"):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)

# Embedding function (optional, for RAG)
def get_gemini_embedding_model(api_key: str):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("embedding-001")
