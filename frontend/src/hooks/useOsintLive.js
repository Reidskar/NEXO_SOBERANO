/**
 * useOsintLive — Live OSINT data hook for OmniGlobe
 * Polls NEXO backend for real-time GDELT conflict events, FIRMS thermal anomalies,
 * OpenSky military flights, and CRUCIX delta signals.
 *
 * Returns globe-ready arrays: conflictMarkers, thermalMarkers, liveFlights, driveMarkers
 */
import { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001';
const API_KEY  = import.meta.env.VITE_NEXO_API_KEY || '';

const headers = API_KEY ? { 'X-API-Key': API_KEY } : {};

// Degrees → radians
const toRad = deg => deg * Math.PI / 180;

// Simple bounding box check — only show markers in a visible tactical area
const isInTacticalArea = (lat, lng) =>
  lat >= -35 && lat <= 65 && lng >= -20 && lng <= 150;

// Parse GDELT events → globe conflict markers
const parseGdelt = (events = []) =>
  (Array.isArray(events) ? events : [])
    .filter(e => e.lat && e.lng && isInTacticalArea(e.lat, e.lng))
    .slice(0, 60)
    .map(e => ({
      id: e.id || `gdelt-${e.lat}-${e.lng}`,
      lat: parseFloat(e.lat),
      lng: parseFloat(e.lng),
      label: e.title || e.summary || 'GDELT Event',
      source: 'gdelt',
      severity: e.goldstein < -5 ? 'critical' : e.goldstein < 0 ? 'high' : 'medium',
      color: e.goldstein < -5 ? 'rgba(239,68,68,0.9)' : e.goldstein < 0 ? 'rgba(245,158,11,0.85)' : 'rgba(251,191,36,0.7)',
      ringColor: e.goldstein < -5 ? 'rgba(239,68,68,0.6)' : 'rgba(245,158,11,0.4)',
      ringSpeed: e.goldstein < -5 ? 12 : 6,
      size: e.goldstein < -5 ? 28 : 20,
    }));

// Parse FIRMS thermal anomalies → globe fire markers
const parseFirms = (fires = []) =>
  (Array.isArray(fires) ? fires : [])
    .filter(f => f.latitude && f.longitude && isInTacticalArea(f.latitude, f.longitude))
    .slice(0, 80)
    .map(f => ({
      id: `firms-${f.latitude}-${f.longitude}-${f.acq_date}`,
      lat: parseFloat(f.latitude),
      lng: parseFloat(f.longitude),
      label: `THERMAL: ${f.acq_date || 'Recent'} · FRP ${f.frp || '?'} MW`,
      source: 'firms',
      severity: f.frp > 200 ? 'critical' : 'medium',
      color: 'rgba(251,146,60,0.85)',
      ringColor: 'rgba(251,146,60,0.4)',
      ringSpeed: 4,
      size: Math.min(24, 12 + (f.frp || 10) / 20),
    }));

// Parse OpenSky flights → globe flight markers (military zones only)
const parseFlights = (flights = []) => {
  const states = Array.isArray(flights?.states) ? flights.states :
                 Array.isArray(flights) ? flights : [];
  return states
    .filter(f => {
      const lat = Array.isArray(f) ? f[6] : f.lat;
      const lng = Array.isArray(f) ? f[5] : f.lng;
      return lat && lng && isInTacticalArea(lat, lng);
    })
    .slice(0, 150)
    .map(f => {
      const isArr = Array.isArray(f);
      return {
        id: isArr ? f[0] : (f.icao || f.callsign),
        lat: parseFloat(isArr ? f[6] : f.lat),
        lng: parseFloat(isArr ? f[5] : f.lng),
        alt: parseFloat(isArr ? (f[7] || 0) / 1000000 : (f.altitude || 0) / 1000000),
        heading: parseFloat(isArr ? (f[10] || 0) : (f.heading || 0)),
        callsign: (isArr ? f[1] : f.callsign || '')?.trim(),
        source: 'opensky',
        color: '#06b6d4',
      };
    });
};

// Classify Drive document by keywords → tactical position
const classifyDriveDoc = (doc) => {
  const text = `${doc.name || ''} ${doc.description || ''}`.toLowerCase();
  // Geo keywords → approximate coordinates
  const GEO_MAP = {
    'ukraine': [49.0, 32.0], 'rusia': [55.7, 37.6], 'russia': [55.7, 37.6],
    'iran': [35.6, 51.4], 'israel': [31.7, 35.2], 'taiwan': [25.0, 121.5],
    'china': [35.0, 105.0], 'gaza': [31.5, 34.4], 'yemen': [15.3, 44.2],
    'siria': [34.8, 38.9], 'syria': [34.8, 38.9], 'irak': [33.3, 44.4],
    'iraq': [33.3, 44.4], 'corea': [37.5, 127.0], 'korea': [37.5, 127.0],
    'mar rojo': [20.0, 38.0], 'red sea': [20.0, 38.0], 'hormuz': [26.5, 56.3],
    'polonia': [52.2, 21.0], 'báltico': [57.0, 20.0], 'baltic': [57.0, 20.0],
    'sudan': [15.5, 32.5], 'sahel': [15.0, 10.0], 'mali': [12.6, -8.0],
    'venezuela': [6.4, -66.6], 'colombia': [4.7, -74.0],
  };
  for (const [key, coords] of Object.entries(GEO_MAP)) {
    if (text.includes(key)) {
      // Add small jitter to avoid stacking
      return [coords[0] + (Math.random() - 0.5) * 2, coords[1] + (Math.random() - 0.5) * 2];
    }
  }
  return null;
};

export const useOsintLive = (intervalMs = 90000) => {
  const [conflictMarkers, setConflictMarkers] = useState([]);
  const [thermalMarkers, setThermalMarkers]   = useState([]);
  const [liveFlights, setLiveFlights]         = useState([]);
  const [driveMarkers, setDriveMarkers]       = useState([]);
  const [lastSweep, setLastSweep]             = useState(null);
  const [loading, setLoading]                 = useState(false);
  const abortRef = useRef(null);

  const fetchAll = useCallback(async () => {
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();
    const { signal } = abortRef.current;

    setLoading(true);
    try {
      // Parallel fetch: threats (GDELT+FIRMS), flights, drive docs
      const [threatsRes, flightsRes, driveRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/osint/threats`, { headers, signal }),
        fetch(`${API_BASE}/api/osint/flights`, { headers, signal }),
        fetch(`${API_BASE}/api/drive/listar?max_resultados=30`, { headers, signal }),
      ]);

      // --- GDELT + FIRMS ---
      if (threatsRes.status === 'fulfilled' && threatsRes.value.ok) {
        const data = await threatsRes.value.json();
        setConflictMarkers(parseGdelt(data.conflict_events));
        setThermalMarkers(parseFirms(data.thermal_anomalies));
      }

      // --- OpenSky Flights ---
      if (flightsRes.status === 'fulfilled' && flightsRes.value.ok) {
        const data = await flightsRes.value.json();
        setLiveFlights(parseFlights(data.data || data));
      }

      // --- Google Drive OSINT docs ---
      if (driveRes.status === 'fulfilled' && driveRes.value.ok) {
        const data = await driveRes.value.json();
        const docs = Array.isArray(data) ? data : (data.archivos || data.files || []);
        const markers = docs
          .map(doc => {
            const coords = classifyDriveDoc(doc);
            if (!coords) return null;
            return {
              id: `drive-${doc.id || doc.name}`,
              lat: coords[0],
              lng: coords[1],
              label: doc.name || 'Doc OSINT',
              url: doc.webViewLink || doc.url || null,
              source: 'drive',
              color: 'rgba(139,92,246,0.9)',
              ringColor: 'rgba(139,92,246,0.4)',
              ringSpeed: 3,
              size: 18,
            };
          })
          .filter(Boolean);
        setDriveMarkers(markers);
      }

      setLastSweep(new Date());
    } catch (err) {
      if (err.name !== 'AbortError') console.error('[useOsintLive]', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const timer = setInterval(fetchAll, intervalMs);
    return () => {
      clearInterval(timer);
      abortRef.current?.abort();
    };
  }, [fetchAll, intervalMs]);

  return { conflictMarkers, thermalMarkers, liveFlights, driveMarkers, lastSweep, loading, refetch: fetchAll };
};
