require("dotenv").config();
const { playTTS } = require("./tts_service");
const { transcribeFile } = require("./stt_service");
const {
  Client,
  GatewayIntentBits,
  EmbedBuilder,
  SlashCommandBuilder,
  Partials,
} = require("discord.js");
const {
  joinVoiceChannel,
  getVoiceConnection,
  VoiceConnectionStatus,
  entersState,
  EndBehaviorType,
} = require("@discordjs/voice");
const axios = require("axios");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");
const prism = require("prism-media");

const FASTAPI_URL = (
  process.env.FASTAPI_URL || "http://127.0.0.1:8080"
).replace(/\/$/, "");
const { runProactiveLoop, handleOsintCommand } = require("./proactive_intel");
const {
  detectarViolacion,
  moderar,
  asegurarEstructura,
} = require("./nexo_guard");
const {
  processVoiceIntelligence,
  handleStreamsCommand,
  handleCaptureCommand,
  handleStopCaptureCommand,
} = require("./voice_intelligence");
const { getGeminiLiveBridge } = require("./gemini_live_bridge");
const { shouldNexoSpeak, notificarAvatarHablando, recordSpeak, recordSilence } = require("./nexo_autonomy");

// Voice mode global: 'classic' (STT+LLM+TTS) or 'live' (Gemini 3.1 Flash Live)
let currentVoiceMode = (process.env.VOICE_MODE || "classic").toLowerCase();

if (!process.env.DISCORD_TOKEN) {
  console.error("[NEXO ERROR] DISCORD_TOKEN no encontrada");
  process.exit(1);
}

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildVoiceStates,
    GatewayIntentBits.GuildMembers,
  ],
  partials: [Partials.Channel],
});

// ── Detección de comandos OBS por voz ────────────────────────────────────────
const OBS_VOICE_PATTERNS = [
  { re: /\b(pausa|pon(te)? en pausa|descansa|brb)\b/i,                        scene: 'NEXO_PAUSA'    },
  { re: /\b(intro|abre|inicio|pon(me)? la intro)\b/i,                          scene: 'NEXO_INTRO'    },
  { re: /\b(alerta|emergencia|modo alerta|modo emergencia)\b/i,                 scene: 'NEXO_ALERTA'   },
  { re: /\b(mercados?|finanzas?|cripto|bitcoin)\b/i,                            scene: 'NEXO_MERCADOS' },
  { re: /\b(inteligencia|intel|osint)\b/i,                                      scene: 'NEXO_INTEL'    },
  { re: /\b(an[aá]lisis|anali[sz]a)\b/i,                                        scene: 'NEXO_ANALISIS' },
  { re: /\b(mapa|geogr[aá]fico|territorio)\b/i,                                 scene: 'NEXO_MAPA'     },
  { re: /\b(grafo|red|conexiones|nodos?)\b/i,                                   scene: 'NEXO_GRAFO'    },
  { re: /\b(pantalla|comparte|screen|captura)\b/i,                              scene: 'NEXO_PANTALLA' },
  { re: /\b(base|inicio|portada|home|principal)\b/i,                            scene: 'NEXO_BASE'     },
  // Directo: "pon escena X" / "cambia a X" / "escena X"
  { re: /\b(pon|cambia|switch|escena|scene)\s+(a\s+)?nexo[_\s]?(\w+)/i,        scene: null, capture: 3 },
];

function detectarComandoOBS(text) {
  const t = text.toLowerCase().trim();
  // Solo actuar si hay palabra clave de escena explícita
  if (!/\b(escena|scene|pon(me)?|cambia|modo|alerta|pausa|intro|mercado|intel|an[aá]lisis|mapa|grafo|pantalla|base)\b/i.test(t)) {
    return null;
  }
  for (const p of OBS_VOICE_PATTERNS) {
    const m = t.match(p.re);
    if (m) {
      if (p.scene) return p.scene;
      if (p.capture && m[p.capture]) {
        return `NEXO_${m[p.capture].toUpperCase()}`;
      }
    }
  }
  return null;
}

const commands = [
  new SlashCommandBuilder()
    .setName("nexo")
    .setDescription("Pregunta a Gemma local")
    .addStringOption((o) =>
      o.setName("query").setDescription("Pregunta").setRequired(true),
    )
    .addStringOption((o) =>
      o
        .setName("modelo")
        .setDescription("Tier: fast|balanced|rag|large|code")
        .setRequired(false)
        .addChoices(
          { name: "fast (1b) — respuesta rápida", value: "fast" },
          { name: "balanced (4b) — uso general", value: "balanced" },
          { name: "rag (12b) — análisis profundo", value: "rag" },
          { name: "large (27b) — máxima calidad", value: "large" },
          { name: "code — programación", value: "code" },
        ),
    ),
  new SlashCommandBuilder()
    .setName("status")
    .setDescription("Métricas del sistema"),
  new SlashCommandBuilder()
    .setName("osint")
    .setDescription(
      "Estado del OSINT Engine — vuelos, satélites, mercados, amenazas",
    ),
  new SlashCommandBuilder()
    .setName("director")
    .setDescription("Controla el Call Director (OBS autónomo durante llamadas)")
    .addStringOption((o) =>
      o
        .setName("accion")
        .setDescription("activar|desactivar|estado|escena")
        .setRequired(true)
        .addChoices(
          { name: "Activar director (modo llamada)", value: "activar" },
          { name: "Pausar director", value: "desactivar" },
          { name: "Ver estado", value: "estado" },
        ),
    )
    .addStringOption((o) =>
      o
        .setName("escena")
        .setDescription("Nombre de escena OBS (para cambio manual)")
        .setRequired(false),
    ),
  new SlashCommandBuilder()
    .setName("actor")
    .setDescription("Gestiona el mapa de conexiones entre actores")
    .addStringOption((o) =>
      o
        .setName("accion")
        .setDescription("nuevo|buscar|grafo|analizar")
        .setRequired(true)
        .addChoices(
          { name: "Abrir mapa de conexiones", value: "grafo" },
          { name: "Buscar actor", value: "buscar" },
          { name: "Analizar actor con Gemma", value: "analizar" },
        ),
    )
    .addStringOption((o) =>
      o
        .setName("query")
        .setDescription("Nombre del actor a buscar/analizar")
        .setRequired(false),
    ),
  new SlashCommandBuilder()
    .setName("briefing")
    .setDescription("Genera el briefing de inteligencia diario ahora"),
  new SlashCommandBuilder()
    .setName("buscar")
    .setDescription("Busca en internet y analiza con Gemma")
    .addStringOption((o) =>
      o.setName("query").setDescription("Qué buscar").setRequired(true),
    )
    .addStringOption((o) =>
      o
        .setName("modelo")
        .setDescription("fast|balanced|rag")
        .setRequired(false),
    ),
  new SlashCommandBuilder()
    .setName("streams")
    .setDescription("Streams en vivo recomendados para un tema")
    .addStringOption((o) =>
      o.setName("tema").setDescription("Tema o región").setRequired(false),
    ),
  new SlashCommandBuilder()
    .setName("captura")
    .setDescription("Inicia grabación de contenido")
    .addStringOption((o) =>
      o.setName("fuente").setDescription("phone|screen|obs").setRequired(false),
    )
    .addStringOption((o) =>
      o
        .setName("tag")
        .setDescription("MIL|ECO|GEO|POL|PSY|GEN")
        .setRequired(false),
    )
    .addStringOption((o) =>
      o
        .setName("titulo")
        .setDescription("Título de la captura")
        .setRequired(false),
    ),
  new SlashCommandBuilder()
    .setName("parar")
    .setDescription("Detiene una grabación activa")
    .addStringOption((o) =>
      o
        .setName("session_id")
        .setDescription("ID de la sesión")
        .setRequired(true),
    ),
  new SlashCommandBuilder()
    .setName("temas")
    .setDescription("Lista temas estratégicos en seguimiento"),
  new SlashCommandBuilder()
    .setName("dispositivo")
    .setDescription("Controla el Xiaomi remotamente via NEXO Mobile Agent")
    .addStringOption((o) =>
      o
        .setName("accion")
        .setDescription("silenciar|volumen_max|pantalla_off|vibrar|ubicacion|foto_frontal|ping|reiniciar_tailscale|estado")
        .setRequired(true)
        .addChoices(
          { name: "silenciar — mute total", value: "silenciar" },
          { name: "volumen_max — subir volumen", value: "volumen_max" },
          { name: "pantalla_off — apagar pantalla", value: "pantalla_off" },
          { name: "vibrar — vibración", value: "vibrar" },
          { name: "ubicacion — GPS actual", value: "ubicacion" },
          { name: "foto_frontal — captura frontal", value: "foto_frontal" },
          { name: "ping — verificar conexión", value: "ping" },
          { name: "reiniciar_tailscale — reconectar VPN", value: "reiniciar_tailscale" },
          { name: "estado — ver batería y métricas", value: "estado" },
        ),
    )
    .addStringOption((o) =>
      o.setName("agente").setDescription("ID del agente (default: xiaomi-14t-pro-1)").setRequired(false),
    ),
  new SlashCommandBuilder()
    .setName("youtube")
    .setDescription(
      "Registra un stream YouTube activo para que NEXO lo monitoree",
    )
    .addStringOption((o) =>
      o.setName("url").setDescription("URL del video/stream").setRequired(true),
    )
    .addStringOption((o) =>
      o
        .setName("titulo")
        .setDescription("Título del contenido")
        .setRequired(false),
    ),
  new SlashCommandBuilder()
    .setName("sesion")
    .setDescription("Estado de la sesión cognitiva activa"),
  new SlashCommandBuilder()
    .setName("canva")
    .setDescription(
      "Crea un diseño visual en Canva con datos de inteligencia NEXO",
    )
    .addStringOption((o) =>
      o
        .setName("tema")
        .setDescription(
          'Qué diseñar — ej: "infografía de tensiones en el Estrecho de Taiwán"',
        )
        .setRequired(true),
    )
    .addStringOption((o) =>
      o
        .setName("tipo")
        .setDescription("poster|infografia|presentacion|documento")
        .setRequired(false),
    ),
  new SlashCommandBuilder()
    .setName("metacog")
    .setDescription("Estadísticas de metacognición del motor cognitivo"),
  new SlashCommandBuilder()
    .setName("agente")
    .setDescription("Gestiona agentes autónomos NEXO")
    .addStringOption((o) =>
      o
        .setName("accion")
        .setDescription("lista|nuevo|activar|desactivar|ejecutar|plantillas")
        .setRequired(true)
        .addChoices(
          { name: "Listar agentes", value: "lista" },
          { name: "Ver plantillas disponibles", value: "plantillas" },
          { name: "Ejecutar ciclo manual", value: "ejecutar" },
          { name: "Activar agente", value: "activar" },
          { name: "Desactivar agente", value: "desactivar" },
        ),
    )
    .addStringOption((o) =>
      o
        .setName("id")
        .setDescription("ID del agente o plantilla")
        .setRequired(false),
    ),
  new SlashCommandBuilder()
    .setName("crear-agente")
    .setDescription("Crea un agente autónomo desde plantilla")
    .addStringOption((o) =>
      o
        .setName("plantilla")
        .setDescription(
          "mercados|osint_sweep|vuelos|amenazas_cyber|noticias_geopolitica|playwright_web",
        )
        .setRequired(true),
    )
    .addStringOption((o) =>
      o
        .setName("nombre")
        .setDescription("Nombre personalizado (opcional)")
        .setRequired(false),
    ),
  new SlashCommandBuilder()
    .setName("mcp")
    .setDescription("Usa herramientas MCP (playwright, cloudflare, discord)")
    .addStringOption((o) =>
      o
        .setName("herramienta")
        .setDescription("screenshot|scrape|tools|status")
        .setRequired(true)
        .addChoices(
          { name: "Ver estado del gateway", value: "status" },
          { name: "Listar herramientas", value: "tools" },
          { name: "Captura de pantalla web", value: "screenshot" },
          { name: "Extraer texto de web", value: "scrape" },
        ),
    )
    .addStringOption((o) =>
      o
        .setName("url")
        .setDescription("URL (para screenshot/scrape)")
        .setRequired(false),
    ),
  new SlashCommandBuilder()
    .setName("vocalmode")
    .setDescription("Controla si NEXO habla contigo, en el stream, o en ambos")
    .addStringOption((o) =>
      o.setName("modo")
        .setDescription("privado | stream | ambos")
        .setRequired(true)
        .addChoices(
          { name: "privado — solo en Discord, no en el stream", value: "privado" },
          { name: "stream — solo para la audiencia del stream",  value: "stream"  },
          { name: "ambos — Discord + stream simultáneo",         value: "ambos"   },
        ),
    ),
  new SlashCommandBuilder()
    .setName("unirse")
    .setDescription("NEXO entra al canal de voz"),
  new SlashCommandBuilder()
    .setName("salir")
    .setDescription("NEXO sale del canal de voz"),
  new SlashCommandBuilder()
    .setName("voice")
    .setDescription("Cambia el modo de voz de NEXO")
    .addStringOption((o) =>
      o
        .setName("modo")
        .setDescription("classic = STT+LLM+TTS | live = Gemini Live streaming")
        .setRequired(true)
        .addChoices(
          { name: "classic — Whisper STT + LLM + TTS", value: "classic" },
          { name: "live — Gemini 3.1 Flash Live (streaming)", value: "live" },
        ),
    ),
  new SlashCommandBuilder()
    .setName("drive")
    .setDescription("Busca información en el Drive de NEXO")
    .addStringOption((opt) =>
      opt
        .setName("consulta")
        .setDescription("Qué quieres buscar o preguntar")
        .setRequired(true),
    ),
  new SlashCommandBuilder()
    .setName("geopolitica")
    .setDescription("Consulta la carpeta Geopolítica del Drive")
    .addStringOption((opt) =>
      opt
        .setName("tema")
        .setDescription("Tema geopolítico a consultar")
        .setRequired(false),
    ),
  new SlashCommandBuilder()
    .setName("torre")
    .setDescription("Control total de la Torre (OBS, backend, sync, logs)")
    .addStringOption((o) =>
      o.setName("accion")
        .setDescription("Qué quieres hacer")
        .setRequired(true)
        .addChoices(
          { name: "⚡ encender — Startup completo de la Torre",    value: "encender" },
          { name: "status — Estado general de la torre",        value: "status"   },
          { name: "obs — Estado y escenas de OBS",              value: "obs"      },
          { name: "director — Activa IA directora de OBS",      value: "director" },
          { name: "stream — Iniciar/detener stream en OBS",     value: "stream"   },
          { name: "sync — Sincronizar Drive/Photos/OneDrive",   value: "sync"     },
          { name: "logs — Últimas líneas del log del backend",  value: "logs"     },
          { name: "reiniciar-bot — Reinicia el bot de Discord", value: "restart"  },
          { name: "pm2 — Estado de todos los procesos PM2",     value: "pm2"      },
        ),
    ),
  new SlashCommandBuilder()
    .setName("social")
    .setDescription("Monitorea o analiza redes sociales")
    .addStringOption((opt) =>
      opt
        .setName("accion")
        .setDescription("monitor, analizar, estado")
        .setRequired(true)
        .addChoices(
          { name: "Ver estado social media", value: "estado" },
          { name: "Analizar sentimiento", value: "analizar" },
        ),
    )
    .addStringOption((opt) =>
      opt
        .setName("texto")
        .setDescription("Texto o keywords para analizar")
        .setRequired(false),
    ),
  new SlashCommandBuilder()
    .setName("video")
    .setDescription("Sistema de creación de contenido: Reels, TikTok, YouTube")
    .addStringOption((opt) =>
      opt
        .setName("accion")
        .setDescription("Qué hacer")
        .setRequired(true)
        .addChoices(
          { name: "auto-reel — Genera reel automático del día",        value: "auto_reel"  },
          { name: "auto-youtube — Genera video largo del día",         value: "auto_yt"    },
          { name: "estado — Ver jobs de video activos",                value: "estado"     },
          { name: "publicar — Publicar último video en YouTube",       value: "publicar"   },
        ),
    )
    .addStringOption((opt) =>
      opt
        .setName("titulo")
        .setDescription("Título opcional para el video")
        .setRequired(false),
    ),
  // ── Claude Code terminal integration ──────────────────────────────────────
  new SlashCommandBuilder()
    .setName("claude")
    .setDescription("Consulta directa a Claude Sonnet — análisis profundo, código, estrategia")
    .addStringOption(o =>
      o.setName("prompt").setDescription("Qué quieres preguntarle a Claude").setRequired(true),
    )
    .addStringOption(o =>
      o.setName("modo")
        .setDescription("Modo de respuesta")
        .addChoices(
          { name: "análisis", value: "analisis" },
          { name: "código", value: "codigo" },
          { name: "estrategia", value: "estrategia" },
          { name: "resumen", value: "resumen" },
        )
        .setRequired(false),
    ),
  new SlashCommandBuilder()
    .setName("cmd")
    .setDescription("Ejecutar comando NEXO desde Discord (terminal remoto)")
    .addStringOption(o =>
      o.setName("accion")
        .setDescription("Comando a ejecutar")
        .setRequired(true)
        .addChoices(
          { name: "status — estado del sistema",        value: "status" },
          { name: "logs — últimas líneas del log",      value: "logs" },
          { name: "drive sync — sincronizar Drive",     value: "drive_sync" },
          { name: "drive status — estado de Drive",     value: "drive_status" },
          { name: "restart bot — reiniciar bot",        value: "restart_bot" },
          { name: "restart api — reiniciar backend",    value: "restart_api" },
          { name: "scout — innovation scout",           value: "scout" },
          { name: "reel — generar reel del día",        value: "reel" },
          { name: "modelos — modelos Ollama activos",   value: "models" },
        ),
    ),
  new SlashCommandBuilder()
    .setName("config")
    .setDescription("Ver o configurar variables de NEXO (solo admin)")
    .addStringOption(o =>
      o.setName("accion")
        .setDescription("Ver o modificar")
        .setRequired(true)
        .addChoices(
          { name: "ver — mostrar config actual",   value: "ver" },
          { name: "voz — modo de voz",             value: "voz" },
          { name: "modelo — modelo Ollama activo", value: "modelo" },
        ),
    )
    .addStringOption(o =>
      o.setName("valor").setDescription("Nuevo valor (si aplica)").setRequired(false),
    ),
];

// ── Estado global de voz/chat ─────────────────────────────────────────────────
let _activeConnection = null;   // VoiceConnection actual
let _activeTextChannel = null;  // Canal texto asociado a la llamada activa
let _voiceReconnectTimer = null;
const _chatCooldowns_map = new Map(); // channelId → timestamp del último reply

async function autoJoinVoice(c) {
  const channelId = process.env.VOICE_CHANNEL_ID;
  const guildId   = process.env.VOICE_GUILD_ID || process.env.DISCORD_GUILD_ID;
  if (!channelId || !guildId) return;
  try {
    const guild   = await c.guilds.fetch(guildId);
    const channel = await guild.channels.fetch(channelId);
    if (!channel?.isVoiceBased()) return;
    // Canal texto emparejado: buscar primero 'nexo-voz', luego 'general', luego cualquiera
    const textChannels = guild.channels.cache.filter(ch => ch.isTextBased());
    _activeTextChannel =
      textChannels.find(ch => ch.name.includes('nexo')) ||
      textChannels.find(ch => ch.name.includes('general')) ||
      textChannels.first();

    // Destruir conexión previa si existe
    const existing = getVoiceConnection(guildId);
    if (existing) { try { existing.destroy(); } catch(_) {} }

    _activeConnection = joinVoiceChannel({
      channelId: channel.id,
      guildId,
      adapterCreator: guild.voiceAdapterCreator,
      selfDeaf: false,
      selfMute: false,
    });

    _activeConnection.on(VoiceConnectionStatus.Disconnected, async () => {
      console.log('[NEXO VOICE] Desconectado — nueva sesión en 20s...');
      try { _activeConnection.destroy(); } catch(_) {}
      _activeConnection = null;
      clearTimeout(_voiceReconnectTimer);
      _voiceReconnectTimer = setTimeout(() => autoJoinVoice(c), 60_000);
    });

    _activeConnection.on(VoiceConnectionStatus.Connecting, () => {
      console.log('[NEXO VOICE] Estado: Connecting (UDP handshake)...');
    });
    _activeConnection.on(VoiceConnectionStatus.Signalling, () => {
      console.log('[NEXO VOICE] Estado: Signalling (WebSocket OK, esperando UDP)...');
    });
    _activeConnection.on(VoiceConnectionStatus.Destroyed, () => {
      console.log('[NEXO VOICE] Conexión destruida.');
    });

    console.log(`[NEXO VOICE] Uniéndose a: ${channel.name}... esperando Ready (30s)`);

    try {
      // Esperar hasta 30s que Ready se alcance (UDP handshake completo)
      await entersState(_activeConnection, VoiceConnectionStatus.Ready, 30_000);
      console.log(`[NEXO VOICE] ✅ READY — receiver activo en: ${channel.name}`);
      setupVoiceHandler(_activeConnection, _activeTextChannel);
      if (_activeTextChannel) {
        _activeTextChannel.send('🎙️ **NEXO** listo en el canal de voz. Habla para activar IA.').catch(() => {});
      }
    } catch (readyErr) {
      console.warn('[NEXO VOICE] ⚠️ UDP no completó en 30s. Estado:', _activeConnection.state.status);
      // El receiver puede igualmente funcionar en algunos casos — intentar de todas formas
      setupVoiceHandler(_activeConnection, _activeTextChannel);
      if (_activeTextChannel) {
        _activeTextChannel.send(
          '⚠️ **NEXO Voz:** Conexión UDP parcial — si no respondo, ejecuta `! netsh advfirewall firewall add rule name="NodeJS UDP" dir=in action=allow program="C:\\Program Files\\nodejs\\node.exe" protocol=udp` en tu terminal para abrir el firewall UDP.'
        ).catch(() => {});
      }
      // Reintentar conexión completa en 60s
      clearTimeout(_voiceReconnectTimer);
      _voiceReconnectTimer = setTimeout(() => autoJoinVoice(c), 300_000); // 5 min backoff
    }

    // Activar Call Director OBS
    axios.post(`${FASTAPI_URL}/api/intel/director/activar`, {}, {
      headers: { 'x-nexo-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' }, timeout: 3000
    }).then(() => console.log('[NEXO OBS] Call Director activado')).catch(() => {});

  } catch(e) {
    console.warn('[NEXO VOICE] No se pudo auto-unir:', e.message);
    clearTimeout(_voiceReconnectTimer);
    _voiceReconnectTimer = setTimeout(() => autoJoinVoice(c), 30_000);
  }
}

client.once("clientReady", async (c) => {
  console.log(`[NEXO] Bot conectado como ${c.user.tag}`);
  // Iniciar loop de inteligencia proactiva
  runProactiveLoop(c).catch((e) =>
    console.error("[NEXO Proactive] Error fatal:", e.message),
  );
  // Auto-join: si alguien ya está en el canal de voz al arrancar, unirse
  const voiceChannelId = process.env.VOICE_CHANNEL_ID;
  const voiceGuildId   = process.env.VOICE_GUILD_ID || process.env.DISCORD_GUILD_ID;
  if (voiceChannelId && voiceGuildId) {
    setTimeout(async () => {
      try {
        const g   = await c.guilds.fetch(voiceGuildId);
        const ch  = await g.channels.fetch(voiceChannelId);
        const humans = ch?.members?.filter(m => !m.user.bot);
        if (humans?.size > 0) {
          console.log(`[NEXO VOICE] Humanos en ${ch.name} al arrancar — uniéndome`);
          await autoJoinVoice(c);
        } else {
          console.log(`[NEXO VOICE] Canal vacío al arrancar — esperando que alguien entre`);
        }
      } catch (e) {
        console.warn('[NEXO VOICE] No se pudo verificar canal al arrancar:', e.message);
      }
    }, 5000);
  }
  try {
    const guildId = process.env.DISCORD_GUILD_ID;
    if (guildId) {
      try {
        const guild = await client.guilds.fetch(guildId);
        await guild.commands.set(commands);
        console.log(`Comandos registrados en guild ${guildId}`);
      } catch (guildErr) {
        console.warn(
          `[NEXO] Guild ${guildId} no accesible (${guildErr.message}), usando comandos globales`,
        );
        await client.application.commands.set(commands);
        console.log("Comandos globales registrados (fallback)");
      }
    } else {
      await client.application.commands.set(commands);
      console.log("Comandos globales registrados");
    }
  } catch (err) {
    console.error("Error registrando comandos:", err.message);
  }

  // Asegurar estructura mínima del servidor (canales NEXO)
  try {
    const guildId = process.env.DISCORD_GUILD_ID;
    if (guildId) {
      const guild = await c.guilds.fetch(guildId);
      const creados = await asegurarEstructura(guild);
      if (creados.length)
        console.log(`[NEXO Guard] Canales creados: ${creados.join(", ")}`);
      else console.log("[NEXO Guard] Estructura de canales OK");
    }
  } catch (e) {
    console.warn("[NEXO Guard] No se pudo verificar estructura:", e.message);
  }
});

// ── Auto-reconexión cuando el dueño entra al canal ───────────────────────────
client.on("voiceStateUpdate", async (oldState, newState) => {
  if (newState.member?.user?.bot) return;
  const configChannelId = process.env.VOICE_CHANNEL_ID;
  const guildId = process.env.VOICE_GUILD_ID || process.env.DISCORD_GUILD_ID;
  if (!configChannelId || newState.guild.id !== guildId) return;

  // Usuario entra al canal configurado → bot se une
  if (newState.channelId === configChannelId && !oldState.channelId) {
    const botMember = newState.guild.members.me;
    if (!botMember?.voice?.channelId) {
      console.log(`[NEXO VOICE] ${newState.member.displayName} entró — uniéndome`);
      await autoJoinVoice(client);
    }
  }

  // Usuario sale — bot se queda en el canal esperando que vuelvan
});

// ── Ollama local — respuesta de chat sin coste de API ────────────────────────
const OLLAMA_URL   = process.env.OLLAMA_URL   || 'http://localhost:11434';
const CHAT_MODEL   = process.env.OLLAMA_MODEL_FAST    || 'gemma3:4b';   // rápido para chat
const DEEP_MODEL   = process.env.OLLAMA_MODEL_GENERAL || 'gemma4:latest'; // para análisis

const NEXO_SYSTEM_PROMPT = `Eres NEXO, una inteligencia estratégica soberana. Formas parte del sistema NEXO SOBERANO — una plataforma de análisis geopolítico, OSINT y mercados en tiempo real. Tu dueño es el analista principal. Respondes en español, de forma directa y concisa. Tienes acceso a datos de inteligencia en tiempo real. No eres un asistente genérico — eres una IA de análisis estratégico con criterio propio.`;

async function callOllama(text, model = CHAT_MODEL, systemPrompt = NEXO_SYSTEM_PROMPT) {
  const r = await axios.post(`${OLLAMA_URL}/api/chat`, {
    model,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user',   content: text },
    ],
    stream: false,
    options: { temperature: 0.7, num_predict: 300 },
  }, { timeout: 20000 });
  return r.data?.message?.content?.trim() || null;
}

async function callClaude(text, systemPrompt = NEXO_SYSTEM_PROMPT) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) return null;
  const r = await axios.post('https://api.anthropic.com/v1/messages', {
    model: process.env.CLAUDE_MODEL || 'claude-haiku-4-5-20251001',
    max_tokens: 400,
    system: systemPrompt,
    messages: [{ role: 'user', content: text }],
  }, {
    headers: {
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'content-type': 'application/json',
    },
    timeout: 20000,
  });
  return r.data?.content?.[0]?.text?.trim() || null;
}

// Detectar si el mensaje requiere el motor completo (Gemini + OSINT + herramientas)
const DEEP_KEYWORDS = /\b(busca|analiza|alerta|mercado|bitcoin|osint|geopolít|satél|vuelo|cisa|predic|urgente|critico|datos|informe|noticias|qué está pasando)\b/i;

async function informarCognitivoBackground(text, channelId, userId) {
  // Fire & forget — NEXO se entera sin bloquear la respuesta
  axios.post(
    `${FASTAPI_URL}/api/cognitive/process`,
    { text, channel_id: channelId, user_id: userId },
    { headers: { 'x-nexo-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' }, timeout: 30000 }
  ).catch(() => {}); // silencio si falla — es background
}

// ── Chat: la IA recibe todo y decide cuándo responder ───────────────────────
client.on("messageCreate", async (message) => {
  if (message.author.bot || !message.guild) return;

  // Moderación siempre
  try {
    const violacion = detectarViolacion(message);
    if (violacion) await moderar(message, violacion);
  } catch (e) {
    console.error("[NEXO Guard] Error en moderación:", e.message);
  }

  const raw = message.content.trim();
  if (!raw || raw.startsWith('/') || raw.length < 2) return;

  const botMentioned = message.mentions.has(client.user);
  const autochatChannels = (process.env.AUTOCHAT_CHANNEL_IDS || '').split(',').filter(Boolean);
  const listenAll = autochatChannels.length === 0;
  if (!botMentioned && !listenAll && !autochatChannels.includes(message.channelId)) return;

  const text = raw.replace(/<@!?\d+>/g, '').trim();
  if (!text) return;

  // ── ¿Necesita motor completo (OSINT + herramientas) o Gemma local basta? ──
  const needsDeep = botMentioned || DEEP_KEYWORDS.test(text);

  let cogResult   = null;
  let respuesta   = null;
  let intent      = 'CONVERSACION';

  if (needsDeep) {
    // Motor cognitivo completo — Gemini + OSINT + herramientas
    message.channel.sendTyping().catch(() => {});
    try {
      const r = await axios.post(
        `${FASTAPI_URL}/api/cognitive/process`,
        { text, channel_id: message.channelId, user_id: message.author.id },
        { headers: { 'x-nexo-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' }, timeout: 30000 }
      );
      cogResult = r.data;
      respuesta = cogResult?.response || cogResult?.respuesta;
      intent    = cogResult?.intent || 'ANALISIS';
    } catch(e) {
      // Fallback: Gemini falló → intentar Claude → intentar Gemma local
      console.warn('[NEXO CHAT] Gemini falló, intentando Claude...');
      respuesta = await callClaude(text).catch(() => null);
      if (!respuesta) respuesta = await callOllama(text, DEEP_MODEL).catch(() => null);
      intent    = respuesta ? 'LOCAL' : 'ERROR';
    }
  } else {
    // Gemma local para conversación — gratis, instantáneo
    // Informar al cognitivo en background para que NEXO esté al tanto
    informarCognitivoBackground(text, message.channelId, message.author.id);

    message.channel.sendTyping().catch(() => {});
    respuesta = await callOllama(text, CHAT_MODEL).catch(() => null);
    intent    = 'LOCAL';
  }

  if (!respuesta) {
    if (botMentioned) message.reply('Sistema procesando. Un momento.').catch(() => {});
    return;
  }

  // ── Cooldown simple para texto (evitar spam, no silenciar conversaciones) ──
  const _chatCooldowns = _chatCooldowns_map;
  const lastReply = _chatCooldowns.get(message.channelId) || 0;
  const elapsed   = Date.now() - lastReply;
  if (!botMentioned && elapsed < 3000) {
    return; // anti-spam: 3s entre respuestas no mencionadas
  }
  _chatCooldowns.set(message.channelId, Date.now());
  recordSpeak(message.channelId);

  const reason = botMentioned ? 'direct_mention' : (needsDeep ? `intent_${intent}` : 'chat');
  console.log(`[NEXO CHAT] mode=${needsDeep?'deep':'local'} intent=${intent} reason=${reason}`);

  // ── Responder ─────────────────────────────────────────────────────────────
  const label = intent === 'LOCAL' ? '🤖' : `**[${intent}]**`;

  if (cogResult?.urgent) {
    const { EmbedBuilder } = require('discord.js');
    const embed = new EmbedBuilder()
      .setColor(0xef4444)
      .setTitle(`⚡ NEXO [${intent}]`)
      .setDescription(respuesta.substring(0, 2000))
      .setTimestamp();
    await message.reply({ embeds: [embed] }).catch(() => {});
  } else {
    await message.reply(`**[${intent}]** ${respuesta.substring(0, 1900)}`).catch(() => {});
  }

  // ── Si está en llamada activa, también hablar por voz ────────────────────
  if (_activeConnection) {
    playTTS(_activeConnection, respuesta).catch(() => {});
  }
});

client.on("interactionCreate", async (interaction) => {
  if (!interaction.isChatInputCommand()) return;
  await interaction.deferReply();
  const { commandName, options, user, guildId, channel } = interaction;

  if (commandName === "youtube") {
    const url = options.getString("url");
    const titulo = options.getString("titulo") || url;
    const chanId = interaction.channelId;
    try {
      await axios.post(
        `${FASTAPI_URL}/api/cognitive/youtube`,
        {
          channel_id: chanId,
          url,
          title: titulo,
        },
        {
          headers: {
            "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
          },
          timeout: 8000,
        },
      );
      return interaction.editReply(
        `📺 Stream registrado: **${titulo}**\nNEXO monitorea el contenido y alertará si algo relevante ocurre.`,
      );
    } catch (e) {
      return interaction.editReply(`Error: ${e.message}`);
    }
  }

  if (commandName === "sesion") {
    const chanId = interaction.channelId;
    try {
      const r = await axios.get(
        `${FASTAPI_URL}/api/cognitive/session?channel_id=${chanId}`,
        {
          headers: {
            "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
          },
          timeout: 8000,
        },
      );
      const s = r.data;
      const { EmbedBuilder } = require("discord.js");
      const embed = new EmbedBuilder()
        .setColor(0x818cf8)
        .setTitle("🧠 Sesión Cognitiva NEXO")
        .addFields(
          { name: "ID Sesión", value: s.session_id || "—", inline: true },
          { name: "Turnos", value: String(s.turns || 0), inline: true },
          {
            name: "YouTube activo",
            value: s.youtube_active
              ? `✅ ${s.youtube_context?.title || "?"}`
              : "—",
            inline: false,
          },
          {
            name: "Temas activos",
            value: s.active_topics?.length
              ? s.active_topics.join(", ")
              : "Ninguno",
            inline: false,
          },
        )
        .setTimestamp();
      return interaction.editReply({ embeds: [embed] });
    } catch (e) {
      return interaction.editReply(`Error: ${e.message}`);
    }
  }

  if (commandName === "osint") return handleOsintCommand(interaction);
  if (commandName === "streams") return handleStreamsCommand(interaction);
  if (commandName === "captura") return handleCaptureCommand(interaction);
  if (commandName === "parar") {
    const sid = options.getString("session_id");
    return handleStopCaptureCommand(interaction, sid);
  }

  if (commandName === "temas") {
    try {
      const r = await axios.get(`${FASTAPI_URL}/api/topics`, {
        headers: {
          "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
        },
        timeout: 10000,
      });
      const topics = r.data?.topics || [];
      if (!topics.length)
        return interaction.editReply(
          "No hay temas en seguimiento. Créalos en `/control/osint`.",
        );
      const { EmbedBuilder } = require("discord.js");
      const embed = new EmbedBuilder()
        .setColor(0x4ade80)
        .setTitle("📡 Temas en Seguimiento — NEXO")
        .setDescription(
          topics
            .slice(0, 10)
            .map(
              (t) =>
                `**${t.name}** [${t.priority}] — ${t.events?.length || 0} eventos · ${t.drive_files?.length || 0} videos Drive`,
            )
            .join("\n"),
        )
        .setTimestamp();
      return interaction.editReply({ embeds: [embed] });
    } catch (e) {
      return interaction.editReply(`Error: ${e.message}`);
    }
  }

  if (commandName === "dispositivo") {
    const accion  = options.getString("accion");
    const agente  = options.getString("agente") || "xiaomi-14t-pro-1";
    const headers = { "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK" };

    try {
      // Estado — consulta métricas sin encolar comando
      if (accion === "estado") {
        const r = await axios.get(`${FASTAPI_URL}/api/mobile/agents`, { headers, timeout: 8000 });
        const agentes = r.data?.agentes || {};
        const ag = agentes[agente];
        if (!ag) return interaction.editReply(`📵 Agente \`${agente}\` no encontrado. ¿Está conectado?`);
        const bat  = ag.bateria_pct ?? "?";
        const cpu  = ag.cpu_pct ?? "?";
        const ram  = ag.ram_pct ?? "?";
        const wifi = ag.wifi_ssid ?? "?";
        const seen = ag.ultimo_contacto ? new Date(ag.ultimo_contacto).toLocaleString("es-AR") : "?";
        const carg = ag.cargando ? "⚡ cargando" : "🔋";
        return interaction.editReply(
          `📱 **${agente}**\n${carg} Batería: **${bat}%** | CPU: ${cpu}% | RAM: ${ram}%\nWiFi: ${wifi}\nÚltimo contacto: ${seen}`
        );
      }

      // Encolar comando en el agente mobile
      const r = await axios.post(
        `${FASTAPI_URL}/api/mobile/comando/${agente}`,
        { accion, params: {} },
        { headers, timeout: 8000 },
      );
      const online = r.data?.agente_online;
      const emojis = {
        silenciar: "🔇", volumen_max: "🔊", pantalla_off: "📵",
        vibrar: "📳", ubicacion: "📍", foto_frontal: "📷",
        ping: "🏓", reiniciar_tailscale: "🔗",
      };
      const emoji = emojis[accion] || "📱";
      const estado = online ? "agente online — ejecutando ahora" : "agente offline — se ejecutará al reconectar";
      return interaction.editReply(`${emoji} \`${accion}\` encolado para **${agente}**\n_${estado}_`);

    } catch (e) {
      const msg = e.response?.data?.detail || e.message;
      return interaction.editReply(`❌ Error: ${msg}`);
    }
  }

  if (commandName === "osint") {
    // fallthrough eliminated above
  }

  if (commandName === "briefing") {
    // Genera diario de inteligencia del día con Gemma local
    try {
      const r = await axios.post(
        `${FASTAPI_URL}/api/intel/diario`,
        {},
        {
          headers: {
            "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
          },
          timeout: 120000,
        },
      );
      const d = r.data;
      const preview = (d.markdown || "").slice(0, 1800);
      await interaction.editReply(
        `📋 **DIARIO DE INTELIGENCIA — ${d.fecha}**\n` +
          `> ${d.eventos_count} eventos | Gemma local | Discord ${d.enviado_discord ? "✓" : "—"}\n\n` +
          `\`\`\`md\n${preview}\n\`\`\``,
      );
    } catch (e) {
      await interaction.editReply(`Error generando briefing: ${e.message}`);
    }
    return;
  }

  if (commandName === "director") {
    const accion = options.getString("accion");
    const escena = options.getString("escena");
    try {
      let r;
      if (accion === "activar") {
        r = await axios.post(
          `${FASTAPI_URL}/api/intel/director/activar`,
          {},
          {
            headers: {
              "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
            },
            timeout: 8000,
          },
        );
        const e = r.data.estado;
        return interaction.editReply(
          `🎬 **CALL DIRECTOR ACTIVO**\nOBS bajo control cognitivo\nEscena actual: \`${e.escena_actual || "NEXO_NEUTRO"}\`\nOBS disponible: ${e.obs_disponible ? "✅" : "⚠️ Modo pasivo (revisar OBS_PASSWORD)"}`,
        );
      } else if (accion === "desactivar") {
        r = await axios.post(
          `${FASTAPI_URL}/api/intel/director/desactivar`,
          {},
          {
            headers: {
              "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
            },
            timeout: 8000,
          },
        );
        return interaction.editReply(`⏸ **Call Director pausado**`);
      } else if (accion === "estado") {
        r = await axios.get(`${FASTAPI_URL}/api/intel/director/estado`, {
          headers: {
            "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
          },
          timeout: 8000,
        });
        const e = r.data;
        return interaction.editReply(
          `🎬 **CALL DIRECTOR**\nActivo: ${e.activo ? "✅" : "❌"}\nOBS: ${e.obs_disponible ? "✅" : "⚠️ Pasivo"}\nEscena: \`${e.escena_actual || "ninguna"}\``,
        );
      } else if (escena) {
        r = await axios.post(
          `${FASTAPI_URL}/api/intel/director/escena?escena=${encodeURIComponent(escena)}`,
          {},
          {
            headers: {
              "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
            },
            timeout: 8000,
          },
        );
        return interaction.editReply(`🎬 Escena cambiada a: \`${escena}\``);
      }
    } catch (e) {
      return interaction.editReply(`Error: ${e.message}`);
    }
    return;
  }

  if (commandName === "actor") {
    const accion = options.getString("accion");
    const query = options.getString("query") || "";
    try {
      if (accion === "grafo") {
        const nexoUrl = process.env.FASTAPI_URL || "http://127.0.0.1:8080";
        const r = await axios.get(`${FASTAPI_URL}/api/intel/actores/grafo`, {
          headers: {
            "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
          },
          timeout: 8000,
        });
        const d = r.data;
        const tiposStr = Object.entries(d.stats?.tipos || {})
          .filter(([, v]) => v > 0)
          .map(([k, v]) => `${k}:${v}`)
          .join(" · ");
        return interaction.editReply(
          `🕸 **MAPA DE ACTORES**\n${d.stats.total_actores} actores · ${d.stats.total_conexiones} conexiones\n${tiposStr}\n\n🌐 [Abrir grafo interactivo](${nexoUrl}/grafo)`,
        );
      } else if (accion === "buscar") {
        if (!query)
          return interaction.editReply(
            "Especifica un nombre con la opción `query`",
          );
        const r = await axios.get(
          `${FASTAPI_URL}/api/intel/actores/buscar?q=${encodeURIComponent(query)}`,
          {
            headers: {
              "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
            },
            timeout: 8000,
          },
        );
        const actores = r.data.actores || [];
        if (!actores.length)
          return interaction.editReply(`Sin resultados para: ${query}`);
        const lista = actores
          .slice(0, 5)
          .map(
            (a) =>
              `**${a.nombre}** (${a.tipo}) · ${a.pais || "?"}\n  Parásito: ${Math.round(a.parasite_index * 100)}% · Poder: ${Math.round(a.poder_index * 100)}%\n  ID: \`${a.id}\``,
          )
          .join("\n\n");
        return interaction.editReply(`🔍 **Actores encontrados:**\n\n${lista}`);
      } else if (accion === "analizar") {
        if (!query)
          return interaction.editReply(
            "Especifica el nombre o ID del actor con `query`",
          );
        // Buscar primero
        const rb = await axios.get(
          `${FASTAPI_URL}/api/intel/actores/buscar?q=${encodeURIComponent(query)}`,
          {
            headers: {
              "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
            },
            timeout: 8000,
          },
        );
        const actores = rb.data.actores || [];
        if (!actores.length)
          return interaction.editReply(`Actor no encontrado: ${query}`);
        const id = actores[0].id;
        const ra = await axios.get(
          `${FASTAPI_URL}/api/intel/actores/${id}/analisis`,
          {
            headers: {
              "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
            },
            timeout: 90000,
          },
        );
        const analisis = (ra.data.analisis || "").slice(0, 1800);
        return interaction.editReply(
          `🧠 **Análisis: ${actores[0].nombre}**\n\n${analisis}`,
        );
      }
    } catch (e) {
      return interaction.editReply(`Error: ${e.message}`);
    }
    return;
  }

  if (commandName === "buscar") {
    const query = options.getString("query");
    const modelo = options.getString("modelo") || "rag";
    try {
      const r = await axios.post(
        `${FASTAPI_URL}/api/intel/buscar`,
        { query, modelo },
        {
          headers: {
            "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
          },
          timeout: 120000,
        },
      );
      const d = r.data;
      const texto = (d.analisis || JSON.stringify(d)).slice(0, 1800);
      await interaction.editReply(
        `🌐 **BÚSQUEDA: ${query}**\n*(${d.modelo || modelo})*\n\n${texto}`,
      );
    } catch (e) {
      await interaction.editReply(`Error buscando: ${e.message}`);
    }
    return;
  }

  if (commandName === "nexo") {
    const query = options.getString("query");
    const modelo = options.getString("modelo") || "balanced";
    try {
      // Intentar primero con NexoBrain (intención detectada + Gemma)
      const resp = await axios.post(
        `${FASTAPI_URL}/api/intel/chat`,
        {
          mensaje: query,
          modelo: modelo,
          temperatura: 0.3,
        },
        {
          headers: {
            "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
          },
          timeout: 90000,
        },
      );
      const d = resp.data;
      const texto = (d.respuesta || "Sin respuesta").slice(0, 1900);
      await interaction.editReply(
        `🤖 **NEXO** *(${d.modelo_usado || modelo})*\n\n${texto}`,
      );
    } catch (err) {
      // Fallback: agente → Claude → Gemma local
      try {
        const resp = await axios.post(`${FASTAPI_URL}/api/agente/`, { query, user_id: user.id });
        await interaction.editReply(resp.data.respuesta || "Sin respuesta");
      } catch {
        try {
          const claudeResp = await callClaude(query);
          await interaction.editReply(claudeResp ? `🟣 **Claude:** ${claudeResp.substring(0,1900)}` : 'Sin respuesta');
        } catch {
          const gemmaResp = await callOllama(query, DEEP_MODEL).catch(() => null);
          await interaction.editReply(gemmaResp ? `🤖 **Gemma:** ${gemmaResp.substring(0,1900)}` : `Error: ${err.message}`);
        }
      }
    }
  }

  if (commandName === "status") {
    try {
      const resp = await axios.get(`${FASTAPI_URL}/api/metrics/`);
      const sys = resp.data.sistema || resp.data.system || {};
      const embed = new EmbedBuilder()
        .setTitle("NEXO Status")
        .setColor(0x00ae86)
        .addFields(
          {
            name: "CPU",
            value: `${sys.cpu_percent || sys.uso_pct || "?"}%`,
            inline: true,
          },
          { name: "RAM", value: `${sys.memory_percent || "?"}%`, inline: true },
          {
            name: "Uptime",
            value: `${resp.data.uptime_legible || "?"}`,
            inline: true,
          },
        );
      await interaction.editReply({ embeds: [embed] });
    } catch (err) {
      await interaction.editReply("Error al rescatar métricas.");
    }
  }

  if (commandName === "unirse") {
    const voiceChannel = interaction.member?.voice?.channel;
    if (!voiceChannel)
      return interaction.editReply("❌ Debes estar en un canal de voz.");

    try {
      const connection = joinVoiceChannel({
        channelId: voiceChannel.id,
        guildId: guildId,
        adapterCreator: voiceChannel.guild.voiceAdapterCreator,
        selfDeaf: false,
      });

      connection.on(VoiceConnectionStatus.Disconnected, async () => {
        try {
          await Promise.race([
            entersState(connection, VoiceConnectionStatus.Signalling, 5_000),
            entersState(connection, VoiceConnectionStatus.Connecting, 5_000),
          ]);
        } catch {
          connection.destroy();
          console.log("[NEXO VOICE] Conexión de voz cerrada limpiamente");
        }
      });

      const textCh = interaction.channel || channel;
      _activeConnection  = connection;
      _activeTextChannel = textCh;
      console.log(`[NEXO VOICE] Uniéndose a ${voiceChannel.name}...`);
      // Esperar Ready antes de activar receiver
      connection.on(VoiceConnectionStatus.Ready, () => {
        console.log(`[NEXO VOICE] READY — receiver activo en ${voiceChannel.name}`);
        setupVoiceHandler(connection, textCh);
      });
      await interaction.editReply(
        `✅ Uniéndome a **${voiceChannel.name}**. Habla para activar NEXO.`,
      );
    } catch (err) {
      await interaction.editReply(`Error al unir: ${err.message}`);
    }
  }

  if (commandName === "salir") {
    const conn = getVoiceConnection(guildId);
    if (conn) {
      conn.destroy();
      _activeConnection  = null;
      _activeTextChannel = null;
      await interaction.editReply("👋 He salido del canal.");
    } else {
      await interaction.editReply("No estoy en un canal de voz.");
    }
  }

  if (commandName === "vocalmode") {
    const { setVocalMode, getVocalMode } = require("./nexo_autonomy");
    const modo = options.getString("modo");
    setVocalMode(modo);
    const descripciones = {
      privado: "🎧 **Privado** — NEXO habla solo contigo en Discord. No habla en el stream.",
      stream:  "📺 **Stream** — NEXO habla solo para la audiencia. En Discord queda en silencio.",
      ambos:   "🔊 **Ambos** — NEXO habla en Discord Y en el stream simultáneamente.",
    };
    await interaction.editReply(descripciones[modo] || `Modo vocal: ${modo}`);
    return;
  }

  if (commandName === "voice") {
    const modo = options.getString("modo");
    currentVoiceMode = modo;
    if (modo === "live") {
      try {
        const bridge = getGeminiLiveBridge();
        await bridge.connect();
        await interaction.editReply(
          "⚡ Modo de voz cambiado a **live** — Gemini 3.1 Flash Live (audio streaming directo)",
        );
      } catch (err) {
        console.error(
          "[VOICE] Error conectando Gemini Live bridge:",
          err.message,
        );
        currentVoiceMode = "classic";
        await interaction.editReply(
          "⚠️ No se pudo conectar a Gemini Live. Manteniendo modo **classic**.",
        );
      }
    } else {
      await interaction.editReply(
        "🎙️ Modo de voz cambiado a **classic** — Whisper STT + LLM + TTS clásico",
      );
    }
  }

  if (commandName === "drive") {
    const consulta = options.getString("consulta");
    try {
      const ctxRes = await axios.post(
        `${FASTAPI_URL}/api/drive/contexto`,
        {
          mensaje_usuario: consulta,
          folder_id: "10pn6Zo5_SUTf2jlWaH98rs0wtF3W0Trx",
        },
        { timeout: 15000 },
      );
      const ctx = ctxRes.data;
      let promptConContexto = consulta;
      if (ctx.contexto_encontrado && ctx.contexto_raw) {
        promptConContexto = `El usuario pregunta: "${consulta}"\n\nContexto desde Drive (${ctx.archivos.join(", ")}):\n${ctx.contexto_raw}\n\nResponde de forma clara y directa usando este contexto.`;
      }
      const resp = await axios.post(
        `${FASTAPI_URL}/api/agente/`,
        { query: promptConContexto, user_id: user.id },
        { timeout: 30000 },
      );
      const respuesta =
        resp.data?.respuesta || resp.data?.mensaje || "Sin respuesta";
      const fuentes = ctx.archivos?.length
        ? `\n\n*Fuentes: ${ctx.archivos.join(", ")}*`
        : "";
      await interaction.editReply(respuesta.substring(0, 1900) + fuentes);
    } catch (err) {
      const msg =
        err.code === "ECONNREFUSED" || err.code === "ETIMEDOUT"
          ? "⚠️ El sistema NEXO está iniciando. Intenta en 30 segundos."
          : `⚠️ Error consultando Drive: ${err.message}`;
      await interaction.editReply(msg);
    }
  }

  if (commandName === "geopolitica") {
    const tema = options.getString("tema") || "situación actual";
    try {
      const ctxRes = await axios.post(
        `${FASTAPI_URL}/api/drive/contexto`,
        {
          mensaje_usuario: tema,
          folder_id: "10pn6Zo5_SUTf2jlWaH98rs0wtF3W0Trx",
        },
        { timeout: 15000 },
      );
      const ctx = ctxRes.data;
      if (!ctx.contexto_encontrado) {
        await interaction.editReply(
          "No encontré archivos relevantes en la carpeta Geopolítica para ese tema.",
        );
        return;
      }
      const prompt = `Analiza y resume la siguiente información geopolítica sobre "${tema}":\n\n${ctx.contexto_raw}\n\nDa un análisis directo, objetivo y estructurado.`;
      const resp = await axios.post(
        `${FASTAPI_URL}/api/agente/`,
        { query: prompt, user_id: user.id },
        { timeout: 30000 },
      );
      const respuesta =
        resp.data?.respuesta || resp.data?.mensaje || "Sin respuesta";
      await interaction.editReply(
        `**Análisis Geopolítico: ${tema}**\n\n${respuesta.substring(0, 1800)}\n\nFuentes: ${ctx.archivos.join(", ")}`,
      );
    } catch (err) {
      const msg =
        err.code === "ECONNREFUSED" || err.code === "ETIMEDOUT"
          ? "⚠️ El sistema NEXO está iniciando. Intenta en 30 segundos."
          : `⚠️ Error: ${err.message}`;
      await interaction.editReply(msg);
    }
  }

  // ── MCP Gateway ────────────────────────────────────────────────────
  if (commandName === "mcp") {
    const herramienta = options.getString("herramienta");
    const url = options.getString("url") || "";
    const headers = {
      "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
    };
    try {
      if (herramienta === "status") {
        const r = await axios.get(`${FASTAPI_URL}/api/mcp/status`, {
          headers,
          timeout: 10000,
        });
        const s = r.data;
        const serverLines = Object.entries(s.servers || {})
          .map(([k, v]) => `**${k}**: ${v} tools`)
          .join("\n");
        const embed = new EmbedBuilder()
          .setColor(s.available ? 0x22c55e : 0xef4444)
          .setTitle(
            `🐳 Docker MCP Gateway — ${s.available ? "ONLINE" : "OFFLINE"}`,
          )
          .setDescription(
            s.available
              ? `**${s.total_tools}** herramientas activas`
              : `⚠️ ${s.note}`,
          )
          .addFields({ name: "Servidores MCP", value: serverLines || "—" })
          .setTimestamp();
        return interaction.editReply({ embeds: [embed] });
      }
      if (herramienta === "tools") {
        const r = await axios.get(`${FASTAPI_URL}/api/mcp/tools`, {
          headers,
          timeout: 15000,
        });
        const tools = r.data.tools || [];
        const names = tools
          .map((t) => t.name)
          .slice(0, 30)
          .join(", ");
        return interaction.editReply(
          `🔧 **${r.data.total} herramientas MCP**\n\`\`\`${names}${r.data.total > 30 ? `... +${r.data.total - 30} más` : ""}\`\`\``,
        );
      }
      if (herramienta === "screenshot") {
        if (!url) return interaction.editReply("❌ Especifica una `url`.");
        const r = await axios.post(
          `${FASTAPI_URL}/api/mcp/playwright/screenshot`,
          { url },
          { headers, timeout: 30000 },
        );
        if (r.data.ok) {
          return interaction.editReply(
            `📸 Captura tomada de **${url}**\n${r.data.result?.substring(0, 200) || "(imagen procesada)"}`,
          );
        }
        return interaction.editReply(`❌ Error: ${r.data.error}`);
      }
      if (herramienta === "scrape") {
        if (!url) return interaction.editReply("❌ Especifica una `url`.");
        const r = await axios.post(
          `${FASTAPI_URL}/api/mcp/playwright/scrape`,
          { url },
          { headers, timeout: 30000 },
        );
        if (r.data.ok) {
          const text = r.data.result?.substring(0, 1800) || "(sin contenido)";
          return interaction.editReply(`🌐 **${url}**\n\`\`\`${text}\`\`\``);
        }
        return interaction.editReply(`❌ ${r.data.error}`);
      }
    } catch (e) {
      return interaction.editReply(`Error MCP: ${e.message}`);
    }
  }

  // ── Agentes autónomos ──────────────────────────────────────────────
  if (commandName === "agente") {
    const accion = options.getString("accion");
    const agentId = options.getString("id") || "";
    const headers = {
      "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
    };
    try {
      if (accion === "lista") {
        const r = await axios.get(`${FASTAPI_URL}/api/agents`, {
          headers,
          timeout: 10000,
        });
        const agents = r.data.agents || [];
        if (!agents.length)
          return interaction.editReply(
            "No hay agentes creados. Usa `/crear-agente` para añadir uno.",
          );
        const lines = agents
          .map(
            (a) =>
              `${a.active ? "🟢" : "🔴"} **${a.name}** \`${a.id}\` — cada ${a.schedule_minutes}min | ciclos: ${a.run_count}`,
          )
          .join("\n");
        const embed = new EmbedBuilder()
          .setColor(0x818cf8)
          .setTitle(`🤖 Agentes Autónomos NEXO (${agents.length})`)
          .setDescription(lines)
          .setTimestamp();
        return interaction.editReply({ embeds: [embed] });
      }
      if (accion === "plantillas") {
        const r = await axios.get(`${FASTAPI_URL}/api/agents/templates`, {
          headers,
          timeout: 8000,
        });
        const templates = r.data.templates || [];
        const lines = templates.map((t) => `• \`${t}\``).join("\n");
        return interaction.editReply(
          `📋 **Plantillas disponibles:**\n${lines}\n\nUsa \`/crear-agente plantilla:[nombre]\``,
        );
      }
      if (accion === "ejecutar") {
        if (!agentId)
          return interaction.editReply("❌ Especifica el `id` del agente.");
        const r = await axios.post(
          `${FASTAPI_URL}/api/agents/${agentId}/run`,
          {},
          { headers, timeout: 60000 },
        );
        const res = r.data;
        return interaction.editReply(
          `✅ **${agentId}** ejecutado\n${res.synthesis || "_Sin resultado_"}\n\nHerramientas: ${res.tools_used?.join(", ")} | Tiempo: ${res.elapsed}s`,
        );
      }
      if (accion === "activar" || accion === "desactivar") {
        if (!agentId)
          return interaction.editReply("❌ Especifica el `id` del agente.");
        const active = accion === "activar";
        await axios.patch(
          `${FASTAPI_URL}/api/agents/${agentId}`,
          { active },
          { headers, timeout: 8000 },
        );
        return interaction.editReply(
          `${active ? "🟢" : "🔴"} Agente \`${agentId}\` ${active ? "activado" : "desactivado"}.`,
        );
      }
    } catch (e) {
      return interaction.editReply(`Error: ${e.message}`);
    }
  }

  if (commandName === "crear-agente") {
    const plantilla = options.getString("plantilla");
    const nombre = options.getString("nombre") || "";
    const headers = {
      "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
    };
    try {
      const r = await axios.post(
        `${FASTAPI_URL}/api/agents/template`,
        {
          template: plantilla,
          discord_channel_id: interaction.channelId,
        },
        { headers, timeout: 10000 },
      );
      const agent = r.data.agent;
      const embed = new EmbedBuilder()
        .setColor(0x22c55e)
        .setTitle("🤖 Agente Creado")
        .setDescription(`**${agent.name}**\n${agent.role}`)
        .addFields(
          { name: "ID", value: agent.id, inline: true },
          { name: "Herramientas", value: agent.tools.join(", "), inline: true },
          {
            name: "Intervalo",
            value: `${agent.schedule_minutes} min`,
            inline: true,
          },
          { name: "Modelo IA", value: agent.model, inline: true },
        )
        .setFooter({
          text: "El agente empezará su primer ciclo en el próximo tick del factory (max 1 min)",
        })
        .setTimestamp();
      return interaction.editReply({ embeds: [embed] });
    } catch (e) {
      return interaction.editReply(
        `Error creando agente: ${e.response?.data?.detail || e.message}`,
      );
    }
  }

  if (commandName === "canva") {
    const tema = options.getString("tema");
    const tipo = options.getString("tipo") || "infografia";
    const chanId = interaction.channelId;
    try {
      // Llamar al cognitive engine con intent CANVA
      const r = await axios.post(
        `${FASTAPI_URL}/api/cognitive/process`,
        {
          text: `Crea un diseño ${tipo} sobre: ${tema}`,
          channel_id: chanId,
          user_id: user.id,
        },
        {
          headers: {
            "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
          },
          timeout: 20000,
        },
      );
      const canva = r.data?.canva;
      if (canva?.design_id && canva?.edit_url) {
        const embed = new EmbedBuilder()
          .setColor(0x7c3aed)
          .setTitle("🎨 Diseño Canva Creado")
          .setDescription(
            `**${canva.title}**\n\nTipo: \`${canva.design_type}\``,
          )
          .addFields({ name: "Editar diseño", value: canva.edit_url })
          .setFooter({
            text: `Respuesta: ${r.data?.response?.substring(0, 80) || ""}`,
          })
          .setTimestamp();
        return interaction.editReply({ embeds: [embed] });
      } else if (canva?.available === false) {
        return interaction.editReply(
          "⚠️ Canva no está configurado. Agrega `CANVA_ACCESS_TOKEN` al `.env`.",
        );
      } else {
        // Sin token Canva — mostrar la respuesta cognitiva
        return interaction.editReply(
          `🎨 **Canva** | ${r.data?.response || "Sin respuesta"}\n\n${canva?.error ? `_Error: ${canva.error}_` : ""}`,
        );
      }
    } catch (e) {
      return interaction.editReply(`Error Canva: ${e.message}`);
    }
  }

  if (commandName === "metacog") {
    try {
      const r = await axios.get(`${FASTAPI_URL}/api/cognitive/metacog`, {
        headers: {
          "x-nexo-api-key": process.env.NEXO_API_KEY || "NEXO_LOCAL_2026_OK",
        },
        timeout: 8000,
      });
      const snap = r.data?.snapshot || {};
      const lowScore = r.data?.intents_with_low_score || [];
      const lines =
        Object.entries(snap)
          .map(
            ([intent, v]) =>
              `**${intent}** — score: ${v.avg_score} | modelo: ${v.best_model || "?"} | hits: ${v.hits} | lento: ${v.slow_pct}%`,
          )
          .join("\n") || "_Sin datos aún_";
      const embed = new EmbedBuilder()
        .setColor(0x0ea5e9)
        .setTitle("🧠 Metacognición NEXO")
        .setDescription(lines)
        .addFields({
          name: "Intents escalando a Claude",
          value: lowScore.length ? lowScore.join(", ") : "Ninguno",
        })
        .setTimestamp();
      return interaction.editReply({ embeds: [embed] });
    } catch (e) {
      return interaction.editReply(`Error: ${e.message}`);
    }
  }

  if (commandName === "social") {
    const accion = options.getString("accion");
    const texto = options.getString("texto") || "";
    try {
      if (accion === "estado") {
        const res = await axios.get(`${FASTAPI_URL}/api/social/health`, {
          timeout: 10000,
        });
        const s = res.data.status;
        const lines = Object.entries(s)
          .map(([k, v]) => `**${k}**: ${v}`)
          .join("\n");
        await interaction.editReply(`**Estado Social Media**\n${lines}`);
      } else if (accion === "analizar" && texto) {
        const res = await axios.post(
          `${FASTAPI_URL}/api/social/analizar-sentimiento`,
          { texto, pais: "Chile" },
          { timeout: 15000 },
        );
        const s = res.data.sentimiento;
        const heatScore =
          s?.heat_score !== undefined
            ? `Heat score: ${s.heat_score}`
            : JSON.stringify(s);
        await interaction.editReply(
          `**Análisis de sentimiento**\n"${texto}"\n→ ${heatScore}`,
        );
      } else {
        await interaction.editReply("Especifica un texto para analizar.");
      }
    } catch (err) {
      const msg =
        err.code === "ECONNREFUSED" || err.code === "ETIMEDOUT"
          ? "⚠️ El sistema NEXO está iniciando. Intenta en 30 segundos."
          : `⚠️ Error: ${err.message}`;
      await interaction.editReply(msg);
    }
  }

  // ── /video — Creación de contenido (Reels, TikTok, YouTube) ─────────────
  if (commandName === "video") {
    const accion = options.getString("accion");
    const titulo = options.getString("titulo") || "";
    try {
      if (accion === "auto_reel" || accion === "auto_yt") {
        const formato = accion === "auto_yt" ? "youtube" : "reel";
        await interaction.editReply(`🎬 Iniciando auto-${formato}... esto puede tardar varios minutos.`);
        const res = await axios.post(`${FASTAPI_URL}/api/video/auto-reel`, {
          formato,
          idiomas: ["es"],
          dominio: "geo",
          max_drive_files: 10,
          publicar: false,
          titulo: titulo || undefined,
        }, { timeout: 30000 });
        const d = res.data;
        await interaction.editReply(
          `**🎬 ${formato === "reel" ? "Reel" : "YouTube"} en proceso**\n` +
          `Job ID: \`${d.job_id}\`\n` +
          `Fuentes: ${d.fuentes}\n` +
          `Preview: ${(d.contenido_preview || "").substring(0, 200)}...\n\n` +
          `Estado: \`/video estado\``
        );
      } else if (accion === "estado") {
        const res = await axios.get(`${FASTAPI_URL}/api/video/jobs`, { timeout: 10000 });
        const jobs = (res.data.jobs || []).slice(0, 5);
        if (!jobs.length) {
          await interaction.editReply("No hay jobs de video. Usa `/video auto-reel` para crear uno.");
        } else {
          const lines = jobs.map(j =>
            `**${j.id}** [${j.formato}] ${j.estado} — ${j.titulo || "sin título"}`
          ).join("\n");
          await interaction.editReply(`**Jobs de Video (últimos 5)**\n${lines}`);
        }
      } else if (accion === "publicar") {
        // Publicar el último video completado
        const res = await axios.get(`${FASTAPI_URL}/api/video/jobs`, { timeout: 10000 });
        const completado = (res.data.jobs || []).find(j => j.estado === "completado" && j.videos?.es);
        if (!completado) {
          await interaction.editReply("No hay videos completados para publicar. Genera uno primero.");
        } else {
          const pub = await axios.post(`${FASTAPI_URL}/api/video/publicar`, {
            job_id: completado.id, idioma: "es", privacy_status: "public"
          }, { timeout: 30000 });
          await interaction.editReply(
            `**✅ Video publicado en YouTube**\nJob: ${completado.id}\nID: ${pub.data.youtube_id || "pendiente"}`
          );
        }
      }
    } catch(err) {
      await interaction.editReply(`⚠️ Error: ${err.response?.data?.detail || err.message}`);
    }
  }

  // ── /torre — Control total de la Torre ───────────────────────────────────
  if (commandName === "torre") {
    const accion = options.getString("accion");
    const { execSync } = require("child_process");
    const exec = (cmd) => { try { return execSync(cmd, { encoding: 'utf8', timeout: 15000 }).trim(); } catch(e) { return `Error: ${e.message.substring(0,200)}`; } };

    if (accion === "status") {
      const pm2     = exec('pm2 jlist').slice(0, 200);
      let procList  = '?';
      try { const arr = JSON.parse(exec('pm2 jlist')); procList = arr.map(p => `${p.name}: ${p.pm2_env?.status}`).join(', '); } catch(_) {}
      let backendOk = false;
      try { await axios.get(`${FASTAPI_URL}/health`, { timeout: 3000 }); backendOk = true; } catch(_) {}
      await interaction.editReply(`**Torre status**\nBackend: ${backendOk ? 'online' : 'offline'}\nProcesos: ${procList}`);

    } else if (accion === "obs") {
      try {
        const res = await axios.get(`${FASTAPI_URL}/api/stream/status`, {
          headers: { 'x-nexo-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' }, timeout: 5000
        });
        const d = res.data;
        await interaction.editReply(`**OBS Status**\nConectado: ${d.obs_connected ? 'sí' : 'no'}\nEscena actual: ${d.current_scene || '?'}\nStreaming: ${d.active ? 'sí' : 'no'}\nDiscord: ${d.discord_connected ? 'sí' : 'no'}`);
      } catch(e) {
        await interaction.editReply(`OBS no responde: ${e.message.substring(0,150)}`);
      }

    } else if (accion === "director") {
      try {
        const res = await axios.post(`${FASTAPI_URL}/api/intel/director/activar`, {}, {
          headers: { 'x-nexo-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' }, timeout: 5000
        });
        const e = res.data.estado;
        await interaction.editReply(`**Call Director OBS activado**\nOBS: ${e.obs_disponible ? 'conectado' : 'desconectado'}\nEscena: ${e.escena_actual || 'ninguna'}\nLa IA ahora controla OBS según el contexto de la llamada.`);
      } catch(err) {
        await interaction.editReply(`Error activando director: ${err.message.substring(0,200)}`);
      }

    } else if (accion === "stream") {
      try {
        const statusRes = await axios.get(`${FASTAPI_URL}/api/stream/status`, {
          headers: { 'x-nexo-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' }, timeout: 5000
        });
        const streaming = statusRes.data.active;
        const endpoint = streaming ? '/api/stream/stop' : '/api/stream/start';
        await axios.post(`${FASTAPI_URL}${endpoint}`, {}, {
          headers: { 'x-nexo-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' }, timeout: 8000
        });
        await interaction.editReply(`Stream ${streaming ? 'detenido' : 'iniciado'} en OBS.`);
      } catch(err) {
        await interaction.editReply(`Error con stream: ${err.message.substring(0,200)}`);
      }

    } else if (accion === "sync") {
      await interaction.editReply('Iniciando sync Drive/Photos/OneDrive en segundo plano...');
      const { spawn } = require('child_process');
      const root = 'C:\\Users\\Admn\\Desktop\\NEXO_SOBERANO';
      const py   = `${root}\\.venv\\Scripts\\python.exe`;
      const proc = spawn(py, [`${root}\\scripts\\run_unified_sync_full.py`], {
        cwd: root, detached: true, stdio: 'ignore',
        env: { ...process.env, NEXO_FULL_DRY_RUN: 'false', NEXO_FULL_PHOTOS_LIMIT: '50', NEXO_FULL_DRIVE_LIMIT: '100', NEXO_FULL_ONEDRIVE_LIMIT: '50' }
      });
      proc.unref();
      if (_activeTextChannel) _activeTextChannel.send('Sync iniciado. Te aviso cuando termine.').catch(() => {});

    } else if (accion === "logs") {
      const logPath = 'C:\\Users\\Admn\\Desktop\\NEXO_SOBERANO\\logs\\sync_unified_last.json';
      try {
        const fs = require('fs');
        const d = JSON.parse(fs.readFileSync(logPath, 'utf8'));
        const s = d.summary || {};
        const lines = Object.entries(s).map(([k,v]) => `**${k}**: ${JSON.stringify(v)}`).join('\n');
        await interaction.editReply(`**Último sync**\nEstado: ${d.status || d.ok}\n${lines}`);
      } catch(e) {
        const pm2log = exec('pm2 logs nexo-bot --lines 10 --nostream');
        await interaction.editReply(`**Logs PM2 (últimas 10 líneas)**\n\`\`\`\n${pm2log.substring(0,1500)}\n\`\`\``);
      }

    } else if (accion === "restart") {
      await interaction.editReply('Reiniciando bot en 3 segundos...');
      setTimeout(() => exec('pm2 restart nexo-bot'), 3000);

    } else if (accion === "pm2") {
      let list = '?';
      try {
        const arr = JSON.parse(exec('pm2 jlist'));
        list = arr.map(p => `**${p.name}** (${p.pm2_env?.status}) mem:${Math.round((p.monit?.memory||0)/1024/1024)}MB cpu:${p.monit?.cpu||0}%`).join('\n');
      } catch(e) { list = exec('pm2 list'); }
      await interaction.editReply(`**Procesos PM2**\n${list.substring(0,1900)}`);

    } else if (accion === "encender") {
      // Startup completo de la Torre — IA organiza todo
      const lines = ['**⚡ NEXO TORRE — Secuencia de encendido**', ''];
      await interaction.editReply('Iniciando secuencia de encendido...');

      // 1. PM2 — servicios Node/Python
      try {
        const arr = JSON.parse(exec('pm2 jlist'));
        const stopped = arr.filter(p => p.pm2_env?.status !== 'online');
        if (stopped.length > 0) {
          exec('pm2 restart all');
          lines.push(`✅ PM2: reiniciados ${stopped.map(p=>p.name).join(', ')}`);
        } else {
          lines.push(`✅ PM2: todos online (${arr.map(p=>p.name).join(', ')})`);
        }
      } catch(e) { lines.push(`⚠️ PM2: ${e.message.substring(0,80)}`); }

      // 2. Docker — nexo_db, nexo_redis, nexo_qdrant
      try {
        const dockerOut = exec('docker ps --filter name=nexo --format "{{.Names}}:{{.Status}}"');
        const nexoContainers = dockerOut.split('\n').filter(Boolean);
        if (nexoContainers.length >= 3) {
          lines.push(`✅ Docker: ${nexoContainers.map(c=>c.split(':')[0]).join(', ')}`);
        } else {
          exec('docker compose -f C:\\Users\\Admn\\Desktop\\NEXO_SOBERANO\\docker-compose.yml up -d nexo_db nexo_redis nexo_qdrant');
          lines.push(`✅ Docker: servicios levantados`);
        }
      } catch(e) { lines.push(`⚠️ Docker: ${e.message.substring(0,80)}`); }

      // 3. Ollama — verificar modelo fast disponible
      try {
        const ollamaResp = await axios.get('http://localhost:11434/api/tags', { timeout: 4000 });
        const models = ollamaResp.data?.models?.map(m => m.name) || [];
        const hasFast = models.includes('gemma3:1b');
        lines.push(`✅ Ollama: ${models.length} modelos | voz: ${hasFast ? 'gemma3:1b ✓' : '⚠️ gemma3:1b no encontrado'}`);
      } catch(e) { lines.push(`⚠️ Ollama: no responde — modelos locales no disponibles`); }

      // 4. OBS — conectar y activar Call Director
      try {
        const obsRes = await axios.get(`${FASTAPI_URL}/api/stream/status`, {
          headers: { 'x-nexo-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' }, timeout: 5000
        });
        const escena = obsRes.data?.current_scene || '?';
        // Activar director
        await axios.post(`${FASTAPI_URL}/api/intel/director/activar`, {}, {
          headers: { 'x-nexo-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' }, timeout: 8000
        }).catch(() => {});
        lines.push(`✅ OBS: conectado | escena: ${escena} | Call Director activo`);
      } catch(e) { lines.push(`⚠️ OBS: ${e.message.substring(0,80)}`); }

      // 5. Backend health
      try {
        const health = await axios.get(`${FASTAPI_URL}/api/health`, { timeout: 5000 });
        lines.push(`✅ Backend: ${health.data?.status} v${health.data?.version}`);
      } catch(e) { lines.push(`⚠️ Backend: lento o caído — reintentando en 30s`); }

      // 6. Voz — unirse al canal si no está
      const guild = interaction.guild;
      const member = guild?.members?.cache?.get(interaction.user.id);
      const voiceChannel = member?.voice?.channel;
      if (voiceChannel && !getVoiceConnection(guild.id)) {
        const { joinVoiceChannel: jvc } = require('@discordjs/voice');
        const conn = jvc({ channelId: voiceChannel.id, guildId: guild.id, adapterCreator: guild.voiceAdapterCreator, selfDeaf: false, selfMute: false });
        conn.on(VoiceConnectionStatus.Ready, () => setupVoiceHandler(conn, interaction.channel));
        lines.push(`✅ Voz: unido a **${voiceChannel.name}** — escuchando`);
      } else if (getVoiceConnection(guild.id)) {
        lines.push(`✅ Voz: ya activa en canal de voz`);
      } else {
        lines.push(`ℹ️ Voz: únete a un canal de voz para activarla`);
      }

      lines.push('');
      lines.push('**La Torre está operativa. NEXO listo.**');
      await interaction.editReply(lines.join('\n'));
    }
  }

  // ── /claude — Claude Sonnet directo ──────────────────────────────────────
  if (commandName === "claude") {
    const prompt = options.getString("prompt");
    const modo   = options.getString("modo") || "analisis";
    const modoPrompts = {
      analisis:   "Eres NEXO, analista geopolítico. Responde con análisis estructurado, usa markdown. Máximo 800 palabras.",
      codigo:     "Eres NEXO, experto en código. Da soluciones precisas con bloques de código. Explica brevemente.",
      estrategia: "Eres NEXO, estratega. Responde con perspectiva táctica y geopolítica. Prioriza impacto y acción.",
      resumen:    "Eres NEXO. Resume la información clave en 5 puntos concisos con bullets.",
    };
    const systemPrompt = modoPrompts[modo] || modoPrompts.analisis;
    try {
      const apiKey = process.env.ANTHROPIC_API_KEY;
      if (!apiKey) {
        // Fallback a Ollama si no hay clave
        const resp = await callOllama(prompt, DEEP_MODEL, systemPrompt);
        await interaction.editReply(`**[NEXO · Ollama]**\n${(resp || 'Sin respuesta').substring(0, 1900)}`);
        return;
      }
      const r = await axios.post('https://api.anthropic.com/v1/messages', {
        model: process.env.CLAUDE_MODEL || 'claude-sonnet-4-6',
        max_tokens: 1024,
        system: systemPrompt,
        messages: [{ role: 'user', content: prompt }],
      }, {
        headers: {
          'x-api-key': apiKey,
          'anthropic-version': '2023-06-01',
          'content-type': 'application/json',
        },
        timeout: 30000,
      });
      const text = r.data?.content?.[0]?.text?.trim() || 'Sin respuesta.';
      // Discord tiene límite de 2000 chars — partir si necesario
      if (text.length <= 1900) {
        await interaction.editReply(`**[NEXO · Claude ${modo}]**\n${text}`);
      } else {
        await interaction.editReply(`**[NEXO · Claude ${modo}]** (parte 1/2)\n${text.substring(0, 1900)}`);
        await interaction.followUp(`(parte 2/2)\n${text.substring(1900, 3800)}`);
      }
    } catch(e) {
      await interaction.editReply(`⚠️ Error Claude: ${e.message.substring(0, 200)}`);
    }
    return;
  }

  // ── /cmd — Terminal remoto NEXO ───────────────────────────────────────────
  if (commandName === "cmd") {
    // Verificar que es admin o el dueño
    const isAdmin = interaction.member?.permissions?.has?.('Administrator') ||
                    interaction.user.id === interaction.guild?.ownerId;
    if (!isAdmin) {
      await interaction.editReply('⛔ Solo el administrador puede ejecutar comandos del sistema.');
      return;
    }
    const accion = options.getString("accion");
    const { execSync } = require("child_process");
    const safeExec = (cmd) => { try { return execSync(cmd, { encoding: 'utf8', timeout: 20000, cwd: 'C:\\Users\\Admn\\Desktop\\NEXO_SOBERANO' }).trim(); } catch(e) { return `Error: ${e.stderr?.substring(0,300) || e.message.substring(0,300)}`; } };
    const ROOT = 'C:\\Users\\Admn\\Desktop\\NEXO_SOBERANO';
    const PY   = `${ROOT}\\.venv\\Scripts\\python.exe`;

    if (accion === "status") {
      let backendOk = false;
      try { await axios.get(`${FASTAPI_URL}/health`, { timeout: 3000 }); backendOk = true; } catch(_) {}
      let pm2Status = '?';
      try {
        const arr = JSON.parse(safeExec('pm2 jlist'));
        pm2Status = arr.map(p => `\`${p.name}\`: ${p.pm2_env?.status === 'online' ? '🟢' : '🔴'} ${p.pm2_env?.status}`).join('\n');
      } catch(_) {}
      const voiceStatus = _activeConnection ? `🟢 activo (${_activeConnection.state.status})` : '⚫ inactivo';
      await interaction.editReply(`**NEXO Status**\nBackend: ${backendOk ? '🟢 online' : '🔴 offline'}\nVoz: ${voiceStatus}\n${pm2Status}`);

    } else if (accion === "logs") {
      const logs = safeExec('pm2 logs nexo-bot --lines 15 --nostream');
      await interaction.editReply(`**Logs nexo-bot**\n\`\`\`\n${logs.substring(0, 1800)}\n\`\`\``);

    } else if (accion === "drive_sync") {
      await interaction.editReply('🔄 Iniciando sync Drive...');
      const proc = require('child_process').spawn(PY, [`${ROOT}\\nexo_drive_sync.py`, 'pull'], {
        cwd: ROOT, detached: true, stdio: 'ignore'
      });
      proc.unref();
      setTimeout(async () => {
        interaction.followUp('✅ Drive sync iniciado en background. Usa `/cmd status` para verificar.').catch(() => {});
      }, 2000);

    } else if (accion === "drive_status") {
      try {
        const fs = require('fs');
        const statePath = `${ROOT}\\exports\\drive_watcher_state.json`;
        if (fs.existsSync(statePath)) {
          const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
          await interaction.editReply(`**Drive Watcher**\nÚltimo poll: ${state.last_poll || '?'}\nArchivos procesados: ${state.files_processed || 0}\nArchivos vistos: ${(state.seen_ids||[]).length}`);
        } else {
          await interaction.editReply('⚠️ Drive watcher no ha corrido aún. Usa `/cmd drive sync` para iniciarlo.');
        }
      } catch(e) {
        await interaction.editReply(`Error: ${e.message.substring(0, 200)}`);
      }

    } else if (accion === "restart_bot") {
      await interaction.editReply('♻️ Reiniciando nexo-bot en 3s...');
      setTimeout(() => safeExec('pm2 restart nexo-bot'), 3000);

    } else if (accion === "restart_api") {
      await interaction.editReply('♻️ Reiniciando nexo-api en 3s...');
      setTimeout(() => safeExec('pm2 restart nexo-api'), 3000);

    } else if (accion === "scout") {
      await interaction.editReply('🔍 Ejecutando Innovation Scout...');
      try {
        const result = safeExec(`"${PY}" "${ROOT}\\scripts\\nexo_innovation_scout.py"`);
        const fs = require('fs');
        const jsonPath = `${ROOT}\\logs\\innovation_scout_last.json`;
        if (fs.existsSync(jsonPath)) {
          const data = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
          const recs = (data.recommendations || []).slice(0, 3).map((r, i) => `${i+1}. ${r}`).join('\n');
          await interaction.editReply(`**Innovation Scout**\nScore: **${data.innovation_score}**/100\nPaquetes faltantes: ${data.integrations?.missing_packages?.length || 0}\n\n**Top recomendaciones:**\n${recs}`);
        } else {
          await interaction.editReply(`Scout ejecutado.\n\`\`\`\n${result.substring(0, 1500)}\n\`\`\``);
        }
      } catch(e) {
        await interaction.editReply(`Error scout: ${e.message.substring(0, 200)}`);
      }

    } else if (accion === "reel") {
      await interaction.editReply('🎬 Generando reel del día en background...');
      const proc = require('child_process').spawn(PY, [`${ROOT}\\make_reel.py`], {
        cwd: ROOT, detached: true, stdio: 'ignore'
      });
      proc.unref();

    } else if (accion === "models") {
      try {
        const r = await axios.get('http://localhost:11434/api/tags', { timeout: 5000 });
        const models = (r.data?.models || []).map(m => `• \`${m.name}\` (${Math.round((m.size||0)/1024/1024/1024*10)/10}GB)`).join('\n');
        await interaction.editReply(`**Modelos Ollama**\n${models || 'Sin modelos instalados'}`);
      } catch(e) {
        await interaction.editReply(`⚠️ Ollama no responde: ${e.message.substring(0, 150)}`);
      }
    }
    return;
  }

  // ── /config — Ver/modificar configuración ────────────────────────────────
  if (commandName === "config") {
    const isAdmin = interaction.member?.permissions?.has?.('Administrator') ||
                    interaction.user.id === interaction.guild?.ownerId;
    if (!isAdmin) {
      await interaction.editReply('⛔ Solo el administrador puede ver/modificar la configuración.');
      return;
    }
    const accion = options.getString("accion");
    const valor  = options.getString("valor");

    if (accion === "ver") {
      const cfg = [
        `**NEXO Config actual**`,
        `Modo vocal: \`${process.env.NEXO_VOCAL_MODE || 'ambos'}\``,
        `Modo voz: \`${currentVoiceMode}\``,
        `Modelo fast (voz): \`${process.env.OLLAMA_MODEL_FAST || 'gemma3:1b'}\``,
        `Modelo balanced: \`${process.env.OLLAMA_MODEL_BALANCED || 'qwen3:4b'}\``,
        `Modelo general: \`${process.env.OLLAMA_MODEL_GENERAL || 'gemma4'}\``,
        `Backend: \`${FASTAPI_URL}\``,
        `OBS: \`${process.env.OBS_ENABLED === 'true' ? 'habilitado' : 'deshabilitado'}\``,
        `FORCE_LOCAL_AI: \`${process.env.FORCE_LOCAL_AI || 'false'}\``,
        `Claude model: \`${process.env.CLAUDE_MODEL || 'claude-sonnet-4-6'}\``,
      ].join('\n');
      await interaction.editReply(cfg);

    } else if (accion === "voz") {
      if (valor && ['classic', 'live'].includes(valor.toLowerCase())) {
        currentVoiceMode = valor.toLowerCase();
        await interaction.editReply(`✅ Modo de voz cambiado a: \`${currentVoiceMode}\``);
      } else {
        await interaction.editReply(`Modo actual: \`${currentVoiceMode}\`. Valores válidos: \`classic\`, \`live\``);
      }

    } else if (accion === "modelo") {
      if (valor) {
        process.env.OLLAMA_MODEL_FAST = valor;
        await interaction.editReply(`✅ Modelo de voz cambiado a: \`${valor}\` (sesión actual)`);
      } else {
        await interaction.editReply(`Modelo voz actual: \`${process.env.OLLAMA_MODEL_FAST || 'gemma3:1b'}\``);
      }
    }
    return;
  }

  // ── Fallthrough: comando no manejado → motor cognitivo ───────────────────
  const _handled = [
    'youtube','sesion','osint','streams','captura','parar','temas','dispositivo',
    'director','actor','buscar','nexo','status','unirse','salir','voice','drive',
    'geopolitica','vocalmode','briefing','mcp','agente','crear-agente','canva',
    'metacog','social','torre','video','claude','cmd','config',
  ];
  if (!_handled.includes(commandName)) {
    try {
      const query = options.getString?.('consulta') || options.getString?.('texto') ||
                    options.getString?.('tema') || options.getString?.('query') || commandName;
      const r = await axios.post(
        `${FASTAPI_URL}/api/cognitive/process`,
        { text: query, channel_id: interaction.channelId, user_id: user.id },
        { headers: { 'x-nexo-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' }, timeout: 20000 }
      );
      await interaction.editReply(
        `**[${r.data?.intent || '?'}]** ${(r.data?.response || 'Sin respuesta.').substring(0, 1900)}`
      );
    } catch(e) {
      await interaction.editReply(`⚠️ Error: ${e.message}`);
    }
  }
});

function setupVoiceHandler(connection, textChannel) {
  console.log(
    `[NEXO VOICE] setupVoiceHandler activo. Canal texto: ${textChannel?.id || "NINGUNO"}`,
  );

  // Limpiar listeners previos para evitar duplicados en reconexiones
  connection.receiver.speaking.removeAllListeners("start");

  connection.receiver.speaking.on("start", (userId) => {
    if (client.user && userId === client.user.id) return; // ignorar al bot mismo
    console.log(`[NEXO VOICE] Usuario ${userId} empezó a hablar`);
    handleUserVoice(connection, userId, textChannel);
  });

  console.log("[NEXO VOICE] Receiver activo — escuchando voz");
}

const activeUsers = new Map();

function handleUserVoice(connection, userId, textChannel) {
  if (activeUsers.has(userId)) return;
  activeUsers.set(userId, true);

  const receiver = connection.receiver;
  const audioStream = receiver.subscribe(userId, {
    end: { behavior: EndBehaviorType.Manual },
  });

  const opusDecoder = new prism.opus.Decoder({
    rate: 48000,
    channels: 2,
    frameSize: 960,
  });
  const wavPath = path.join(__dirname, `tmp_${userId}_${Date.now()}.wav`);

  const ffmpegStatic = require("ffmpeg-static");
  const ffProc = spawn(ffmpegStatic, [
    "-f",
    "s16le",
    "-ar",
    "48000",
    "-ac",
    "2",
    "-i",
    "pipe:0",
    "-af",
    "volume=3.0",
    "-ar",
    "16000",
    "-ac",
    "1",
    wavPath,
    "-y",
  ]);

  let chunkCount = 0;
  let lastDataTime = Date.now();

  // Detector de silencio — 900ms sin datos = fin de turno
  const silenceCheck = setInterval(() => {
    if (Date.now() - lastDataTime > 900 && chunkCount > 0) {
      console.log(
        `[NEXO VOICE] Silencio detectado (${chunkCount} chunks). Cerrando grabación.`,
      );
      cleanup();
    }
  }, 500);

  const cleanup = () => {
    activeUsers.delete(userId);
    clearInterval(silenceCheck);
    try {
      audioStream.unpipe(opusDecoder);
      opusDecoder.unpipe(ffProc.stdin);
      ffProc.stdin.end();
    } catch (e) {}
  };

  opusDecoder.on("data", () => {
    chunkCount++;
    lastDataTime = Date.now();
    if (chunkCount === 10)
      console.log(`[NEXO VOICE] Grabando audio de ${userId}...`);
  });

  audioStream.pipe(opusDecoder).pipe(ffProc.stdin);

  ffProc.on("close", async () => {
    if (chunkCount < 18) {
      console.log(
        `[NEXO VOICE] Audio muy corto (${chunkCount} chunks). Ignorando.`,
      );
      if (fs.existsSync(wavPath)) fs.unlinkSync(wavPath);
      return;
    }
    if (!fs.existsSync(wavPath)) return;

    console.log(`[NEXO VOICE] Procesando ${chunkCount} chunks de audio...`);

    // ── Gemini Live Mode ────────────────────────────────────────────────
    if (currentVoiceMode === "live") {
      try {
        const pcmData = fs.readFileSync(wavPath);
        if (fs.existsSync(wavPath)) fs.unlinkSync(wavPath);
        const bridge = getGeminiLiveBridge();
        if (!bridge.ws || bridge.ws.readyState !== 1) await bridge.connect();
        await bridge.sendAudio(pcmData);
        bridge.sendEndOfTurn();
        await bridge.playResponseInDiscord(connection);
        console.log("[NEXO VOICE LIVE] Respuesta Gemini Live reproducida.");
        if (textChannel)
          textChannel.send("⚡ *Respuesta via Gemini Live*").catch(() => {});
      } catch (liveErr) {
        console.error("[NEXO VOICE LIVE] Error:", liveErr.message);
        if (fs.existsSync(wavPath)) fs.unlinkSync(wavPath);
        if (textChannel)
          textChannel
            .send(
              "⚠️ Error en Gemini Live, usa `/voice classic` para volver al modo clásico.",
            )
            .catch(() => {});
      }
      return;
    }

    // ── Classic Mode ────────────────────────────────────────────────────
    try {
      let text = "";
      if (process.env.GROQ_API_KEY) {
        console.log("[NEXO VOICE] STT via Groq...");
        text = await transcribeFile(wavPath);
      } else {
        // Usar backend /api/voice/stt (faster-whisper tiny — rápido)
        console.log("[NEXO VOICE] STT via backend faster-whisper...");
        text = await transcribirBackend(wavPath);
        if (!text) {
          console.log("[NEXO VOICE] STT backend falló, intentando Whisper local...");
          text = await transcribirWhisper(wavPath);
        }
      }
      if (fs.existsSync(wavPath)) fs.unlinkSync(wavPath);

      if (!text || text.trim().length < 3) {
        console.log("[NEXO VOICE] STT vacío, ignorando.");
        return;
      }

      const lowered = text.toLowerCase().trim();
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
        console.log(`[NEXO VOICE] Alucinación filtrada: "${text}"`);
        return;
      }

      console.log(`[NEXO VOICE] STT: "${text}"`);
      const user = client.users.cache.get(userId);
      if (textChannel)
        textChannel
          .send(`🎙️ **${user?.username || userId}:** ${text}`)
          .catch(() => {});

      // ── Control de OBS por voz (respuesta inmediata, sin esperar al LLM) ──
      const obsEscena = detectarComandoOBS(text);
      if (obsEscena) {
        console.log(`[NEXO OBS] Comando de voz → escena: ${obsEscena}`);
        axios.post(`${FASTAPI_URL}/api/intel/director/escena?escena=${encodeURIComponent(obsEscena)}`, {}, {
          headers: { 'x-nexo-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' },
          timeout: 3000,
        }).catch(() => {});
        if (textChannel)
          textChannel.send(`🎬 Escena → \`${obsEscena}\``).catch(() => {});
        // Para comandos de escena, TTS de confirmación corta y retorna
        await playTTS(connection, `Cambiando a escena ${obsEscena.replace('NEXO_','').toLowerCase()}.`).catch(() => {});
        return;
      }

      // ── Respuesta de voz: directo a Ollama local (<8s) ──────────────────
      let iaText = "Procesando...";
      const OLLAMA_URL = process.env.OLLAMA_URL || "http://localhost:11434";
      const VOICE_MODEL = process.env.OLLAMA_MODEL_FAST || "gemma3:1b";
      try {
        const ollamaResp = await axios.post(
          `${OLLAMA_URL}/api/chat`,
          {
            model: VOICE_MODEL,
            messages: [
              {
                role: "system",
                content: `Eres NEXO, un analista de inteligencia geopolítica conciso.
Respondes por AUDIO en una llamada de Discord. Máximo 2 oraciones breves.
Sin listas, sin formato markdown, sin asteriscos. Tono directo y seguro.`,
              },
              { role: "user", content: text },
            ],
            stream: false,
            options: { temperature: 0.2, num_predict: 120 },
          },
          { timeout: 12000 },
        );
        let resp = ollamaResp.data?.message?.content || "";
        // Limpiar thinking tags (qwen/gemma pueden emitirlos)
        if (resp.includes("<think>")) resp = resp.split("</think>").pop().trim();
        iaText = resp.substring(0, 300) || "Entendido.";
        console.log(`[NEXO VOICE] Ollama → "${iaText.substring(0, 80)}"`);
        if (textChannel)
          textChannel.send(`🤖 **NEXO:** ${iaText}`).catch(() => {});
      } catch (voiceErr) {
        console.warn("[NEXO VOICE] Ollama falló:", voiceErr.message);
        iaText = "Dame un segundo, procesando.";
        if (textChannel)
          textChannel.send(`🤖 **NEXO:** ${iaText}`).catch(() => {});
      }

      // ── Voz: NEXO siempre responde cuando alguien habla en llamada ─────
      const chanId = textChannel?.id || "default";
      const { shouldSpeakInDiscord, shouldSpeakInStream } = require("./nexo_autonomy");
      const voiceText = iaText;

      console.log(`[NEXO VOICE] Respondiendo por voz a: "${text.substring(0, 60)}" → modo=${require("./nexo_autonomy").getVocalMode()}`);

      // Notificar OBS/avatar si stream activo
      if (shouldSpeakInStream()) {
        notificarAvatarHablando(voiceText, cogResult?.intent || 'CONVERSACION').catch(() => {});
      }

      // Siempre hablar en Discord voice cuando alguien nos habla
      recordSpeak(chanId);
      await playTTS(connection, voiceText);
    } catch (err) {
      console.error(
        "[NEXO VOICE] Error pipeline:",
        err.response?.data || err.message,
      );
      if (fs.existsSync(wavPath)) fs.unlinkSync(wavPath);
    }
  });
}

async function transcribirBackend(wavPath) {
  // STT via faster-whisper tiny (subprocess Python directo — ~3-6s)
  const pythonExe = process.env.PYTHON_PATH ||
    'C:\\Users\\Admn\\Desktop\\NEXO_SOBERANO\\.venv\\Scripts\\python.exe';
  return new Promise((resolve) => {
    const safePath = wavPath.replace(/\\/g, '/');
    const py = spawn(pythonExe, ['-c', `
import sys
try:
    from faster_whisper import WhisperModel
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    segments, _ = model.transcribe("${safePath}", language="es", beam_size=1, vad_filter=True)
    print("".join(s.text for s in segments).strip())
except Exception as e:
    sys.stderr.write(str(e))
    print("")
`]);
    let out = '';
    py.stdout.on('data', d => { out += d; });
    py.stderr.on('data', () => {});
    py.on('close', () => resolve(out.trim()));
    setTimeout(() => { py.kill(); resolve(''); }, 20000);
  });
}

async function transcribirWhisper(wavPath) {
  // Fallback: Whisper local Python (requiere: pip install openai-whisper)
  return new Promise((resolve) => {
    const py = spawn("python", [
      "-c",
      `
import whisper
model = whisper.load_model('base')
result = model.transcribe('${wavPath.replace(/\\/g, "/")}', language='es')
print(result['text'].strip())
    `,
    ]);
    let output = "";
    py.stdout.on("data", (d) => {
      output += d;
    });
    py.stderr.on("data", () => {}); // silenciar warnings de pytorch
    py.on("close", () => resolve(output.trim()));
    setTimeout(() => {
      py.kill();
      resolve("");
    }, 60000);
  });
}

const token = process.env.DISCORD_TOKEN.trim();
console.log(`[NEXO INFO] Iniciando login (Token length: ${token.length})`);
client.login(token);
