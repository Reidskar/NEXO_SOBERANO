// Minimal webhook relay for alerts
import http from 'node:http';
// Native fetch used
import process from 'node:process';

const PORT = process.env.PORT ? parseInt(process.env.PORT) : 4000;
const SLACK_WEBHOOK = process.env.TARGET_SLACK_WEBHOOK || '';
const DISCORD_WEBHOOK = process.env.TARGET_DISCORD_WEBHOOK || '';
const PAGERDUTY_KEY = process.env.PAGERDUTY_KEY || '';
const DEDUP_WINDOW = parseInt(process.env.ALERT_DEDUP_WINDOW || '300'); // seconds
const MAX_RETRIES = parseInt(process.env.MAX_RETRIES || '5');
const RETRY_BASE_MS = parseInt(process.env.RETRY_BASE_MS || '1000');

const dedupeMap = new Map(); // key -> timestamp

function nowTs() { return Math.floor(Date.now() / 1000); }
function logJson(o) { console.log(JSON.stringify(o)); }

async function forwardToSlack(payload) {
    if (!SLACK_WEBHOOK) return { ok: false, reason: 'no_slack' };
    const body = { text: payload.text || payload.title || 'Alert' };
    const res = await fetch(SLACK_WEBHOOK, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    return { ok: res.ok, status: res.status };
}

async function forwardToDiscord(payload) {
    if (!DISCORD_WEBHOOK) return { ok: false, reason: 'no_discord' };
    const body = { 
        content: `**${(payload.level || 'alert').toUpperCase()}**: ${payload.title || payload.text || ''}`, 
        embeds: payload.embeds || [] 
    };
    const res = await fetch(DISCORD_WEBHOOK, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    return { ok: res.ok, status: res.status };
}

async function forwardToPagerDuty(payload) {
    if (!PAGERDUTY_KEY) return { ok: false, reason: 'no_pd' };
    const res = await fetch('https://events.pagerduty.com/v2/enqueue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            routing_key: PAGERDUTY_KEY,
            event_action: 'trigger',
            payload: {
                summary: payload.title || payload.text || 'Alert',
                severity: payload.level === 'critical' ? 'critical' : 'error',
                source: payload.source || 'nexo-bot'
            }
        })
    });
    return { ok: res.ok, status: res.status };
}

function dedupeKey(payload) {
    return `${payload.type || 'health'}::${payload.source || 'bot'}::${payload.title || payload.text || ''}`;
}

async function handleAlert(payload) {
    const key = dedupeKey(payload);
    const ts = nowTs();
    const last = dedupeMap.get(key) || 0;

    if (ts - last < DEDUP_WINDOW) {
        logJson({ event: 'deduped', key, last, now: ts });
        return { deduped: true };
    }
    dedupeMap.set(key, ts);

    logJson({ event: 'alert_received', payload, ts });

    const targets = [forwardToSlack, forwardToDiscord];
    if (payload.level === 'critical') targets.push(forwardToPagerDuty);

    const results = [];
    for (const fn of targets) {
        let attempt = 0, ok = false, lastErr = null;
        while (attempt < MAX_RETRIES && !ok) {
            attempt++;
            try {
                const r = await fn(payload);
                if (r && r.ok) { 
                    ok = true; 
                    results.push({ fn: fn.name, ok: true, status: r.status }); 
                    break; 
                }
                lastErr = r;
            } catch (err) { lastErr = err.message; }
            const backoff = RETRY_BASE_MS * Math.pow(2, attempt - 1);
            await new Promise(res => setTimeout(res, backoff + Math.floor(Math.random() * 200)));
        }
        if (!ok) results.push({ fn: fn.name, ok: false, lastErr });
    }
    logJson({ event: 'alert_forwarded', key, results });
    return { ok: true, results };
}

const server = http.createServer(async (req, res) => {
    if (req.method === 'GET' && req.url === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true, uptime: process.uptime() }));
        return;
    }

    if (req.method === 'POST' && req.url === '/alerts') {
        let body = '';
        for await (const chunk of req) body += chunk;
        try {
            const payload = JSON.parse(body);
            const r = await handleAlert(payload);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(r));
        } catch (err) {
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: err.message }));
        }
        return;
    }

    res.writeHead(404);
    res.end();
});

server.listen(PORT, () => console.log(`Webhook relay listening on ${PORT}`));
