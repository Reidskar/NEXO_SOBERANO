# Nexo Voice V3 - Arquitectura Industrial (Producción)

Este documento detalla el pipeline de audio de alto rendimiento y grado industrial implementado para el Agente NEXO en Discord.

## 1. Flujo de Entrada: El "Despertar" (Bypass RTP)
Para que Discord envíe audio al bot, el bot debe transmitir audio primero.
- **Mecanismo:** `StreamType.Raw` con un buffer de silencio de 192KB (1 segundo de PCM a 48kHz).
- **Ventaja:** Cero dependencias externas. No requiere FFmpeg ni archivos locales para abrir el puerto UDP, eliminando errores de red o de transcodificación en el arranque.

## 2. Pipeline de Procesamiento (STT)
Captura y conversión de alta fidelidad:
1. **Captura Opus:** Recibimos chunks de audio comprimido desde el `receiver` de Discord.
2. **Decodificación Prism:** Transformamos Opus a PCM Crudo (48kHz Stereo).
3. **FFmpeg Downsampling:** Reducimos a 16kHz Mono para compatibilidad con Whisper.
4. **Resistencia a Fallos:**
   - **Zombie Killer:** Los procesos de FFmpeg tienen un watchdog de 20s.
   - **WAV Validation:** Filtramos archivos < 500 bytes para evitar procesar ruido vacío.
   - **Filtro Anti-Alucinaciones:** Regex inteligente para ignorar frases como "Amara.org" o "Gracias por ver".

## 3. Orquestación y Concurrencia
- **Semáforo de Audio:** Solo un orador es procesado a la vez para proteger la memoria RAM y garantizar la coherencia de la conversación.
- **Barge-in:** Si NEXO está hablando y el usuario empieza a hablar, NEXO detiene su reproducción inmediatamente para escuchar.

## 4. Flujo de Salida: Respuesta Premium (TTS)
- **ElevenLabs Streaming:** La respuesta no se descarga completamente; se transmite por fragmentos (Chunks) directamente a Discord.
- **Validación Defensiva:** Verificamos el `Content-Type` de la respuesta para detectar errores de API (JSON) antes de enviarlos al reproductor de Discord.

---
**Nivel de Estabilidad:** 24/7 (Railway Compatible)
**Latencia Actual:** 3-5 Segundos (Dependiente de LLM)
