require('dotenv').config();
const axios = require('axios');

async function playTestTTS() {
    const port = process.env.PORT || 3000;
    const url = `http://localhost:${port}/internal/tts_test`;
    const text = process.argv[2] || 'Prueba de integración total: El bot debería estar hablando ahora mismo en el canal de voz.';

    console.log(`--- Full Integration TTS Test ---`);
    console.log(`Target: ${url}`);
    console.log(`Text: "${text}"`);

    try {
        const response = await axios.post(url, {
            text: text
        }, {
            timeout: 10000
        });

        console.log('✅ Solicitud enviada correctamente.');
        console.log('Respuesta del bot:', response.data);
        console.log('Verifica el canal de voz de Discord para confirmar la salida de audio.');

    } catch (err) {
        console.error('❌ Error al contactar con el endpoint interno del bot:');
        if (err.code === 'ECONNREFUSED') {
            console.error(`Status: El bot no parece estar corriendo en el puerto ${port}.`);
        } else {
            console.error(err.message);
        }
        process.exit(1);
    }
}

playTestTTS();
