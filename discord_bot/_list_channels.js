require('dotenv').config();
const { Client, GatewayIntentBits } = require('discord.js');
const c = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildVoiceStates] });
c.once('ready', async () => {
  const g = await c.guilds.fetch('1474844765806919680');
  const channels = await g.channels.fetch();
  channels.forEach(ch => {
    if (ch) console.log(`${ch.id} | type=${ch.type} | name=${ch.name}`);
  });
  process.exit(0);
});
c.login(process.env.DISCORD_TOKEN);
