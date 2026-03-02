from nexo_soberano import crear_infraestructura, crear_boveda_db, inicializar_bitacoras

if __name__ == "__main__":
    # el asistente simplemente delega a nexo_soberano
    crear_infraestructura()
    crear_boveda_db()
    inicializar_bitacoras()
    log.info("\n🚀 ASISTENTE NEXO ACTIVADO.")
