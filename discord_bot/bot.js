#!/usr/bin/env node

/**
 * NEXO Discord Bot - Bot de Discord con soporte de voz, soundboard y webhooks
 * Conecta a canales de voz, reproduce sonidos y responde preguntas
 */

require('dotenv').config({ path: './.env' });

const {
  Client,
  GatewayIntentBits,
  REST,
  Routes,
  SlashCommandBuilder,
  ChannelType,
  PermissionFlagsBits,
  ButtonBuilder,
  ButtonStyle,
  ActionRowBuilder,
  EmbedBuilder
} = require('discord.js');

const {
  joinVoiceChannel,
  getVoiceConnection,
  createAudioPlayer,
  createAudioResource,
  AudioPlayerStatus,
  VoiceConnectionStatus,
  entersState,
  NoSubscriberError
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

// ==================== SONIDOS DISPONIBLES ====================

const SOUNDS = {
  'nexo': { name: '🤖 NEXO', file: 'sounds/nexo.mp3', emoji: '🤖' },
  'alerta': { name: '🚨 Alerta', file: 'sounds/alert.mp3', emoji: '🚨' },
  'exito': { name: '✅ Éxito', file: 'sounds/success.mp3', emoji: '✅' },
  'error': { name: '❌ Error', file: 'sounds/error.mp3', emoji: '❌' },
  'risa': { name: '😂 Risa', file: 'sounds/laugh.mp3', emoji: '😂' },
  'aplausos': { name: '👏 Aplausos', file: 'sounds/applause.mp3', emoji: '👏' },
  'campana': { name: '🔔 Campana', file: 'sounds/bell.mp3', emoji: '🔔' },
  'silbido': { name: '🎵 Silbido', file: 'sounds/whistle.mp3', emoji: '🎵' }
};

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

// Almacenar conexiones de voz
const voiceConnections = new Map();
const audioPlayers = new Map();

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
    .setName('soundboard')
    .setDescription('Abre la botonera de sonidos'),

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
    console.error('❌ Error registrando comandos:', error.message);
  }
}

// ==================== FUNCIONES DE VOZ ====================

async function connectToVoiceChannel(member, guild) {
  try {
    const voiceChannel = member.voice.channel;

    if (!voiceChannel) {
      throw new Error('No estás en un canal de voz');
    }

    // Verificar permisos
    const botMember = guild.members.me;
    if (!botMember.permissionsIn(voiceChannel).has('Connect')) {
      throw new Error('No tengo permiso para conectarme a este canal');
    }

    if (!botMember.permissionsIn(voiceChannel).has('Speak')) {
      throw new Error('No tengo permiso para hablar en este canal');
    }

    // Desconectar si ya estaba conectado
    const existingConnection = getVoiceConnection(guild.id);
    if (existingConnection) {
      existingConnection.destroy();
    }

    // Crear nueva conexión
    const connection = joinVoiceChannel({
      channelId: voiceChannel.id,
      guildId: guild.id,
      adapterCreator: guild.voiceAdapterCreator,
      selfDeaf: false,
      selfMute: false
    });

    // Crear reproductor de audio
    const player = createAudioPlayer({
      behaviors: {
        noSubscriber: NoSubscriberError.Ignore
      }
    });

    // Suscribir el reproductor a la conexión
    connection.subscribe(player);

    // Esperar a que esté listo
    await entersState(connection, VoiceConnectionStatus.Ready, 30_000);

    // Guardar referencias
    voiceConnections.set(guild.id, connection);
    audioPlayers.set(guild.id, player);

    // Manejo de desconexión
    connection.on(VoiceConnectionStatus.Disconnected, async () => {
      try {
        await entersState(connection, VoiceConnectionStatus.Connecting, 5_000);
      } catch (error) {
        connection.destroy();
        voiceConnections.delete(guild.id);
        audioPlayers.delete(guild.id);
        console.log(`🔌 Desconectado de ${voiceChannel.name}`);
      }
    });

    connection.on('error', error => {
      console.error(`❌ Error de conexión de voz:`, error.message);
    });

    console.log(`🎙️ Conectado a: ${voiceChannel.name}`);
    return connection;
  } catch (error) {
    console.error('❌ Error conectando a voz:', error.message);
    throw error;
  }
}

function disconnectFromVoiceChannel(guildId) {
  try {
    const connection = voiceConnections.get(guildId);
    if (connection) {
      connection.destroy();
      voiceConnections.delete(guildId);
      audioPlayers.delete(guildId);
      return true;
    }
    return false;
  } catch (error) {
    console.error('❌ Error desconectando:', error.message);
    return false;
  }
}

async function playSound(guildId, soundKey) {
  try {
    const player = audioPlayers.get(guildId);
    if (!player) {
      throw new Error('No hay reproductor de audio disponible');
    }

    const sound = SOUNDS[soundKey];
    if (!sound) {
      throw new Error(`Sonido no encontrado: ${soundKey}`);
    }

    const soundPath = path.join(__dirname, sound.file);

    // Si el archivo no existe, crear un sonido de prueba
    if (!fs.existsSync(soundPath)) {
      console.warn(`⚠️ Archivo de sonido no encontrado: ${soundPath}`);
      // Continuar sin error - el bot no se caerá
      return;
    }

    const resource = createAudioResource(soundPath);
    player.play(resource);

    console.log(`🔊 Reproduciendo: ${sound.name}`);

    return new Promise((resolve) => {
      player.once(AudioPlayerStatus.Idle, () => {
        resolve();
      });

      player.once('error', (error) => {
        console.error(`❌ Error reproduciendo sonido:`, error.message);
        resolve();
      });

      // Timeout de 30 segundos
      setTimeout(resolve, 30000);
    });
  } catch (error) {
    console.error('❌ Error reproduciendo sonido:', error.message);
    throw error;
  }
}

// ==================== BOTONERA DE SONIDOS ====================

function createSoundboardButtons() {
  const rows = [];
  const soundKeys = Object.keys(SOUNDS);

  // Crear filas de botones (máximo 5 botones por fila)
  for (let i = 0; i < soundKeys.length; i += 5) {
    const row = new ActionRowBuilder();
    const soundsInRow = soundKeys.slice(i, i + 5);

    for (const soundKey of soundsInRow) {
      const sound = SOUNDS[soundKey];
      row.addComponents(
        new ButtonBuilder()
          .setCustomId(`sound_${soundKey}`)
          .setLabel(sound.name)
          .setStyle(ButtonStyle.Primary)
          .setEmoji(sound.emoji)
      );
    }

    rows.push(row);
  }

  return rows;
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
  try {
    // Manejo de comandos slash
    if (interaction.isChatInputCommand()) {
      const { commandName, user, member, guild } = interaction;
      console.log(`\n📨 Comando: /${commandName} | Usuario: ${user.tag}`);

      // -------- COMANDO: unirse --------
      if (commandName === 'unirse') {
        await interaction.deferReply();

        if (!member?.voice?.channel) {
          return interaction.editReply({
            content: '❌ Debes estar en un canal de voz primero',
            ephemeral: true
          });
        }

        try {
          await connectToVoiceChannel(member, guild);
          const voiceChannel = member.voice.channel;

          return interaction.editReply({
            content: `🎙️ **NEXO conectado a ${voiceChannel.name}**\n\nUsa \`/soundboard\` para reproducir sonidos`,
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

        const disconnected = disconnectFromVoiceChannel(guild.id);

        if (!disconnected) {
          return interaction.editReply({
            content: '❌ No estoy en ningún canal de voz',
            ephemeral: true
          });
        }

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

        const connection = voiceConnections.get(guild.id);
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

        const embed = new EmbedBuilder()
          .setColor(0x00D9FF)
          .setTitle('🤖 Estado de NEXO')
          .addFields(
            { name: '🎙️ Voz', value: voiceState, inline: true },
            { name: '🧠 Backend', value: backendStatus, inline: true },
            { name: '📊 Servidores', value: `${client.guilds.cache.size}`, inline: true },
            { name: '👥 Usuarios', value: `${client.users.cache.size}`, inline: true }
          )
          .setTimestamp();

        return interaction.editReply({ embeds: [embed] });
      }

      // -------- COMANDO: soundboard --------
      else if (commandName === 'soundboard') {
        await interaction.deferReply();

        const connection = voiceConnections.get(guild.id);
        if (!connection) {
          return interaction.editReply({
            content: '❌ Primero debes conectarme a un canal de voz con `/unirse`',
            ephemeral: true
          });
        }

        const buttons = createSoundboardButtons();

        return interaction.editReply({
          content: '🎵 **Botonera de Sonidos**\n\nHaz clic en un botón para reproducir un sonido:',
          components: buttons,
          ephemeral: false
        });
      }

      // -------- COMANDO: ayuda --------
      else if (commandName === 'ayuda') {
        await interaction.deferReply();

        const embed = new EmbedBuilder()
          .setColor(0xFF006E)
          .setTitle('📚 Ayuda de NEXO')
          .setDescription('Comandos disponibles:')
          .addFields(
            { name: '/unirse', value: 'Conecta NEXO a tu canal de voz', inline: false },
            { name: '/salir', value: 'Desconecta NEXO del canal de voz', inline: false },
            { name: '/nexo <pregunta>', value: 'Consulta una pregunta a NEXO', inline: false },
            { name: '/soundboard', value: 'Abre la botonera de sonidos', inline: false },
            { name: '/estado', value: 'Muestra el estado actual de NEXO', inline: false },
            { name: '/ayuda', value: 'Muestra este mensaje', inline: false }
          )
          .setFooter({ text: 'El Anarcocapital - NEXO Control Hub' });

        return interaction.editReply({ embeds: [embed] });
      }
    }

    // Manejo de botones
    else if (interaction.isButton()) {
      const customId = interaction.customId;

      if (customId.startsWith('sound_')) {
        await interaction.deferReply({ ephemeral: true });

        const soundKey = customId.replace('sound_', '');
        const sound = SOUNDS[soundKey];

        if (!sound) {
          return interaction.editReply({
            content: '❌ Sonido no encontrado',
            ephemeral: true
          });
        }

        try {
          await playSound(interaction.guildId, soundKey);
          return interaction.editReply({
            content: `✅ Reproduciendo: ${sound.name}`,
            ephemeral: true
          });
        } catch (error) {
          return interaction.editReply({
            content: `❌ Error reproduciendo sonido: ${error.message}`,
            ephemeral: true
          });
        }
      }
    }
  } catch (error) {
    console.error('❌ Error procesando interacción:', error);
    if (interaction.replied || interaction.deferred) {
      return interaction.editReply({
        content: `❌ Error: ${error.message}`,
        ephemeral: true
      }).catch(() => {});
    }
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
  
  // Desconectar de todos los canales de voz
  for (const [guildId] of voiceConnections) {
    disconnectFromVoiceChannel(guildId);
  }
  
  await client.destroy();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\n👋 Apagando bot...');
  
  // Desconectar de todos los canales de voz
  for (const [guildId] of voiceConnections) {
    disconnectFromVoiceChannel(guildId);
  }
  
  await client.destroy();
  process.exit(0);
});

start();
