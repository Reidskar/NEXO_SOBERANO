require('dotenv').config();
const { Client, GatewayIntentBits, EmbedBuilder, SlashCommandBuilder } = require('discord.js');
const {
  joinVoiceChannel,
  getVoiceConnection,
  VoiceConnectionStatus,
  entersState,
  createAudioPlayer,
  createAudioResource,
  AudioPlayerStatus,
  NoSubscriberBehavior,
  StreamType
} = require('@discordjs/voice');
const axios = require('axios');
const discordTTS = require('discord-tts');
const OBSWebSocket = require('obs-websocket-js').default;
const fs = require('fs');
const path = require('path');
const { pipeline } = require('stream');
const prism = require('prism-media');
const { createWriteStream } = require('fs');

const http = require('http');
const { sendAlert } = require('./alert_client');

// ═══ CRASH PROTECTION & ALERTING ═══
process.on('uncaughtException', async (err) => {
  console.error('CRITICAL ERROR:', err);
  await sendAlert({
    type: 'system',
    source: 'nexo-bot',
    title: 'uncaughtException - Bot Crashed',
    text: err.stack || err.message,
    level: 'critical'
  });
  process.exit(1);
});

process.on('unhandledRejection', async (reason) => {
  console.error('Unhandled Rejection:', reason);
  await sendAlert({
    type: 'system',
    source: 'nexo-bot',
    title: 'unhandledRejection',
    text: String(reason),
    level: 'error'
  });
});

// ═══ HEALTH MONITORING & INTERNAL TEST ═══
http.createServer(async (req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', bot: client.user?.tag || 'offline' }));
  } else if (req.url === '/internal/tts_test' && req.method === 'POST') {
    let body = '';
    for await (const chunk of req) body += chunk;
    try {
      const { text, voice_id } = JSON.parse(body);
      console.log(`[HTTP TEST] Solicitando TTS para: "${text}"`);
      await speakInVoice(text || 'Prueba de voz interna ejecutada correctamente.', voice_id);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'queued', text }));
    } catch (err) {
      res.writeHead(400);
      res.end(JSON.stringify({ error: err.message }));
    }
  } else {
    res.writeHead(404);
    res.end();
  }
}).listen(process.env.PORT || 3000, () => {
  console.log(`Servidor de monitoreo del bot escuchando en puerto ${process.env.PORT || 3000}`);
});

// ═══ OBS MANAGER ═══
const OBS_HOST = process.env.OBS_HOST || 'localhost';
const OBS_PORT = process.env.OBS_PORT || '4455';
const OBS_PASSWORD = process.env.OBS_PASSWORD || '';
const obs = new OBSWebSocket();
let obsConnected = false;

async function connectOBS() {
  try {
    await obs.connect(`ws://${OBS_HOST}:${OBS_PORT}`, OBS_PASSWORD || undefined);
    obsConnected = true;
    console.log(`OBS conectado en ${OBS_HOST}:${OBS_PORT}`);
  } catch (e) {
    obsConnected = false;
    console.warn(`OBS no disponible: ${e.message}`);
  }
}

async function getOBSStatus() {
  if (!obsConnected) return { connected: false, streaming: false, recording: false, scene: 'N/A' };
  try {
    const stream = await obs.call('GetStreamStatus');
    const record = await obs.call('GetRecordStatus');
    const scene = await obs.call('GetCurrentProgramScene');
    return {
      connected: true,
      streaming: stream.outputActive,
      recording: record.outputActive,
      scene: scene.currentProgramSceneName,
      streamTime: stream.outputTimecode || '00:00:00'
    };
  } catch (e) {
    obsConnected = false;
    return { connected: false, streaming: false, recording: false, scene: 'N/A', error: e.message };
  }
}

const FASTAPI_URL = (process.env.FASTAPI_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const AUTOCHAT_ENABLED = (process.env.AUTOCHAT_ENABLED || 'true').toLowerCase() === 'true';
const AUTOCHAT_CHANNEL_IDS = new Set(
  (process.env.AUTOCHAT_CHANNEL_IDS || '')
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)
);
const NEXO_API_KEY = process.env.NEXO_API_KEY || '';
const AUTOCHAT_MIN_INTERVAL_MS = Number(process.env.AUTOCHAT_MIN_INTERVAL_SECONDS || 10) * 1000;
const AUTOCHAT_ACTIVE_WINDOW_MS = Number(process.env.AUTOCHAT_ACTIVE_WINDOW_SECONDS || 180) * 1000;
const AUTOCHAT_MAX_CONTEXT_MESSAGES = Number(process.env.AUTOCHAT_MAX_CONTEXT_MESSAGES || 12);
const AUTOCHAT_ALLOW_WITHOUT_MENTION = (process.env.AUTOCHAT_ALLOW_WITHOUT_MENTION || 'true').toLowerCase() === 'true';
const AUTOCHAT_NAME = (process.env.AUTOCHAT_NAME || 'nexo').toLowerCase();
const VOICE_ALWAYS_ON = (process.env.VOICE_ALWAYS_ON || 'false').toLowerCase() === 'true';
const VOICE_GUILD_ID = (process.env.VOICE_GUILD_ID || '').trim();
const VOICE_CHANNEL_ID = (process.env.VOICE_CHANNEL_ID || '').trim();
const VOICE_SELF_DEAF = (process.env.VOICE_SELF_DEAF || 'true').toLowerCase() === 'true';
const VOICE_RECONNECT_SECONDS = Number(process.env.VOICE_RECONNECT_SECONDS || 20);
const VOICE_TTS_ENABLED = (process.env.VOICE_TTS_ENABLED || 'true').toLowerCase() === 'true';
const VOICE_TTS_MAX_CHARS = Number(process.env.VOICE_TTS_MAX_CHARS || 220);

if (!process.env.DISCORD_TOKEN) {
  throw new Error('Falta DISCORD_TOKEN en .env');
}

const OPENAI_API_KEY = process.env.OPENAI_API_KEY || '';
const TEMP_DIR = path.join(__dirname, 'temp_audio');
if (!fs.existsSync(TEMP_DIR)) fs.mkdirSync(TEMP_DIR);

const channelRuntime = new Map();
const autoDisabledChannels = new Set();
let voiceCheckTimer = null;
let voicePlayer = null;
let voiceSpeakQueue = Promise.resolve();

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildVoiceStates
  ]
});

const commands = [
  new SlashCommandBuilder()
    .setName('tutor')
    .setDescription('Pregunta sobre geopolítica con evidencia real')
    .addStringOption(option =>
      option
        .setName('pregunta')
        .setDescription('Tu pregunta')
        .setRequired(true)
    ),
  new SlashCommandBuilder()
    .setName('aporte')
    .setDescription('Envía un aporte (texto, link, imagen) al sistema')
    .addStringOption(option =>
      option
        .setName('contenido')
        .setDescription('Texto o link')
        .setRequired(true)
    )
    .addAttachmentOption(option =>
      option
        .setName('archivo')
        .setDescription('Imagen o archivo opcional')
        .setRequired(false)
    ),
  new SlashCommandBuilder()
    .setName('autonomo')
    .setDescription('Activa o desactiva respuestas autónomas en este canal')
    .addStringOption(option =>
      option
        .setName('modo')
        .setDescription('Estado del modo autónomo en este canal')
        .setRequired(true)
        .addChoices(
          { name: 'on', value: 'on' },
          { name: 'off', value: 'off' },
          { name: 'status', value: 'status' }
        )
    ),
  new SlashCommandBuilder()
    .setName('llamada')
    .setDescription('Estado de conexión de voz del bot en el canal always-on')
    .addStringOption(option =>
      option
        .setName('accion')
        .setDescription('Acción sobre la conexión de voz')
        .setRequired(true)
        .addChoices(
          { name: 'status', value: 'status' },
          { name: 'reconnect', value: 'reconnect' },
          { name: 'speaktest', value: 'speaktest' }
        )
    )
    .addStringOption(option =>
      option
        .setName('mensaje')
        .setDescription('Mensaje de prueba para hablar en la llamada')
        .setRequired(false)
    ),
  new SlashCommandBuilder()
    .setName('nexo')
    .setDescription('Consulta el estado de la bóveda de memoria de NEXO SOBERANO (VectorDB y RAG)')
];

function voiceConfigured() {
  return VOICE_ALWAYS_ON && Boolean(VOICE_GUILD_ID) && Boolean(VOICE_CHANNEL_ID);
}

function getVoiceConnectionSafe() {
  if (!voiceConfigured()) return null;
  const connection = getVoiceConnection(VOICE_GUILD_ID);
  if (!connection) return null;
  if (connection.state.status === VoiceConnectionStatus.Destroyed) return null;
  return connection;
}

function getOrCreateVoicePlayer() {
  if (voicePlayer) return voicePlayer;
  voicePlayer = createAudioPlayer({
    behaviors: {
      noSubscriber: NoSubscriberBehavior.Pause
    }
  });
  voicePlayer.on('error', error => {
    const detail = error?.message || String(error);
    console.error(`Voice player error: ${detail}`);
  });
  return voicePlayer;
}

const { transcribeFile } = require('./stt_service');
const { playTTS } = require('./tts_service');
const { concurrencySemaphore } = require('./concurrency_semaphore');

// ... (existing OBS and config code remains same)

async function speakInVoice(text, voiceId = null) {
  if (!VOICE_TTS_ENABLED) return { ok: false, reason: 'VOICE_TTS disabled' };
  if (!voiceConfigured()) return { ok: false, reason: 'VOICE not configured' };

  console.log(`[TTS] Solicitante: IA | Texto: "${text.slice(0, 60)}..."`);

  const connection = getVoiceConnectionSafe();
  if (!connection) {
    console.log('[TTS] No hay conexión activa, intentando conectar...');
    await ensureVoiceConnected();
  }

  const readyConnection = getVoiceConnectionSafe();
  if (!readyConnection) {
    console.error('[TTS] Error: No se pudo establecer conexión de voz para reproducir.');
    return { ok: false, reason: 'No voice connection' };
  }

  try {
    const result = await playTTS(readyConnection, text, { voiceId });
    console.log('[TTS] Proceso de reproducción completado:', result || 'ok');
    return { ok: true };
  } catch (error) {
    console.error('[TTS] Error crítico en speakInVoice:', error.message);
    return { ok: false, error: error.message };
  }
}

async function handleVoiceTranscript(userId, username, text) {
  if (!text || text.length < 3) return;
  console.log(`[STT] ${username}: ${text}`);

  const state = getChannelState(VOICE_CHANNEL_ID);
  state.lastHumanAt = Date.now();
  state.participants.add(userId);
  pushHistory(state, 'user', username, userId, text);

  // Wake word or question
  const wakeSignal = text.toLowerCase().includes(AUTOCHAT_NAME);
  const questionSignal = hasQuestionSignal(text);

  if (wakeSignal || questionSignal) {
    try {
      const prompt = buildAutonomousPrompt(state, { author: { username }, content: text });
      
      const res = await axios.post(
        `${FASTAPI_URL}/agente/consultar-rag`,
        {
          pregunta: prompt,
          usuario_id: userId
        },
        {
          timeout: 45000,
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${NEXO_API_KEY}`
          }
        }
      );

      const respuesta = res?.data?.respuesta || 'No pude procesar tu solicitud por voz.';
      await speakInVoice(respuesta);
      pushHistory(state, 'assistant', 'NEXO', 'assistant', respuesta);
      state.lastBotReplyAt = Date.now();
    } catch (e) {
      console.error('Error procesando comando de voz:', e.message);
    }
  }
}

async function listenToUser(connection, userId, username) {
  const receiver = connection.receiver;
  if (receiver.speaking.users.has(userId)) return;

  console.log(`Escuchando a ${username}...`);

  // Acquire concurrency slot
  await concurrencySemaphore.acquire();

  const tmpWav = path.join(TEMP_DIR, `nexo_voice_${userId}_${Date.now()}.wav`);
  
  try {
    const opusStream = receiver.subscribe(userId, {
      end: {
        behavior: 'silence',
        duration: 1000,
      },
    });

    const decoder = new prism.opus.Decoder({ frameSize: 960, channels: 2, rate: 48000 });
    const ffmpegProc = spawn('ffmpeg', [
      '-f', 's16le', '-ar', '48000', '-ac', '2', '-i', 'pipe:0',
      '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', '-f', 'wav', tmpWav
    ], { stdio: ['pipe', 'ignore', 'inherit'] });

    pipeline(opusStream, decoder, ffmpegProc.stdin, async (err) => {
      if (err) {
        console.error('Pipeline error:', err);
        concurrencySemaphore.release();
        if (fs.existsSync(tmpWav)) fs.unlinkSync(tmpWav);
        return;
      }

      ffmpegProc.once('close', async (code) => {
        try {
          if (code === 0 && fs.existsSync(tmpWav)) {
            const transcript = await transcribeFile(tmpWav);
            if (transcript) {
              await handleVoiceTranscript(userId, username, transcript);
            }
          }
        } catch (e) {
          console.error('STT Processing error:', e.message);
        } finally {
          concurrencySemaphore.release();
          if (fs.existsSync(tmpWav)) fs.unlinkSync(tmpWav);
        }
      });
    });

  } catch (err) {
    console.error('Error en listenToUser:', err);
    concurrencySemaphore.release();
  }
}

async function connectVoiceAlwaysOn(force = false) {
  // ... (rest of the voice connection logic remains roughly the same, 
  // ensuring the receiver is set up as before)
  if (!voiceConfigured()) return { ok: false, reason: 'VOICE not configured' };

  const guild = await client.guilds.fetch(VOICE_GUILD_ID);
  const channel = await guild.channels.fetch(VOICE_CHANNEL_ID);
  if (!channel || channel.type !== 2) {
    throw new Error('VOICE_CHANNEL_ID no corresponde a un canal de voz');
  }

  if (!force) {
    const existing = getVoiceConnection(VOICE_GUILD_ID);
    if (existing && existing.joinConfig.channelId === VOICE_CHANNEL_ID && existing.state.status !== VoiceConnectionStatus.Destroyed) {
      return { ok: true, reason: 'already connected', status: existing.state.status };
    }
  }

  const existing = getVoiceConnection(VOICE_GUILD_ID);
  if (existing) existing.destroy();

  const connection = joinVoiceChannel({
    guildId: VOICE_GUILD_ID,
    channelId: VOICE_CHANNEL_ID,
    adapterCreator: guild.voiceAdapterCreator,
    selfDeaf: VOICE_SELF_DEAF,
    selfMute: false
  });

  connection.on(VoiceConnectionStatus.Disconnected, async () => {
    try {
      await Promise.race([
        entersState(connection, VoiceConnectionStatus.Signalling, 5000),
        entersState(connection, VoiceConnectionStatus.Connecting, 5000),
      ]);
    } catch {
      connection.destroy();
    }
  });

  try {
    await entersState(connection, VoiceConnectionStatus.Ready, 30000);
    console.log(`Voice always-on conectado al canal ${VOICE_CHANNEL_ID}`);
    
    // Configurar el receiver para escuchar a todos los que hablen
    connection.receiver.speaking.on('start', userId => {
      const user = client.users.cache.get(userId);
      if (user && !user.bot) {
        listenToUser(connection, userId, user.username);
      }
    });

    return { ok: true, reason: 'connected', status: connection.state.status };
  } catch (err) {
    // If signalling, wait a bit more
    if (connection.state.status === VoiceConnectionStatus.Signalling || connection.state.status === VoiceConnectionStatus.Connecting) {
      await entersState(connection, VoiceConnectionStatus.Ready, 15000);
      console.log(`Voice always-on conectado al canal ${VOICE_CHANNEL_ID} (retry)`);
      return { ok: true, reason: 'connected-retry', status: connection.state.status };
    }
    throw err;
  }
}

async function ensureVoiceConnected() {
  if (!voiceConfigured()) return;
  try {
    const result = await connectVoiceAlwaysOn(false);
  } catch (error) {
    const detail = error?.message || String(error);
    console.error(`Voice keepalive falló: ${detail}`);
  }
}

function isAllowedAutochatChannel(channelId) {
  if (!AUTOCHAT_CHANNEL_IDS.size) return true;
  return AUTOCHAT_CHANNEL_IDS.has(channelId);
}

function getChannelState(channelId) {
  if (!channelRuntime.has(channelId)) {
    channelRuntime.set(channelId, {
      pending: false,
      lastHumanAt: 0,
      lastBotReplyAt: 0,
      history: [],
      participants: new Set()
    });
  }
  return channelRuntime.get(channelId);
}

function compactText(value, max = 500) {
  const text = (value || '').replace(/\s+/g, ' ').trim();
  return text.length <= max ? text : `${text.slice(0, max - 3)}...`;
}

function pushHistory(state, role, username, userId, content) {
  state.history.push({
    role,
    username,
    userId,
    content: compactText(content, 700),
    at: Date.now()
  });
  if (state.history.length > AUTOCHAT_MAX_CONTEXT_MESSAGES) {
    state.history = state.history.slice(-AUTOCHAT_MAX_CONTEXT_MESSAGES);
  }
}

function hasQuestionSignal(content) {
  const text = (content || '').toLowerCase();
  return (
    text.includes('?') ||
    /\b(que|qué|como|cómo|por que|por qué|puedes|podrias|podrías|explica|opinas|ayuda)\b/.test(text)
  );
}

function hasWakeSignal(content) {
  const text = (content || '').toLowerCase().trim();
  return text.startsWith(`${AUTOCHAT_NAME} `) || text === AUTOCHAT_NAME;
}

function shouldAutoRespond(message, state) {
  if (!AUTOCHAT_ENABLED) return false;
  if (!isAllowedAutochatChannel(message.channelId)) return false;
  if (autoDisabledChannels.has(message.channelId)) return false;

  const now = Date.now();
  if (now - state.lastBotReplyAt < AUTOCHAT_MIN_INTERVAL_MS) return false;

  const mentioned = message.mentions?.has(client.user.id);
  const wakeSignal = hasWakeSignal(message.content);
  const questionSignal = hasQuestionSignal(message.content);
  const activeConversation =
    now - state.lastHumanAt <= AUTOCHAT_ACTIVE_WINDOW_MS &&
    now - state.lastBotReplyAt <= AUTOCHAT_ACTIVE_WINDOW_MS;
  const multiUser = state.participants.size >= 2;

  if (mentioned || wakeSignal) return true;
  if (!AUTOCHAT_ALLOW_WITHOUT_MENTION) {
    return activeConversation && multiUser && questionSignal;
  }
  return activeConversation && (questionSignal || multiUser);
}

function buildAutonomousPrompt(state, message) {
  const contextLines = state.history
    .slice(-AUTOCHAT_MAX_CONTEXT_MESSAGES)
    .map(item => `- ${item.role === 'assistant' ? 'IA' : item.username}: ${item.content}`)
    .join('\n');

  return [
    'Sos NEXO, un asistente de Discord. Responde en español de forma natural, breve y amigable (máximo 80 palabras).',
    'Si te saludan, saludá de vuelta. Si preguntan algo que no sabés, decilo.',
    'Si la pregunta es sobre geopolítica, usá la evidencia disponible.',
    `Participantes activos: ${state.participants.size}.`,
    'Historial reciente:',
    contextLines || '- (sin contexto)',
    `Último mensaje de ${message.author.username}: ${compactText(message.content, 600)}`
  ].join('\n');
}

async function sendLongReply(message, text) {
  const safe = text && text.trim() ? text.trim() : 'No tengo suficiente contexto aún para responder con precisión.';
  const chunks = safe.match(/(.|[\r\n]){1,1800}/g) || [safe];

  for (let index = 0; index < chunks.length; index += 1) {
    const chunk = chunks[index];
    if (index === 0) {
      await message.reply(chunk);
    } else {
      await message.channel.send(chunk);
    }
  }
}

function detectDirectHarm(contenido, fileUrls = []) {
  const text = (contenido || '').toLowerCase();

  const spam = /(.)\1{9,}/.test(text) || ((text.match(/https?:\/\/\S+/g) || []).length >= 6);
  if (spam) return 'spam';

  const doxxing =
    /[\w.-]+@[\w.-]+\.\w+/.test(text) ||
    /\b\d{8,}\b/.test(text) ||
    /(direccion|dirección|domicilio|dni|pasaporte|rut)\b/.test(text);
  if (doxxing) return 'doxxing';

  const malwareTerms = ['.exe', '.bat', '.scr', '.dll', 'keylogger', 'ransomware', 'stealer', 'payload'];
  const hasMalware = malwareTerms.some(term => text.includes(term)) ||
    fileUrls.some(url => malwareTerms.some(term => (url || '').toLowerCase().includes(term)));
  if (hasMalware) return 'malware';

  return null;
}

async function registerCommands() {
  const guildId = (process.env.DISCORD_GUILD_ID || '').trim();

  if (guildId) {
    try {
      const guild = await client.guilds.fetch(guildId);
      await guild.commands.set(commands);
      console.log(`Comandos registrados en guild ${guild.id}`);
      return;
    } catch (error) {
      const detail = error?.message || String(error);
      console.warn(`No se pudo registrar en guild ${guildId}: ${detail}. Usando registro global.`);
    }
  }

  try {
    await client.application.commands.set(commands);
    console.log('Comandos globales registrados');
  } catch (error) {
    const detail = error?.message || String(error);
    console.error(`Falló registro global de comandos: ${detail}`);
  }
}

client.once('ready', async () => {
  console.log(`Bot conectado como ${client.user.tag}`);
  
  await sendAlert({
    type: 'lifecycle',
    source: 'nexo-bot',
    title: 'Bot Ready',
    text: `NEXO se ha conectado como ${client.user.tag}`,
    level: 'info'
  });
  
  // Voice dependency diagnostic
  try {
    const { generateDependencyReport } = require('@discordjs/voice');
    console.log('=== Voice Dependencies ===');
    console.log(generateDependencyReport());
    console.log('=========================');
  } catch (e) { console.warn('No se pudo generar reporte de dependencias de voz'); }
  
  await registerCommands();
  await connectOBS();

  if (voiceConfigured()) {
    await ensureVoiceConnected();
    voiceCheckTimer = setInterval(ensureVoiceConnected, Math.max(10, VOICE_RECONNECT_SECONDS) * 1000);
  } else if (VOICE_ALWAYS_ON) {
    console.warn('VOICE_ALWAYS_ON=true pero faltan VOICE_GUILD_ID o VOICE_CHANNEL_ID');
  }
});

client.on('interactionCreate', async interaction => {
  if (!interaction.isChatInputCommand()) return;

  if (interaction.commandName === 'autonomo') {
    const modo = interaction.options.getString('modo', true);

    if (modo === 'status') {
      const enabled = !autoDisabledChannels.has(interaction.channelId) && AUTOCHAT_ENABLED && isAllowedAutochatChannel(interaction.channelId);
      const scope = AUTOCHAT_CHANNEL_IDS.size ? 'filtrado por AUTOCHAT_CHANNEL_IDS' : 'sin filtro de canales';
      await interaction.reply({
        content: enabled
          ? `Modo autónomo ACTIVO en este canal (${scope}).`
          : `Modo autónomo INACTIVO en este canal (${scope}).`,
        ephemeral: true
      });
      return;
    }

    if (modo === 'off') {
      autoDisabledChannels.add(interaction.channelId);
      await interaction.reply({ content: 'Modo autónomo desactivado para este canal.', ephemeral: true });
      return;
    }

    autoDisabledChannels.delete(interaction.channelId);
    await interaction.reply({ content: 'Modo autónomo activado para este canal.', ephemeral: true });
    return;
  }

  if (interaction.commandName === 'llamada') {
    const accion = interaction.options.getString('accion', true);

    if (!voiceConfigured()) {
      await interaction.reply({
        content: 'Conexión de voz no configurada. Define VOICE_ALWAYS_ON, VOICE_GUILD_ID y VOICE_CHANNEL_ID.',
        ephemeral: true
      });
      return;
    }

    if (accion === 'status') {
      const existing = getVoiceConnection(VOICE_GUILD_ID);
      const status = existing ? existing.state.status : 'disconnected';
      await interaction.reply({ content: `Estado de llamada: ${status}. Canal objetivo: ${VOICE_CHANNEL_ID}`, ephemeral: true });
      return;
    }

    if (accion === 'speaktest') {
      try {
        await connectVoiceAlwaysOn(false);
        const custom = interaction.options.getString('mensaje', false);
        const testText = custom || 'Nexo conectado. Prueba de voz correcta en Discord.';
        await speakInVoice(testText);
        await interaction.reply({ content: 'Prueba de voz encolada y enviada al canal.', ephemeral: true });
      } catch (error) {
        const detail = error?.message || String(error);
        await interaction.reply({ content: `No pude ejecutar la prueba de voz: ${detail}`, ephemeral: true });
      }
      return;
    }

    try {
      const result = await connectVoiceAlwaysOn(true);
      await interaction.reply({ content: `Reconexión ejecutada: ${result.status || result.reason}`, ephemeral: true });
    } catch (error) {
      const detail = error?.message || String(error);
      await interaction.reply({ content: `No pude reconectar la llamada: ${detail}`, ephemeral: true });
    }
    return;
  }

  if (interaction.commandName === 'tutor') {
    const pregunta = interaction.options.getString('pregunta', true);
    await interaction.deferReply();

    try {
      const res = await axios.post(
        `${FASTAPI_URL}/agente/consultar-rag`,
        {
          pregunta,
          usuario_id: interaction.user.id
        },
        {
          timeout: 45000,
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${NEXO_API_KEY}`
          }
        }
      );

      const respuesta = res?.data?.respuesta || 'No encontré evidencia suficiente.';
      const fuentes = Array.isArray(res?.data?.fuentes) ? res.data.fuentes.slice(0, 4) : [];

      const embed = new EmbedBuilder()
        .setColor(0x0099ff)
        .setTitle('Tutor SIG - Respuesta')
        .setDescription(respuesta.length > 3900 ? `${respuesta.slice(0, 3890)}...` : respuesta)
        .setFooter({ text: 'Basado en evidencia real del NEXO SOBERANO' })
        .setTimestamp();

      if (fuentes.length) {
        embed.addFields({
          name: 'Fuentes',
          value: fuentes.map((f, i) => `• [Fuente ${i + 1}](${f})`).join('\n').slice(0, 1024)
        });
      }

      await interaction.editReply({ embeds: [embed] });
      await speakInVoice(respuesta);
    } catch (error) {
      const detail = error?.response?.data?.detail || error?.message || 'Error desconocido';
      console.error('Error /tutor:', detail);
      await interaction.editReply(`Error al consultar el sistema: ${detail}`);
    }

    return;
  }

  if (interaction.commandName === 'aporte') {
    const contenido = interaction.options.getString('contenido', true);
    const attachment = interaction.options.getAttachment('archivo');
    await interaction.deferReply({ ephemeral: true });

    try {
      const files = attachment ? [{ url: attachment.url, name: attachment.name }] : [];
      const blocked = detectDirectHarm(contenido, files.map(f => f.url));
      if (blocked) {
        await interaction.editReply(`Aporte bloqueado por moderación de daño directo: ${blocked}.`);
        return;
      }

      const res = await axios.post(
        `${FASTAPI_URL}/agente/drive/upload-aporte`,
        {
          contenido,
          usuario: interaction.user.username,
          files
        },
        {
          timeout: 45000,
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${NEXO_API_KEY}`
          }
        }
      );

      const aporteId = res?.data?.aporte_id || 'procesando';
      const status = res?.data?.status || 'recibido';
      await interaction.editReply(`Aporte ${status} y enviado a cuarentena. Gracias. ID: ${aporteId}`);
    } catch (error) {
      const detail = error?.response?.data?.detail || error?.message || 'Error desconocido';
      console.error('Error /aporte:', detail);
      await interaction.editReply(`Error al enviar aporte: ${detail}`);
    }
    return;
  }

  if (interaction.commandName === 'nexo') {
    await interaction.deferReply();
    try {
      const res = await axios.get(`${FASTAPI_URL}/agente/health`, { 
        timeout: 15000,
        headers: { 'Authorization': `Bearer ${NEXO_API_KEY}` }
      });
      const stats = res?.data || {};
      
      const embed = new EmbedBuilder()
        .setColor(stats.status === 'ok' ? 0x00FF00 : 0xFF0000)
        .setTitle('Estado del Sistema NEXO SOBERANO')
        .addFields(
          { name: 'Core API', value: '🟢 Online', inline: true },
          { name: 'Motor RAG', value: stats.rag_loaded ? '🟢 Sincronizado (Supabase Vector)' : '🔴 Desconectado', inline: true },
          { name: 'Documentos en Bóveda', value: `${stats.total_documentos || 0} fragmentos de inteligencia`, inline: true },
          { name: 'Tokens Gemini/Presupuesto', value: `${stats.presupuesto?.estado_presupuesto || 'Desconocido'}`, inline: true }
        )
        .setFooter({ text: 'Monitoreo de Infraestructura Híbrida' })
        .setTimestamp();

      await interaction.editReply({ embeds: [embed] });
      await speakInVoice(`Infraestructura verificada. Bóveda vectorial cuenta con ${stats.total_documentos || 0} fragmentos.`);
    } catch (error) {
      console.error('Error /nexo health check:', error.message);
      await interaction.editReply('Error al conectar con la API central de NEXO SOBERANO.');
    }
  }
});

client.on('messageCreate', async message => {
  if (!message.guild || message.author.bot) return;
  if (!message.content || !message.content.trim()) return;

  // ═══ OBS PREFIX COMMANDS ═══
  if (message.content.startsWith('!obs')) {
    const parts = message.content.trim().split(/\s+/);
    const cmd = parts[1] || 'status';
    try {
      if (cmd === 'status') {
        const s = await getOBSStatus();
        const e = new EmbedBuilder()
          .setTitle('Estado OBS')
          .setColor(s.connected ? 0x00ff00 : 0xff0000)
          .addFields(
            { name: 'Conexion', value: s.connected ? 'Online' : 'Offline', inline: true },
            { name: 'Escena', value: s.scene, inline: true },
            { name: 'Stream', value: s.streaming ? 'ACTIVO' : 'Inactivo', inline: true },
            { name: 'Grabacion', value: s.recording ? 'ACTIVA' : 'Inactiva', inline: true },
          )
          .setFooter({ text: 'NEXO SOBERANO' })
          .setTimestamp();
        if (s.streamTime) e.addFields({ name: 'Tiempo', value: s.streamTime, inline: true });
        await message.channel.send({ embeds: [e] });
      } else if (cmd === 'start') {
        if (!obsConnected) await connectOBS();
        await obs.call('StartStream');
        await message.channel.send('Stream iniciado.');
      } else if (cmd === 'stop') {
        await obs.call('StopStream');
        await message.channel.send('Stream detenido.');
      } else if (cmd === 'rec') {
        const sub = parts[2] || 'start';
        if (sub === 'start') { await obs.call('StartRecord'); await message.channel.send('Grabacion iniciada.'); }
        else { await obs.call('StopRecord'); await message.channel.send('Grabacion detenida.'); }
      } else if (cmd === 'scene') {
        const name = parts.slice(2).join(' ');
        if (!name) { await message.channel.send('Uso: `!obs scene NombreEscena`'); return; }
        await obs.call('SetCurrentProgramScene', { sceneName: name });
        await message.channel.send(`Escena cambiada a ${name}.`);
      } else if (cmd === 'reconnect') {
        await connectOBS();
        await message.channel.send(obsConnected ? 'Reconexion OK.' : 'Reconexion fallida.');
      } else if (cmd === 'help') {
        const e = new EmbedBuilder().setTitle('Comandos OBS').setColor(0x3498db)
          .addFields(
            { name: '`!obs status`', value: 'Ver estado', inline: false },
            { name: '`!obs start/stop`', value: 'Iniciar/detener stream', inline: false },
            { name: '`!obs rec start/stop`', value: 'Grabacion', inline: false },
            { name: '`!obs scene Nombre`', value: 'Cambiar escena', inline: false },
            { name: '`!obs reconnect`', value: 'Reconectar OBS', inline: false },
          )
          .setFooter({ text: 'NEXO SOBERANO' });
        await message.channel.send({ embeds: [e] });
      }
    } catch (err) {
      await message.channel.send(`Error OBS: ${err.message}`);
    }
    return;
  }

  const state = getChannelState(message.channelId);
  state.lastHumanAt = Date.now();
  state.participants.add(message.author.id);
  pushHistory(state, 'user', message.author.username, message.author.id, message.content);

  if (!shouldAutoRespond(message, state) || state.pending) return;

  state.pending = true;
  try {
    await message.channel.sendTyping();
    const pregunta = buildAutonomousPrompt(state, message);

    const res = await axios.post(
      `${FASTAPI_URL}/agente/consultar-rag`,
      {
        pregunta,
        usuario_id: message.author.id
      },
      {
        timeout: 45000,
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${NEXO_API_KEY}`
        }
      }
    );

    const respuesta = res?.data?.respuesta || 'No encontré evidencia suficiente para responder con certeza.';
    await sendLongReply(message, respuesta);
    await speakInVoice(respuesta);

    pushHistory(state, 'assistant', 'NEXO', 'assistant', respuesta);
    state.lastBotReplyAt = Date.now();
  } catch (error) {
    const detail = error?.response?.data?.detail || error?.message || 'Error desconocido';
    console.error('Error autónomo:', detail);
    await message.reply(`No pude responder ahora: ${detail}`);
  } finally {
    state.pending = false;
  }
});

client.login(process.env.DISCORD_TOKEN);

process.on('SIGINT', async () => {
  await sendAlert({
    type: 'lifecycle',
    source: 'nexo-bot',
    title: 'Bot Stopping',
    text: 'Recibida señal SIGINT. Apagando...',
    level: 'warning'
  });
  if (voiceCheckTimer) clearInterval(voiceCheckTimer);
  const existing = VOICE_GUILD_ID ? getVoiceConnection(VOICE_GUILD_ID) : null;
  if (existing) existing.destroy();
  process.exit(0);
});
