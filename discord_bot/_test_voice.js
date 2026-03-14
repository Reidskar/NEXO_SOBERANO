require('dotenv').config();
const { Client, GatewayIntentBits } = require('discord.js');
const { joinVoiceChannel, EndBehaviorType } = require('@discordjs/voice');

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildVoiceStates,
    ]
});

client.on('ready', () => {
    console.log(`[TEST] Logged in as ${client.user.tag}`);
    // Wait a bit to let the user join the voice channel
    setTimeout(async () => {
        const guildId = process.env.DISCORD_GUILD_ID || client.guilds.cache.first()?.id;
        const guild = client.guilds.cache.get(guildId);
        
        // Find a channel to join (the one the user is in)
        let targetChannel = null;
        guild.channels.cache.forEach(c => {
            if (c.type === 2 && c.members.size > 0) { // Voice channel with people
                targetChannel = c;
            }
        });

        if (!targetChannel) {
            console.log('[TEST] No active voice channel found with members.');
            process.exit(0);
        }

        console.log(`[TEST] Joining ${targetChannel.name}...`);
        const connection = joinVoiceChannel({
            channelId: targetChannel.id,
            guildId: guild.id,
            adapterCreator: guild.voiceAdapterCreator,
            selfDeaf: false,
        });

        connection.receiver.speaking.on('start', (userId) => {
            console.log(`[TEST] EVENT => User ${userId} started speaking!`);
        });

        console.log('[TEST] Listening for 10 seconds...');
        setTimeout(() => {
            console.log('[TEST] Test finished.');
            process.exit(0);
        }, 10000);
        
    }, 2000);
});

client.login(process.env.DISCORD_TOKEN);
