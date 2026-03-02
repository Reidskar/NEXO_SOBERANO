require('dotenv').config();
const { Client, GatewayIntentBits, EmbedBuilder, SlashCommandBuilder } = require('discord.js');
const axios = require('axios');

const FASTAPI_URL = (process.env.FASTAPI_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

if (!process.env.DISCORD_TOKEN) {
  throw new Error('Falta DISCORD_TOKEN en .env');
}

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
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
    )
];

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
  if (process.env.DISCORD_GUILD_ID) {
    const guild = await client.guilds.fetch(process.env.DISCORD_GUILD_ID);
    await guild.commands.set(commands);
    console.log(`Comandos registrados en guild ${guild.id}`);
    return;
  }

  await client.application.commands.set(commands);
  console.log('Comandos globales registrados');
}

client.once('ready', async () => {
  console.log(`Bot conectado como ${client.user.tag}`);
  await registerCommands();
});

client.on('interactionCreate', async interaction => {
  if (!interaction.isChatInputCommand()) return;

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
          headers: { 'Content-Type': 'application/json' }
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
          headers: { 'Content-Type': 'application/json' }
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
  }
});

client.login(process.env.DISCORD_TOKEN);
