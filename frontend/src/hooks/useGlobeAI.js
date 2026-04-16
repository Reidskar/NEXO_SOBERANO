/**
 * useGlobeAI — Real-time AI tactical alerts for OmniGlobe
 * Connects to NEXO backend via WebSocket (or polling fallback) to receive
 * AI-generated tactical intelligence alerts based on current globe state.
 *
 * Alerts appear in the globe ticker and can trigger animated rings/arcs.
 */
import { useCallback, useEffect, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8080";
const WS_BASE = API_BASE.replace(/^http/, "ws");
const API_KEY = import.meta.env.VITE_NEXO_API_KEY || "";

const MAX_ALERTS = 12;

// Classify alert → color and severity
const classifyAlert = (text = "") => {
  const t = text.toLowerCase();
  if (
    t.includes("ataque") ||
    t.includes("strike") ||
    t.includes("bomba") ||
    t.includes("misil")
  )
    return { severity: "critical", color: "#ef4444", prefix: "[STRIKE]" };
  if (
    t.includes("movimiento") ||
    t.includes("despliegue") ||
    t.includes("deploy") ||
    t.includes("naval")
  )
    return { severity: "high", color: "#f97316", prefix: "[MOVIMIENTO]" };
  if (
    t.includes("alerta") ||
    t.includes("alert") ||
    t.includes("riesgo") ||
    t.includes("rojo")
  )
    return { severity: "high", color: "#f59e0b", prefix: "[ALERTA]" };
  if (t.includes("drive") || t.includes("documento") || t.includes("osint"))
    return { severity: "medium", color: "#a855f7", prefix: "[DRIVE OSINT]" };
  return { severity: "low", color: "#22c55e", prefix: "[INTEL]" };
};

// Generate a synthetic alert from OSINT sweep data (fallback when no WS)
const buildSyntheticAlert = (sweepData) => {
  if (!sweepData) return null;
  const templates = [
    () =>
      `Actividad thermal detectada en ${sweepData.region || "zona táctica"} — ${sweepData.frp || "?"} MW`,
    () =>
      `GDELT registra ${sweepData.events || "+"} eventos de conflicto en últimas 2h`,
    () =>
      `OpenSky detecta ${sweepData.flights || "?"} vuelos militares sobre zonas estratégicas`,
    () => `Drive OSINT: nuevo documento geolocalizad — análisis IA en proceso`,
  ];
  const text = templates[Math.floor(Math.random() * templates.length)]();
  return { id: Date.now(), text, ts: new Date(), ...classifyAlert(text) };
};

// osintContext: { conflictCount, thermalCount, hotCities: ['Gaza', 'Kyiv', ...] }
export const useGlobeAI = (enabled = true, osintContext = null) => {
  const [alerts, setAlerts] = useState([]);
  const [connected, setConnected] = useState(false);
  const [wsMode, setWsMode] = useState(false); // true = WebSocket, false = polling
  const wsRef = useRef(null);
  const pollRef = useRef(null);

  const pushAlert = useCallback((text, extra = {}) => {
    const classified = classifyAlert(text);
    setAlerts((prev) =>
      [
        {
          id: Date.now() + Math.random(),
          text,
          ts: new Date(),
          ...classified,
          ...extra,
        },
        ...prev,
      ].slice(0, MAX_ALERTS),
    );
  }, []);

  // --- WebSocket path (NEXO stream endpoint) ---
  const connectWS = useCallback(() => {
    if (!enabled) return;
    try {
      const ws = new WebSocket(`${WS_BASE}/ws/alerts/demo`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setWsMode(true);
      };

      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          if (msg.tipo === "ai_alert" && msg.descripcion)
            pushAlert(msg.descripcion, msg);
          else if (msg.type === "alert" && msg.text) pushAlert(msg.text, msg);
        } catch (_) {}
      };

      ws.onerror = () => {
        setConnected(false);
        setWsMode(false);
        startPolling();
      };
      ws.onclose = () => {
        setConnected(false);
        startPolling();
      };
    } catch (_) {
      startPolling();
    }
  }, [enabled, pushAlert]);

  // --- Polling fallback: ask NEXO AI for a tactical brief ---
  const pollAI = useCallback(async () => {
    if (!enabled) return;
    try {
      // Construir prompt con contexto de ciudades activas
      const hotCities = osintContext?.hotCities?.slice(0, 4).join(", ") || "";
      const conflictCount = osintContext?.conflictCount || 0;
      const thermalCount = osintContext?.thermalCount || 0;

      const contextClause = hotCities
        ? `Ciudades con actividad GDELT ahora: ${hotCities}. Eventos activos: ${conflictCount} conflictos, ${thermalCount} anomalías térmicas. `
        : "";

      const question = `${contextClause}Genera 1 alerta táctica concreta a nivel CIUDAD (máx 25 palabras). Menciona una ciudad específica. SIEMPRE incluye al inicio el canal de noticias apropiado así: [MEDIA:UCNye-wNBqNL5ZzHSJj3l8Bg] para MedioOriente/Gaza/Yemen/Irán, [MEDIA:UCknLrEdhRCp1aegoMqRaCZg] para Europa/Rusia/Ucrania/Bielorrusia, [MEDIA:UChLtXXcb4uMD67reUmx_B6g] para Asia/Pacifico/Taiwan/Corea, [MEDIA:UCIvaNCsHSQplMbyxzWXBp1g] para África/Sahel. Solo el texto de la alerta, sin explicaciones.`;

      const res = await fetch(`${API_BASE}/api/ai/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
        },
        body: JSON.stringify({
          question,
          category: "omniglobe_tactical",
        }),
        signal: AbortSignal.timeout(15000),
      });
      if (res.ok) {
        const data = await res.json();
        let text = data.answer || data.response || "";
        if (text) {
          // Parsear [MEDIA:id]
          let media_url = null;
          const mediaMatch = text.match(/\[MEDIA:([^\]]+)\]/);
          if (mediaMatch) {
            const mediaId = mediaMatch[1];
            // Si tiene más de 15 caracteres asumimos que es un channelID, si es 11 es un Video de YouTube
            if (mediaId.length >= 15) {
              media_url = `https://www.youtube.com/embed/live_stream?channel=${mediaId}&autoplay=1&controls=1`;
            } else {
              media_url = `https://www.youtube.com/embed/${mediaId}?autoplay=1&controls=1`;
            }
            text = text.replace(/\[MEDIA:([^\]]+)\]/g, "").trim();
          }

          if (text.length > 5) {
            pushAlert(text, { media_url });
            setConnected(true);
          }
        }
      }
    } catch (_) {
      // Silent fail — globe still works without AI alerts
    }
  }, [enabled, pushAlert, osintContext]);

  const startPolling = useCallback(() => {
    clearInterval(pollRef.current);
    pollRef.current = null;
    setWsMode(false);
    pollAI(); // immediate first call
    pollRef.current = setInterval(pollAI, 35000); // every 35s con contexto actualizado
  }, [pollAI]);

  useEffect(() => {
    if (!enabled) return;
    connectWS();
    return () => {
      wsRef.current?.close();
      clearInterval(pollRef.current);
      pollRef.current = null;
    };
  }, [enabled, connectWS]);

  return { alerts, connected, wsMode, pushAlert };
};
