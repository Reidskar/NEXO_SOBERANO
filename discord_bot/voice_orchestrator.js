try {
  require("prism-media");
  console.log("[NEXO CHECK] prism-media OK");
  require("libsodium-wrappers");
  console.log("[NEXO CHECK] libsodium OK");
  try {
    const opus = require("prism-media").opus;
    console.log(
      `[NEXO CHECK] Motor Opus detectado:`,
      opus.Decoder ? "Nativo/Fallback OK" : "Matusalén?",
    );
  } catch (e) {
    console.error(
      `[NEXO FATAL] Ningún motor Opus encontrado. El bot será sordo. Ejecuta: npm i @discordjs/opus opusscript`,
    );
  }
} catch (e) {
  console.error(
    "[NEXO FATAL] Faltan dependencias críticas de audio:",
    e.message,
  );
}

// --- INICIO FFMPEG FIX (NIVEL KERNEL) ---
const ffmpegStatic = require("ffmpeg-static");
const prism = require("prism-media");
const path = require("path");

// 1. Extraer solo la carpeta donde vive ffmpeg.exe
const ffmpegDir = path.dirname(ffmpegStatic);

// 2. HACK: Inyectar la carpeta en el PATH de Windows solo para este proceso
process.env.PATH = ffmpegDir + path.delimiter + process.env.PATH;

// 3. Mantener variables de entorno secundarias por seguridad
process.env.FFMPEG_PATH = ffmpegStatic;
prism.FFmpeg.command = ffmpegStatic;

console.log(`[NEXO CHECK] FFMPEG inyectado en KERNEL PATH: ${ffmpegDir}`);
// --- FIN FFMPEG FIX ---

const {
  joinVoiceChannel,
  createAudioPlayer,
  createAudioResource,
  AudioPlayerStatus,
  VoiceConnectionStatus,
  EndBehaviorType,
  StreamType,
} = require("@discordjs/voice");
const { spawn } = require("child_process");
const ffmpeg = require("ffmpeg-static");
const axios = require("axios");
const fs = require("fs");
const { Readable } = require("stream");
const { transcribeFile } = require("./stt_service");
const { playTTS } = require("./tts_service");
const { concurrencySemaphore } = require("./concurrency_semaphore");
const { getGeminiLiveBridge } = require("./gemini_live_bridge");

// Voice mode: 'classic' = Groq Whisper STT → LLM → TTS, 'live' = Gemini Live streaming
const VOICE_MODE = (process.env.VOICE_MODE || "classic").toLowerCase();

class VoiceOrchestrator {
  constructor(client) {
    this.client = client;
    this.connections = new Map();
    this.voiceMode = VOICE_MODE; // 'classic' or 'live'
    this.players = new Map();
    this.TEMP_DIR = path.join(__dirname, "temp_audio");
    if (!fs.existsSync(this.TEMP_DIR)) fs.mkdirSync(this.TEMP_DIR);
    this.idleTimers = new Map();
  }

  async joinChannel(channel) {
    const connection = joinVoiceChannel({
      channelId: channel.id,
      guildId: channel.guild.id,
      adapterCreator: channel.guild.voiceAdapterCreator,
      selfDeaf: false,
    });

    const player = createAudioPlayer();

    // 🚨 CRÍTICO: Capturador de Errores del Player
    player.on("error", (error) => {
      console.error(
        `[NEXO AUDIO CRASH CRÍTICO] ❌ El reproductor falló:`,
        error.message,
        error.resource?.metadata,
      );
    });

    connection.subscribe(player);

    this.connections.set(channel.guild.id, connection);
    this.players.set(channel.guild.id, player);

    console.log(`[NEXO VOICE] Conectado al canal de voz: ${channel.name}`);

    connection.on(VoiceConnectionStatus.Ready, async () => {
      console.log(`[NEXO VOICE] P2P Listo. Iniciando saludo interactivo...`);
      this.startListening(connection, channel.guild.id);

      // 1. Saludo inicial con TTS real (Esto arregla el RTP obligando a Discord a rutear audio)
      await this.speak(
        channel.guild.id,
        "Sistemas en línea. Te escucho, Camilo.",
      );

      // 2. Iniciar el guardián de inactividad
      this.resetIdleTimer(channel.guild.id);
    });

    // Parche 3: Garbage Collection (Desconexiones)
    connection.on(VoiceConnectionStatus.Disconnected, () => {
      console.warn(
        `[NEXO VOICE] ⚠️ Conexión perdida en ${channel.guild.id}. Liberando recursos...`,
      );
      if (this.idleTimers.has(channel.guild.id))
        clearTimeout(this.idleTimers.get(channel.guild.id));
      this.connections.delete(channel.guild.id);
      this.players.delete(channel.guild.id);
      connection.destroy();
    });

    return connection;
  }

  resetIdleTimer(guildId) {
    if (this.idleTimers.has(guildId))
      clearTimeout(this.idleTimers.get(guildId));

    const timer = setTimeout(async () => {
      const connection = this.connections.get(guildId);
      if (
        connection &&
        connection.state.status === VoiceConnectionStatus.Ready
      ) {
        console.log(
          `[NEXO VOICE] ⚠️ Inactividad. Llamando la atención del usuario...`,
        );
        await this.speak(
          guildId,
          "Sigo aquí en la llamada. Avísame cuando estés listo para operar.",
        );
        this.resetIdleTimer(guildId); // Bucle infinito hasta que responda o se vaya
      }
    }, 30000); // Habla cada 30 segundos si hay silencio prolongado

    this.idleTimers.set(guildId, timer);
  }

  startListening(connection, guildId) {
    const receiver = connection.receiver;
    const activeUserStreams = new Map(); // Guarda por usuario

    receiver.speaking.on("start", (userId) => {
      if (activeUserStreams.has(userId)) {
        // Ya estamos grabando a este usuario, ignorar evento duplicado
        return;
      }
      activeUserStreams.set(userId, true);
      const activePlayer = this.players.get(guildId);
      if (
        activePlayer &&
        activePlayer.state.status === AudioPlayerStatus.Playing
      ) {
        console.log(`[NEXO VOICE] Interrupción detectada. Deteniendo audio.`);
        activePlayer.stop();
      }

      console.log(`[NEXO VOICE] Escuchando al usuario: ${userId}`);
      // Parche 9: Control manual del fin de grabación (Ignorar VAD de Discord)
      const audioStream = receiver.subscribe(userId, {
        end: {
          behavior: EndBehaviorType.Manual,
        },
      });

      const opusDecoder = new prism.opus.Decoder({
        rate: 48000,
        channels: 2,
        frameSize: 960,
      });
      let chunkCount = 0;
      let lastDataTime = Date.now();

      // Detector de Silencio Manual (Heartbeat)
      const silenceCheck = setInterval(() => {
        const idleTime = Date.now() - lastDataTime;
        if (idleTime > 1500 && chunkCount > 0) {
          // 1.5 segundos de silencio real
          console.log(
            `[NEXO VOICE] ⌚ Silencio detectado (1.5s). Cerrando grabación de ${userId}.`,
          );
          cleanup();
        }
      }, 500);

      const cleanup = () => {
        activeUserStreams.delete(userId); // Liberar para próxima grabación
        clearInterval(silenceCheck);
        try {
          audioStream.unpipe(opusDecoder);
          opusDecoder.unpipe(ffmpegProc.stdin);
          ffmpegProc.stdin.end();
        } catch (e) {}
      };

      opusDecoder.on("data", () => {
        chunkCount++;
        lastDataTime = Date.now(); // Reset con cada paquete de audio
        if (chunkCount === 10 || chunkCount % 50 === 0) {
          console.log(`[NEXO VOICE] 🎙️ Grabando... (${chunkCount} chunks)`);
        }
      });

      const tmpFile = path.join(
        this.TEMP_DIR,
        `voice_${guildId}_${userId}_${Date.now()}.wav`,
      );
      const ffmpegProc = spawn(ffmpeg, [
        "-f",
        "s16le",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-i",
        "pipe:0",
        "-af",
        "volume=3.0", // Boost de volumen para mejor STT
        "-ar",
        "16000",
        "-ac",
        "1",
        tmpFile,
      ]);

      audioStream.pipe(opusDecoder).pipe(ffmpegProc.stdin);

      ffmpegProc.on("close", async (code) => {
        console.log(
          `[NEXO ULTRA-DEBUG] Grabación finalizada (código ${code}). Chunks: ${chunkCount}`,
        );

        if (chunkCount > 40) {
          // Umbral equilibrado
          try {
            const stats = fs.statSync(tmpFile);
            console.log(
              `[NEXO VOICE] Audio capturado (${stats.size} bytes). Procesando...`,
            );
            await this.processUserAudio(tmpFile, guildId, userId);
          } catch (err) {
            console.error(`[NEXO VOICE] Error procesando audio:`, err.message);
          }
        } else {
          console.log(
            `[NEXO VOICE] Audio insuficiente/ruido (${chunkCount} chunks). Ignorando.`,
          );
          if (fs.existsSync(tmpFile)) fs.unlinkSync(tmpFile);
        }
      });

      const onSpeakingEnd = (stoppedUserId) => {
        if (stoppedUserId === userId) {
          console.log(
            `[NEXO ULTRA-DEBUG] 🛑 Discord dice que ${userId} terminó. Esperando buffer de silencio manual...`,
          );
        }
      };
      receiver.speaking.on("end", onSpeakingEnd);
    });
  }

  async processUserAudio(filePath, guildId, userId) {
    // Route to Gemini Live mode if active
    if (this.voiceMode === "live") {
      return this.processUserAudioLive(filePath, guildId, userId);
    }
    console.log(
      `[NEXO ULTRA-DEBUG] 0️⃣ Intentando adquirir semáforo para ${filePath}...`,
    );
    // Multi-Speaker Lock: Solo procesar un orador a la vez para proteger RAM y coherencia
    await concurrencySemaphore.acquire();
    try {
      console.log(`[NEXO ULTRA-DEBUG] 1️⃣ Iniciando STT (TranscribeFile)...`);

      // 1. Convertir Audio a Texto (STT)
      const textInput = await transcribeFile(filePath);

      // Regla 4: Protección de RAM & Clean up
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }

      if (!textInput || textInput.trim().length < 2) {
        console.warn(
          `[NEXO ULTRA-DEBUG] ⚠️ Texto STT vacío o alucinación. Abortando.`,
        );
        return;
      }

      // Filtrado de alucinaciones comunes de Whisper en silencio
      const lowered = textInput.toLowerCase().trim();
      const hallucinations = [
        "gracias.",
        "gracias",
        "subtitles by",
        "mushrooms",
        "amara.org",
      ];
      if (
        hallucinations.some((h) => lowered.includes(h)) &&
        lowered.length < 15
      ) {
        console.warn(
          `[NEXO ULTRA-DEBUG] ⚠️ Filtrada posible alucinación de Whisper: "${textInput}"`,
        );
        return;
      }

      console.log(`[NEXO ULTRA-DEBUG] 2️⃣ STT Exitoso: "${textInput}"`);

      // 2. Enviar a Nexo Core Backend (LLM)
      console.log(`[NEXO ULTRA-DEBUG] 3️⃣ Consultando LLM en FastAPI...`);
      const FASTAPI_URL = process.env.FASTAPI_URL || "http://localhost:8080";
      const nexoResponse = await axios.post(
        `${FASTAPI_URL}/agente/consultar-rag`,
        {
          pregunta: textInput,
          usuario_id: userId,
          contexto: "discord_voice",
        },
        {
          headers: { Authorization: `Bearer ${process.env.NEXO_API_KEY}` },
          timeout: 15000, // Timeout defensivo de 15 segundos
        },
      );

      const iaText =
        nexoResponse.data.respuesta || "No pude procesar tu solicitud.";
      console.log(`[NEXO ULTRA-DEBUG] 4️⃣ LLM Exitoso: "${iaText}"`);

      // 3. Reproducir respuesta vía TTS Stream (Regla 2)
      console.log(`[NEXO ULTRA-DEBUG] 5️⃣ Enviando a ElevenLabs (TTS)...`);
      await this.speak(guildId, iaText);
      console.log(
        `[NEXO ULTRA-DEBUG] 6️⃣ Audio enviado al reproductor de Discord.`,
      );

      this.resetIdleTimer(guildId);
    } catch (error) {
      // ESTO ES CRÍTICO PARA EL DEBUG
      const apiError = error.response
        ? JSON.stringify(error.response.data)
        : error.message;
      console.error(`[NEXO ULTRA-DEBUG FATAL] Fallo en el pipeline:`, apiError);
    } finally {
      concurrencySemaphore.release();
    }
  }

  async speak(guildId, text) {
    const connection = this.connections.get(guildId);
    if (!connection) return;

    console.log(`[NEXO VOICE] Sintetizando respuesta por stream...`);
    try {
      await playTTS(connection, text);
    } catch (err) {
      console.error("[NEXO VOICE] Error en reproducción TTS:", err.message);
    }
  }

  /**
   * Cambiar modo de voz en caliente.
   * @param {'classic'|'live'} mode
   */
  async setVoiceMode(mode) {
    const prev = this.voiceMode;
    this.voiceMode = mode;
    console.log(`[NEXO VOICE] Modo cambiado: ${prev} → ${mode}`);
    if (mode === "live") {
      try {
        const bridge = getGeminiLiveBridge();
        if (!bridge.connected) await bridge.connect();
        console.log("[NEXO VOICE] Gemini Live bridge activo");
      } catch (e) {
        console.error(
          "[NEXO VOICE] No se pudo activar Gemini Live, volviendo a classic:",
          e.message,
        );
        this.voiceMode = "classic";
      }
    }
    return this.voiceMode;
  }

  /**
   * Procesar audio del usuario en modo Gemini Live (streaming directo).
   * En vez de guardar archivo → STT → LLM → TTS, envía PCM a Gemini Live
   * y reproduce la respuesta de audio directamente.
   */
  async processUserAudioLive(filePath, guildId, userId) {
    const bridge = getGeminiLiveBridge();
    if (!bridge.connected) {
      try {
        await bridge.connect();
      } catch (e) {
        console.error(
          "[NEXO VOICE LIVE] Bridge no disponible, cayendo a classic",
        );
        return this.processUserAudio(filePath, guildId, userId);
      }
    }

    try {
      // Leer el WAV/PCM capturado y enviarlo a Gemini Live
      const audioBuffer = fs.readFileSync(filePath);
      if (fs.existsSync(filePath)) fs.unlinkSync(filePath);

      console.log(
        `[NEXO VOICE LIVE] Enviando ${audioBuffer.length} bytes a Gemini Live...`,
      );
      bridge.sendAudio(audioBuffer);
      bridge.sendEndOfTurn();

      // Esperar respuesta (max 15s)
      await new Promise((resolve) => setTimeout(resolve, 3000));

      const connection = this.connections.get(guildId);
      if (connection && bridge.audioQueue.length > 0) {
        console.log(
          `[NEXO VOICE LIVE] Reproduciendo respuesta de Gemini (${bridge.audioQueue.length} chunks)`,
        );
        await bridge.playResponseInDiscord(connection);
      } else {
        console.log("[NEXO VOICE LIVE] Sin respuesta de audio de Gemini");
      }

      this.resetIdleTimer(guildId);
    } catch (e) {
      console.error("[NEXO VOICE LIVE] Error:", e.message);
      if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
    }
  }

  leaveChannel(guildId) {
    const connection = this.connections.get(guildId);
    if (connection) {
      if (this.idleTimers.has(guildId))
        clearTimeout(this.idleTimers.get(guildId));
      connection.destroy();
      this.connections.delete(guildId);
      this.players.delete(guildId);
      console.log(`[NEXO VOICE] Desconectado del canal.`);
    }
  }
}

module.exports = VoiceOrchestrator;
