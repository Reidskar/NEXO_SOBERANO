# NEXO SOBERANO: Manifiesto Arquitectónico y Flujos de Sistema

**Versión:** 3.0 (Post-Sprint 0.9) | **Clasificación:** Confidencial / Core System

## 1. Filosofía del Sistema (El "Modo de Pensar")

Nexo Soberano no es un simple bot, es un **ecosistema de inteligencia personal y logística**. Su diseño se basa en tres pilares inquebrantables:

1. **Soberanía de Datos:** Uso de base de datos vectorial propia (Qdrant) y relacional (Supabase PostgreSQL).
2. **Tolerancia a Fallos (Anti-Zombie):** Está estrictamente prohibido silenciar errores (`try/except: pass`). El sistema debe gritar cuando duele y usar supervisores pasivos (PM2 para Node, y Healthchecks en Python) para garantizar alta disponibilidad.
3. **Omnisciencia Multimodal:** Nexo no es ciego ni sordo. Procesa texto nativo, escucha audio (vía Whisper) y analiza visualmente imágenes y video-frames (vía Gemini Flash) para indexarlos en su bóveda semántica.

## 2. Topología del Sistema (Los Componentes)

La arquitectura sigue un patrón de **Monolito Modular Asíncrono** dividido en dos grandes "cuerpos":

### A. El Cerebro (FastAPI - Python)
Vive en `NEXO_CORE/`. Maneja la lógica pesada.
* **Routers Especializados:** `rag.py` (Inteligencia), `sync.py` (Ingesta), `media_auth.py` (Tokens OAuth), `metrics.py` (Salud), `voice.py` (STT/TTS).
* **Celery Workers:** `celery_app.py`. El músculo de fondo. Se encarga de descargar, leer y clasificar archivos pesados de Google Drive y OneDrive en paralelo sin colgar la API.
* **Supervisores (Health Probers):** Scripts en Python que monitorean el consumo de RAM/CPU y hacen ping a la API.

### B. El Cuerpo / Interfaz (Node.js - PM2)
Vive en `discord_bot/bot.js`.
* Es un cliente ligero gestionado por **PM2**.
* Solo se encarga de capturar eventos (mensajes, comandos de voz) y enviarlos al Cerebro vía peticiones HTTP (`axios`), esperando la respuesta para actuar en Discord.

## 3. Flujos de Operación Crítica

### Flujo 1: Ingesta Multimodal (El Sistema Digestivo)
Cómo aprende Nexo de los archivos que subes:
1. **Trigger:** El usuario sube un archivo a Google Drive o OneDrive (o un Webhook de n8n/Make avisa al sistema).
2. **Despacho:** FastAPI recibe la orden y la delega al Worker de Celery.
3. **Extracción (Video Service):**
   * Si es texto: Indexación directa.
   * Si es imagen: Gemini Flash extrae texto (OCR) y describe la escena semánticamente.
   * Si es video/audio: `ffmpeg` extrae un frame clave (analizado por Gemini) y el audio completo (transcrito localmente con `faster-whisper`).
4. **Almacenamiento:** Todo se vectoriza y se guarda en Qdrant.

### Flujo 2: Interacción de Voz en Tiempo Real (El Sistema Nervioso)
Cómo conversa Nexo en Discord:
1. **Conexión:** Usuario ejecuta `/voz accion:unir`. Discord.js ejecuta `deferReply()` y entra al canal usando `libsodium-wrappers`.
2. **Escucha:** `VoiceReceiver` detecta cuando el usuario habla y hace silencio (`AfterSilence`). Captura el buffer de audio PCM.
3. **Comprensión (STT):** Node.js envía el audio en base64 a `POST /api/voice/stt`. Whisper en Python lo vuelve texto.
4. **Cognición (RAG):** El texto va a `POST /agente/consultar-rag`. El LLM cruza tu pregunta con la bóveda de datos y genera una respuesta.
5. **Habla (TTS):** La respuesta va a `POST /api/voice/tts`. `gTTS` la pasa a audio MP3 base64 y Node.js la reproduce en el canal de Discord.

## 4. Orquestación y Despliegue (Railway + Local)

* **Despliegue Slim (Railway):** El servidor en la nube usa `nixpacks.toml` y `requirements_railway.txt` (sin librerías pesadas como Torch/Whisper) para mantener la API web y el War Room vivos 24/7 sin agotar la RAM.
* **Procesamiento Local (Tu PC):** Tu máquina ejecuta el Worker de Celery con el stack completo, actuando como el procesador "músculo" conectado a la misma base de datos.
