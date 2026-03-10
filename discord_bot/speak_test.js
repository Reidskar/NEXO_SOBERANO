const { speakInVoice, client, connectVoiceAlwaysOn } = require('./bot.js');

// We need to bypass some of the bot's structure to test speakInVoice directly
// or just wait for the bot to be ready.

const { joinVoiceChannel, createAudioPlayer, createAudioResource, StreamType, AudioPlayerStatus, getVoiceConnection } = require('@discordjs/voice');
const discordTTS = require('discord-tts');
const dotenv = require('dotenv');
dotenv.config();

const { Client, GatewayIntentBits } = require('discord.js');

const c = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildVoiceStates]
});

c.once('ready', async () => {
    console.log('Bot ready for speak test');
    const guildId = process.env.VOICE_GUILD_ID;
    const channelId = process.env.VOICE_CHANNEL_ID;
    
    const guild = await c.guilds.fetch(guildId);
    const connection = joinVoiceChannel({
        guildId: guildId,
        channelId: channelId,
        adapterCreator: guild.voiceAdapterCreator,
    });

    connection.on('stateChange', (old, nw) => console.log(`Connection: ${old.status} -> ${nw.status}`));

    const player = createAudioPlayer();
    connection.subscribe(player);

    const stream = discordTTS.getVoiceStream("Hola, esta es una prueba de voz del sistema NEXO SOBERANO.");
    const resource = createAudioResource(stream, { inputType: StreamType.Arbitrary });
    
    console.log('Playing audio...');
    player.play(resource);

    player.on(AudioPlayerStatus.Playing, () => console.log('Audio playing!'));
    player.on(AudioPlayerStatus.Idle, () => {
        console.log('Audio finished.');
        process.exit(0);
    });
    player.on('error', e => console.error('Player error:', e));

    setTimeout(() => {
        console.log('Timeout - forcing exit');
        process.exit(1);
    }, 15000);
});

c.login(process.env.DISCORD_TOKEN);
