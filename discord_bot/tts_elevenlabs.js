const axios = require('axios');
const { Readable } = require('stream');

const ELEVENLABS_API_KEY = process.env.ELEVENLABS_API_KEY;
const ELEVENLABS_VOICE_ID = process.env.ELEVENLABS_VOICE_ID || 'pNInz6obpgDQGcFmaJgB'; // Adam as default
const ELEVENLABS_API_URL = process.env.ELEVENLABS_API_URL || 'https://api.elevenlabs.io/v1/text-to-speech';

/**
 * Returns a readable stream for ElevenLabs TTS
 */
async function streamElevenLabs(text, voiceId = ELEVENLABS_VOICE_ID) {
    if (!ELEVENLABS_API_KEY) {
        throw new Error('ELEVENLABS_API_KEY not configured');
    }

    const url = `${ELEVENLABS_API_URL}/${voiceId}/stream`;

    try {
        const response = await axios({
            method: 'post',
            url: url,
            data: {
                text: text,
                model_id: 'eleven_multilingual_v2',
                voice_settings: {
                    stability: 0.5,
                    similarity_boost: 0.75
                }
            },
            headers: {
                'Accept': 'audio/ogg; codecs=opus',
                'xi-api-key': ELEVENLABS_API_KEY,
                'Content-Type': 'application/json'
            },
            responseType: 'stream'
        });

        return response.data;
    } catch (err) {
        console.error('ElevenLabs API error:', err?.response?.data || err?.message);
        throw err;
    }
}

module.exports = {
    streamElevenLabs
};
