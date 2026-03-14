const axios = require('axios');
const fs = require('fs');

const ELEVENLABS_API_KEY = 'sk_140abd592450008d19728f7110b52725ff97980168749410';
const VOICE_ID = 'EXAVITQu4vr4xnSDxMaL'; // Sarah

async function testTTS() {
    try {
        const response = await axios({
            method: 'post',
            url: `https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}/stream`,
            data: {
                text: "Prueba de conexión Nexo.",
                model_id: 'eleven_multilingual_v2'
            },
            headers: {
                'xi-api-key': ELEVENLABS_API_KEY,
                'Content-Type': 'application/json'
            },
            responseType: 'stream'
        });
        console.log('TTS_OK: Conexión establecida, recibiendo stream.');
        process.exit(0);
    } catch (err) {
        console.error('TTS_ERR:', err.response ? err.response.status : err.message);
        if (err.response) console.error('DATA:', err.response.data.detail || err.response.data);
        process.exit(1);
    }
}

testTTS();
