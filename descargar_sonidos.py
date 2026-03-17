import os
import requests

path = 'assets/sounds/'
os.makedirs(path, exist_ok=True)

sonidos = {
    "afuera.mp3": "https://www.myinstants.com/media/sounds/afuera-milei.mp3",
    "bruh.mp3": "https://www.myinstants.com/media/sounds/movie_1.mp3",
    "fah.mp3": "https://www.myinstants.com/media/sounds/fuaa.mp3",
    "brrr.mp3": "https://www.myinstants.com/media/sounds/money-printer-go-brrr.mp3"
}

log.info("📥 Iniciando descarga de artillería sonora...")
for nombre, url in sonidos.items():
    try:
        r = requests.get(url, allow_redirects=True)
        with open(os.path.join(path, nombre), 'wb') as f:
            f.write(r.content)
        log.info(f"✅ Descargado: {nombre}")
    except Exception as e:
        log.info(f"❌ Error al descargar {nombre}: {e}")
