const { REST, Routes, SlashCommandBuilder } = require('discord.js');
require('dotenv').config({path: require('path').join(__dirname, '..', '.env')});

const commands = [
  new SlashCommandBuilder()
    .setName('nexo')
    .setDescription('Pregunta a NEXO (Gemma 4 local → Gemini fallback)')
    .addStringOption(o => o.setName('query').setDescription('Tu pregunta').setRequired(true)),

  new SlashCommandBuilder()
    .setName('ai')
    .setDescription('Consulta a la inteligencia principal con contexto persistente')
    .addStringOption(o =>
      o.setName('pregunta').setDescription('Tu pregunta o instrucción').setRequired(true)
    )
    .addBooleanOption(o =>
      o.setName('recordar').setDescription('Mantener en contexto (default: sí)').setRequired(false)
    ),

  new SlashCommandBuilder()
    .setName('memoria')
    .setDescription('Gestiona el contexto de tu conversación con NEXO')
    .addStringOption(o =>
      o.setName('accion')
        .setDescription('ver o limpiar')
        .setRequired(false)
        .addChoices(
          { name: 'Ver contexto actual', value: 'ver' },
          { name: 'Limpiar contexto',   value: 'limpiar' }
        )
    ),

  new SlashCommandBuilder()
    .setName('status')
    .setDescription('Métricas del sistema NEXO'),

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
