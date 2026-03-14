import asyncio
import logging
from backend.services.vector_db import ensure_table, asimilar_documento, buscar_similares, close_pool

logging.basicConfig(level=logging.INFO)

async def test_search():
    log.info("🚀 Iniciando test de pgvector...")
    await ensure_table()
    
    docs = [
        ("hash_test_1", "La OTAN discutió sobre estrategias de defensa conjuntas en Europa del Este.", {"categoria": "Defensa", "archivo": "test_otan.txt"}),
        ("hash_test_2", "Rusia aumentó sus exportaciones de energía hacia Asia en el último mes.", {"categoria": "Economia", "archivo": "test_rusia.txt"}),
        ("hash_test_3", "La economía austríaca defiende el libre mercado y critica la inflación estatal.", {"categoria": "Economia_Austriaca", "archivo": "test_austria.txt"}),
    ]

    log.info("\n📥 Insertando documentos de prueba...")
    for hash_val, content, meta in docs:
        await asimilar_documento(hash_val, content, meta)

    try:
        query = "¿Qué dijo la OTAN sobre Europa?"
        log.info(f"\n🔍 Buscando: '{query}'")
        resultados = await buscar_similares(query, k=2)
        
        for idx, res in enumerate(resultados):
            log.info(f"  {idx + 1}. {(res['similarity']*100):.1f}% -> {res['content']}")
            log.info(f"     Meta: {res['metadata']}")
            
    finally:
        await close_pool()
        log.info("\n✅ Test finalizado.")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_search())
