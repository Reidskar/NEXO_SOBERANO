const axios = require('axios');
const { Readable } = require('stream');

// Keys are read inside functions to avoid race conditions with dotenv
const DEFAULT_VOICE_ID = 'pNInz6obpgDQGcFmaJcg'; // Adam as legacy default
const ELEVENLABS_API_URL = 'https://api.elevenlabs.io/v1/text-to-speech';

/**
 * Returns a readable stream for ElevenLabs TTS
 */
async function streamElevenLabs(text, voiceId = process.env.ELEVENLABS_VOICE_ID || DEFAULT_VOICE_ID) {
    const apiKey = process.env.ELEVENLABS_API_KEY;
    if (!apiKey) {
        throw new Error('ELEVENLABS_API_KEY not configured');
    }
    console.log(`[TTS] Requesting ElevenLabs: Voice="${voiceId}" Text="${text.substring(0, 30)}..."`);

    const url = `${ELEVENLABS_API_URL}/${voiceId}/stream`;

    try {
        const response = await axios({
            method: 'post',
            url: url,
            data: {
                text: text,
                model_id: 'eleven_multilingual_v2', // CRÍTICO: Modelo V2 para mejor español y pausas
                voice_settings: {
                    stability: 0.45,       // Menos estabilidad = más emoción y variaciones naturales
                    similarity_boost: 0.80, // Más realismo
                    style: 0.15,           // Toque de estilo
                    use_speaker_boost: true
                }
            },
            headers: {
                'Accept': 'audio/ogg; codecs=opus',
                'xi-api-key': apiKey,
                'Content-Type': 'application/json'
            },
            responseType: 'stream',
            timeout: 15000 // Timeout de 15 segundos
        });

        // Parche 4: Validación de Headers
        const contentType = response.headers['content-type'] || '';
        if (contentType.includes('application/json')) {
            console.error('[TTS ELEVENLABS] ❌ Error de API recibido como JSON en lugar de Audio.');
            throw new Error('ElevenLabs devolvió un JSON de error (posible falta de créditos o API key inválida)');
        }

        return response.data;
    } catch (err) {
        if (err.response && err.response.data) {
            // Intentar leer el cuerpo del stream del error
            try {
                const chunks = [];
                for await (const chunk of err.response.data) {
                    chunks.push(chunk);
                }
                const errorBody = Buffer.concat(chunks).toString();
                console.error('[TTS ELEVENLABS] API Error Detail:', errorBody);
            } catch (e) {
                console.error('ElevenLabs API error (Stream):', err.message);
            }
        } else {
            console.error('ElevenLabs API error:', err.message);
        }
        throw err;
    }
}

module.exports = {
    streamElevenLabs
};
