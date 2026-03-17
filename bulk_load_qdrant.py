import os
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
import PyPDF2

# 1. CONFIGURACIÓN
COLLECTION_NAME = "nexo_soberano_knowledge"
DOCS_PATH = "assets/docs/"
MODEL_NAME = "all-MiniLM-L6-v2"

client = QdrantClient("localhost", port=6333)
model = SentenceTransformer(MODEL_NAME)

def extract_text(file_path):
    if file_path.endswith('.pdf'):
        with open(file_path, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)
            return " ".join([page.extract_text() for page in pdf.pages])
    elif file_path.endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def chunk_text(text, size=500):
    words = text.split()
    return [" ".join(words[i:i + size]) for i in range(0, len(words), size)]

def iniciar_memoria():
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    )
    log.info(f"🚀 Iniciando carga masiva desde: {DOCS_PATH}")
    id_counter = 1
    for file in os.listdir(DOCS_PATH):
        if file.endswith(('.pdf', '.txt')):
            log.info(f"📄 Procesando: {file}...")
            full_text = extract_text(os.path.join(DOCS_PATH, file))
            chunks = chunk_text(full_text)
            points = []
            for i, chunk in enumerate(chunks):
                vector = model.encode(chunk).tolist()
                points.append(models.PointStruct(
                    id=id_counter,
                    vector=vector,
                    payload={"text": chunk, "source": file}
                ))
                id_counter += 1
            client.upsert(collection_name=COLLECTION_NAME, points=points)
            log.info(f"✅ {file} indexado ({len(chunks)} fragmentos).")

if __name__ == "__main__":
    if not os.path.exists(DOCS_PATH):
        os.makedirs(DOCS_PATH)
        log.info(f"📁 Carpeta {DOCS_PATH} creada. Pon tus archivos ahí y vuelve a ejecutar.")
    else:
        iniciar_memoria()
        log.info("\n🧠 Memoria Vectorial alimentada y lista.")
