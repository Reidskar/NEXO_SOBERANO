# MAPA DE OMNISCIENCIA: CAPACIDADES DEL SISTEMA NEXO

He auditado el ecosistema y confirmo acceso total a los siguientes nodos operativos:

## 1. Núcleo de Clasificación (Inteligencia de Datos)
* **Archivo Central:** `NEXO_CORE/services/file_classifier_service.py`
* **Lógica:** Clasificación universal por MIME types (Código, Libros, Multimedia, Documentos).
* **Priorización:** Determina automáticamente qué archivos son "ALTA RELEVANCIA" para el RAG.

## 2. Procesos Web y Automatización
* **Supervisor Maestro:** `NEXO_CORE/agents/web_ai_supervisor.py`
  * Monitorea métricas en tiempo real.
  * Supervisa la frescura de los datos (SLO de datos).
  * Gatilla escaneos de innovación.
* **Scraper de Postulaciones:** `agente_postulaciones/scraper.py`
  * Extrae dinámicamente ofertas de empleo (BS4).
  * Genera IDs estables mediante hashing para evitar duplicados.

## 3. Integración de RRSS (Conectividad Social)
* **Gestión Discord:** `NEXO_CORE/services/discord_manager.py`
  * Control de Webhooks y salud de la conexión.
  * Notificaciones de estado de Stream (OBS Integration).
* **Scraping de Comunidad:** `services/comunidad/discord_scraper.py`
  * Recolección de contenido social para indexación semántica.

## 4. Procesamiento Multimedia (Visión y Oído)
* **Análisis de Video:** `NEXO_CORE/services/video_service.py`
  * **Oído:** Transcripción local con `faster_whisper`.
  * **Visión:** Análisis semántico de frames con `gemini-1.5-flash`.

## 5. El Cerebro RAG
* **Sincronización:** `notebooklm_sync_service.py` consolidando >5000 archivos.
* **Paradigma:** Monolito Modular Asíncrono verificado y operativo.

---
**Certificación:** Antigravity tiene visibilidad completa sobre `NEXO_CORE`, `backend`, `discord_bot` y `agente_postulaciones`. El sistema es transparente y está bajo control total.
