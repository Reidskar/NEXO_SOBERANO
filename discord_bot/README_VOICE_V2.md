# NEXO Voice V2 - Guía de Operación

Esta nueva arquitectura modular permite al bot de Discord escuchar, procesar y responder con voces humanas premium de forma eficiente.

## 🚀 Arquitectura Modular
El sistema está dividido en servicios independientes para máxima flexibilidad:
- `bot.js`: Orquestador principal e interacción con Discord.
- `stt_service.js`: Transcripción de audio ultra-precisa con OpenAI Whisper.
- `tts_service.js`: Inteligencia de voz con pre-selección de ElevenLabs y fallback a Google TTS.
- `tts_elevenlabs.js`: Motor de streaming Opus para voces humanas premium de ElevenLabs.
- `concurrency_semaphore.js`: Control de semáforo para evitar sobrepoblar el servidor con procesos FFmpeg.

## 🛠️ Despliegue con Docker (Recomendado)
Para desplegar todo el ecosistema (Backend + DB + Bot):
1. Configura las llaves en `discord_bot/.env`.
2. Ejecuta:
   ```bash
   docker-compose up -d --build
   ```

## 🧪 Pruebas en Discord
1. **Unirse**: Usa el comando `/llamada accion:reconnect` o simplemente escribe `!join` en un canal de texto (asegúrate de estar tú en un canal de voz).
2. **Hablar**: Di algo como "Nexo, ¿puedes explicarme el estado actual de la boveda?".
3. **Respuesta**: El bot transcribirá tu voz, consultará Supabase Vector y te responderá con una voz humana streaming.

## 🩺 Monitoreo de Salud
- **Local**: El bot expone un endpoint en `http://localhost:3000/health`.
- **Script**: Ejecuta `bash scripts/check_bot_health.sh` para un reporte rápido.
- **Remoto**: Usa la Edge Function `bot-monitor` en Supabase para vigilar el estado desde la web.

## 🔑 Requerimientos de API Keys
- `OPENAI_API_KEY`: Necesaria para la escucha (STT).
- `ELEVENLABS_API_KEY`: Necesaria para la voz premium (TTS).

---
*NEXO SOBERANO - Inteligencia Geopolítica Híbrida*
