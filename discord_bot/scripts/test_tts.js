require('dotenv').config();
const axios = require('axios');
const fs = require('fs');
const path = require('path');

const ELEVENLABS_API_KEY = process.env.ELEVENLABS_API_KEY;
const VOICE_ID = process.env.ELEVENLABS_VOICE_ID || 'pNInz6obpgDQGcFmaJgB';

async function testTTS() {
    console.log('--- ElevenLabs TTS Test ---');
    if (!ELEVENLABS_API_KEY) {
        console.error('❌ Error: ELEVENLABS_API_KEY no encontrada en .env');
        process.exit(1);
    }

    const text = 'Esta es una prueba de voz del sistema Nexo Soberano usando ElevenLabs y el codec Opus.';
    const url = `https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}/stream`;

    console.log(`Enviando solicitud para: "${text}"`);
    console.log(`Voice ID: ${VOICE_ID}`);

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

        const outputPath = path.join(__dirname, 'test_output.opus');
        const writer = fs.createWriteStream(outputPath);

        response.data.pipe(writer);

        return new Promise((resolve, reject) => {
            writer.on('finish', () => {
                console.log(`✅ Prueba exitosa. Archivo guardado en: ${outputPath}`);
                console.log('Si puedes escuchar este archivo, el componente ElevenLabs está funcionando perfectamente.');
                resolve();
            });
            writer.on('error', reject);
        });

    } catch (err) {
        console.error('❌ Error en la API de ElevenLabs:');
        if (err.response) {
            console.error(`Status: ${err.response.status}`);
            console.error(err.response.data);
        } else {
            console.error(err.message);
        }
        process.exit(1);
    }
}

testTTS();
