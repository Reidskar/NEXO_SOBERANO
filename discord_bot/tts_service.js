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
    const player = createAudioPlayer();
    connection.subscribe(player);

    let resource;
    let isStream = false;

    // Try ElevenLabs if key exists
    if (process.env.ELEVENLABS_API_KEY && !opts.forceFallback) {
        try {
            console.log(`[TTS] Generando con ElevenLabs... (Voice: ${opts.voiceId || 'Default'})`);
            const audioStream = await streamElevenLabs(text, opts.voiceId);
            resource = createAudioResource(audioStream, {
                inputType: StreamType.Arbitrary
            });
            isStream = true;
            console.log('[TTS] Stream ElevenLabs establecido con éxito.');
        } catch (err) {
            console.warn('[TTS] ElevenLabs falló, intentando fallback a Google TTS:', err.message);
        }
    }

    // Fallback to discord-tts (Google TTS)
    if (!resource) {
        console.log('Using discord-tts for fallback...');
        const stream = discordTTS.getVoiceStream(text, { lang: 'es' });
        resource = createAudioResource(stream, {
            inputType: StreamType.Arbitrary
        });
    }

    player.play(resource);

    try {
        // Wait for it to start playing
        await entersState(player, AudioPlayerStatus.Playing, 5000);
    } catch (e) {
        // Audio might be very short or there was a delay
    }

    return new Promise((resolve) => {
        let finished = false;
        const done = () => {
            if (finished) return;
            finished = true;
            player.stop();
            resolve();
        };

        player.once(AudioPlayerStatus.Idle, done);
        player.once('error', (err) => {
            console.error('Playback error:', err);
            done();
        });

        // Safety timeout for long responses (60s)
        setTimeout(done, 60000);
    });
}

module.exports = {
    playTTS
};
