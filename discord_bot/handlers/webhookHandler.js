/**
 * Webhook Handler - Manejo de webhooks de Discord
 * Permite recibir eventos desde aplicaciones externas
 */

const express = require('express');
const crypto = require('crypto');

class WebhookHandler {
  constructor(client, port = 3000) {
    this.client = client;
    this.port = port;
    this.app = express();
    this.setupRoutes();
  }

  setupRoutes() {
    // Middleware
    this.app.use(express.json());

    // Ruta de health check
    this.app.get('/health', (req, res) => {
      res.json({ status: 'ok', bot: this.client.user?.tag });
    });

    // Webhook para enviar mensajes
    this.app.post('/webhook/message', (req, res) => {
      try {
        const { channelId, content, embed } = req.body;

        if (!channelId || !content) {
          return res.status(400).json({
            error: 'channelId y content son requeridos'
          });
        }

        const channel = this.client.channels.cache.get(channelId);
        if (!channel) {
          return res.status(404).json({
            error: 'Canal no encontrado'
          });
        }

        const messageOptions = { content };
        if (embed) {
          messageOptions.embeds = [embed];
        }

        channel.send(messageOptions)
          .then(message => {
            res.json({
              success: true,
              messageId: message.id
            });
          })
          .catch(error => {
            res.status(500).json({
              error: error.message
            });
          });
      } catch (error) {
        res.status(500).json({
          error: error.message
        });
      }
    });

    // Webhook para reproducir sonidos
    this.app.post('/webhook/sound', (req, res) => {
      try {
        const { guildId, soundKey } = req.body;

        if (!guildId || !soundKey) {
          return res.status(400).json({
            error: 'guildId y soundKey son requeridos'
          });
        }

        // Emitir evento para reproducir sonido
        this.client.emit('playSound', { guildId, soundKey });

        res.json({
          success: true,
          message: `Reproduciendo sonido: ${soundKey}`
        });
      } catch (error) {
        res.status(500).json({
          error: error.message
        });
      }
    });

    // Webhook para conectar a voz
    this.app.post('/webhook/voice/connect', (req, res) => {
      try {
        const { guildId, channelId } = req.body;

        if (!guildId || !channelId) {
          return res.status(400).json({
            error: 'guildId y channelId son requeridos'
          });
        }

        const guild = this.client.guilds.cache.get(guildId);
        if (!guild) {
          return res.status(404).json({
            error: 'Servidor no encontrado'
          });
        }

        const channel = guild.channels.cache.get(channelId);
        if (!channel || channel.type !== 2) { // 2 = GUILD_VOICE
          return res.status(404).json({
            error: 'Canal de voz no encontrado'
          });
        }

        // Emitir evento para conectar a voz
        this.client.emit('connectVoice', { guild, channel });

        res.json({
          success: true,
          message: `Conectando a ${channel.name}`
        });
      } catch (error) {
        res.status(500).json({
          error: error.message
        });
      }
    });

    // Webhook para desconectar de voz
    this.app.post('/webhook/voice/disconnect', (req, res) => {
      try {
        const { guildId } = req.body;

        if (!guildId) {
          return res.status(400).json({
            error: 'guildId es requerido'
          });
        }

        // Emitir evento para desconectar de voz
        this.client.emit('disconnectVoice', { guildId });

        res.json({
          success: true,
          message: 'Desconectando de voz'
        });
      } catch (error) {
        res.status(500).json({
          error: error.message
        });
      }
    });

    // Webhook para obtener estado
    this.app.get('/webhook/status/:guildId', (req, res) => {
      try {
        const { guildId } = req.params;

        const guild = this.client.guilds.cache.get(guildId);
        if (!guild) {
          return res.status(404).json({
            error: 'Servidor no encontrado'
          });
        }

        res.json({
          guildId,
          guildName: guild.name,
          memberCount: guild.memberCount,
          botStatus: 'online'
        });
      } catch (error) {
        res.status(500).json({
          error: error.message
        });
      }
    });

    // Ruta 404
    this.app.use((req, res) => {
      res.status(404).json({
        error: 'Ruta no encontrada'
      });
    });
  }

  start() {
    this.server = this.app.listen(this.port, () => {
      console.log(`🌐 Webhook server escuchando en puerto ${this.port}`);
    });
  }

  stop() {
    if (this.server) {
      this.server.close();
      console.log('🌐 Webhook server detenido');
    }
  }
}

module.exports = WebhookHandler;
