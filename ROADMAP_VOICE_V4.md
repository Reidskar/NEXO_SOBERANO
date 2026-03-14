# Roadmap Nexo Voice V4: Ultra-Low Latency (<1s)

El objetivo de la Fase V4 es romper la barrera de la "espera" transformando el sistema de una arquitectura transaccional a una de streaming de flujo continuo.

## 1. Evolución del Backend (FastAPI + SSE)
- **Endpoint Streaming:** Transformar `/agente/consultar-rag` para que use `StreamingResponse`.
- **SSE (Server-Sent Events):** El LLM enviará tokens a medida que se generan, sin esperar a que la oración termine.

## 2. Orquestador V4 (Fragmentos Inteligentes)
En `voice_orchestrator.js`:
- **Token Aggregator:** Un buffer de texto que busca signos de puntuación (`.`, `,`, `?`, `!`, `\n`).
- **Parallel TTS Synthesis:** En cuanto se detecta una oración completa (ej: "Hola, ¿cómo estás?"), esa oración se envía a ElevenLabs mientras el LLM sigue generando la siguiente.
- **Audio Queue Management:** Un sistema de colas en el reproductor de Discord para encadenar las respuestas de ElevenLabs sin saltos de audio.

## 3. Optimizaciones de Red
- **WebSockets:** Evaluar la migración de HTTP a WebSockets para el control bidireccional STT/LLM.
- **Local Transcoding:** Optimizar los parámetros de FFmpeg para reducir el uso de CPU en un 15%.

## Objetivo Final
Que la respuesta de NEXO empiece a sonar antes de que el usuario termine de captar que el bot ha pasado de "escuchar" a "pensar".
