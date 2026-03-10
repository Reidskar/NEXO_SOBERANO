// Check voice version and test connection debugging
require('dotenv').config();
const { Client, GatewayIntentBits } = require('discord.js');
const {
  joinVoiceChannel,
  getVoiceConnection,
  VoiceConnectionStatus,
  entersState,
  generateDependencyReport,
} = require('@discordjs/voice');

const VOICE_GUILD_ID = process.env.VOICE_GUILD_ID;
const VOICE_CHANNEL_ID = process.env.VOICE_CHANNEL_ID;

const c = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildVoiceStates]
});

c.once('ready', async () => {
  console.log('Bot ready, attempting voice connection...');
  
  try {
    const guild = await c.guilds.fetch(VOICE_GUILD_ID);
    const channel = await guild.channels.fetch(VOICE_CHANNEL_ID);
    console.log(`Channel: ${channel.name} type=${channel.type}`);
    
    const connection = joinVoiceChannel({
      guildId: VOICE_GUILD_ID,
      channelId: VOICE_CHANNEL_ID,
      adapterCreator: guild.voiceAdapterCreator,
      selfDeaf: false,
      selfMute: false,
      debug: true,
    });
    
    connection.on('stateChange', (oldState, newState) => {
      console.log(`Voice state: ${oldState.status} -> ${newState.status}`);
    });
    
    connection.on('error', (error) => {
      console.error(`Voice error: ${error.message}`);
    });
    
    console.log('Waiting for Ready state (60s timeout)...');
    await entersState(connection, VoiceConnectionStatus.Ready, 60000);
    console.log('SUCCESS: Voice connected!');
    connection.destroy();
  } catch (error) {
    console.error(`FAILED: ${error.message}`);
  }
  
  setTimeout(() => process.exit(0), 2000);
});

c.login(process.env.DISCORD_TOKEN);
