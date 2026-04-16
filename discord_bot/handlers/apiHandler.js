/**
 * API Handler - Comunicación con NEXO Backend
 */

const axios = require('axios');

class APIHandler {
  constructor(baseURL, apiKey) {
    this.baseURL = baseURL || process.env.NEXO_BACKEND || 'http://127.0.0.1:8080';
    this.apiKey = apiKey || process.env.NEXO_API_KEY || 'NEXO_LOCAL_2026_OK';
    this.timeout = parseInt(process.env.REQUEST_TIMEOUT) || 10000;

    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: this.timeout,
      headers: {
        'Content-Type': 'application/json',
        'X-NEXO-API-KEY': this.apiKey,
        'User-Agent': 'NEXO-Discord-Bot/1.0'
      }
    });

    // Interceptor para manejo de errores
    this.client.interceptors.response.use(
      response => response,
      error => {
        console.error(`❌ API Error: ${error.response?.status || error.code} - ${error.message}`);
        throw error;
      }
    );
  }

  /**
   * Verificar salud del backend
   */
  async healthCheck() {
    try {
      const response = await this.client.get('/health', { timeout: 5000 });
      return {
        status: 'online',
        data: response.data
      };
    } catch (error) {
      return {
        status: 'offline',
        error: error.message
      };
    }
  }

  /**
   * Consultar pregunta a NEXO
   */
  async askQuestion(question) {
    try {
      const response = await this.client.post('/api/ai/ask', {
        question: question.trim()
      });

      return {
        success: true,
        answer: response.data.answer || response.data.respuesta || response.data.response || 'Sin respuesta'
      };
    } catch (error) {
      console.error('❌ Error consultando NEXO:', error.message);
      return {
        success: false,
        error: error.message,
        answer: 'Error al consultar el backend'
      };
    }
  }

  /**
   * Obtener métricas del sistema
   */
  async getMetrics() {
    try {
      const response = await this.client.get('/api/metrics');
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('❌ Error obteniendo métricas:', error.message);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Obtener estado de servicios
   */
  async getServices() {
    try {
      const response = await this.client.get('/api/services');
      return {
        success: true,
        services: response.data.services || []
      };
    } catch (error) {
      console.error('❌ Error obteniendo servicios:', error.message);
      return {
        success: false,
        error: error.message,
        services: []
      };
    }
  }

  /**
   * Enviar evento a Discord
   */
  async sendDiscordEvent(eventType, data) {
    try {
      const response = await this.client.post('/api/discord/event', {
        type: eventType,
        data: data
      });
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('❌ Error enviando evento:', error.message);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Obtener logs del sistema
   */
  async getLogs(limit = 50) {
    try {
      const response = await this.client.get(`/api/logs?limit=${limit}`);
      return {
        success: true,
        logs: response.data.logs || []
      };
    } catch (error) {
      console.error('❌ Error obteniendo logs:', error.message);
      return {
        success: false,
        error: error.message,
        logs: []
      };
    }
  }

  /**
   * Ejecutar comando en el backend
   */
  async executeCommand(command, params = {}) {
    try {
      const response = await this.client.post('/api/commands/execute', {
        command: command,
        params: params
      });
      return {
        success: true,
        result: response.data
      };
    } catch (error) {
      console.error('❌ Error ejecutando comando:', error.message);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Obtener configuración
   */
  async getConfig() {
    try {
      const response = await this.client.get('/api/config');
      return {
        success: true,
        config: response.data
      };
    } catch (error) {
      console.error('❌ Error obteniendo configuración:', error.message);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Actualizar configuración
   */
  async updateConfig(config) {
    try {
      const response = await this.client.put('/api/config', config);
      return {
        success: true,
        config: response.data
      };
    } catch (error) {
      console.error('❌ Error actualizando configuración:', error.message);
      return {
        success: false,
        error: error.message
      };
    }
  }
}

module.exports = APIHandler;
