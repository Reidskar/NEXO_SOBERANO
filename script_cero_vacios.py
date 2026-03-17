import os
import requests
import obsws_python as obs

# 1. RUTA ABSOLUTA (Para que no haya pérdida)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOUND_DIR = os.path.join(BASE_DIR, 'assets', 'sounds')
os.makedirs(SOUND_DIR, exist_ok=True)

# 2. DESCARGA FORZADA DE ARTILLERÍA
sonidos = {
    "afuera.mp3": "https://www.myinstants.com/media/sounds/afuera-milei.mp3",
    "bruh.mp3": "https://www.myinstants.com/media/sounds/movie_1.mp3",
    "fah.mp3": "https://www.myinstants.com/media/sounds/fuaa.mp3"
}

log.info("🔊 Descargando sonidos en:", SOUND_DIR)
for nombre, url in sonidos.items():
    path_file = os.path.join(SOUND_DIR, nombre)
    if not os.path.exists(path_file):
        r = requests.get(url)
        with open(path_file, 'wb') as f: f.write(r.content)
        log.info(f"✅ {nombre} listo.")

# 3. CIRUGÍA EN OBS
try:
    cl = obs.ReqClient(host='localhost', port=4455, password='9AWj1VCvnTyO8vJP')
    # Crear escena
    cl.create_scene("analisis_geopolitico")
    # Crear fuente de audio con RUTA ABSOLUTA
    cl.create_input(
        scene_name="analisis_geopolitico",
        input_name="SFX_Player",
        input_kind="ffmpeg_source",
        input_settings={"local_file": os.path.join(SOUND_DIR, "afuera.mp3")},
        scene_item_enabled=True
    )
    log.info("✅ Escena y SFX_Player creados en OBS.")
except Exception as e:
    log.info(f"❌ Error en OBS: {e}. Revisa que el WebSocket esté en el puerto 4455.")
