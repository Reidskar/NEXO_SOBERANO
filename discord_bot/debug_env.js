require('dotenv').config();
require('dotenv').config({ path: require('path').join(__dirname, '../.env') });

console.log('--- ENV DEBUG ---');
console.log('ELEVENLABS_API_KEY:', process.env.ELEVENLABS_API_KEY ? 'DEFINED (Length: ' + process.env.ELEVENLABS_API_KEY.length + ')' : 'UNDEFINED');
console.log('ELEVENLABS_API_KEY STARTS WITH:', process.env.ELEVENLABS_API_KEY ? process.env.ELEVENLABS_API_KEY.substring(0, 5) : 'N/A');
console.log('ELEVENLABS_VOICE_ID:', process.env.ELEVENLABS_VOICE_ID);
console.log('------------------');
