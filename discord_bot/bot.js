require('dotenv').config();
const { 
  const dotenv = require('dotenv');
  dotenv.config({ path: '../.env' });
  const { Client, GatewayIntentBits } = require('discord.js');
  const { joinVoiceChannel, getVoiceConnection } = require('@discordjs/voice');

  const client = new Client({
    intents: [
      GatewayIntentBits.Guilds,
      GatewayIntentBits.GuildVoiceStates,
      GatewayIntentBits.GuildMessages,

      GatewayIntentBits.MessageContent
    ]
});

const NEXO_BACKEND = process.env.FASTAPI_URL || 'http://127.0.0.1:8000';
const NEXO_KEY = 'NEXO_LOCAL_2026_OK'; 

client.once('ready', () => {
  console.log(`[NEXO INFO] Bot conectado como ${client.user.tag}`);
});

client.on('interactionCreate', async interaction => {
  console.log(`\n[EVENTO] Interacción recibida: /${interaction.commandName} de ${interaction.user.tag}`);

  if (!interaction.isChatInputCommand()) return;

  if (interaction.commandName === 'unirse') {
    await interaction.deferReply();
    try {
      const channel = interaction.member?.voice?.channel;
      if (!channel) return interaction.editReply('❌ Entra a un canal de voz primero.');

      joinVoiceChannel({
        channelId: channel.id,
        guildId: channel.guild.id,
        adapterCreator: channel.guild.voiceAdapterCreator,
        selfDeaf: false,
      });
      console.log(`[VOZ] Conectado exitosamente a: ${channel.name}`);
      return interaction.editReply(`🎙️ NEXO conectado a **${channel.name}**`);
    } catch (e) {
      console.error('[ERROR VOZ]', e);
      return interaction.editReply(`❌ Error al conectar voz: ${e.message}`);
    }
  }

  if (interaction.commandName === 'salir') {
    await interaction.deferReply();
    const conn = getVoiceConnection(interaction.guild.id);
    if (conn) { 
        conn.destroy(); 
        console.log('[VOZ] Desconectado del canal.');
        return interaction.editReply('👋 NEXO desconectado.'); 
    }
    return interaction.editReply('❌ No estoy en ningún canal.');
  }

  if (interaction.commandName === 'nexo') {
    await interaction.deferReply();
    const query = interaction.options.getString('pregunta');
    console.log(`[RAG] Consultando backend: "${query}"`);
    
    try {
      const res = await fetch(`${NEXO_BACKEND}/api/ai/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-NEXO-API-KEY': NEXO_KEY
        },
        body: JSON.stringify({ question: query })
      });
      
      const data = await res.json();
      console.log('[RAG] Respuesta recibida del backend.');
      return interaction.editReply(`🤖 **NEXO:** ${data.answer || data.respuesta || 'Sin respuesta'}`);
    } catch (e) {
      console.error('[ERROR RAG]', e);
      return interaction.editReply(`❌ Error de conexión con el Cerebro: ${e.message}`);
    }
  }
});

client.login(process.env.DISCORD_TOKEN);
          GatewayIntentBits.MessageContent
        ]
      });

      const NEXO_BACKEND = process.env.FASTAPI_URL || 'http://127.0.0.1:8000';
      const NEXO_KEY = 'NEXO_LOCAL_2026_OK'; 

      client.once('ready', () => {
        console.log(`[NEXO INFO] Bot conectado como ${client.user.tag}`);
      });

      client.on('interactionCreate', async interaction => {
        console.log(`\n[EVENTO] Interação recebida: /${interaction.commandName} de ${interaction.user.tag}`);

        if (!interaction.isChatInputCommand()) return;

        if (interaction.commandName === 'unirse') {
          await interaction.deferReply();
          try {
            const channel = interaction.member?.voice?.channel;
            if (!channel) return interaction.editReply('❌ Entre em um canal de voz primeiro.');

            joinVoiceChannel({
              channelId: channel.id,
              guildId: channel.guild.id,
              adapterCreator: channel.guild.voiceAdapterCreator,
              selfDeaf: false,
            });
            console.log(`[VOZ] Conectado com sucesso a: ${channel.name}`);
            return interaction.editReply(`🎙️ NEXO conectado a **${channel.name}**`);
          } catch (e) {
            console.error('[ERRO VOZ]', e);
            return interaction.editReply(`❌ Erro ao conectar voz: ${e.message}`);
          }
        }

        if (interaction.commandName === 'salir') {
          await interaction.deferReply();
          const conn = getVoiceConnection(interaction.guild.id);
          if (conn) { 
              conn.destroy(); 
              console.log('[VOZ] Desconectado do canal.');
              return interaction.editReply('👋 NEXO desconectado.'); 
          }
          return interaction.editReply('❌ Não estou em nenhum canal.');
        }

        if (interaction.commandName === 'nexo') {
          await interaction.deferReply();
          const query = interaction.options.getString('pregunta');
          console.log(`[RAG] Consultando backend: "${query}"`);
    
          try {
            const res = await fetch(`${NEXO_BACKEND}/api/ai/ask`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-NEXO-API-KEY': NEXO_KEY
              },
              body: JSON.stringify({ question: query })
            });
      
            const data = await res.json();
            console.log('[RAG] Resposta recebida do backend.');
            return interaction.editReply(`🤖 **NEXO:** ${data.answer || data.respuesta || 'Sem resposta'}`);
          } catch (e) {
            console.error('[ERRO RAG]', e);
            return interaction.editReply(`❌ Erro de conexão com o Cérebro: ${e.message}`);
          }
        }
      });

      client.login(process.env.DISCORD_TOKEN);
          console.log('[RAG] Respuesta recibida del backend.');
