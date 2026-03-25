require('dotenv').config();
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
  new SlashCommandBuilder().setName('nexo').setDescription('Pregunta general').addStringOption(o => o.setName('query').setDescription('Pregunta').setRequired(true)),
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
      const guild = await client.guilds.fetch(guildId);
      await guild.commands.set(commands);
      console.log(`Comandos registrados en guild ${guildId}`);
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
    try {
      const resp = await axios.post(`${FASTAPI_URL}/api/agente/`, { query, user_id: user.id });
      await interaction.editReply(resp.data.respuesta || 'Sin respuesta');
    } catch (err) { await interaction.editReply(`Error: ${err.message}`); }
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

      setupVoiceHandler(connection, channel);
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
  connection.receiver.speaking.on('start', userId => {
    handleUserVoice(connection, userId, textChannel);
  });
}

function handleUserVoice(connection, userId, textChannel) {
  const receiver = connection.receiver;
  const audioStream = receiver.subscribe(userId, {
    end: { behavior: EndBehaviorType.AfterSilence, duration: 1500 }
  });

  const opusDecoder = new prism.opus.Decoder({ rate: 48000, channels: 2, frameSize: 960 });
  const pcmPath = path.join(__dirname, `tmp_${userId}.pcm`);
  const writeStream = fs.createWriteStream(pcmPath);

  audioStream.pipe(opusDecoder).pipe(writeStream);

  audioStream.on('end', async () => {
    writeStream.end();
    const text = await transcribirWhisper(pcmPath);
    if (text && text.length > 3) {
      const user = client.users.cache.get(userId);
      await textChannel.send(`🎙️ **${user?.username || userId}:** ${text}`);
      try {
        const resp = await axios.post(`${FASTAPI_URL}/api/agente/`, {
          query: text, user_id: userId, canal: textChannel.id
        });
        await textChannel.send(`🤖 **NEXO:** ${resp.data.respuesta}`);
      } catch (err) {
        console.error('Error IA voz:', err.message);
      }
    }
    if (fs.existsSync(pcmPath)) fs.unlinkSync(pcmPath);
  });
}

async function transcribirWhisper(pcmPath) {
  return new Promise(resolve => {
    const wavPath = pcmPath.replace('.pcm', '.wav');
    const ffmpegProc = spawn('ffmpeg', [
      '-y', '-f', 's16le', '-ar', '48000', '-ac', '2', '-i', pcmPath,
      '-ar', '16000', '-ac', '1', wavPath
    ]);

    ffmpegProc.on('close', () => {
      const py = spawn('python', ['-c', `
import whisper, sys
model = whisper.load_model('base')
result = model.transcribe('${wavPath.replace(/\\/g, '/')}', language='es')
print(result['text'].strip())
      `]);
      let output = '';
      py.stdout.on('data', d => output += d);
      py.on('close', () => {
        if (fs.existsSync(wavPath)) fs.unlinkSync(wavPath);
        resolve(output.trim());
      });
      setTimeout(() => { py.kill(); resolve(''); }, 45000);
    });
  });
}

const token = process.env.DISCORD_TOKEN.trim();
console.log(`[NEXO INFO] Iniciando login (Token length: ${token.length})`);
client.login(token);
