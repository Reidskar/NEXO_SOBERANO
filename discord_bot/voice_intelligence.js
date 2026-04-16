/**
 * discord_bot/voice_intelligence.js
 * Inteligencia de voz en tiempo real para NEXO
 *
 * Cuando el usuario habla en Discord:
 * 1. Transcribe (STT ya existente)
 * 2. Detecta temas estratégicos mencionados → alerta con streams en vivo
 * 3. Detecta comandos de dispositivo → ejecuta via cola ADB
 * 4. Almacena en topic tracker para seguimiento progresivo
 * 5. Sugiere qué grabar o analizar a continuación
 *
 * Comandos de voz reconocidos:
 * - "nexo, abre [url/app]" → launch_url/launch_app en teléfono
 * - "nexo, captura/graba pantalla" → screenshot / record en teléfono
 * - "nexo, [pregunta]" → análisis IA + búsqueda OSINT
 * - "nexo, streams sobre [tema]" → recomienda streams en vivo
 */

const axios = require('axios');

const NEXO_URL = process.env.FASTAPI_URL || 'http://127.0.0.1:8080';
const NEXO_KEY = process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK';
const HEADERS = { 'x-api-key': NEXO_KEY, 'Content-Type': 'application/json' };

// ── Patrones de comandos de dispositivo ───────────────────────────────────────
const DEVICE_PATTERNS = [
  { re: /nexo[,.]?\s+(?:abre|open|lanza)\s+(.+)/i,         action: 'launch_url',  param: 'url' },
  { re: /nexo[,.]?\s+(?:captura|screenshot|foto)\s*pantalla/i, action: 'screenshot', param: null },
  { re: /nexo[,.]?\s+(?:graba|record|grabá)\s+(?:pantalla|screen)/i, action: 'scrcpy_start', param: null },
  { re: /nexo[,.]?\s+(?:para|stop|detén)\s+(?:grabación|record)/i, action: 'scrcpy_stop', param: null },
  { re: /nexo[,.]?\s+(?:vuelve|home|inicio)\s*(?:al inicio)?/i, action: 'home', param: null },
  { re: /nexo[,.]?\s+(?:vuelve|back|atrás)/i,              action: 'back', param: null },
  { re: /nexo[,.]?\s+(?:despierta|wake up|enciende)\s+(?:el)?(?:teléfono|pantalla|phone)?/i, action: 'wake', param: null },
  { re: /nexo[,.]?\s+(?:streams?|noticias|news)\s+(?:de|sobre|of|on)\s+(.+)/i, action: 'streams', param: 'region' },
  { re: /nexo[,.]?\s+(?:analiza|analize|qué está pasando)\s+(?:en|con|about)\s+(.+)/i, action: 'analyze', param: 'topic' },
  { re: /nexo[,.]?\s+(?:graba|captura|guarda)\s+(?:esto|this|contenido)/i, action: 'capture_content', param: null },
];

// ── Detectar comando de dispositivo en texto ──────────────────────────────────
function detectDeviceCommand(text) {
  for (const pattern of DEVICE_PATTERNS) {
    const match = text.match(pattern.re);
    if (match) {
      return {
        action: pattern.action,
        param: pattern.param ? match[1]?.trim() : null,
        raw: text,
      };
    }
  }
  return null;
}

// ── Ejecutar comando en dispositivo via NEXO API ──────────────────────────────
async function executeDeviceCommand(cmd) {
  try {
    if (cmd.action === 'launch_url') {
      const url = cmd.param?.startsWith('http') ? cmd.param : `https://${cmd.param}`;
      await axios.post(`${NEXO_URL}/api/device/open`, { url }, { headers: HEADERS, timeout: 10000 });
      return `📱 Abriendo ${url} en el teléfono`;
    }
    if (cmd.action === 'streams') {
      // Esto se maneja por detect_topics, no por device
      return null;
    }
    if (cmd.action === 'capture_content') {
      await axios.post(`${NEXO_URL}/api/content/record/start`, {
        source: 'screen', tag: 'GEN', title: `Captura voz ${new Date().toISOString()}`
      }, { headers: HEADERS, timeout: 10000 });
      return '🎙️ Grabación de pantalla iniciada — habla `/nexo para grabar content`';
    }
    // Acciones simples del dispositivo
    const simpleActions = ['screenshot', 'home', 'back', 'wake', 'scrcpy_start', 'scrcpy_stop'];
    if (simpleActions.includes(cmd.action)) {
      if (cmd.action === 'scrcpy_start') {
        await axios.post(`${NEXO_URL}/api/device/scrcpy/start`, {}, { headers: HEADERS, timeout: 10000 });
        return '📱 Espejo de pantalla iniciado';
      }
      if (cmd.action === 'scrcpy_stop') {
        await axios.post(`${NEXO_URL}/api/device/scrcpy/stop`, {}, { headers: HEADERS, timeout: 10000 });
        return '📱 Espejo de pantalla detenido';
      }
      await axios.post(`${NEXO_URL}/api/device/action`, {
        action: cmd.action, params: {}
      }, { headers: HEADERS, timeout: 10000 });
      const labels = {
        screenshot: '📸 Screenshot capturado',
        home: '📱 → Pantalla de inicio',
        back: '📱 → Atrás',
        wake: '📱 Teléfono activado',
      };
      return labels[cmd.action] || `📱 Comando ${cmd.action} ejecutado`;
    }
  } catch (e) {
    console.warn(`[VoiceIntel] Error ejecutando comando ${cmd.action}: ${e.message}`);
    return `⚠️ No se pudo ejecutar ${cmd.action}: ${e.message}`;
  }
  return null;
}

// ── Detectar temas y obtener streams recomendados ─────────────────────────────
async function detectTopicsAndStreams(text) {
  try {
    const r = await axios.post(`${NEXO_URL}/api/topics/detect`,
      { text },
      { headers: HEADERS, timeout: 10000 }
    );
    return r.data;
  } catch(e) {
    return null;
  }
}

// ── Almacenar en Topic Tracker ────────────────────────────────────────────────
async function storeVoiceInTopics(text, topicIds) {
  for (const topicId of topicIds) {
    try {
      await axios.post(`${NEXO_URL}/api/topics/${topicId}/event`, {
        source: 'discord_voice',
        text: text.slice(0, 300),
      }, { headers: HEADERS, timeout: 5000 });
    } catch(e) { /* silencioso */ }
  }
}

// ── Construir respuesta de streams para Discord ───────────────────────────────
function buildStreamsMessage(detection) {
  if (!detection) return null;

  const { matched_topics, detected_regions, recommended_streams } = detection;
  if (!detected_regions?.length && !matched_topics?.length) return null;

  let msg = '';

  if (matched_topics?.length) {
    const names = matched_topics.map(t => `**${t.name}**${t.priority === 'alta' ? ' 🔴' : ''}`).join(', ');
    msg += `📡 Temas activos detectados: ${names}\n`;
  }
  if (detected_regions?.length) {
    msg += `🌍 Regiones: ${detected_regions.join(', ')}\n`;
  }
  if (recommended_streams?.length) {
    msg += `\n📺 **Streams en vivo recomendados:**\n`;
    for (const s of recommended_streams.slice(0, 3)) {
      msg += `• [${s.label}](${s.url})${s.region ? ` — ${s.region}` : ''}\n`;
    }
  }

  return msg || null;
}

// ── Pipeline principal de inteligencia de voz ─────────────────────────────────
async function processVoiceIntelligence(text, userId, textChannel, connection) {
  const results = {
    device_cmd: null,
    topics_detected: null,
    streams_message: null,
    stored_in_topics: false,
  };

  // 1. ¿Hay un comando de dispositivo?
  const deviceCmd = detectDeviceCommand(text);
  if (deviceCmd && deviceCmd.action !== 'streams' && deviceCmd.action !== 'analyze') {
    const cmdResult = await executeDeviceCommand(deviceCmd);
    if (cmdResult && textChannel) {
      await textChannel.send(cmdResult).catch(() => {});
      results.device_cmd = cmdResult;
    }
  }

  // 2. Detectar temas estratégicos en el texto
  const detection = await detectTopicsAndStreams(text);
  results.topics_detected = detection;

  // 3. Si detectó temas/regiones → enviar streams recomendados
  const streamsMsg = buildStreamsMessage(detection);
  if (streamsMsg && textChannel) {
    // Solo enviar si hay contenido sustancial (no en frases muy cortas)
    if (text.length > 15) {
      await textChannel.send(streamsMsg).catch(() => {});
      results.streams_message = streamsMsg;
    }
  }

  // 4. Almacenar en topic tracker para seguimiento progresivo
  const matchedIds = (detection?.matched_topics || []).map(t => t.id);
  if (matchedIds.length) {
    await storeVoiceInTopics(text, matchedIds);
    results.stored_in_topics = true;
  }

  // 5. Si el comando fue "analiza sobre X" → buscar en OSINT
  if (deviceCmd?.action === 'analyze' && deviceCmd.param) {
    try {
      const r = await axios.post(`${NEXO_URL}/api/agente/`, {
        query: `Análisis rápido sobre: ${deviceCmd.param}. Datos OSINT actuales, situación, riesgo.`,
        user_id: userId,
      }, { headers: HEADERS, timeout: 20000 });
      const analysis = r.data?.respuesta;
      if (analysis && textChannel) {
        await textChannel.send(`🧠 **NEXO sobre ${deviceCmd.param}:**\n${analysis.slice(0, 1500)}`).catch(() => {});
      }
    } catch(e) { /* silencioso */ }
  }

  return results;
}

// ── Comando /streams para Discord ─────────────────────────────────────────────
async function handleStreamsCommand(interaction) {
  await interaction.deferReply();
  const topic = interaction.options?.getString('tema') || 'general';
  const detection = await detectTopicsAndStreams(topic);
  const streams = detection?.recommended_streams || [];

  if (!streams.length) {
    return interaction.editReply('No encontré streams recomendados para ese tema.');
  }

  const { EmbedBuilder } = require('discord.js');
  const embed = new EmbedBuilder()
    .setColor(0x4ade80)
    .setTitle(`📺 Streams en Vivo — ${topic}`)
    .setDescription(streams.map(s => `• [${s.label}](${s.url})`).join('\n'))
    .setTimestamp();

  if (detection?.detected_regions?.length) {
    embed.addFields({ name: 'Regiones detectadas', value: detection.detected_regions.join(', ') });
  }

  await interaction.editReply({ embeds: [embed] });
}

// ── Comando /captura para Discord ─────────────────────────────────────────────
async function handleCaptureCommand(interaction) {
  await interaction.deferReply();
  const source = interaction.options?.getString('fuente') || 'screen';
  const tag = interaction.options?.getString('tag') || 'GEN';
  const title = interaction.options?.getString('titulo') || '';

  try {
    const r = await axios.post(`${NEXO_URL}/api/content/record/start`, {
      source, tag, title: title || `Discord capture ${new Date().toLocaleString('es-CL')}`,
    }, { headers: HEADERS, timeout: 10000 });

    await interaction.editReply(`🎙️ Grabación iniciada [${r.data.session_id}]. Usa \`/parar\` para detener y procesar.`);
  } catch(e) {
    await interaction.editReply(`Error: ${e.message}`);
  }
}

async function handleStopCaptureCommand(interaction, sessionId) {
  await interaction.deferReply();
  if (!sessionId) {
    return interaction.editReply('Indica el session_id: `/parar session_id:xxx`');
  }
  try {
    const r = await axios.post(`${NEXO_URL}/api/content/record/stop`, {
      session_id: sessionId
    }, { headers: HEADERS, timeout: 10000 });
    await interaction.editReply(`✅ Grabación ${sessionId} detenida — procesando con Whisper + Gemini...`);
  } catch(e) {
    await interaction.editReply(`Error: ${e.message}`);
  }
}

// ── Alertas de Drive al canal de Discord ──────────────────────────────────────
async function sendDriveAlert(client, fileInfo, linkedTopics) {
  const { EmbedBuilder } = require('discord.js');
  const channelId = process.env.DISCORD_ALERT_CHANNEL_ID;
  if (!channelId) return;

  try {
    const channel = await client.channels.fetch(channelId);
    if (!channel?.isTextBased()) return;

    const embed = new EmbedBuilder()
      .setColor(0x818cf8)
      .setTitle(`📁 Nuevo contenido en Drive — ${fileInfo.name}`)
      .setTimestamp();

    if (fileInfo.drive_url) {
      embed.setURL(fileInfo.drive_url);
    }
    if (fileInfo.description) {
      embed.setDescription(fileInfo.description.slice(0, 300));
    }
    if (linkedTopics?.length) {
      embed.addFields({
        name: '📡 Temas relacionados',
        value: linkedTopics.map(t => `**${t.name}**`).join(', '),
      });
    }
    if (fileInfo.transcript) {
      embed.addFields({
        name: '📝 Extracto',
        value: fileInfo.transcript.slice(0, 400) + '...',
      });
    }

    await channel.send({ embeds: [embed] });
  } catch(e) {
    console.warn('[VoiceIntel] Error enviando Drive alert:', e.message);
  }
}

module.exports = {
  processVoiceIntelligence,
  handleStreamsCommand,
  handleCaptureCommand,
  handleStopCaptureCommand,
  sendDriveAlert,
  detectTopicsAndStreams,
};
