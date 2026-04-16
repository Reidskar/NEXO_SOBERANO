/**
 * discord_bot/proactive_intel.js
 * Sistema de alertas proactivas NEXO — monitorea OSINT Engine y notifica Discord
 *
 * Comportamientos:
 * - Cada 60 min: sweep OSINT, si hay delta significativo → alerta en canal
 * - Cada día a las 08:00: resumen de inteligencia diario (usa Ollama local)
 * - Alertas inmediatas: CISA KEV nuevas críticas, vuelos anómalos
 */

const axios = require('axios');

const NEXO_URL = process.env.FASTAPI_URL || 'http://127.0.0.1:8080';
const NEXO_KEY = process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK';
const ALERT_CHANNEL_ID = process.env.DISCORD_ALERT_CHANNEL_ID || process.env.DISCORD_GUILD_ID;

const HEADERS = { 'x-api-key': NEXO_KEY };

let lastDeltaHash = null;
let lastDailySummaryDate = null;

// ── Fetch OSINT con timeout ────────────────────────────────────────────────────
async function fetchOsint(endpoint, timeout = 30000) {
  try {
    const r = await axios.get(`${NEXO_URL}${endpoint}`, {
      headers: HEADERS, timeout
    });
    return r.data;
  } catch(e) {
    return null;
  }
}

// ── Hash simple para detectar cambios ─────────────────────────────────────────
function hashDelta(delta) {
  return JSON.stringify(Object.keys(delta || {}).sort());
}

// ── Embed: Alerta Delta ────────────────────────────────────────────────────────
function buildDeltaEmbed(delta, significant, client) {
  const { EmbedBuilder } = require('discord.js');
  const embed = new EmbedBuilder()
    .setColor(0xef4444)
    .setTitle('⚡ NEXO OSINT — CAMBIO DETECTADO')
    .setTimestamp()
    .setFooter({ text: 'NEXO SOBERANO · OSINT Engine' });

  const lines = [];
  for (const [source, data] of Object.entries(significant).slice(0, 8)) {
    const changes = Object.entries(data.changes || {}).slice(0, 2).map(([k, v]) => {
      const pct = v.pct_change != null ? ` (${v.pct_change > 0 ? '+' : ''}${v.pct_change.toFixed(1)}%)` : '';
      return `\`${k}\`: ${v.prev} → **${v.curr}**${pct}`;
    }).join('\n');
    lines.push(`**${source.toUpperCase()}**\n${changes || 'cambio detectado'}`);
  }

  embed.setDescription(lines.join('\n\n') || 'Cambios en múltiples fuentes OSINT.');
  embed.addFields({ name: 'Fuentes con cambios significativos', value: `${significant_count(significant)}/${Object.keys(delta).length}`, inline: true });
  return embed;
}

function significant_count(obj) {
  return Object.values(obj).filter(v => v.significant).length;
}

// ── Embed: Resumen Diario ──────────────────────────────────────────────────────
function buildDailySummaryEmbed(status, markets, satData) {
  const { EmbedBuilder } = require('discord.js');
  const embed = new EmbedBuilder()
    .setColor(0x4ade80)
    .setTitle('🌐 NEXO SOBERANO — BRIEFING DIARIO')
    .setTimestamp()
    .setFooter({ text: 'NEXO SOBERANO · Resumen Automático 08:00' });

  // OSINT Status
  if (status) {
    embed.addFields({
      name: '📡 OSINT Engine',
      value: `Fuentes OK: **${status.sources_ok}/${status.sources}**\nÚltimo sweep: ${status.last_sweep ? new Date(status.last_sweep).toLocaleString('es-CL') : '—'}`,
      inline: true
    });
  }

  // Mercados
  if (markets?.data) {
    const mkt = markets.data;
    const lines = [];
    if (mkt.VIX?.price) lines.push(`VIX: **${mkt.VIX.price.toFixed(2)}** ${mkt.VIX.change_pct > 0 ? '🔴' : '🟢'}`);
    if (mkt['BTC-USD']?.price) lines.push(`BTC: **$${mkt['BTC-USD'].price.toLocaleString('en-US', {maximumFractionDigits:0})}**`);
    if (mkt.GC=F?.price || mkt['GC=F']?.price) {
      const gold = mkt['GC=F'] || mkt.GC;
      if (gold?.price) lines.push(`ORO: **$${gold.price.toFixed(0)}**`);
    }
    if (mkt['CL=F']?.price) lines.push(`WTI: **$${mkt['CL=F'].price.toFixed(2)}**`);
    if (lines.length) embed.addFields({ name: '📈 Mercados', value: lines.join('\n'), inline: true });
  }

  // Satélites
  if (satData?.data) {
    const maneuvers = satData.data.maneuvers?.length || 0;
    const iss = satData.data.iss;
    let satText = `Satélites tracked: **${(satData.data.total_tracked || 0).toLocaleString()}**\nManiobras (48h): **${maneuvers}**`;
    if (iss) satText += `\nISS: ${iss.latitude?.toFixed(1)}° lat · ${Math.round(iss.altitude || 0)} km`;
    embed.addFields({ name: '🛰 Satélites', value: satText, inline: true });
  }

  embed.setDescription('Sistema operativo. Todos los feeds monitoreados. Use `/nexo` para consultas.');
  return embed;
}

// ── Embed: CISA KEV Crítica ────────────────────────────────────────────────────
function buildCisaEmbed(vuln) {
  const { EmbedBuilder } = require('discord.js');
  return new EmbedBuilder()
    .setColor(0xf59e0b)
    .setTitle(`⚠ CISA KEV — Nueva Vulnerabilidad Crítica`)
    .setDescription(`**${vuln.cve_id || vuln.id}** — ${vuln.vulnerability_name || vuln.product || 'Desconocido'}`)
    .addFields(
      { name: 'Vendor', value: vuln.vendor_project || '—', inline: true },
      { name: 'Fecha agregada', value: vuln.date_added || '—', inline: true },
      { name: 'Acción requerida', value: (vuln.required_action || 'Aplicar parche').slice(0, 200), inline: false }
    )
    .setTimestamp()
    .setFooter({ text: 'NEXO SOBERANO · CISA Known Exploited Vulnerabilities' });
}

// ── Encontrar canal de alertas ─────────────────────────────────────────────────
async function getAlertChannel(client) {
  try {
    const channelId = process.env.DISCORD_ALERT_CHANNEL_ID;
    if (channelId) {
      const ch = await client.channels.fetch(channelId);
      if (ch?.isTextBased()) return ch;
    }
    // Fallback: primer canal de texto del primer guild
    const guild = client.guilds.cache.first();
    if (!guild) return null;
    const channels = await guild.channels.fetch();
    return channels.find(ch => ch?.isTextBased() && ch.name.includes('general')) ||
           channels.find(ch => ch?.isTextBased());
  } catch(e) {
    return null;
  }
}

// ── Loop principal ─────────────────────────────────────────────────────────────
async function runProactiveLoop(client) {
  console.log('[NEXO Proactive] Loop de inteligencia iniciado');

  // Esperar 2 min antes del primer ciclo (dar tiempo al backend)
  await new Promise(r => setTimeout(r, 120_000));

  while (true) {
    try {
      await runCycle(client);
    } catch(e) {
      console.error('[NEXO Proactive] Error en ciclo:', e.message);
    }
    // Cada 60 minutos
    await new Promise(r => setTimeout(r, 60 * 60 * 1000));
  }
}

async function runCycle(client) {
  const channel = await getAlertChannel(client);
  if (!channel) {
    console.warn('[NEXO Proactive] No se encontró canal de alertas');
    return;
  }

  // 0. Forzar sweep y procesar contra temas activos
  const sweepData = await fetchOsint('/api/osint/sweep');
  if (sweepData && sweepData.sources) {
    try {
      const alertsResp = await axios.post(`${NEXO_URL}/api/topics/osint-sweep`,
        { sweep: sweepData },
        { headers: { 'x-api-key': NEXO_KEY, 'Content-Type': 'application/json' }, timeout: 15000 }
      );
      const topicAlerts = alertsResp.data?.alerts || [];
      for (const alert of topicAlerts.slice(0, 3)) {
        try {
          const { EmbedBuilder } = require('discord.js');
          const embed = new EmbedBuilder()
            .setColor(alert.priority === 'alta' ? 0xef4444 : 0xf59e0b)
            .setTitle(`${alert.priority === 'alta' ? '🔴' : '⚡'} NEXO — Actividad en: ${alert.topic_name}`)
            .setDescription(alert.hits.slice(0,3).map(h => `• [${h.source}] ${h.text}`).join('\n') || 'Nueva actividad detectada')
            .setTimestamp();

          if (alert.live_streams?.length) {
            embed.addFields({
              name: '📺 Ver en vivo',
              value: alert.live_streams.map(s => `[${s.label}](${s.url})`).join(' · '),
            });
          }
          await channel.send({ embeds: [embed] });
        } catch(e) { console.warn('[NEXO Proactive] Error enviando topic alert:', e.message); }
        await new Promise(r => setTimeout(r, 1500));
      }
    } catch(e) { console.warn('[NEXO Proactive] Error procesando topics:', e.message); }
  }

  // 1. Verificar delta OSINT
  const deltaResp = await fetchOsint('/api/osint/delta');
  if (deltaResp?.delta && deltaResp.significant_changes > 0) {
    const hash = hashDelta(deltaResp.delta);
    if (hash !== lastDeltaHash) {
      lastDeltaHash = hash;
      const significant = Object.fromEntries(
        Object.entries(deltaResp.delta).filter(([, v]) => v?.significant)
      );
      if (Object.keys(significant).length > 0) {
        try {
          const embed = buildDeltaEmbed(deltaResp.delta, significant);
          await channel.send({ embeds: [embed] });
          console.log(`[NEXO Proactive] Alerta delta enviada — ${Object.keys(significant).length} cambios`);
        } catch(e) {
          console.warn('[NEXO Proactive] Error enviando delta:', e.message);
        }
      }
    }
  }

  // 2. Resumen diario a las 08:00
  const now = new Date();
  const todayStr = now.toDateString();
  const hour = now.getHours();
  if (hour === 8 && lastDailySummaryDate !== todayStr) {
    lastDailySummaryDate = todayStr;
    await sendDailySummary(client, channel);
  }

  // 3. Nuevas vulns CISA KEV críticas
  const threats = await fetchOsint('/api/osint/threats');
  if (threats?.cyber?.vulnerabilities) {
    const recent = threats.cyber.vulnerabilities.filter(v => {
      if (!v.date_added) return false;
      const added = new Date(v.date_added);
      const ageHours = (Date.now() - added.getTime()) / 3600000;
      return ageHours < 72; // últimas 72h
    }).slice(0, 2);

    for (const vuln of recent) {
      try {
        const embed = buildCisaEmbed(vuln);
        await channel.send({ embeds: [embed] });
        console.log(`[NEXO Proactive] CISA KEV enviado: ${vuln.cve_id}`);
      } catch(e) {
        console.warn('[NEXO Proactive] Error enviando CISA:', e.message);
      }
      await new Promise(r => setTimeout(r, 2000));
    }
  }
}

async function sendDailySummary(client, channel) {
  const [status, markets, satData] = await Promise.all([
    fetchOsint('/api/osint/status'),
    fetchOsint('/api/osint/markets'),
    fetchOsint('/api/osint/satellites'),
  ]);

  try {
    const embed = buildDailySummaryEmbed(status, markets, satData);
    await channel.send({ content: '🌅 **Briefing de inteligencia NEXO — ' + new Date().toLocaleDateString('es-CL', {weekday:'long', year:'numeric', month:'long', day:'numeric'}) + '**', embeds: [embed] });
    console.log('[NEXO Proactive] Briefing diario enviado');
  } catch(e) {
    console.warn('[NEXO Proactive] Error enviando briefing diario:', e.message);
  }

  // También pedir sweep forzado para empezar el día con datos frescos
  try {
    await axios.post(`${NEXO_URL}/api/osint/sweep/force`, {}, { headers: HEADERS, timeout: 10000 });
  } catch(e) { /* silencioso */ }
}

// ── Comando /osint para el bot ─────────────────────────────────────────────────
async function handleOsintCommand(interaction) {
  await interaction.deferReply();
  try {
    const [status, markets, delta] = await Promise.all([
      fetchOsint('/api/osint/status'),
      fetchOsint('/api/osint/markets'),
      fetchOsint('/api/osint/delta'),
    ]);

    const { EmbedBuilder } = require('discord.js');
    const embed = new EmbedBuilder()
      .setColor(0x4ade80)
      .setTitle('📡 NEXO OSINT — Estado Actual')
      .setTimestamp();

    if (status) {
      embed.addFields({
        name: 'Engine',
        value: `OK: ${status.sources_ok}/${status.sources} fuentes\nÚltimo: ${status.last_sweep ? new Date(status.last_sweep).toLocaleTimeString('es-CL') : '—'}\nDuración: ${status.last_duration_seconds?.toFixed(1) || '—'}s`,
        inline: true
      });
    }
    if (markets?.data) {
      const m = markets.data;
      const lines = Object.entries(m).slice(0, 6).map(([k, v]) => {
        const chg = v.change_pct;
        const arrow = chg > 0 ? '▲' : chg < 0 ? '▼' : '—';
        return `**${k}**: ${v.price?.toLocaleString('en-US', {maximumFractionDigits:2}) || '—'} ${arrow}${Math.abs(chg || 0).toFixed(2)}%`;
      });
      embed.addFields({ name: '📈 Mercados', value: lines.join('\n'), inline: true });
    }
    if (delta) {
      embed.addFields({
        name: '⚡ Delta',
        value: delta.significant_changes > 0
          ? `${delta.significant_changes} cambios significativos detectados`
          : delta.message || 'Sin cambios significativos',
        inline: false
      });
    }

    await interaction.editReply({ embeds: [embed] });
  } catch(e) {
    await interaction.editReply(`Error consultando OSINT Engine: ${e.message}`);
  }
}

module.exports = { runProactiveLoop, handleOsintCommand };
