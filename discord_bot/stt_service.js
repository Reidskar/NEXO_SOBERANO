const fs = require('fs');
const FormData = require('form-data');
const axios = require('axios');

const OPENAI_KEY = process.env.OPENAI_API_KEY;

async function transcribeFile(filePath) {
    if (!OPENAI_KEY) {
        throw new Error('OPENAI_API_KEY not configured');
    }

    const form = new FormData();
    form.append('file', fs.createReadStream(filePath));
    form.append('model', 'whisper-1');
    form.append('language', 'es');

    try {
        const res = await axios.post('https://api.openai.com/v1/audio/transcriptions', form, {
            headers: {
                ...form.getHeaders(),
                'Authorization': `Bearer ${OPENAI_KEY}`
            },
            maxContentLength: Infinity,
            maxBodyLength: Infinity,
            timeout: 120000
        });

        return res.data?.text || '';
    } catch (err) {
        console.error('Whisper transcription error:', err?.response?.data || err?.message);
        throw err;
    }
}

module.exports = {
    transcribeFile
};
