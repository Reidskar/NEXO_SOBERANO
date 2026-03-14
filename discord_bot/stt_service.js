const fs = require('fs');
const path = require('path');
const FormData = require('form-data');
const axios = require('axios');
const { spawn } = require('child_process');
const ffmpegStatic = require('ffmpeg-static');
const prism = require('prism-media');
const { EndBehaviorType, getVoiceConnection } = require('@discordjs/voice');
const { playTTS } = require('./tts_service');

const TEMP_DIR = path.join(__dirname, 'temp_audio');
if (!fs.existsSync(TEMP_DIR)) fs.mkdirSync(TEMP_DIR);

const activeUserStreams = new Map();

async function transcribeFile(filePath) {
    const apiKey = process.env.GROQ_API_KEY;
    if (!apiKey) throw new Error('GROQ_API_KEY no está configurada en el .env');

    const form = new FormData();
    form.append('file', fs.createReadStream(filePath));
    form.append('model', 'whisper-large-v3');
    form.append('language', 'es');
    form.append('prompt', 'Nexo Soberano assistant conversation. Regional geopolitics, evidence, and situation reports. Argentina and global analysis.');

    try {
        const response = await axios.post('https://api.groq.com/openai/v1/audio/transcriptions', form, {
            headers: { ...form.getHeaders(), 'Authorization': `Bearer ${apiKey}` },
            timeout: 20000
        });
        return response.data.text;
    } catch (error) {
        const errorDetail = error.response ? JSON.stringify(error.response.data) : error.message;
        console.error('[NEXO STT GROQ ERROR]', errorDetail);
        throw error;
    }
}

async function handleAudioStream(receiver, userId, client, player, guildId) {
    if (activeUserStreams.has(userId)) return;
    activeUserStreams.set(userId, true);

    const audioStream = receiver.subscribe(userId, {
        end: { behavior: EndBehaviorType.Manual }
    });

    const opusDecoder = new prism.opus.Decoder({ rate: 48000, channels: 2, frameSize: 960 });
    let chunkCount = 0;
    let lastDataTime = Date.now();

    const silenceCheck = setInterval(() => {
        const idleTime = Date.now() - lastDataTime;
        if (idleTime > 1500 && chunkCount > 0) {
            console.log(`[NEXO VOICE] ⌚ Silencio detectado (1.5s). Cerrando grabación de ${userId}.`);
            cleanup();
        }
    }, 500);

    const tmpFile = path.join(TEMP_DIR, `voice_${guildId}_${userId}_${Date.now()}.wav`);
    
    const ffmpegProc = spawn(ffmpegStatic, [
        '-f', 's16le', '-ar', '48000', '-ac', '2', '-i', 'pipe:0',
        '-af', 'volume=3.0',
        '-ar', '16000', '-ac', '1', tmpFile
    ]);

    const cleanup = () => {
        activeUserStreams.delete(userId);
        clearInterval(silenceCheck);
        try {
            audioStream.unpipe(opusDecoder);
            opusDecoder.unpipe(ffmpegProc.stdin);
            ffmpegProc.stdin.end();
        } catch (e) {}
    };

    opusDecoder.on('data', () => {
        chunkCount++;
        lastDataTime = Date.now();
    });

    audioStream.pipe(opusDecoder).pipe(ffmpegProc.stdin);

    ffmpegProc.on('close', async (code) => {
        if (chunkCount > 40) {
            try {
                console.log(`[NEXO VOICE] Audio capturado. Procesando STT...`);
                const textInput = await transcribeFile(tmpFile);
                if (fs.existsSync(tmpFile)) fs.unlinkSync(tmpFile);

                if (!textInput || textInput.trim().length < 2) return;
                const lowered = textInput.toLowerCase().trim();
                const hallucinations = ['gracias.', 'gracias', 'subtitles by', 'mushrooms', 'amara.org'];
                if (hallucinations.some(h => lowered.includes(h)) && lowered.length < 15) return;

                console.log(`[NEXO VOICE] STT Exitoso: "${textInput}"`);

                const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';
                const nexoResponse = await axios.post(`${FASTAPI_URL}/agente/consultar-rag`, {
                    pregunta: textInput,
                    usuario_id: userId,
                    contexto: "discord_voice"
                }, {
                    headers: { 'Authorization': `Bearer ${process.env.NEXO_API_KEY}` },
                    timeout: 20000
                });

                const iaText = nexoResponse.data.respuesta || "No pude procesar tu solicitud.";
                console.log(`[NEXO VOICE] LLM Exitoso. Sintetizando TTS...`);

                const connection = getVoiceConnection(guildId);
                if (connection) {
                    await playTTS(connection, iaText);
                }

            } catch (err) {
                console.error(`[NEXO VOICE] Error procesando audio:`, err.response?.data || err.message);
                if (fs.existsSync(tmpFile)) fs.unlinkSync(tmpFile);
            }
        } else {
            console.log(`[NEXO VOICE] Audio insuficiente/ruido (${chunkCount} chunks). Ignorando.`);
            if (fs.existsSync(tmpFile)) fs.unlinkSync(tmpFile);
        }
    });
}

module.exports = { transcribeFile, handleAudioStream };
