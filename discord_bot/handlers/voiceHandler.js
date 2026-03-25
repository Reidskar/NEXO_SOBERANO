/**
 * Voice Handler - Manejo de conexiones de voz en Discord
 */

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

class VoiceHandler {
  constructor() {
    this.players = new Map();
    this.connections = new Map();
  }

  /**
   * Conectar a un canal de voz
   */
  async joinVoiceChannel(guild, voiceChannel) {
    try {
      if (!voiceChannel) {
        throw new Error('Canal de voz no especificado');
      }

      // Verificar permisos
      const botMember = guild.members.me;
      if (!botMember.permissions.has('Connect')) {
        throw new Error('Sin permiso para conectarse al canal');
      }

      if (!botMember.permissions.has('Speak')) {
        throw new Error('Sin permiso para hablar en el canal');
      }

      // Crear conexión
      const connection = joinVoiceChannel({
        channelId: voiceChannel.id,
        guildId: guild.id,
        adapterCreator: guild.voiceAdapterCreator,
        selfDeaf: false,
        selfMute: false
      });

      // Esperar a que esté listo
      await entersState(connection, VoiceConnectionStatus.Ready, 30_000);

      // Crear reproductor de audio
      const player = createAudioPlayer();
      connection.subscribe(player);

      // Guardar referencias
      this.connections.set(guild.id, connection);
      this.players.set(guild.id, player);

      // Manejo de desconexión
      connection.on(VoiceConnectionStatus.Disconnected, async () => {
        try {
          await entersState(connection, VoiceConnectionStatus.Connecting, 5_000);
        } catch {
          connection.destroy();
          this.connections.delete(guild.id);
          this.players.delete(guild.id);
        }
      });

      connection.on('error', error => {
        console.error(`❌ Error de conexión de voz en ${guild.name}:`, error);
      });

      return connection;
    } catch (error) {
      console.error('❌ Error al conectar a voz:', error.message);
      throw error;
    }
  }

  /**
   * Desconectar de un canal de voz
   */
  leaveVoiceChannel(guildId) {
    try {
      const connection = this.connections.get(guildId);
      if (connection) {
        connection.destroy();
        this.connections.delete(guildId);
        this.players.delete(guildId);
        return true;
      }
      return false;
    } catch (error) {
      console.error('❌ Error al desconectar de voz:', error.message);
      return false;
    }
  }

  /**
   * Reproducir audio en un canal
   */
  async playAudio(guildId, audioPath) {
    try {
      const player = this.players.get(guildId);
      if (!player) {
        throw new Error('No hay reproductor de audio disponible');
      }

      if (!fs.existsSync(audioPath)) {
        throw new Error(`Archivo de audio no encontrado: ${audioPath}`);
      }

      const resource = createAudioResource(audioPath);
      player.play(resource);

      return new Promise((resolve, reject) => {
        player.once(AudioPlayerStatus.Idle, () => {
          resolve();
        });

        player.once('error', error => {
          reject(error);
        });
      });
    } catch (error) {
      console.error('❌ Error reproduciendo audio:', error.message);
      throw error;
    }
  }

  /**
   * Obtener estado de conexión
   */
  getConnectionStatus(guildId) {
    const connection = this.connections.get(guildId);
    if (!connection) {
      return {
        connected: false,
        status: 'disconnected'
      };
    }

    return {
      connected: connection.state.status === VoiceConnectionStatus.Ready,
      status: connection.state.status,
      channelId: connection.joinConfig.channelId
    };
  }

  /**
   * Obtener todas las conexiones activas
   */
  getActiveConnections() {
    return Array.from(this.connections.entries()).map(([guildId, connection]) => ({
      guildId,
      connected: connection.state.status === VoiceConnectionStatus.Ready,
      status: connection.state.status
    }));
  }

  /**
   * Limpiar recursos
   */
  cleanup() {
    for (const [guildId, connection] of this.connections.entries()) {
      connection.destroy();
    }
    this.connections.clear();
    this.players.clear();
  }
}

module.exports = new VoiceHandler();
