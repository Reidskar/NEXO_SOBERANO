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
const { runProactiveLoop, handleOsintCommand } = require('./proactive_intel');
const { processVoiceIntelligence, handleStreamsCommand, handleCaptureCommand, handleStopCaptureCommand } = require('./voice_intelligence');

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
  new SlashCommandBuilder().setName('osint').setDescription('Estado del OSINT Engine — vuelos, satélites, mercados, amenazas'),
  new SlashCommandBuilder().setName('briefing').setDescription('Genera el briefing de inteligencia diario ahora'),
  new SlashCommandBuilder().setName('streams')
    .setDescription('Streams en vivo recomendados para un tema')
    .addStringOption(o => o.setName('tema').setDescription('Tema o región').setRequired(false)),
  new SlashCommandBuilder().setName('captura')
    .setDescription('Inicia grabación de contenido')
    .addStringOption(o => o.setName('fuente').setDescription('phone|screen|obs').setRequired(false))
    .addStringOption(o => o.setName('tag').setDescription('MIL|ECO|GEO|POL|PSY|GEN').setRequired(false))
    .addStringOption(o => o.setName('titulo').setDescription('Título de la captura').setRequired(false)),
  new SlashCommandBuilder().setName('parar')
    .setDescription('Detiene una grabación activa')
    .addStringOption(o => o.setName('session_id').setDescription('ID de la sesión').setRequired(true)),
  new SlashCommandBuilder().setName('temas').setDescription('Lista temas estratégicos en seguimiento'),
  new SlashCommandBuilder().setName('dispositivo')
    .setDescription('Controla el teléfono remotamente')
    .addStringOption(o => o.setName('accion').setDescription('screenshot|home|back|wake|scrcpy_start|scrcpy_stop').setRequired(true)),
  new SlashCommandBuilder().setName('youtube')
    .setDescription('Registra un stream YouTube activo para que NEXO lo monitoree')
    .addStringOption(o => o.setName('url').setDescription('URL del video/stream').setRequired(true))
    .addStringOption(o => o.setName('titulo').setDescription('Título del contenido').setRequired(false)),
  new SlashCommandBuilder().setName('sesion').setDescription('Estado de la sesión cognitiva activa'),
  new SlashCommandBuilder()
    .setName('canva')
    .setDescription('Crea un diseño visual en Canva con datos de inteligencia NEXO')
    .addStringOption(o => o.setName('tema').setDescription('Qué diseñar — ej: "infografía de tensiones en el Estrecho de Taiwán"').setRequired(true))
    .addStringOption(o => o.setName('tipo').setDescription('poster|infografia|presentacion|documento').setRequired(false)),
  new SlashCommandBuilder().setName('metacog').setDescription('Estadísticas de metacognición del motor cognitivo'),
  new SlashCommandBuilder()
    .setName('agente')
    .setDescription('Gestiona agentes autónomos NEXO')
    .addStringOption(o => o.setName('accion')
      .setDescription('lista|nuevo|activar|desactivar|ejecutar|plantillas')
      .setRequired(true)
      .addChoices(
        { name: 'Listar agentes', value: 'lista' },
        { name: 'Ver plantillas disponibles', value: 'plantillas' },
        { name: 'Ejecutar ciclo manual', value: 'ejecutar' },
        { name: 'Activar agente', value: 'activar' },
        { name: 'Desactivar agente', value: 'desactivar' },
      ))
    .addStringOption(o => o.setName('id').setDescription('ID del agente o plantilla').setRequired(false)),
  new SlashCommandBuilder()
    .setName('crear-agente')
    .setDescription('Crea un agente autónomo desde plantilla')
    .addStringOption(o => o.setName('plantilla')
      .setDescription('mercados|osint_sweep|vuelos|amenazas_cyber|noticias_geopolitica|playwright_web')
      .setRequired(true))
    .addStringOption(o => o.setName('nombre').setDescription('Nombre personalizado (opcional)').setRequired(false)),
  new SlashCommandBuilder()
    .setName('mcp')
    .setDescription('Usa herramientas MCP (playwright, cloudflare, discord)')
    .addStringOption(o => o.setName('herramienta')
      .setDescription('screenshot|scrape|tools|status')
      .setRequired(true)
      .addChoices(
        { name: 'Ver estado del gateway', value: 'status' },
        { name: 'Listar herramientas', value: 'tools' },
        { name: 'Captura de pantalla web', value: 'screenshot' },
        { name: 'Extraer texto de web', value: 'scrape' },
      ))
    .addStringOption(o => o.setName('url').setDescription('URL (para screenshot/scrape)').setRequired(false)),
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
  // Iniciar loop de inteligencia proactiva
  runProactiveLoop(c).catch(e => console.error('[NEXO Proactive] Error fatal:', e.message));
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

  if (commandName === 'youtube') {
    const url = options.getString('url');
    const titulo = options.getString('titulo') || url;
    const chanId = interaction.channelId;
    try {
      await axios.post(`${FASTAPI_URL}/api/cognitive/youtube`, {
        channel_id: chanId, url, title: titulo,
      }, { headers: { 'x-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' }, timeout: 8000 });
      return interaction.editReply(`📺 Stream registrado: **${titulo}**\nNEXO monitorea el contenido y alertará si algo relevante ocurre.`);
    } catch(e) { return interaction.editReply(`Error: ${e.message}`); }
  }

  if (commandName === 'sesion') {
    const chanId = interaction.channelId;
    try {
      const r = await axios.get(`${FASTAPI_URL}/api/cognitive/session?channel_id=${chanId}`, {
        headers: { 'x-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' }, timeout: 8000
      });
      const s = r.data;
      const { EmbedBuilder } = require('discord.js');
      const embed = new EmbedBuilder()
        .setColor(0x818cf8)
        .setTitle('🧠 Sesión Cognitiva NEXO')
        .addFields(
          { name: 'ID Sesión', value: s.session_id || '—', inline: true },
          { name: 'Turnos', value: String(s.turns || 0), inline: true },
          { name: 'YouTube activo', value: s.youtube_active ? `✅ ${s.youtube_context?.title || '?'}` : '—', inline: false },
          { name: 'Temas activos', value: s.active_topics?.length ? s.active_topics.join(', ') : 'Ninguno', inline: false },
        )
        .setTimestamp();
      return interaction.editReply({ embeds: [embed] });
    } catch(e) { return interaction.editReply(`Error: ${e.message}`); }
  }

  if (commandName === 'osint')    return handleOsintCommand(interaction);
  if (commandName === 'streams')  return handleStreamsCommand(interaction);
  if (commandName === 'captura')  return handleCaptureCommand(interaction);
  if (commandName === 'parar') {
    const sid = options.getString('session_id');
    return handleStopCaptureCommand(interaction, sid);
  }

  if (commandName === 'temas') {
    try {
      const r = await axios.get(`${FASTAPI_URL}/api/topics`, {
        headers: { 'x-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' }, timeout: 10000
      });
      const topics = r.data?.topics || [];
      if (!topics.length) return interaction.editReply('No hay temas en seguimiento. Créalos en `/control/osint`.');
      const { EmbedBuilder } = require('discord.js');
      const embed = new EmbedBuilder()
        .setColor(0x4ade80)
        .setTitle('📡 Temas en Seguimiento — NEXO')
        .setDescription(topics.slice(0, 10).map(t =>
          `**${t.name}** [${t.priority}] — ${t.events?.length || 0} eventos · ${t.drive_files?.length || 0} videos Drive`
        ).join('\n'))
        .setTimestamp();
      return interaction.editReply({ embeds: [embed] });
    } catch(e) { return interaction.editReply(`Error: ${e.message}`); }
  }

  if (commandName === 'dispositivo') {
    const accion = options.getString('accion');
    try {
      if (accion === 'scrcpy_start') {
        await axios.post(`${FASTAPI_URL}/api/device/scrcpy/start`, {}, {
          headers: { 'x-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' }, timeout: 10000
        });
        return interaction.editReply('📱 Espejo de pantalla iniciado');
      }
      if (accion === 'scrcpy_stop') {
        await axios.post(`${FASTAPI_URL}/api/device/scrcpy/stop`, {}, {
          headers: { 'x-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' }, timeout: 10000
        });
        return interaction.editReply('📱 Espejo de pantalla detenido');
      }
      await axios.post(`${FASTAPI_URL}/api/device/action`, { action: accion, params: {} }, {
        headers: { 'x-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' }, timeout: 10000
      });
      return interaction.editReply(`📱 Comando \`${accion}\` ejecutado`);
    } catch(e) { return interaction.editReply(`Error: ${e.message}`); }
  }

  if (commandName === 'osint') {
    // fallthrough eliminated above
  }

  if (commandName === 'briefing') {
    const { runProactiveLoop: _, handleOsintCommand: __, ...intel } = require('./proactive_intel');
    // Forzar sweep y responder con resumen
    try {
      const r = await axios.get(`${FASTAPI_URL}/api/osint/status`, { headers: {'x-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK'}, timeout:10000 });
      const s = r.data;
      await interaction.editReply(`🌐 **NEXO BRIEFING** | ${s.sources_ok}/${s.sources} fuentes OK | Último sweep: ${s.last_sweep ? new Date(s.last_sweep).toLocaleTimeString('es-CL') : 'N/A'} | Usa \`/osint\` para detalles.`);
    } catch(e) {
      await interaction.editReply(`Error: ${e.message}`);
    }
    return;
  }

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

  // ── MCP Gateway ────────────────────────────────────────────────────
  if (commandName === 'mcp') {
    const herramienta = options.getString('herramienta');
    const url = options.getString('url') || '';
    const headers = { 'x-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' };
    try {
      if (herramienta === 'status') {
        const r = await axios.get(`${FASTAPI_URL}/api/mcp/status`, { headers, timeout: 10000 });
        const s = r.data;
        const serverLines = Object.entries(s.servers || {}).map(([k, v]) => `**${k}**: ${v} tools`).join('\n');
        const embed = new EmbedBuilder()
          .setColor(s.available ? 0x22c55e : 0xef4444)
          .setTitle(`🐳 Docker MCP Gateway — ${s.available ? 'ONLINE' : 'OFFLINE'}`)
          .setDescription(s.available ? `**${s.total_tools}** herramientas activas` : `⚠️ ${s.note}`)
          .addFields({ name: 'Servidores MCP', value: serverLines || '—' })
          .setTimestamp();
        return interaction.editReply({ embeds: [embed] });
      }
      if (herramienta === 'tools') {
        const r = await axios.get(`${FASTAPI_URL}/api/mcp/tools`, { headers, timeout: 15000 });
        const tools = r.data.tools || [];
        const names = tools.map(t => t.name).slice(0, 30).join(', ');
        return interaction.editReply(`🔧 **${r.data.total} herramientas MCP**\n\`\`\`${names}${r.data.total > 30 ? `... +${r.data.total - 30} más` : ''}\`\`\``);
      }
      if (herramienta === 'screenshot') {
        if (!url) return interaction.editReply('❌ Especifica una `url`.');
        const r = await axios.post(`${FASTAPI_URL}/api/mcp/playwright/screenshot`, { url }, { headers, timeout: 30000 });
        if (r.data.ok) {
          return interaction.editReply(`📸 Captura tomada de **${url}**\n${r.data.result?.substring(0, 200) || '(imagen procesada)'}`);
        }
        return interaction.editReply(`❌ Error: ${r.data.error}`);
      }
      if (herramienta === 'scrape') {
        if (!url) return interaction.editReply('❌ Especifica una `url`.');
        const r = await axios.post(`${FASTAPI_URL}/api/mcp/playwright/scrape`, { url }, { headers, timeout: 30000 });
        if (r.data.ok) {
          const text = r.data.result?.substring(0, 1800) || '(sin contenido)';
          return interaction.editReply(`🌐 **${url}**\n\`\`\`${text}\`\`\``);
        }
        return interaction.editReply(`❌ ${r.data.error}`);
      }
    } catch(e) {
      return interaction.editReply(`Error MCP: ${e.message}`);
    }
  }

  // ── Agentes autónomos ──────────────────────────────────────────────
  if (commandName === 'agente') {
    const accion = options.getString('accion');
    const agentId = options.getString('id') || '';
    const headers = { 'x-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' };
    try {
      if (accion === 'lista') {
        const r = await axios.get(`${FASTAPI_URL}/api/agents`, { headers, timeout: 10000 });
        const agents = r.data.agents || [];
        if (!agents.length) return interaction.editReply('No hay agentes creados. Usa `/crear-agente` para añadir uno.');
        const lines = agents.map(a =>
          `${a.active ? '🟢' : '🔴'} **${a.name}** \`${a.id}\` — cada ${a.schedule_minutes}min | ciclos: ${a.run_count}`
        ).join('\n');
        const embed = new EmbedBuilder()
          .setColor(0x818cf8)
          .setTitle(`🤖 Agentes Autónomos NEXO (${agents.length})`)
          .setDescription(lines)
          .setTimestamp();
        return interaction.editReply({ embeds: [embed] });
      }
      if (accion === 'plantillas') {
        const r = await axios.get(`${FASTAPI_URL}/api/agents/templates`, { headers, timeout: 8000 });
        const templates = r.data.templates || [];
        const lines = templates.map(t => `• \`${t}\``).join('\n');
        return interaction.editReply(`📋 **Plantillas disponibles:**\n${lines}\n\nUsa \`/crear-agente plantilla:[nombre]\``);
      }
      if (accion === 'ejecutar') {
        if (!agentId) return interaction.editReply('❌ Especifica el `id` del agente.');
        const r = await axios.post(`${FASTAPI_URL}/api/agents/${agentId}/run`, {}, { headers, timeout: 60000 });
        const res = r.data;
        return interaction.editReply(`✅ **${agentId}** ejecutado\n${res.synthesis || '_Sin resultado_'}\n\nHerramientas: ${res.tools_used?.join(', ')} | Tiempo: ${res.elapsed}s`);
      }
      if (accion === 'activar' || accion === 'desactivar') {
        if (!agentId) return interaction.editReply('❌ Especifica el `id` del agente.');
        const active = accion === 'activar';
        await axios.patch(`${FASTAPI_URL}/api/agents/${agentId}`, { active }, { headers, timeout: 8000 });
        return interaction.editReply(`${active ? '🟢' : '🔴'} Agente \`${agentId}\` ${active ? 'activado' : 'desactivado'}.`);
      }
    } catch(e) {
      return interaction.editReply(`Error: ${e.message}`);
    }
  }

  if (commandName === 'crear-agente') {
    const plantilla = options.getString('plantilla');
    const nombre = options.getString('nombre') || '';
    const headers = { 'x-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' };
    try {
      const r = await axios.post(`${FASTAPI_URL}/api/agents/template`, {
        template: plantilla,
        discord_channel_id: interaction.channelId,
      }, { headers, timeout: 10000 });
      const agent = r.data.agent;
      const embed = new EmbedBuilder()
        .setColor(0x22c55e)
        .setTitle('🤖 Agente Creado')
        .setDescription(`**${agent.name}**\n${agent.role}`)
        .addFields(
          { name: 'ID', value: agent.id, inline: true },
          { name: 'Herramientas', value: agent.tools.join(', '), inline: true },
          { name: 'Intervalo', value: `${agent.schedule_minutes} min`, inline: true },
          { name: 'Modelo IA', value: agent.model, inline: true },
        )
        .setFooter({ text: 'El agente empezará su primer ciclo en el próximo tick del factory (max 1 min)' })
        .setTimestamp();
      return interaction.editReply({ embeds: [embed] });
    } catch(e) {
      return interaction.editReply(`Error creando agente: ${e.response?.data?.detail || e.message}`);
    }
  }

  if (commandName === 'canva') {
    const tema = options.getString('tema');
    const tipo = options.getString('tipo') || 'infografia';
    const chanId = interaction.channelId;
    try {
      // Llamar al cognitive engine con intent CANVA
      const r = await axios.post(`${FASTAPI_URL}/api/cognitive/process`, {
        text: `Crea un diseño ${tipo} sobre: ${tema}`,
        channel_id: chanId,
        user_id: user.id,
      }, {
        headers: { 'x-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' },
        timeout: 20000,
      });
      const canva = r.data?.canva;
      if (canva?.design_id && canva?.edit_url) {
        const embed = new EmbedBuilder()
          .setColor(0x7c3aed)
          .setTitle('🎨 Diseño Canva Creado')
          .setDescription(`**${canva.title}**\n\nTipo: \`${canva.design_type}\``)
          .addFields({ name: 'Editar diseño', value: canva.edit_url })
          .setFooter({ text: `Respuesta: ${r.data?.response?.substring(0, 80) || ''}` })
          .setTimestamp();
        return interaction.editReply({ embeds: [embed] });
      } else if (canva?.available === false) {
        return interaction.editReply('⚠️ Canva no está configurado. Agrega `CANVA_ACCESS_TOKEN` al `.env`.');
      } else {
        // Sin token Canva — mostrar la respuesta cognitiva
        return interaction.editReply(`🎨 **Canva** | ${r.data?.response || 'Sin respuesta'}\n\n${canva?.error ? `_Error: ${canva.error}_` : ''}`);
      }
    } catch(e) {
      return interaction.editReply(`Error Canva: ${e.message}`);
    }
  }

  if (commandName === 'metacog') {
    try {
      const r = await axios.get(`${FASTAPI_URL}/api/cognitive/metacog`, {
        headers: { 'x-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' },
        timeout: 8000,
      });
      const snap = r.data?.snapshot || {};
      const lowScore = r.data?.intents_with_low_score || [];
      const lines = Object.entries(snap).map(([intent, v]) =>
        `**${intent}** — score: ${v.avg_score} | modelo: ${v.best_model || '?'} | hits: ${v.hits} | lento: ${v.slow_pct}%`
      ).join('\n') || '_Sin datos aún_';
      const embed = new EmbedBuilder()
        .setColor(0x0ea5e9)
        .setTitle('🧠 Metacognición NEXO')
        .setDescription(lines)
        .addFields({ name: 'Intents escalando a Claude', value: lowScore.length ? lowScore.join(', ') : 'Ninguno' })
        .setTimestamp();
      return interaction.editReply({ embeds: [embed] });
    } catch(e) {
      return interaction.editReply(`Error: ${e.message}`);
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

      // ── Motor Cognitivo Multi-Modelo ──────────────────────────────────────
      let iaText = 'Procesando...';
      let cogResult = null;
      try {
        const cogResp = await axios.post(`${FASTAPI_URL}/api/cognitive/process`, {
          text,
          channel_id: textChannel?.id || 'default',
          user_id: userId,
        }, {
          headers: { 'x-api-key': process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK' },
          timeout: 35000,
        });
        cogResult = cogResp.data;
        iaText = cogResult.response || 'Sin respuesta.';
        console.log(`[NEXO VOICE] Cognitivo [${cogResult.intent}] tools:${(cogResult.tools_used||[]).join(',')} → "${iaText.substring(0, 80)}"`);

        // Mostrar streams recomendados si los hay
        if (cogResult.streams?.recommended_streams?.length && textChannel) {
          const streams = cogResult.streams.recommended_streams.slice(0, 2);
          const streamMsg = '📺 ' + streams.map(s => `[${s.label}](${s.url})`).join(' · ');
          textChannel.send(streamMsg).catch(() => {});
        }

        // Si es urgente → destacar en el canal
        if (cogResult.urgent && textChannel) {
          textChannel.send(`🔴 **ALERTA:** ${iaText}`).catch(() => {});
        } else if (textChannel) {
          textChannel.send(`🤖 **NEXO [${cogResult.intent || '?'}]:** ${iaText}`).catch(() => {});
        }

        // Si ejecutó comando de dispositivo → notificar
        if (cogResult.device_result && textChannel) {
          const dr = cogResult.device_result;
          if (dr.action) textChannel.send(`📱 Dispositivo: \`${dr.action}\` → ${dr.result?.ok ? '✅' : '⚠️'}`).catch(() => {});
        }

      } catch(cogErr) {
        console.warn('[NEXO VOICE] Motor cognitivo falló, usando agente simple:', cogErr.message);
        // Fallback al agente simple
        try {
          const fallback = await axios.post(`${FASTAPI_URL}/api/agente/`, {
            query: text, user_id: userId,
          }, { timeout: 15000 });
          iaText = fallback.data?.respuesta || 'No pude procesar.';
        } catch(e2) { iaText = 'Error en el sistema.'; }
        if (textChannel) textChannel.send(`🤖 **NEXO:** ${iaText}`).catch(() => {});
      }

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
