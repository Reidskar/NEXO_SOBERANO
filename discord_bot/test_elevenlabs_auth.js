const axios = require('axios');

const API_KEY = 'sk_140abd592450008d19728f7110b52725ff97980168749410';

async function testAuth() {
  try {
    const response = await axios.get('https://api.elevenlabs.io/v1/voices', {
      headers: {
        'xi-api-key': API_KEY
      }
    });
    console.log('AUTH_OK: Voices found:', response.data.voices.length);
    response.data.voices.slice(0, 5).forEach(v => console.log(` - ${v.name} (${v.voice_id})`));
  } catch (err) {
    console.error('AUTH_ERR:', err.response ? err.response.status : err.message);
    if (err.response) console.error('DETAIL:', err.response.data);
  }
}

testAuth();
