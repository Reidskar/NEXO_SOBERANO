FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias
# gcc, postgres, OCR y FFMPEG para el Motor de Video
RUN apt-get update && apt-get install -y \
    gcc libpq-dev tesseract-ocr poppler-utils ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copiar configuración SLIM para evitar límites de Railway
COPY requirements_railway.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements_railway.txt

# Copiar el código del sistema
COPY . .

# Comando por defecto para Railway
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
