/**
 * useGlobeAI — Real-time AI tactical alerts for OmniGlobe
 *
 * Conecta al backend NEXO via WebSocket (o polling de respaldo) para recibir:
 * - Alertas tácticas generadas por IA basadas en el estado actual del globo.
 * - Eventos de Discord (cuando el usuario habla con la IA en Discord).
 * - Notificaciones de nuevos documentos en Drive.
 *
 * Las alertas alimentan el ticker del globo y pueden disparar anillos/arcos.
 */
import { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE  = API_BASE.replace(/^http/, 'ws');
const API_KEY  = import.meta.env.VITE_NEXO_API_KEY || '';

const MAX_ALERTS  = 15;
const MAX_DISCORD = 20;
const MAX_DRIVE   = 20;

// Classify alert text → severity + color + prefix
const classifyAlert = (text = '') => {
  const t = text.toLowerCase();
  if (t.includes('ataque') || t.includes('strike') || t.includes('bomba') || t.includes('misil') || t.includes('missile'))
    return { severity: 'critical', color: '#ef4444', prefix: '[STRIKE]' };
  if (t.includes('movimiento') || t.includes('despliegue') || t.includes('deploy') || t.includes('naval'))
    return { severity: 'high',     color: '#f97316', prefix: '[MOVIMIENTO]' };
  if (t.includes('alerta') || t.includes('alert') || t.includes('riesgo') || t.includes('rojo'))
    return { severity: 'high',     color: '#f59e0b', prefix: '[ALERTA]' };
  if (t.includes('discord'))
    return { severity: 'medium',   color: '#5865f2', prefix: '[DISCORD]' };
  if (t.includes('drive') || t.includes('documento') || t.includes('osint'))
    return { severity: 'medium',   color: '#a855f7', prefix: '[DRIVE OSINT]' };
  return { severity: 'low',        color: '#22c55e', prefix: '[INTEL]' };
};

// osintContext: { conflictCount, thermalCount, hotCities: ['Gaza', 'Kyiv', ...] }
export const useGlobeAI = (enabled = true, osintContext = null) => {
  const [alerts, setAlerts]               = useState([]);
  const [connected, setConnected]         = useState(false);
  const [wsMode, setWsMode]               = useState(false);
  // Separate feeds for Drive and Discord activity (shown in HUD panels)
  const [discordActivity, setDiscordActivity] = useState([]);
  const [driveActivity, setDriveActivity]     = useState([]);

  const wsRef     = useRef(null);
  const pollRef   = useRef(null);
  const osintRef  = useRef(osintContext);
  useEffect(() => { osintRef.current = osintContext; }, [osintContext]);

  const pushAlert = useCallback((text, extra = {}) => {
    const classified = classifyAlert(text);
    const entry = {
      id: Date.now() + Math.random(),
      text,
      ts: new Date(),
      ...classified,
      ...extra,
    };
    setAlerts(prev => [entry, ...prev].slice(0, MAX_ALERTS));
    return entry;
  }, []);

  // ─── WebSocket main channel (/ws/alerts/demo) ────────────────────────────
  const connectWS = useCallback(() => {
    if (!enabled) return;
    try {
      const ws = new WebSocket(`${WS_BASE}/ws/alerts/demo`);
      wsRef.current = ws;

      ws.onopen = () => { setConnected(true); setWsMode(true); };

      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);

          // Tactical simulation events (handled by OmniGlobe.jsx directly, but also push alert)
          if (msg.tipo === 'TACTICAL_SIMULATION' && msg.descripcion) {
            pushAlert(msg.descripcion, { color: '#ef4444', prefix: '[SIM]', ...msg });
            return;
          }

          // Standard ai_alert
          if (msg.tipo === 'ai_alert' && msg.descripcion) {
            pushAlert(msg.descripcion, msg);
            return;
          }
          if (msg.type === 'alert' && msg.text) {
            pushAlert(msg.text, msg);
            return;
          }

          // Discord activity events (forwarded via backend webhook)
          if (msg.tipo === 'discord_message' || msg.source === 'discord') {
            const entry = {
              id: msg.id || Date.now(),
              text: msg.content || msg.text || msg.descripcion || '',
              ts: msg.ts || new Date().toISOString(),
              prefix: '[DISCORD]',
              color: '#5865f2',
              author: msg.author || msg.username || 'NEXO-BOT',
            };
            setDiscordActivity(prev => [entry, ...prev].slice(0, MAX_DISCORD));
            // Also push to main ticker with Discord prefix
            pushAlert(`Discord: ${entry.text}`, { color: '#5865f2', prefix: '[DISCORD]' });
            return;
          }

          // Drive upload / new document events
          if (msg.tipo === 'drive_update' || msg.source === 'drive') {
            const entry = {
              id: msg.id || Date.now(),
              text: msg.name || msg.nombre || msg.title || msg.descripcion || 'Nuevo documento',
              label: msg.name || msg.nombre || msg.title || '',
              ts: msg.ts || new Date().toISOString(),
              lat: msg.lat, lng: msg.lng,
              prefix: '[DRIVE]',
              color: '#a855f7',
              webViewLink: msg.webViewLink,
            };
            setDriveActivity(prev => [entry, ...prev].slice(0, MAX_DRIVE));
            pushAlert(`Drive: ${entry.text}`, { color: '#a855f7', prefix: '[DRIVE]', lat: msg.lat, lng: msg.lng });
            return;
          }
        } catch (_) {}
      };

      ws.onerror = () => { setConnected(false); setWsMode(false); startPolling(); };
      ws.onclose = () => { setConnected(false); startPolling(); };
    } catch (_) {
      startPolling();
    }
  }, [enabled, pushAlert]);

  // ─── Polling fallback: ask NEXO AI for a tactical brief ─────────────────
  const pollAI = useCallback(async () => {
    if (!enabled) return;
    const ctx = osintRef.current;
    try {
      const hotCities    = ctx?.hotCities?.slice(0, 4).join(', ') || '';
      const conflictCount = ctx?.conflictCount || 0;
      const thermalCount  = ctx?.thermalCount  || 0;

      const contextClause = hotCities
        ? `Ciudades con actividad GDELT ahora: ${hotCities}. Eventos activos: ${conflictCount} conflictos, ${thermalCount} anomalías térmicas. `
        : '';

      const question = `${contextClause}Genera 1 alerta táctica concreta a nivel CIUDAD (máx 25 palabras). Menciona una ciudad específica. SIEMPRE incluye al inicio el canal de noticias apropiado así: [MEDIA:UCNye-wNBqNL5ZzHSJj3l8Bg] para MedioOriente/Gaza/Yemen/Irán, [MEDIA:UCknLrEdhRCp1aegoMqRaCZg] para Europa/Rusia/Ucrania/Bielorrusia, [MEDIA:UChLtXXcb4uMD67reUmx_B6g] para Asia/Pacifico/Taiwan/Corea, [MEDIA:UCIvaNCsHSQplMbyxzWXBp1g] para África/Sahel. Solo el texto de la alerta, sin explicaciones.`;

      const res = await fetch(`${API_BASE}/api/ai/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
        },
        body: JSON.stringify({ question, category: 'omniglobe_tactical' }),
        signal: AbortSignal.timeout(18000),
      });

      if (res.ok) {
        const data = await res.json();
        let text = data.answer || data.response || '';
        if (text) {
          let media_url = null;
          const mediaMatch = text.match(/\[MEDIA:([^\]]+)\]/);
          if (mediaMatch) {
            const mediaId = mediaMatch[1];
            media_url = mediaId.length >= 15
              ? `https://www.youtube.com/embed/live_stream?channel=${mediaId}&autoplay=1&controls=1`
              : `https://www.youtube.com/embed/${mediaId}?autoplay=1&controls=1`;
            text = text.replace(/\[MEDIA:([^\]]+)\]/g, '').trim();
          }
          if (text.length > 5) {
            pushAlert(text, { media_url });
            setConnected(true);
          }
        }
      }
    } catch (_) {}
  }, [enabled, pushAlert]);

  // ─── Polling: also check Drive for new documents ─────────────────────────
  const pollDrive = useCallback(async () => {
    if (!enabled) return;
    try {
      const res = await fetch(`${API_BASE}/api/drive/listar`, {
        headers: { ...(API_KEY ? { 'X-API-Key': API_KEY } : {}) },
        signal: AbortSignal.timeout(10000),
      });
      if (res.ok) {
        const data = await res.json();
        const files = data.archivos || data.files || data.documents || [];
        if (files.length > 0) {
          setDriveActivity(prev => {
            const existingIds = new Set(prev.map(d => d.id));
            const newDocs = files
              .filter(f => !existingIds.has(f.id))
              .map(f => ({
                id: f.id,
                text: f.name || f.nombre || f.title || 'Sin nombre',
                label: f.name || f.nombre || f.title || '',
                ts: f.modifiedTime || f.createdTime || new Date().toISOString(),
                prefix: '[DRIVE]',
                color: '#a855f7',
                webViewLink: f.webViewLink,
              }));
            if (newDocs.length > 0) {
              // Batch alert to avoid ticker spam
              const alertText = newDocs.length === 1
                ? `Nuevo doc en Drive: ${newDocs[0].text}`
                : `${newDocs.length} nuevos documentos en Drive — análisis IA en proceso`;
              pushAlert(alertText, { color: '#a855f7', prefix: '[DRIVE]' });
              return [...newDocs, ...prev].slice(0, MAX_DRIVE);
            }
            return prev;
          });
        }
      }
    } catch (_) {}
  }, [enabled, pushAlert]);

  const startPolling = useCallback(() => {
    clearInterval(pollRef.current);
    setWsMode(false);
    // Immediate first poll for both AI and Drive
    pollAI();
    pollDrive();
    // Alternate: AI every 35s, Drive every 2 AI cycles (~70s)
    // Use a simple counter that resets at 2 to avoid integer overflow
    let driveTick = 0;
    pollRef.current = setInterval(() => {
      pollAI();
      driveTick = (driveTick + 1) % 2;
      if (driveTick === 0) pollDrive();
    }, 35000);
  }, [pollAI, pollDrive]);

  useEffect(() => {
    if (!enabled) return;
    connectWS();
    // Also poll Drive periodically even when WS is connected
    const driveInterval = setInterval(pollDrive, 90000);
    return () => {
      wsRef.current?.close();
      clearInterval(pollRef.current);
      clearInterval(driveInterval);
      pollRef.current = null;
    };
  }, [enabled, connectWS, pollDrive]);

  return { alerts, connected, wsMode, pushAlert, discordActivity, driveActivity };
};
