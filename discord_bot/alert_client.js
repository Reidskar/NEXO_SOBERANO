const axios = require('axios');

/**
 * Sends an alert to the webhook relay.
 * @param {Object} payload 
 */
async function sendAlert(payload) {
    try {
        const url = process.env.ALERT_RELAY_URL || 'http://localhost:4000/alerts';
        const res = await axios.post(url, {
            ...payload,
            timestamp: new Date().toISOString()
        }, {
            timeout: 5000
        });
        return res.status === 200;
    } catch (err) {
        console.error('Failed to send alert:', err.message);
        return false;
    }
}

module.exports = { sendAlert };
