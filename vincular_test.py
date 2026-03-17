import os
from pathlib import Path

def run_linking_test():
    log.info("=== NEXO SOBERANO: PRUEBA DE VINCULACIÓN ===")
    
    results = {
        "Cerebro (Celery)": False,
        "Memoria (Master Context)": False,
        "Cuerpo (Discord Bot Logic)": False,
        "Cuerpo (Discord Native Libs)": False
    }

    # 1. Verificar Celery
    celery_path = Path("NEXO_CORE/worker/celery_app.py")
    if celery_path.exists():
        log.info(f"[OK] Celery detectado en: {celery_path}")
        results["Cerebro (Celery)"] = True
    else:
        log.info("[FAIL] No se encontró celery_app.py en NEXO_CORE/worker/")

    # 2. Verificar Master Context
    # Nota: El sprint 0.9 generó 'exports/nexo_master_context.txt' o 'nexo_soberano_para_notebooklm.txt'
    # El prompt menciona 'exports/nexo_master_context.txt'
    master_context_path = Path("exports/nexo_master_context.txt")
    if master_context_path.exists():
        log.info(f"[OK] Master Context detectado en: {master_context_path}")
        results["Memoria (Master Context)"] = True
    else:
        # Reintentar con el otro nombre generado anteriormente
        alt_path = Path("nexo_soberano_para_notebooklm.txt")
        if alt_path.exists():
            log.info(f"[OK] Master Context detectado (nombre alternativo): {alt_path}")
            results["Memoria (Master Context)"] = True
        else:
            log.info("[FAIL] No se encontró el archivo de contexto maestro.")

    # 3. Verificar Discord Bot
    bot_path = Path("discord_bot/bot.js")
    if bot_path.exists():
        content = bot_path.read_text(encoding='utf-8', errors='ignore')
        if "deferReply" in content:
            log.info("[OK] Lógica 'deferReply' detectada en el bot.")
            results["Cuerpo (Discord Bot Logic)"] = True
        else:
            log.info("[WARN] No se encontró 'deferReply' en bot.js (Revisar flujo UI)")

        if "libsodium-wrappers" in content:
            log.info("[OK] Libreria 'libsodium-wrappers' detectada en el bot.")
            results["Cuerpo (Discord Native Libs)"] = True
        else:
            # Check alternative file
            vo_path = Path("discord_bot/voice_orchestrator.js")
            if vo_path.exists() and "libsodium-wrappers" in vo_path.read_text(encoding='utf-8', errors='ignore'):
                log.info(f"[OK] Libreria 'libsodium-wrappers' detectada en: {vo_path}")
                results["Cuerpo (Discord Native Libs)"] = True
            else:
                log.info("[WARN] No se encontro 'libsodium-wrappers' en el bot (Revisar soporte voz)")
    else:
        log.info("[FAIL] No se encontro discord_bot/bot.js")

    log.info("\n=== RESUMEN DE VINCULACION ===")
    all_ok = all(results.values())
    for k, v in results.items():
        status = "[OK]" if v else "[FAIL]"
        log.info(f"{status} {k}")
    
    if all_ok:
        log.info("\n[VINCULACIÓN EXITOSA] El sistema opera bajo el paradigma de Monolito Modular Asíncrono.")
    else:
        log.info("\n[VINCULACIÓN PARCIAL] Se detectaron faltantes o inconsistencias.")

if __name__ == "__main__":
    run_linking_test()
