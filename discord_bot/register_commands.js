const { REST, Routes, SlashCommandBuilder } = require('discord.js');
require('dotenv').config();

const commands = [
  new SlashCommandBuilder()
    .setName('nexo')
    .setDescription('Consulta al cerebro NEXO')
    .addStringOption(o =>
      o.setName('pregunta')
       .setDescription('Tu pregunta')
       .setRequired(true)),
  new SlashCommandBuilder()
    .setName('unirse')
    .setDescription('NEXO se une a tu canal de voz'),
  new SlashCommandBuilder()
    .setName('salir')
    .setDescription('NEXO abandona el canal de voz'),
].map(c => c.toJSON());

const rest = new REST({ version: '10' })
  .setToken(process.env.DISCORD_TOKEN);

(async () => {
  try {
    console.log('Registrando slash commands...');
    await rest.put(
      Routes.applicationCommands(process.env.DISCORD_CLIENT_ID),
      { body: commands }
    );
    console.log('✅ Slash commands registrados.');
  } catch (e) {
    console.error('❌ Error:', e.message);
  }
})();
