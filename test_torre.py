import obsws_python as obs
import os
import time

# --- CONFIGURACIÓN ---
password_obs = '9AWj1VCvnTyO8vJP' # Tu clave ya conocida

def diagnostico_soberano():
    log.info("🚀 INICIANDO DIAGNÓSTICO TOTAL DE LA TORRE...")
    
    # 1. Verificar Archivos de Sonido
    log.info("\n[1/4] Verificando Sonidos...")
    path_sfx = 'assets/sounds/'
    sonidos = ['afuera.mp3', 'bruh.mp3', 'fah.mp3']
    for s in sonidos:
        if os.path.exists(os.path.join(path_sfx, s)):
            log.info(f"✅ Sonido encontrado: {s}")
        else:
            log.info(f"❌ ERROR: No encuentro {s} en {path_sfx}")

    # 2. Probar Conexión OBS (Forzar Escena)
    log.info("\n[2/4] Probando Conexión OBS...")
    try:
        cl = obs.ReqClient(host='localhost', port=4455, password=password_obs)
        # Forzar cambio de escena para ver si responde
        cl.set_current_program_scene("analisis_geopolitico")
        log.info("✅ OBS respondiendo: Escena cambiada a 'analisis_geopolitico'.")
        
        # Intentar disparar sonido si la fuente existe
        cl.set_input_settings("SFX_Player", {"local_file": os.path.abspath(path_sfx + "afuera.mp3")}, True)
        log.info("✅ Comando de audio enviado a OBS.")
    except Exception as e:
        log.info(f"❌ ERROR OBS: No se pudo conectar. ¿Está el WebSocket activo? {e}")

    # 3. Verificar Docker/Qdrant
    log.info("\n[3/4] Verificando Memoria (Docker)...")
    qdrant_status = os.system("docker ps | findstr qdrant")
    if qdrant_status == 0:
        log.info("✅ Qdrant está vivo en Docker.")
    else:
        log.info("❌ ERROR: Qdrant está apagado. Ejecuta 'docker start qdrant'.")

    # 4. Reporte a Discord
    log.info("\n[4/4] Probando Reporte a Discord...")
    log.info("⚠️ Si el bot de Discord NO envía un mensaje de 'DIAGNÓSTICO' ahora, activa el 'Message Content Intent' en el Portal.")

if __name__ == "__main__":
    diagnostico_soberano()
