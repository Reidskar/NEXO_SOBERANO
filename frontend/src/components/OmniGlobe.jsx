import { useRef, useState, useEffect, useCallback, useMemo } from 'react';
import Globe from 'react-globe.gl';
import { POWER_PLANTS, FUEL_CONFIG, STATUS_CONFIG, calcOutageImpact, COUNTRY_NAMES } from '../data/infrastructure';

// ─── WS URL ───────────────────────────────────────────────────────────────────
const WS_URL = (() => {
  // Auto-detect: Vite proxy in dev, real domain in prod
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const backendHost = import.meta.env.VITE_BACKEND_URL
    ? import.meta.env.VITE_BACKEND_URL.replace(/^https?:\/\//, '')
    : location.host;
  return `${proto}://${backendHost}/ws/alerts/globe`;
})();

// API base — relative in prod (same origin), Vite proxy in dev
const API_BASE = import.meta.env.VITE_BACKEND_URL || '';

// ─── SEVERITY → RGB ───────────────────────────────────────────────────────────
const SEV_RGB = {
  CRITICAL: [239, 68,  68 ],
  HIGH:     [249, 115, 22 ],
  MODERATE: [245, 158, 11 ],
  MONITOR:  [0,   229, 255],
};
const SEV_PERIOD = { CRITICAL: 800, HIGH: 1000, MODERATE: 1300, MONITOR: 1600 };
const SEV_RAD    = { CRITICAL: 0.14, HIGH: 0.10, MODERATE: 0.08, MONITOR: 0.06 };

// ─── MOCK DATA ────────────────────────────────────────────────────────────────

const VESSELS = [
  { id: 'v01', cat: 'vessel', type: 'MILITARY',   name: 'USS GERALD R. FORD',      flag: 'US', lat: 36.5,   lng: 15.2,   mmsi: '338234567', imo: 'N/A',     speed: 18.3, course: 245, dest: 'NAPLES',    eta: '04 Apr 09:00', size: '333m × 77m',  draft: '12.0m', color: '#ef4444' },
  { id: 'v02', cat: 'vessel', type: 'MILITARY',   name: 'HMS PRINCE OF WALES',      flag: 'GB', lat: 48.2,   lng: -7.1,   mmsi: '235096837', imo: 'N/A',     speed: 14.1, course: 190, dest: 'BREST',    eta: '05 Apr 18:00', size: '284m × 70m',  draft: '11.0m', color: '#ef4444' },
  { id: 'v03', cat: 'vessel', type: 'MILITARY',   name: 'RFS MOSKVA (REPLICA)',     flag: 'RU', lat: 45.1,   lng: 31.4,   mmsi: '273352980', imo: 'N/A',     speed: 6.2,  course: 90,  dest: 'NOVOROSSIYSK', eta: 'N/A',       size: '186m × 20m',  draft: '7.9m',  color: '#ef4444' },
  { id: 'v04', cat: 'vessel', type: 'CARGO',      name: 'ARKLOW FERN',              flag: 'IE', lat: 51.15,  lng: 1.52,   mmsi: '250802173', imo: '9527661', speed: 8.1,  course: 234, dest: 'IEFOV',   eta: '04 Apr 13:00', size: '90m × 14m',   draft: '6.3m',  color: '#00e5ff' },
  { id: 'v05', cat: 'vessel', type: 'CARGO',      name: 'EVER ACE',                 flag: 'PA', lat: 37.8,   lng: 32.0,   mmsi: '357488000', imo: '9810563', speed: 14.2, course: 180, dest: 'PORT SAID', eta: '06 Apr 08:00', size: '400m × 62m',  draft: '15.5m', color: '#00e5ff' },
  { id: 'v06', cat: 'vessel', type: 'CARGO',      name: 'MSC GÜLSÜN',              flag: 'PA', lat: 5.2,    lng: 103.8,  mmsi: '370773000', imo: '9811000', speed: 16.4, course: 270, dest: 'SINGAPORE', eta: '03 Apr 22:00', size: '400m × 62m',  draft: '16.0m', color: '#00e5ff' },
  { id: 'v07', cat: 'vessel', type: 'TANKER',     name: 'HORMUZ TITAN I',           flag: 'IR', lat: 26.6,   lng: 56.5,   mmsi: '422134500', imo: '9421030', speed: 3.2,  course: 145, dest: 'BANDAR ABBAS', eta: 'ANCHORED', size: '332m × 58m', draft: '20.0m', color: '#f97316' },
  { id: 'v08', cat: 'vessel', type: 'TANKER',     name: 'GULF PRIDE',               flag: 'SA', lat: 24.5,   lng: 54.3,   mmsi: '403234100', imo: '9312044', speed: 11.2, course: 315, dest: 'ROTTERDAM', eta: '20 Apr 06:00', size: '310m × 55m',  draft: '18.5m', color: '#f97316' },
  { id: 'v09', cat: 'vessel', type: 'TANKER',     name: 'PETRO OLYMPUS',            flag: 'GR', lat: 22.8,   lng: 63.1,   mmsi: '241234560', imo: '9433221', speed: 13.8, course: 280, dest: 'ROTTERDAM', eta: '18 Apr 12:00', size: '290m × 52m',  draft: '17.0m', color: '#f97316' },
  { id: 'v10', cat: 'vessel', type: 'TANKER',     name: 'LNG CHALLENGER',           flag: 'MH', lat: 25.9,   lng: 57.2,   mmsi: '538123456', imo: '9500123', speed: 7.5,  course: 60,  dest: 'TOKYO',   eta: '15 Apr 08:00', size: '295m × 46m',  draft: '11.5m', color: '#f97316' },
  { id: 'v11', cat: 'vessel', type: 'PASSENGER',  name: 'MSC VIRTUOSA',             flag: 'PA', lat: 43.2,   lng: 5.3,    mmsi: '215678900', imo: '9741471', speed: 19.2, course: 270, dest: 'BARCELONA', eta: '04 Apr 07:00', size: '332m × 43m',  draft: '8.9m',  color: '#60a5fa' },
  { id: 'v12', cat: 'vessel', type: 'CARGO',      name: 'COSCO SHIPPING UNIVERSE',  flag: 'CN', lat: 31.2,   lng: 121.8,  mmsi: '477123456', imo: '9786028', speed: 17.1, course: 90,  dest: 'LONG BEACH', eta: '12 Apr 10:00', size: '400m × 58m',  draft: '16.0m', color: '#00e5ff' },
  { id: 'v13', cat: 'vessel', type: 'MILITARY',   name: 'USS RONALD REAGAN',        flag: 'US', lat: 20.5,   lng: 120.3,  mmsi: '338901234', imo: 'N/A',     speed: 22.0, course: 180, dest: 'YOKOSUKA', eta: 'CLASSIFIED',  size: '333m × 77m',  draft: '12.0m', color: '#ef4444' },
  { id: 'v14', cat: 'vessel', type: 'CARGO',      name: 'OOCL HONG KONG',           flag: 'HK', lat: 1.3,    lng: 104.0,  mmsi: '477000200', imo: '9776171', speed: 15.3, course: 315, dest: 'ROTTERDAM', eta: '22 Apr 14:00', size: '400m × 59m',  draft: '15.5m', color: '#00e5ff' },
  { id: 'v15', cat: 'vessel', type: 'TANKER',     name: 'ARCTIC DISCOVERER',        flag: 'NO', lat: 70.2,   lng: 25.8,   mmsi: '257123400', imo: '9812301', speed: 10.4, course: 135, dest: 'ROTTERDAM', eta: '10 Apr 20:00', size: '280m × 44m',  draft: '13.0m', color: '#f97316' },
];

const AIRCRAFT = [
  { id: 'a01', cat: 'aircraft', type: 'RECON',   name: 'RQ-4B GLOBAL HAWK',  callsign: 'FORTE10',  lat: 43.2,  lng: 34.5,  alt: 60000, speed: 340, org: 'SIGONELLA',   dest: 'BLACK SEA PATROL', color: '#f59e0b' },
  { id: 'a02', cat: 'aircraft', type: 'SIGINT',  name: 'RC-135W RIVET JOINT', callsign: 'JAKE21',   lat: 52.4,  lng: 20.1,  alt: 35000, speed: 485, org: 'MILDENHALL',  dest: 'UKRAINE BORDER',  color: '#f59e0b' },
  { id: 'a03', cat: 'aircraft', type: 'PATROL',  name: 'P-8A POSEIDON',       callsign: 'NEPTUNE3', lat: 48.5,  lng: -20.3, alt: 25000, speed: 490, org: 'LAJES',       dest: 'ASW ATLANTIC',    color: '#34d399' },
  { id: 'a04', cat: 'aircraft', type: 'CARGO',   name: 'C-17A GLOBEMASTER',   callsign: 'RCH497',   lat: 51.5,  lng: 7.8,   alt: 38000, speed: 520, org: 'RAMSTEIN AB', dest: 'RZESZÓW',         color: '#a78bfa' },
  { id: 'a05', cat: 'aircraft', type: 'BOMBER',  name: 'B-52H STRATOFORTRESS',callsign: 'BONE21',   lat: 52.8,  lng: -1.2,  alt: 42000, speed: 610, org: 'RAF FAIRFORD', dest: 'NATO EXERCISE',   color: '#f59e0b' },
  { id: 'a06', cat: 'aircraft', type: 'RECON',   name: 'U-2S DRAGON LADY',    callsign: 'DRAGON44', lat: 38.1,  lng: 46.2,  alt: 70000, speed: 690, org: 'AL DHAFRA',   dest: 'IRAN ISR ORBIT',  color: '#f59e0b' },
  { id: 'a07', cat: 'aircraft', type: 'PATROL',  name: 'P-3C ORION',          callsign: 'IRON77',   lat: 36.2,  lng: 18.5,  alt: 22000, speed: 410, org: 'SIGONELLA',   dest: 'MED SUBMARINE',   color: '#34d399' },
  { id: 'a08', cat: 'aircraft', type: 'CARGO',   name: 'AN-124 RUSLAN',       callsign: 'RFF2241',  lat: 55.7,  lng: 37.9,  alt: 33000, speed: 865, org: 'ZHUKOVSKY',   dest: 'KALININGRAD',     color: '#a78bfa' },
];

const EVENTS = [
  { id: 'e01', name: 'CIERRE ESTRECHO DE HORMUZ', lat: 26.58,  lng: 56.50,  severity: 'CRITICAL', radiusDeg: 0.14, r: 239, g: 68,  b: 68,  desc: 'Cierre total por escalada US-Iran. 1.6 Mt/mes de combustible de aviación fuera del mercado.', period: 800  },
  { id: 'e02', name: 'CONFLICTO GAZA',            lat: 31.52,  lng: 34.45,  severity: 'CRITICAL', radiusDeg: 0.06, r: 239, g: 68,  b: 68,  desc: 'Operaciones terrestres activas. Infraestructura civil comprometida.', period: 700  },
  { id: 'e03', name: 'FRENTE DONBÁS',             lat: 48.00,  lng: 37.80,  severity: 'HIGH',     radiusDeg: 0.10, r: 249, g: 115, b: 22,  desc: 'Actividad artillería elevada. Avance reportado en sector norte.', period: 1000 },
  { id: 'e04', name: 'TENSIÓN TAIWAN STRAIT',     lat: 24.50,  lng: 120.00, severity: 'HIGH',     radiusDeg: 0.12, r: 249, g: 115, b: 22,  desc: 'Ejercicios PLAN en ambos lados del estrecho. 12 fragatas desplegadas.', period: 1100 },
  { id: 'e05', name: 'ACTIVIDAD RF BÁLTICO',      lat: 58.50,  lng: 21.00,  severity: 'MODERATE', radiusDeg: 0.09, r: 245, g: 158, b: 11,  desc: 'Proliferación señales GPS spoofing. Afecta rutas aéreas civiles.', period: 1300 },
  { id: 'e06', name: 'CRISIS SAHEL',              lat: 14.50,  lng: 1.50,   severity: 'MODERATE', radiusDeg: 0.11, r: 245, g: 158, b: 11,  desc: 'Avance grupos armados en región fronteriza Mali-Níger. MINUSMA retirada.', period: 1400 },
  { id: 'e07', name: 'CANAL DE SUEZ — MONITOR',   lat: 30.60,  lng: 32.35,  severity: 'MONITOR',  radiusDeg: 0.07, r: 0,   g: 229, b: 255, desc: 'Tráfico normal. Control reforzado post-conflicto Gaza.', period: 1600 },
  { id: 'e08', name: 'MAR DE CHINA SUR — FIERY', lat: 9.55,   lng: 112.88, severity: 'HIGH',     radiusDeg: 0.08, r: 249, g: 115, b: 22,  desc: 'Construcción instalaciones PLA en Fiery Cross Reef. Zona disputada.', period: 1050 },
];

const ARCS = [
  { id: 'arc01', name: 'Bloqueo combustible aviación',    startLat: 26.58, startLng: 56.50, endLat: 51.9,  endLng: 4.5,    colorStart: '#ef4444', colorEnd: '#f97316', stroke: 0.7, dash: 0.35, gap: 0.15, anim: 1800 },
  { id: 'arc02', name: 'Ruta LNG Asia-Pacífico',          startLat: 25.90, startLng: 57.20, endLat: 35.7,  endLng: 139.7,  colorStart: '#f97316', colorEnd: '#60a5fa', stroke: 0.5, dash: 0.4,  gap: 0.2,  anim: 2400 },
  { id: 'arc03', name: 'Airlift OTAN Ramstein→Rzeszów',   startLat: 49.44, startLng: 7.60,  endLat: 50.11, endLng: 22.01,  colorStart: '#a78bfa', colorEnd: '#60a5fa', stroke: 0.5, dash: 0.3,  gap: 0.1,  anim: 1500 },
  { id: 'arc04', name: 'Ruta logística Beijing→Malacca',  startLat: 39.91, startLng: 116.4, endLat: 1.35,  endLng: 103.8,  colorStart: '#ef4444', colorEnd: '#f97316', stroke: 0.4, dash: 0.4,  gap: 0.2,  anim: 2000 },
  { id: 'arc05', name: 'Corredor militar Moscú→Kalinin',  startLat: 55.75, startLng: 37.62, endLat: 54.71, endLng: 20.51,  colorStart: '#ef4444', colorEnd: '#ef4444', stroke: 0.5, dash: 0.3,  gap: 0.12, anim: 1600 },
  { id: 'arc06', name: 'Suministros AUKUS',               startLat: 33.87, startLng: -118.2, endLat: -33.9, endLng: 151.2, colorStart: '#60a5fa', colorEnd: '#34d399', stroke: 0.4, dash: 0.5,  gap: 0.25, anim: 2800 },
];

// ─── HELPERS ──────────────────────────────────────────────────────────────────

const ALL_POINTS = [
  ...VESSELS.map(v => ({ ...v, radius: v.type === 'MILITARY' ? 0.55 : 0.4 })),
  ...AIRCRAFT.map(a => ({ ...a, radius: 0.35 })),
];

const SEVERITY_BADGE = {
  CRITICAL: 'bg-red-900/60 text-red-400 border-red-700',
  HIGH:     'bg-orange-900/60 text-orange-400 border-orange-700',
  MODERATE: 'bg-amber-900/60 text-amber-400 border-amber-700',
  MONITOR:  'bg-cyan-900/60 text-cyan-400 border-cyan-700',
};

function DetailPanel({ entity, onClose }) {
  if (!entity) return null;

  const isVessel = entity.cat === 'vessel';
  const isAircraft = entity.cat === 'aircraft';
  const isEvent = entity.cat === 'event';

  return (
    <div style={{
      position: 'absolute', top: 12, right: 12, zIndex: 20,
      background: 'rgba(13,20,33,0.97)', border: '1px solid #1a2540',
      borderRadius: 10, padding: '14px 16px', width: 270,
      fontFamily: "'JetBrains Mono', 'Courier New', monospace",
      backdropFilter: 'blur(8px)',
      boxShadow: '0 4px 32px rgba(0,0,0,0.6)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <div>
          <div style={{ fontSize: 11, color: entity.color || '#00e5ff', fontWeight: 700, letterSpacing: '0.05em' }}>
            {isVessel ? `⛵ ${entity.type}` : isAircraft ? `✈ ${entity.type}` : `⚠ ${entity.severity}`}
          </div>
          <div style={{ fontSize: 13, color: '#e2e8f0', fontWeight: 700, marginTop: 3, lineHeight: 1.3 }}>{entity.name}</div>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 16, padding: '0 0 0 8px' }}>✕</button>
      </div>

      <div style={{ borderTop: '1px solid #1a2540', paddingTop: 10 }}>
        {isVessel && (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, color: '#94a3b8' }}>
            <tbody>
              {[['MMSI', entity.mmsi], ['IMO', entity.imo], ['FLAG', entity.flag], ['SPEED', `${entity.speed} kts`], ['COURSE', `${entity.course}°`], ['DEST', entity.dest], ['ETA', entity.eta], ['SIZE', entity.size], ['DRAFT', entity.draft]].map(([k, v]) => (
                <tr key={k}>
                  <td style={{ padding: '2px 0', color: '#475569', width: '40%' }}>{k}</td>
                  <td style={{ padding: '2px 0', color: '#cbd5e1' }}>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {isAircraft && (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, color: '#94a3b8' }}>
            <tbody>
              {[['CALLSIGN', entity.callsign], ['ALT', `${entity.alt.toLocaleString()} ft`], ['SPEED', `${entity.speed} kts`], ['FROM', entity.org], ['MISSION', entity.dest]].map(([k, v]) => (
                <tr key={k}>
                  <td style={{ padding: '2px 0', color: '#475569', width: '40%' }}>{k}</td>
                  <td style={{ padding: '2px 0', color: '#cbd5e1' }}>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {isEvent && (
          <>
            <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.6 }}>{entity.desc}</div>
            <div style={{ marginTop: 8, fontSize: 10, color: '#475569' }}>
              📍 {entity.lat.toFixed(2)}°, {entity.lng.toFixed(2)}°
            </div>
          </>
        )}
        {entity.cat === 'infra' && (() => {
          const impact = calcOutageImpact(entity);
          const cfg = FUEL_CONFIG[entity.fuel] || FUEL_CONFIG.Other;
          return (
            <>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, color: '#94a3b8' }}>
                <tbody>
                  {[
                    ['COUNTRY', COUNTRY_NAMES[entity.country] || entity.country],
                    ['FUEL', `${entity.fuelIcon} ${entity.fuel}`],
                    ['CAPACITY', `${entity.capacity_mw?.toLocaleString()} MW`],
                    ['STATUS', entity.statusLabel],
                    ['DAMAGE', `${entity.damage_pct || 0}%`],
                    ['THREAT LVL', cfg.threat],
                    ['OUTAGE RADIUS', `~${Math.round(impact.outage_radius_km)} km`],
                    ['POP AFFECTED', `~${impact.affected_people.toLocaleString()}`],
                  ].map(([k, v]) => (
                    <tr key={k}>
                      <td style={{ padding: '2px 0', color: '#475569', width: '45%' }}>{k}</td>
                      <td style={{ padding: '2px 0', color: '#cbd5e1' }}>{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {entity.notes && (
                <div style={{ marginTop: 8, fontSize: 10, color: '#64748b', lineHeight: 1.5, borderTop: '1px solid #1a2540', paddingTop: 6 }}>
                  {entity.notes}
                </div>
              )}
            </>
          );
        })()}
      </div>
    </div>
  );
}

// ─── MAIN COMPONENT ───────────────────────────────────────────────────────────

export default function OmniGlobe({ height = 600 }) {
  const globeRef = useRef();
  const containerRef = useRef();
  const [selected, setSelected]   = useState(null);
  const [dims, setDims]           = useState({ w: 800, h: 600 });
  const [layers, setLayers]       = useState({ vessels: true, aircraft: true, events: true, arcs: true, infrastructure: true });

  // ── Dynamic AI-controlled state ─────────────────────────────────────────────
  const [dynEvents, setDynEvents]         = useState([]);  // extra events added by AI
  const [dynArcs,   setDynArcs]           = useState([]);  // extra arcs
  const [dynPoints, setDynPoints]         = useState([]);  // extra points
  const [infraOverride, setInfraOverride] = useState({}); // { id: { status, damage_pct } }
  const [narrative, setNarrative]         = useState(''); // overlay text
  const [narrativeVisible, setNarrVisible]= useState(false);
  const [highlightId, setHighlightId]     = useState(null);

  // ── Responsive sizing ────────────────────────────────────────────────────────
  useEffect(() => {
    const obs = new ResizeObserver(entries => {
      const { width, height: h } = entries[0].contentRect;
      if (width > 0 && h > 0) setDims({ w: Math.floor(width), h: Math.floor(h) });
    });
    if (containerRef.current) obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  // ── WebSocket — AI Globe Command Receiver ─────────────────────────────────
  useEffect(() => {
    if (!WS_URL) return;
    let ws = null;
    let retryTimer = null;
    let retryDelay = 2000;

    const connect = () => {
      try {
        ws = new WebSocket(WS_URL);
        ws.onopen  = () => { retryDelay = 2000; };
        ws.onclose = () => { retryTimer = setTimeout(connect, retryDelay); retryDelay = Math.min(retryDelay * 2, 30000); };
        ws.onerror = () => ws.close();
        ws.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data);
            if (msg?.channel === 'globe_command') handleCommand(msg.payload);
          } catch {}
        };
      } catch { retryTimer = setTimeout(connect, retryDelay); }
    };

    // Also poll /api/globe/poll every 4s as WebSocket fallback
    let lastTs = new Date().toISOString();
    const poll = setInterval(async () => {
      try {
        const r = await fetch(`${API_BASE}/api/globe/poll?since=${encodeURIComponent(lastTs)}`);
        const d = await r.json();
        if (d.commands?.length) {
          d.commands.forEach(c => handleCommand(c));
          lastTs = d.commands[d.commands.length - 1]._ts || lastTs;
        }
      } catch {}
    }, 4000);

    connect();
    return () => { ws?.close(); clearTimeout(retryTimer); clearInterval(poll); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Command handler called by WS / poll ──────────────────────────────────
  const handleCommand = useCallback((cmd) => {
    if (!cmd?.type) return;
    const g = globeRef.current;

    switch (cmd.type) {
      case 'fly_to':
        if (g && cmd.lat != null && cmd.lng != null) {
          g.controls().autoRotate = false;
          g.pointOfView({ lat: cmd.lat, lng: cmd.lng, altitude: cmd.altitude ?? 1.5 }, cmd.duration ?? 1200);
        }
        break;

      case 'add_event':
        if (!cmd.id) break;
        setDynEvents(prev => {
          const filtered = prev.filter(e => e.id !== cmd.id);
          const rgb = SEV_RGB[cmd.severity] ?? [245, 158, 11];
          return [...filtered, {
            id: cmd.id, name: cmd.name || cmd.id, cat: 'event',
            lat: cmd.lat, lng: cmd.lng,
            severity: cmd.severity || 'HIGH',
            radiusDeg: cmd.radius_deg ?? SEV_RAD[cmd.severity] ?? 0.09,
            r: cmd.r ?? rgb[0], g: cmd.g ?? rgb[1], b: cmd.b ?? rgb[2],
            desc: cmd.desc || '', period: SEV_PERIOD[cmd.severity] ?? 1000,
          }];
        });
        break;

      case 'remove_event':
        setDynEvents(prev => prev.filter(e => e.id !== cmd.id));
        break;

      case 'update_infra':
        if (cmd.id) setInfraOverride(prev => ({ ...prev, [cmd.id]: { status: cmd.status, damage_pct: cmd.damage_pct } }));
        break;

      case 'add_arc':
        if (!cmd.id) break;
        setDynArcs(prev => {
          const filtered = prev.filter(a => a.id !== cmd.id);
          return [...filtered, {
            id: cmd.id, name: cmd.name || cmd.id,
            startLat: cmd.start_lat, startLng: cmd.start_lng,
            endLat: cmd.end_lat,     endLng: cmd.end_lng,
            colorStart: cmd.color_start || '#ef4444',
            colorEnd:   cmd.color_end   || '#f97316',
            stroke: cmd.stroke ?? 0.6, dash: 0.35, gap: 0.15, anim: 1800,
          }];
        });
        break;

      case 'remove_arc':
        setDynArcs(prev => prev.filter(a => a.id !== cmd.id));
        break;

      case 'add_point':
        if (!cmd.id) break;
        setDynPoints(prev => {
          const filtered = prev.filter(p => p.id !== cmd.id);
          return [...filtered, {
            id: cmd.id, name: cmd.name || cmd.id, cat: cmd.cat || 'point',
            lat: cmd.lat, lng: cmd.lng,
            color: cmd.color || '#00e5ff', radius: 0.45,
            notes: cmd.notes || '',
          }];
        });
        break;

      case 'remove_point':
        setDynPoints(prev => prev.filter(p => p.id !== cmd.id));
        break;

      case 'set_layer':
        if (cmd.layer && cmd.visible != null)
          setLayers(prev => ({ ...prev, [cmd.layer]: cmd.visible }));
        break;

      case 'narrative':
        setNarrative(cmd.text || '');
        setNarrVisible(true);
        if (cmd.clear_after_ms !== 0) {
          setTimeout(() => setNarrVisible(false), cmd.clear_after_ms ?? 6000);
        }
        break;

      case 'clear_narrative':
        setNarrVisible(false);
        break;

      case 'highlight':
        setHighlightId(cmd.entity_id || cmd.id || null);
        setTimeout(() => setHighlightId(null), 5000);
        break;

      case 'reset_view':
        if (g) {
          g.controls().autoRotate = true;
          g.pointOfView({ lat: 35, lng: 20, altitude: 2.2 }, 1200);
        }
        setSelected(null);
        break;

      case 'clear_dynamic':
        setDynEvents([]); setDynArcs([]); setDynPoints([]); setInfraOverride({});
        break;

      default:
        break;
    }
  }, []);

  // Initial camera + auto-rotate
  useEffect(() => {
    if (!globeRef.current) return;
    const ctrl = globeRef.current.controls();
    ctrl.autoRotate = true;
    ctrl.autoRotateSpeed = 0.25;
    ctrl.enableZoom = true;
    ctrl.minDistance = 150;
    ctrl.maxDistance = 600;
    globeRef.current.pointOfView({ lat: 35, lng: 20, altitude: 2.2 }, 1200);
  }, []);

  const handlePointClick = useCallback(point => {
    setSelected(point);
    if (globeRef.current) {
      globeRef.current.controls().autoRotate = false;
      globeRef.current.pointOfView({ lat: point.lat, lng: point.lng, altitude: 1.6 }, 900);
    }
  }, []);

  const handleRingClick = useCallback(ring => {
    setSelected({ ...ring, cat: 'event' });
    if (globeRef.current) {
      globeRef.current.controls().autoRotate = false;
      globeRef.current.pointOfView({ lat: ring.lat, lng: ring.lng, altitude: 1.4 }, 900);
    }
  }, []);

  const toggleLayer = useCallback(key => setLayers(prev => ({ ...prev, [key]: !prev[key] })), []);

  // ── Merge infra with AI overrides ────────────────────────────────────────
  const infraPoints = useMemo(() => POWER_PLANTS.map(p => {
    const ov    = infraOverride[p.id] || {};
    const plant = { ...p, ...ov };
    const cfg   = FUEL_CONFIG[plant.fuel] || FUEL_CONFIG.Other;
    const stCfg = STATUS_CONFIG[plant.status] || STATUS_CONFIG.active;
    const isHL  = highlightId === plant.id;
    return {
      ...plant, cat: 'infra',
      color: isHL ? '#ffffff' : stCfg.color,
      radius: plant.fuel === 'Nuclear' ? 0.65 : plant.capacity_mw > 3000 ? 0.55 : 0.38,
      fuelIcon: cfg.icon, statusLabel: stCfg.label,
    };
  }), [infraOverride, highlightId]);

  // ── All visible points (memoized) ────────────────────────────────────────
  const visiblePoints = useMemo(() => [
    ...(layers.vessels ? ALL_POINTS.filter(p => p.cat === 'vessel').map(p => ({
      ...p, color: p.id === highlightId ? '#ffffff' : p.color
    })) : []),
    ...(layers.aircraft ? ALL_POINTS.filter(p => p.cat === 'aircraft').map(p => ({
      ...p, color: p.id === highlightId ? '#ffffff' : p.color
    })) : []),
    ...(layers.infrastructure ? infraPoints : []),
    ...dynPoints,
  ], [layers, infraPoints, dynPoints, highlightId]);

  // ── All visible events (memoized) ────────────────────────────────────────
  const visibleEvents = useMemo(() => [
    ...(layers.events ? EVENTS : []),
    ...dynEvents,
  ], [layers.events, dynEvents]);

  // ── All visible arcs (memoized) ──────────────────────────────────────────
  const visibleArcs = useMemo(() => [
    ...(layers.arcs ? ARCS : []),
    ...dynArcs,
  ], [layers.arcs, dynArcs]);

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '100%', height: height, background: '#040810', borderRadius: 8, overflow: 'hidden' }}>

      {/* Globe — performance: waitForGlobeReady, rendererConfig antiAlias off for mobile */}
      <Globe
        ref={globeRef}
        width={dims.w}
        height={dims.h || 600}
        globeImageUrl="//unpkg.com/three-globe/example/img/earth-night.jpg"
        backgroundImageUrl="//unpkg.com/three-globe/example/img/night-sky.png"
        atmosphereColor="#0a3060"
        atmosphereAltitude={0.18}
        waitForGlobeReady={true}
        animateIn={true}
        rendererConfig={{ antialias: false, alpha: true }}

        /* Points — memoized */
        pointsData={visiblePoints}
        pointLat="lat"
        pointLng="lng"
        pointColor="color"
        pointRadius="radius"
        pointAltitude={0.005}
        pointsMerge={false}
        pointResolution={6}
        pointLabel={d => `<div style="background:#0d1421;border:1px solid #1a2540;padding:8px 10px;border-radius:6px;font-family:'Courier New',monospace;pointer-events:none;max-width:230px"><div style="color:${d.color};font-weight:700;font-size:12px">${d.fuelIcon || (d.cat==='vessel'?'⛵':d.cat==='aircraft'?'✈':'●')} ${d.name}</div><div style="color:#64748b;font-size:10px;margin-top:3px">${d.cat==='vessel'?`${d.type} · ${d.speed} kts`:d.cat==='aircraft'?`${d.type} · ${d.alt?.toLocaleString()} ft`:`${d.fuel} · ${d.capacity_mw?.toLocaleString()} MW · ${d.statusLabel||''}`}</div></div>`}
        onPointClick={handlePointClick}

        /* Rings — memoized */
        ringsData={visibleEvents}
        ringLat="lat"
        ringLng="lng"
        ringColor={d => t => `rgba(${d.r},${d.g},${d.b},${Math.sqrt(1 - t) * 0.85})`}
        ringMaxRadius="radiusDeg"
        ringPropagationSpeed={1.2}
        ringRepeatPeriod="period"
        onRingClick={handleRingClick}

        /* Arcs — memoized */
        arcsData={visibleArcs}
        arcStartLat="startLat"
        arcStartLng="startLng"
        arcEndLat="endLat"
        arcEndLng="endLng"
        arcColor={d => [d.colorStart, d.colorEnd]}
        arcStroke="stroke"
        arcDashLength="dash"
        arcDashGap="gap"
        arcDashAnimateTime="anim"
        arcAltitudeAutoScale={0.35}
      />

      {/* Narrative overlay — AI speech */}
      {narrativeVisible && narrative && (
        <div style={{
          position: 'absolute', bottom: 56, left: '50%', transform: 'translateX(-50%)',
          zIndex: 30, background: 'rgba(8,12,20,0.93)', border: '1px solid #00e5ff40',
          borderRadius: 8, padding: '10px 20px', maxWidth: 560, textAlign: 'center',
          fontFamily: "'Courier New', monospace", fontSize: 13, color: '#00e5ff',
          backdropFilter: 'blur(8px)',
          boxShadow: '0 0 24px rgba(0,229,255,0.15)',
          animation: 'nexoFadeIn 0.4s ease',
        }}>
          <span style={{ marginRight: 8, opacity: 0.7 }}>◈ NEXO</span>
          {narrative}
        </div>
      )}

      {/* Layer controls — top left */}
      <div style={{
        position: 'absolute', top: 12, left: 12, zIndex: 20,
        display: 'flex', flexDirection: 'column', gap: 6,
      }}>
        {[
          { key: 'vessels',        label: '⛵ Vessels',   color: '#00e5ff', count: VESSELS.length },
          { key: 'aircraft',       label: '✈ Aircraft',  color: '#f59e0b', count: AIRCRAFT.length },
          { key: 'events',         label: '⚠ Events',    color: '#ef4444', count: EVENTS.length },
          { key: 'arcs',           label: '↗ Flows',     color: '#a78bfa', count: ARCS.length },
          { key: 'infrastructure', label: '⚡ CritInfra', color: '#f0abfc', count: POWER_PLANTS.length },
        ].map(({ key, label, color, count }) => (
          <button
            key={key}
            onClick={() => toggleLayer(key)}
            style={{
              display: 'flex', alignItems: 'center', gap: 7,
              background: layers[key] ? 'rgba(13,20,33,0.92)' : 'rgba(13,20,33,0.5)',
              border: `1px solid ${layers[key] ? color + '60' : '#1a2540'}`,
              borderRadius: 6, padding: '5px 10px', cursor: 'pointer',
              fontFamily: "'Courier New', monospace", fontSize: 11,
              color: layers[key] ? color : '#475569',
              backdropFilter: 'blur(6px)',
              transition: 'all 0.2s',
            }}
          >
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: layers[key] ? color : '#334155', display: 'inline-block', flexShrink: 0 }} />
            {label}
            <span style={{ marginLeft: 'auto', paddingLeft: 8, fontSize: 10, color: layers[key] ? '#64748b' : '#334155' }}>{count}</span>
          </button>
        ))}
      </div>

      {/* Live counter — bottom left */}
      <div style={{
        position: 'absolute', bottom: 12, left: 12, zIndex: 20,
        display: 'flex', gap: 12,
        fontFamily: "'Courier New', monospace",
      }}>
        {[
          { v: VESSELS.length,       icon: '⛵', label: 'vessels',  c: '#00e5ff' },
          { v: AIRCRAFT.length,      icon: '✈',  label: 'aircraft', c: '#f59e0b' },
          { v: EVENTS.length,        icon: '⚠',  label: 'events',   c: '#ef4444' },
          { v: POWER_PLANTS.filter(p => p.status !== 'active').length, icon: '⚡', label: 'infra down', c: '#f0abfc' },
        ].map(({ v, icon, label, c }) => (
          <div key={label} style={{ background: 'rgba(13,20,33,0.85)', border: '1px solid #1a2540', borderRadius: 6, padding: '4px 10px', fontSize: 11, color: c }}>
            {icon} <span style={{ color: '#e2e8f0', fontWeight: 700 }}>{v}</span>
            <span style={{ color: '#475569', marginLeft: 4 }}>{label}</span>
          </div>
        ))}
      </div>

      {/* Detail panel */}
      <DetailPanel entity={selected} onClose={() => setSelected(null)} />

      {/* Double-click = reset view */}
      <div
        style={{ position: 'absolute', inset: 0, zIndex: 5, pointerEvents: 'none' }}
        onDoubleClick={() => handleCommand({ type: 'reset_view' })}
      />

      <style>{`
        @keyframes nexoFadeIn { from { opacity:0; transform: translateX(-50%) translateY(6px); } to { opacity:1; transform: translateX(-50%) translateY(0); } }
      `}</style>
    </div>
  );
}
