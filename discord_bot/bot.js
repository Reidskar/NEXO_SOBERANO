require('dotenv').config();
const { playTTS } = require('./tts_service');
const { transcribeFile } = require('./stt_service');
const {
  Client,
  GatewayIntentBits,
  EmbedBuilder,
  SlashCommandBuilder,
  Partials
} = require('discord.js');
const { 
  joinVoiceChannel, 
  getVoiceConnection, 
  VoiceConnectionStatus, 
  entersState,
  EndBehaviorType 
} = require('@discordjs/voice');
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const prism = require('prism-media');

const FASTAPI_URL = (process.env.FASTAPI_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

// ─── NEXO AI — Función centralizada → Gemma 4 (torre, $0) ────────────────────
// Usa /api/ai/mobile/query con contexto por usuario Discord.
// Fallback: /api/ai/ask (ruta legacy) si el nuevo endpoint no responde.
async function askNexoAI(prompt, userId, { remember = true, maxTokens = 1500 } = {}) {
  const agentId = `discord_${userId}`;
  try {
    const resp = await axios.post(
      `${FASTAPI_URL}/api/ai/mobile/query`,
      { prompt, agent_id: agentId, max_tokens: maxTokens, remember },
      { timeout: 90000 }
    );
    return {
      text:   resp.data?.text || resp.data?.respuesta || 'Sin respuesta',
      model:  resp.data?.model_used  || 'desconocido',
      source: resp.data?.source      || '',
      ctx:    resp.data?.context_size || 0,
    };
  } catch (err) {
    console.warn(`[NEXO AI] mobile/query falló (${err.message}), usando legacy /api/ai/ask`);
    try {
      const fb = await axios.post(
        `${FASTAPI_URL}/api/ai/ask`,
        { question: prompt },
        { timeout: 30000 }
      );
      return {
        text:   fb.data?.answer || fb.data?.respuesta || 'Sin respuesta',
        model:  'legacy',
        source: 'api_ai_ask',
        ctx:    0,
      };
    } catch (err2) {
      return { text: `Error: ${err2.message}`, model: 'error', source: 'error', ctx: 0 };
    }
  }
}

if (!process.env.DISCORD_TOKEN) {
  console.error('[NEXO ERROR] DISCORD_TOKEN no encontrada');
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
  partials: [Partials.Channel]
});

const commands = [
  new SlashCommandBuilder()
    .setName('nexo')
    .setDescription('Pregunta a NEXO (Gemma 4 local → Gemini fallback)')
    .addStringOption(o => o.setName('query').setDescription('Pregunta').setRequired(true)),
  new SlashCommandBuilder()
    .setName('ai')
    .setDescription('Consulta a la inteligencia principal con contexto persistente')
    .addStringOption(o => o.setName('pregunta').setDescription('Tu pregunta o instrucción').setRequired(true))
    .addBooleanOption(o => o.setName('recordar').setDescription('Mantener en contexto (default: sí)').setRequired(false)),
  new SlashCommandBuilder()
    .setName('memoria')
    .setDescription('Gestiona el contexto de tu conversación con NEXO')
    .addStringOption(o =>
      o.setName('accion')
        .setDescription('ver o limpiar')
        .setRequired(false)
        .addChoices(
          { name: 'Ver contexto actual', value: 'ver' },
          { name: 'Limpiar contexto', value: 'limpiar' },
        )
    ),
  new SlashCommandBuilder().setName('status').setDescription('Métricas del sistema'),
  new SlashCommandBuilder().setName('unirse').setDescription('NEXO entra al canal de voz'),
  new SlashCommandBuilder().setName('salir').setDescription('NEXO sale del canal de voz'),
  new SlashCommandBuilder()
    .setName('drive')
    .setDescription('Busca información en el Drive de NEXO')
    .addStringOption(opt =>
      opt.setName('consulta').setDescription('Qué quieres buscar o preguntar').setRequired(true)
    ),
  new SlashCommandBuilder()
    .setName('geopolitica')
    .setDescription('Consulta la carpeta Geopolítica del Drive')
    .addStringOption(opt =>
      opt.setName('tema').setDescription('Tema geopolítico a consultar').setRequired(false)
    ),
  new SlashCommandBuilder()
    .setName('social')
    .setDescription('Monitorea o analiza redes sociales')
    .addStringOption(opt =>
      opt.setName('accion')
        .setDescription('monitor, analizar, estado')
        .setRequired(true)
        .addChoices(
          { name: 'Ver estado social media', value: 'estado' },
          { name: 'Analizar sentimiento', value: 'analizar' }
        )
    )
    .addStringOption(opt =>
      opt.setName('texto')
        .setDescription('Texto o keywords para analizar')
        .setRequired(false)
    ),
];

client.once('clientReady', async (c) => {
  console.log(`[NEXO] Bot conectado como ${c.user.tag}`);
  try {
    const guildId = process.env.DISCORD_GUILD_ID;
    if (guildId) {
      try {
        const guild = await client.guilds.fetch(guildId);
        await guild.commands.set(commands);
        console.log(`Comandos registrados en guild ${guildId}`);
      } catch (guildErr) {
        console.warn(`[NEXO] Guild ${guildId} no accesible (${guildErr.message}), usando comandos globales`);
        await client.application.commands.set(commands);
        console.log('Comandos globales registrados (fallback)');
      }
    } else {
      await client.application.commands.set(commands);
      console.log('Comandos globales registrados');
    }
  } catch (err) {
    console.error('Error registrando comandos:', err.message);
  }
});

client.on('interactionCreate', async interaction => {
  if (!interaction.isChatInputCommand()) return;
  await interaction.deferReply();
  const { commandName, options, user, guildId, channel } = interaction;

  if (commandName === 'nexo') {
    const query = options.getString('query');
    const result = await askNexoAI(query, user.id);
    const footer = result.source !== 'error' ? `\n-# ${result.model} · ctx:${result.ctx}` : '';
    await interaction.editReply((result.text.substring(0, 1990) + footer).trim());
  }

  if (commandName === 'ai') {
    const pregunta = options.getString('pregunta');
    const recordar = options.getBoolean('recordar') ?? true;
    const result = await askNexoAI(pregunta, user.id, { remember: recordar, maxTokens: 2000 });

    if (result.source === 'error') {
      await interaction.editReply(`⚠️ ${result.text}`);
      return;
    }

    const embed = new EmbedBuilder()
      .setColor(result.source.includes('ollama') ? 0x00e5ff : 0xf59e0b)
      .setDescription(result.text.substring(0, 4000))
      .setFooter({ text: `${result.model} · ${result.source} · ctx:${result.ctx} turnos` })
      .setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  }

  if (commandName === 'memoria') {
    const accion = options.getString('accion') || 'ver';
    const agentId = `discord_${user.id}`;

    if (accion === 'limpiar') {
      try {
        await axios.delete(
          `${FASTAPI_URL}/api/ai/mobile/context/${agentId}`,
          { headers: { 'X-API-Key': process.env.NEXO_API_KEY || 'nexo_dev_key_2025' }, timeout: 5000 }
        );
        await interaction.editReply('🧹 Contexto limpiado. La próxima pregunta empieza desde cero.');
      } catch (err) {
        await interaction.editReply(`Error al limpiar contexto: ${err.message}`);
      }
      return;
    }

    // ver
    try {
      const resp = await axios.get(`${FASTAPI_URL}/api/ai/mobile/context/${agentId}`, { timeout: 5000 });
      const ctx = resp.data;
      if (!ctx.turns || ctx.turns === 0) {
        await interaction.editReply('No hay contexto guardado aún. Haz una pregunta con `/ai` para empezar.');
        return;
      }
      const last = ctx.context.slice(-6); // last 3 turns
      const preview = last.map(t => `**${t.role === 'user' ? '👤' : '🤖'}** ${t.content.substring(0, 200)}`).join('\n');
      const embed = new EmbedBuilder()
        .setTitle(`Contexto NEXO — ${ctx.turns} turnos`)
        .setColor(0x00e5ff)
        .setDescription(preview.substring(0, 4000))
        .setFooter({ text: 'Usa /memoria limpiar para resetear' });
      await interaction.editReply({ embeds: [embed] });
    } catch (err) {
      await interaction.editReply(`Error: ${err.message}`);
    }
  }

  if (commandName === 'status') {
    try {
      const resp = await axios.get(`${FASTAPI_URL}/api/metrics/`);
      const sys = resp.data.sistema || resp.data.system || {};
      const embed = new EmbedBuilder()
        .setTitle('NEXO Status')
        .setColor(0x00AE86)
        .addFields(
          { name: 'CPU', value: `${sys.cpu_percent || sys.uso_pct || '?'}%`, inline: true },
          { name: 'RAM', value: `${sys.memory_percent || '?'}%`, inline: true },
          { name: 'Uptime', value: `${resp.data.uptime_legible || '?'}`, inline: true }
        );
      await interaction.editReply({ embeds: [embed] });
    } catch (err) { await interaction.editReply('Error al rescatar métricas.'); }
  }

  if (commandName === 'unirse') {
    const voiceChannel = interaction.member?.voice?.channel;
    if (!voiceChannel) return interaction.editReply('❌ Debes estar en un canal de voz.');
    
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
          console.log('[NEXO VOICE] Conexión de voz cerrada limpiamente');
        }
      });

      const textCh = interaction.channel || channel;
      console.log(`[NEXO VOICE] Conectando a ${voiceChannel.name}, texto en ${textCh?.id}`);
      setupVoiceHandler(connection, textCh);
      await interaction.editReply(`✅ Conectado a **${voiceChannel.name}**. Escuchando...`);
    } catch (err) {
      await interaction.editReply(`Error al unir: ${err.message}`);
    }
  }

  if (commandName === 'salir') {
    const conn = getVoiceConnection(guildId);
    if (conn) {
      conn.destroy();
      await interaction.editReply('👋 He salido del canal.');
    } else {
      await interaction.editReply('No estoy en un canal de voz.');
    }
  }

  if (commandName === 'drive') {
    const consulta = options.getString('consulta');
    try {
      const ctxRes = await axios.post(
        `${FASTAPI_URL}/api/drive/contexto`,
        { mensaje_usuario: consulta, folder_id: '10pn6Zo5_SUTf2jlWaH98rs0wtF3W0Trx' },
        { timeout: 15000 }
      );
      const ctx = ctxRes.data;
      let promptConContexto = consulta;
      if (ctx.contexto_encontrado && ctx.contexto_raw) {
        promptConContexto = `El usuario pregunta: "${consulta}"\n\nContexto desde Drive (${ctx.archivos.join(', ')}):\n${ctx.contexto_raw}\n\nResponde de forma clara y directa usando este contexto.`;
      }
      const resp = await axios.post(
        `${FASTAPI_URL}/api/agente/`,
        { query: promptConContexto, user_id: user.id },
        { timeout: 30000 }
      );
      const respuesta = resp.data?.respuesta || resp.data?.mensaje || 'Sin respuesta';
      const fuentes = ctx.archivos?.length ? `\n\n*Fuentes: ${ctx.archivos.join(', ')}*` : '';
      await interaction.editReply(respuesta.substring(0, 1900) + fuentes);
    } catch (err) {
      const msg = (err.code === 'ECONNREFUSED' || err.code === 'ETIMEDOUT')
        ? '⚠️ El sistema NEXO está iniciando. Intenta en 30 segundos.'
        : `⚠️ Error consultando Drive: ${err.message}`;
      await interaction.editReply(msg);
    }
  }

  if (commandName === 'geopolitica') {
    const tema = options.getString('tema') || 'situación actual';
    try {
      const ctxRes = await axios.post(
        `${FASTAPI_URL}/api/drive/contexto`,
        { mensaje_usuario: tema, folder_id: '10pn6Zo5_SUTf2jlWaH98rs0wtF3W0Trx' },
        { timeout: 15000 }
      );
      const ctx = ctxRes.data;
      if (!ctx.contexto_encontrado) {
        await interaction.editReply('No encontré archivos relevantes en la carpeta Geopolítica para ese tema.');
        return;
      }
      const prompt = `Analiza y resume la siguiente información geopolítica sobre "${tema}":\n\n${ctx.contexto_raw}\n\nDa un análisis directo, objetivo y estructurado.`;
      const resp = await axios.post(
        `${FASTAPI_URL}/api/agente/`,
        { query: prompt, user_id: user.id },
        { timeout: 30000 }
      );
      const respuesta = resp.data?.respuesta || resp.data?.mensaje || 'Sin respuesta';
      await interaction.editReply(
        `**Análisis Geopolítico: ${tema}**\n\n${respuesta.substring(0, 1800)}\n\nFuentes: ${ctx.archivos.join(', ')}`
      );
    } catch (err) {
      const msg = (err.code === 'ECONNREFUSED' || err.code === 'ETIMEDOUT')
        ? '⚠️ El sistema NEXO está iniciando. Intenta en 30 segundos.'
        : `⚠️ Error: ${err.message}`;
      await interaction.editReply(msg);
    }
  }

  if (commandName === 'social') {
    const accion = options.getString('accion');
    const texto = options.getString('texto') || '';
    try {
      if (accion === 'estado') {
        const res = await axios.get(`${FASTAPI_URL}/api/social/health`, { timeout: 10000 });
        const s = res.data.status;
        const lines = Object.entries(s).map(([k, v]) => `**${k}**: ${v}`).join('\n');
        await interaction.editReply(`**Estado Social Media**\n${lines}`);
      } else if (accion === 'analizar' && texto) {
        const res = await axios.post(
          `${FASTAPI_URL}/api/social/analizar-sentimiento`,
          { texto, pais: 'Chile' },
          { timeout: 15000 }
        );
        const s = res.data.sentimiento;
        const heatScore = s?.heat_score !== undefined ? `Heat score: ${s.heat_score}` : JSON.stringify(s);
        await interaction.editReply(`**Análisis de sentimiento**\n"${texto}"\n→ ${heatScore}`);
      } else {
        await interaction.editReply('Especifica un texto para analizar.');
      }
    } catch (err) {
      const msg = (err.code === 'ECONNREFUSED' || err.code === 'ETIMEDOUT')
        ? '⚠️ El sistema NEXO está iniciando. Intenta en 30 segundos.'
        : `⚠️ Error: ${err.message}`;
      await interaction.editReply(msg);
    }
  }
});

function setupVoiceHandler(connection, textChannel) {
  console.log(`[NEXO VOICE] setupVoiceHandler activo. Canal texto: ${textChannel?.id || 'NINGUNO'}`);

  connection.receiver.speaking.on('start', userId => {
    console.log(`[NEXO VOICE] Usuario ${userId} empezó a hablar`);
    handleUserVoice(connection, userId, textChannel);
  });

  connection.on(VoiceConnectionStatus.Ready, () => {
    console.log('[NEXO VOICE] Conexión READY - escuchando audio');
  });
}

const activeUsers = new Map();

function handleUserVoice(connection, userId, textChannel) {
  if (activeUsers.has(userId)) return;
  activeUsers.set(userId, true);

  const receiver = connection.receiver;
  const audioStream = receiver.subscribe(userId, {
    end: { behavior: EndBehaviorType.Manual }
  });

  const opusDecoder = new prism.opus.Decoder({ rate: 48000, channels: 2, frameSize: 960 });
  const wavPath = path.join(__dirname, `tmp_${userId}_${Date.now()}.wav`);

  const ffmpegStatic = require('ffmpeg-static');
  const ffProc = spawn(ffmpegStatic, [
    '-f', 's16le', '-ar', '48000', '-ac', '2', '-i', 'pipe:0',
    '-af', 'volume=3.0',
    '-ar', '16000', '-ac', '1', wavPath, '-y'
  ]);

  let chunkCount = 0;
  let lastDataTime = Date.now();

  // Detector de silencio manual (1.5s sin datos = fin)
  const silenceCheck = setInterval(() => {
    if (Date.now() - lastDataTime > 1500 && chunkCount > 0) {
      console.log(`[NEXO VOICE] Silencio detectado (${chunkCount} chunks). Cerrando grabación.`);
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

  opusDecoder.on('data', () => {
    chunkCount++;
    lastDataTime = Date.now();
    if (chunkCount === 10) console.log(`[NEXO VOICE] Grabando audio de ${userId}...`);
  });

  audioStream.pipe(opusDecoder).pipe(ffProc.stdin);

  ffProc.on('close', async () => {
    if (chunkCount < 40) {
      console.log(`[NEXO VOICE] Audio muy corto (${chunkCount} chunks). Ignorando.`);
      if (fs.existsSync(wavPath)) fs.unlinkSync(wavPath);
      return;
    }
    if (!fs.existsSync(wavPath)) return;

    console.log(`[NEXO VOICE] Procesando ${chunkCount} chunks de audio...`);

    try {
      let text = '';
      if (process.env.GROQ_API_KEY) {
        console.log('[NEXO VOICE] STT via Groq...');
        text = await transcribeFile(wavPath);
      } else {
        console.log('[NEXO VOICE] STT via Whisper local (puede tardar 30s)...');
        text = await transcribirWhisper(wavPath);
      }
      if (fs.existsSync(wavPath)) fs.unlinkSync(wavPath);

      if (!text || text.trim().length < 3) {
        console.log('[NEXO VOICE] STT vacío, ignorando.');
        return;
      }

      const lowered = text.toLowerCase().trim();
      const hallucinations = ['gracias.', 'gracias', 'subtitles by', 'mushrooms', 'amara.org'];
      if (hallucinations.some(h => lowered.includes(h)) && lowered.length < 15) {
        console.log(`[NEXO VOICE] Alucinación filtrada: "${text}"`);
        return;
      }

      console.log(`[NEXO VOICE] STT: "${text}"`);
      const user = client.users.cache.get(userId);
      if (textChannel) textChannel.send(`🎙️ **${user?.username || userId}:** ${text}`).catch(() => {});

      const aiResult = await askNexoAI(text, userId, { remember: true, maxTokens: 600 });
      const iaText = aiResult.text || 'No pude procesar tu solicitud.';
      console.log(`[NEXO VOICE] IA: "${iaText.substring(0, 80)}"`);

      if (textChannel) textChannel.send(`🤖 **NEXO:** ${iaText}`).catch(() => {});
      await playTTS(connection, iaText);

    } catch (err) {
      console.error('[NEXO VOICE] Error pipeline:', err.response?.data || err.message);
      if (fs.existsSync(wavPath)) fs.unlinkSync(wavPath);
    }
  });
}

async function transcribirWhisper(wavPath) {
  // Fallback: Whisper local Python (requiere: pip install openai-whisper)
  return new Promise(resolve => {
    const py = spawn('python', ['-c', `
import whisper
model = whisper.load_model('base')
result = model.transcribe('${wavPath.replace(/\\/g, '/')}', language='es')
print(result['text'].strip())
    `]);
    let output = '';
    py.stdout.on('data', d => { output += d; });
    py.stderr.on('data', () => {}); // silenciar warnings de pytorch
    py.on('close', () => resolve(output.trim()));
    setTimeout(() => { py.kill(); resolve(''); }, 60000);
  });
}

const token = process.env.DISCORD_TOKEN.trim();
console.log(`[NEXO INFO] Iniciando login (Token length: ${token.length})`);
client.login(token);

// ─── /phone command — control remoto del teléfono desde Discord ───────────────
client.on('interactionCreate', async interaction => {
  if (!interaction.isChatInputCommand() || interaction.commandName !== 'phone') return;
  await interaction.deferReply();

  const action  = interaction.options.getString('accion');
  const agentId = interaction.options.getString('dispositivo') || 'telefono';
  const message = interaction.options.getString('mensaje') || '';

  try {
    const resp = await axios.post(
      `${FASTAPI_URL}/api/mobile/quick/${agentId}/${action}`,
      {},
      {
        headers: { 'X-API-Key': process.env.NEXO_API_KEY || 'nexo_dev_key_2025' },
        params:  message ? { message } : {},
        timeout: 10000,
      }
    );

    const ACTION_LABELS = {
      silence:    '🔇 Silenciado',    unsilence: '🔊 Volumen restaurado',
      find:       '📍 Buscando...',   locate:    '🗺️ Solicitando GPS',
      camera:     '📷 Foto tomada',   screenshot:'🖼️ Captura',
      lock_screen:'🔒 Bloqueando',    torch_on:  '🔦 Linterna ON',
      torch_off:  '🔦 Linterna OFF',  ping:      '🏓 Ping enviado',
      wakeup:     '🔔 Wake-up enviado',
    };

    const label = ACTION_LABELS[action] || action;
    const embed = new EmbedBuilder()
      .setTitle(`${label} → ${agentId}`)
      .setColor(0x00e5ff)
      .setDescription(`Comando enviado al dispositivo.\nSe ejecutará en el próximo ciclo del agente (~10s).`)
      .addFields(
        { name: 'Comandos encolados', value: String(resp.data.queued_commands || 1), inline: true },
        { name: 'Dispositivo',        value: agentId,                                inline: true },
      )
      .setFooter({ text: 'Torre — dispositivo de confianza' })
      .setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  } catch (err) {
    await interaction.editReply(`⚠️ Error: ${err.response?.data?.detail || err.message}`);
  }
});
