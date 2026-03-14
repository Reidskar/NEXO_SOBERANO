const fs = require('fs');
const path = require('path');
const { createAudioPlayer, createAudioResource, AudioPlayerStatus, entersState, StreamType } = require('@discordjs/voice');
const discordTTS = require('discord-tts');
const { streamElevenLabs } = require('./tts_elevenlabs');

const TEMP_DIR = path.join(__dirname, 'temp_audio');
if (!fs.existsSync(TEMP_DIR)) fs.mkdirSync(TEMP_DIR);

/**
 * Unified TTS player that supports streaming and fallbacks
 */
async function playTTS(connection, text, opts = {}) {
    // Regla 2: Streaming en TTS (No disco)
    const player = createAudioPlayer();
    connection.subscribe(player);

    let resource;

    // Try ElevenLabs if key exists
    if (process.env.ELEVENLABS_API_KEY && !opts.forceFallback) {
        try {
            console.log(`[TTS] Generando STREAM con ElevenLabs...`);
            const audioStream = await streamElevenLabs(text, opts.voiceId);
            
            // Pasamos el stream directamente a createAudioResource
            resource = createAudioResource(audioStream, {
                inputType: StreamType.Arbitrary,
                inlineVolume: true
            });
            console.log('[TTS] Stream ElevenLabs establecido. Reproduciendo...');
        } catch (err) {
            console.warn('[TTS] ElevenLabs falló, intentando fallback a Google TTS:', err.message);
        }
    }

    // Fallback to discord-tts (Google TTS)
    if (!resource) {
        console.log('[TTS] Usando Google TTS (Stream)...');
        // Parche 5: google-tts-api tiene límite de 200 chars. 
        // Si es largo, truncamos para voz (la voz debe ser breve) o podríamos splitear.
        // Por ahora, truncamos a un nivel razonable para evitar crashes y saturación.
        const safeText = text.substring(0, 200); 
        const stream = discordTTS.getVoiceStream(safeText, { lang: 'es' });
        resource = createAudioResource(stream, {
            inputType: StreamType.Arbitrary,
            inlineVolume: true
        });
    }

    player.play(resource);

    return new Promise((resolve) => {
        player.once(AudioPlayerStatus.Idle, () => {
            player.stop();
            resolve();
        });
        player.once('error', (err) => {
            console.error('[TTS] Error en el reproductor:', err);
            player.stop();
            resolve();
        });
        // Safety timeout (90s for long responses)
        setTimeout(() => {
            player.stop();
            resolve();
        }, 90000);
    });
}

module.exports = {
    playTTS
};
