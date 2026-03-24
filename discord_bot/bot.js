#!/usr/bin/env node

/**
 * NEXO Discord Bot - Bot de Discord con soporte de voz y comandos IA
 * Conecta a canales de voz, responde preguntas y ejecuta comandos
 */

require('dotenv').config({ path: '../.env' });

const {
  Client,
  GatewayIntentBits,
  REST,
  Routes,
  SlashCommandBuilder,
  ChannelType,
  PermissionFlagsBits
} = require('discord.js');

const {
  joinVoiceChannel,
  getVoiceConnection,
  createAudioPlayer,
  createAudioResource,
  AudioPlayerStatus,
  VoiceConnectionStatus,
  entersState
} = require('@discordjs/voice');

const fs = require('fs');
const path = require('path');

// ==================== CONFIGURACIÓN ====================

const DISCORD_TOKEN = process.env.DISCORD_TOKEN;
const DISCORD_CLIENT_ID = process.env.DISCORD_CLIENT_ID;
const NEXO_BACKEND = process.env.NEXO_BACKEND || 'http://127.0.0.1:8000';
const NEXO_API_KEY = process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK';

// Validar variables de entorno
if (!DISCORD_TOKEN) {
  console.error('❌ ERROR: DISCORD_TOKEN no está configurado en .env');
  process.exit(1);
}

if (!DISCORD_CLIENT_ID) {
  console.error('❌ ERROR: DISCORD_CLIENT_ID no está configurado en .env');
  process.exit(1);
}

console.log('✅ Configuración cargada:');
console.log(`   - Backend: ${NEXO_BACKEND}`);
console.log(`   - Client ID: ${DISCORD_CLIENT_ID}`);

// ==================== CLIENTE DISCORD ====================

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildVoiceStates,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.DirectMessages,
    GatewayIntentBits.MessageContent
  ]
});

// ==================== COMANDOS SLASH ====================

const commands = [
  new SlashCommandBuilder()
    .setName('unirse')
    .setDescription('Conecta NEXO a tu canal de voz')
    .setDefaultMemberPermissions(PermissionFlagsBits.Connect),

  new SlashCommandBuilder()
    .setName('salir')
    .setDescription('Desconecta NEXO del canal de voz'),

  new SlashCommandBuilder()
    .setName('nexo')
    .setDescription('Consulta a NEXO una pregunta')
    .addStringOption(option =>
      option
        .setName('pregunta')
        .setDescription('Tu pregunta para NEXO')
        .setRequired(true)
    ),

  new SlashCommandBuilder()
    .setName('estado')
    .setDescription('Muestra el estado actual de NEXO'),

  new SlashCommandBuilder()
    .setName('ayuda')
    .setDescription('Muestra la ayuda de comandos disponibles')
];

// ==================== REGISTRAR COMANDOS ====================

async function registerCommands() {
  try {
    console.log('🔄 Registrando comandos slash...');
    const rest = new REST({ version: '10' }).setToken(DISCORD_TOKEN);

    const commandsData = commands.map(cmd => cmd.toJSON());

    const data = await rest.put(
      Routes.applicationCommands(DISCORD_CLIENT_ID),
      { body: commandsData }
    );

    console.log(`✅ ${data.length} comandos registrados exitosamente`);
  } catch (error) {
    console.error('❌ Error registrando comandos:', error);
  }
}

// ==================== EVENT HANDLERS ====================

client.once('ready', () => {
  console.log(`\n✅ Bot conectado como: ${client.user.tag}`);
  console.log(`📊 Servidores: ${client.guilds.cache.size}`);
  client.user.setActivity('🎙️ NEXO Control Hub', { type: 'LISTENING' });
});

client.on('error', error => {
  console.error('❌ Error del cliente Discord:', error);
});

process.on('unhandledRejection', error => {
  console.error('❌ Promise rejection no manejada:', error);
});

// ==================== INTERACCIONES ====================

client.on('interactionCreate', async interaction => {
  if (!interaction.isChatInputCommand()) return;

  const { commandName, user, member, guild } = interaction;
  console.log(`\n📨 Comando: /${commandName} | Usuario: ${user.tag}`);

  try {
    // -------- COMANDO: unirse --------
    if (commandName === 'unirse') {
      await interaction.deferReply();

      if (!member?.voice?.channel) {
        return interaction.editReply({
          content: '❌ Debes estar en un canal de voz primero',
          ephemeral: true
        });
      }

      const voiceChannel = member.voice.channel;

      // Verificar permisos
      if (!voiceChannel.permissionsFor(guild.members.me).has('Connect')) {
        return interaction.editReply({
          content: '❌ No tengo permiso para conectarme a este canal',
          ephemeral: true
        });
      }

      try {
        const connection = joinVoiceChannel({
          channelId: voiceChannel.id,
          guildId: guild.id,
          adapterCreator: guild.voiceAdapterCreator,
          selfDeaf: false,
          selfMute: false
        });

        // Esperar a que se conecte
        await entersState(connection, VoiceConnectionStatus.Ready, 30_000);

        console.log(`🎙️ Conectado a: ${voiceChannel.name}`);

        return interaction.editReply({
          content: `🎙️ **NEXO conectado a ${voiceChannel.name}**\n\nUsa \`/nexo pregunta\` para consultarme`,
          ephemeral: false
        });
      } catch (error) {
        console.error('❌ Error conectando a voz:', error.message);
        return interaction.editReply({
          content: `❌ Error al conectar: ${error.message}`,
          ephemeral: true
        });
      }
    }

    // -------- COMANDO: salir --------
    else if (commandName === 'salir') {
      await interaction.deferReply();

      const connection = getVoiceConnection(guild.id);

      if (!connection) {
        return interaction.editReply({
          content: '❌ No estoy en ningún canal de voz',
          ephemeral: true
        });
      }

      connection.destroy();
      console.log('👋 Desconectado del canal de voz');

      return interaction.editReply({
        content: '👋 **NEXO desconectado**',
        ephemeral: false
      });
    }

    // -------- COMANDO: nexo --------
    else if (commandName === 'nexo') {
      await interaction.deferReply();

      const query = interaction.options.getString('pregunta');
      console.log(`🤖 Consultando backend: "${query}"`);

      try {
        const response = await fetch(`${NEXO_BACKEND}/api/ai/ask`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-NEXO-API-KEY': NEXO_API_KEY,
            'User-Agent': 'NEXO-Discord-Bot/1.0'
          },
          body: JSON.stringify({ question: query }),
          timeout: 10000
        });

        if (!response.ok) {
          throw new Error(`Backend error: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        const answer = data.answer || data.respuesta || data.response || 'Sin respuesta disponible';

        console.log('✅ Respuesta recibida del backend');

        return interaction.editReply({
          content: `🤖 **NEXO:** ${answer.substring(0, 2000)}`,
          ephemeral: false
        });
      } catch (error) {
        console.error('❌ Error consultando backend:', error.message);
        return interaction.editReply({
          content: `❌ Error de conexión: ${error.message}`,
          ephemeral: true
        });
      }
    }

    // -------- COMANDO: estado --------
    else if (commandName === 'estado') {
      await interaction.deferReply();

      const connection = getVoiceConnection(guild.id);
      const voiceState = connection ? '🟢 Conectado' : '🔴 Desconectado';

      // Verificar backend
      let backendStatus = '⚠️ Desconocido';
      try {
        const response = await fetch(`${NEXO_BACKEND}/health`, {
          timeout: 5000
        });
        backendStatus = response.ok ? '🟢 Online' : '🔴 Offline';
      } catch {
        backendStatus = '🔴 Offline';
      }

      const embed = {
        color: 0x00D9FF,
        title: '🤖 Estado de NEXO',
        fields: [
          {
            name: '🎙️ Voz',
            value: voiceState,
            inline: true
          },
          {
            name: '🧠 Backend',
            value: backendStatus,
            inline: true
          },
          {
            name: '📊 Servidores',
            value: `${client.guilds.cache.size}`,
            inline: true
          },
          {
            name: '👥 Usuarios',
            value: `${client.users.cache.size}`,
            inline: true
          }
        ],
        timestamp: new Date()
      };

      return interaction.editReply({ embeds: [embed] });
    }

    // -------- COMANDO: ayuda --------
    else if (commandName === 'ayuda') {
      await interaction.deferReply();

      const embed = {
        color: 0xFF006E,
        title: '📚 Ayuda de NEXO',
        description: 'Comandos disponibles:',
        fields: [
          {
            name: '/unirse',
            value: 'Conecta NEXO a tu canal de voz',
            inline: false
          },
          {
            name: '/salir',
            value: 'Desconecta NEXO del canal de voz',
            inline: false
          },
          {
            name: '/nexo <pregunta>',
            value: 'Consulta una pregunta a NEXO',
            inline: false
          },
          {
            name: '/estado',
            value: 'Muestra el estado actual de NEXO',
            inline: false
          },
          {
            name: '/ayuda',
            value: 'Muestra este mensaje',
            inline: false
          }
        ],
        footer: {
          text: 'El Anarcocapital - NEXO Control Hub'
        }
      };

      return interaction.editReply({ embeds: [embed] });
    }
  } catch (error) {
    console.error('❌ Error procesando comando:', error);
    return interaction.editReply({
      content: `❌ Error: ${error.message}`,
      ephemeral: true
    }).catch(() => {});
  }
});

// ==================== INICIAR BOT ====================

async function start() {
  try {
    console.log('🚀 Iniciando NEXO Discord Bot...\n');

    // Registrar comandos
    await registerCommands();

    // Conectar a Discord
    await client.login(DISCORD_TOKEN);
    console.log('✅ Bot iniciado correctamente\n');
  } catch (error) {
    console.error('❌ Error iniciando bot:', error);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n👋 Apagando bot...');
  await client.destroy();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\n👋 Apagando bot...');
  await client.destroy();
  process.exit(0);
});

start();
