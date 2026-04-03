/**
 * useAISStream — Real-time AIS vessel tracking hook
 * Connects to aisstream.io WebSocket API for live vessel positions.
 * Filters the Red Sea / Persian Gulf / Strait of Hormuz tactical area.
 *
 * Usage:
 *   const { vessels, connected } = useAISStream(apiKey);
 *
 * Free API keys at https://aisstream.io (no credit card required).
 */
import { useState, useEffect, useRef, useCallback } from 'react';

// Bounding boxes for the tactical area of interest (Red Sea + Persian Gulf + Horn of Africa)
const BOUNDING_BOXES = [
  // Red Sea + Suez
  [{ latitude_min: 11.0, latitude_max: 30.0, longitude_min: 32.0, longitude_max: 44.0 }],
  // Persian Gulf + Strait of Hormuz + Gulf of Oman
  [{ latitude_min: 22.0, latitude_max: 30.5, longitude_min: 47.0, longitude_max: 65.0 }],
  // Gulf of Aden + Horn of Africa
  [{ latitude_min: 10.0, latitude_max: 16.0, longitude_min: 43.0, longitude_max: 55.0 }],
];

// Ship type codes → display category
const SHIP_TYPE_MAP = {
  // Tankers
  80: 'oil_tanker', 81: 'oil_tanker', 82: 'oil_tanker', 83: 'oil_tanker', 84: 'oil_tanker', 89: 'oil_tanker',
  // Cargo
  70: 'cargo', 71: 'cargo', 72: 'cargo', 79: 'cargo',
  // Warships / Naval
  35: 'warship', 36: 'warship',
  // Passenger
  60: 'passenger', 69: 'passenger',
  // Tug / Special
  21: 'tug', 22: 'tug', 51: 'sar', 52: 'tug',
  // High Speed
  40: 'highspeed', 49: 'highspeed',
};

const SHIP_COLORS = {
  oil_tanker: '#eab308',
  warship: '#3b82f6',
  cargo: '#94a3b8',
  passenger: '#22c55e',
  tug: '#f97316',
  sar: '#ef4444',
  highspeed: '#a855f7',
  unknown: '#64748b',
};

const AIS_WS_URL = 'wss://stream.aisstream.io/v0/stream';
// Maximum number of vessels to render simultaneously (performance budget)
const MAX_VESSELS = 300;

export const useAISStream = (apiKey) => {
  const [vessels, setVessels] = useState({});
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);

  const connect = useCallback(() => {
    if (!apiKey) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(AIS_WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      // Subscribe to position reports for all bounding boxes
      ws.send(JSON.stringify({
        APIKey: apiKey,
        BoundingBoxes: BOUNDING_BOXES,
        FilterMessageTypes: ['PositionReport', 'ExtendedClassBPositionReport', 'StandardClassBPositionReport'],
      }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const msg = data.Message;
        if (!msg) return;

        // Get position report (could be one of several message types)
        const pos = msg.PositionReport || msg.ExtendedClassBPositionReport || msg.StandardClassBPositionReport;
        if (!pos) return;

        const mmsi = String(pos.UserID || pos.Mmsi);
        const lat = pos.Latitude;
        const lng = pos.Longitude;
        const sog = pos.Sog || 0; // Speed Over Ground (knots)
        const cog = pos.Cog || 0; // Course Over Ground (degrees)

        if (!lat || !lng || lat === 0 || lng === 0) return;

        const meta = data.MetaData || {};
        const shipType = msg.ShipInfo?.ShipType || 0;
        const category = SHIP_TYPE_MAP[shipType] || 'unknown';

        setVessels(prev => {
          // Evict oldest entries when budget exceeded
          let next = { ...prev, [mmsi]: {
            mmsi, lat, lng, sog, cog, category,
            name: meta.ShipName?.trim() || mmsi,
            flag: meta.MMSI_CountryCode || '',
            color: SHIP_COLORS[category],
            lastUpdate: Date.now(),
          }};

          const keys = Object.keys(next);
          if (keys.length > MAX_VESSELS) {
            // Remove the oldest vessel
            const oldest = keys.sort((a, b) => next[a].lastUpdate - next[b].lastUpdate)[0];
            delete next[oldest];
          }
          return next;
        });
      } catch (_) {}
    };

    ws.onerror = () => setConnected(false);

    ws.onclose = () => {
      setConnected(false);
      // Reconnect after 5s
      reconnectTimerRef.current = setTimeout(connect, 5000);
    };
  }, [apiKey]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  // Stale vessel cleanup — remove vessels not updated in 10 minutes
  useEffect(() => {
    const interval = setInterval(() => {
      const cutoff = Date.now() - 10 * 60 * 1000;
      setVessels(prev => {
        const next = { ...prev };
        Object.keys(next).forEach(k => { if (next[k].lastUpdate < cutoff) delete next[k]; });
        return next;
      });
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  return { vessels: Object.values(vessels), connected };
};

export { SHIP_COLORS };
