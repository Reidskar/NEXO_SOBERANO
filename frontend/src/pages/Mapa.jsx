import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import { Map, Globe, Crosshair, Layers, AlertTriangle, Radio } from 'lucide-react';
import 'leaflet/dist/leaflet.css';

const mono = "'Space Mono', monospace";

const card = {
  background: 'var(--bg2)',
  border: '1px solid var(--border)',
  padding: '20px 24px',
};

const lbl = (color = 'var(--dim)') => ({
  fontFamily: mono, fontSize: 10, color, letterSpacing: '.12em', textTransform: 'uppercase',
});

const badge = (color = 'var(--cyan)') => ({
  fontFamily: mono, fontSize: 9, letterSpacing: '.08em', textTransform: 'uppercase',
  background: `${color}14`, color, border: `1px solid ${color}30`,
  padding: '3px 10px', borderRadius: 2,
});

const ZONES = [
  { name: 'Irán — Programa Nuclear',    coords: [32.4, 53.7],  threat: 'high',   type: 'military',  notes: 'Enriquecimiento >60% — actividad instalaciones Fordow' },
  { name: 'Estrecho de Taiwán',         coords: [24.5, 122.0], threat: 'high',   type: 'air',       notes: 'Maniobras navales PLA — portaaviones activos + ADIZ violaciones diarias' },
  { name: 'Israel / Gaza / Líbano',     coords: [31.5, 34.8],  threat: 'high',   type: 'military',  notes: 'Operaciones terrestres activas — alerta Hezbolá norte' },
  { name: 'Ucrania Oriental',           coords: [48.5, 37.5],  threat: 'medium', type: 'military',  notes: 'Línea de frente estabilizada — artillería intensiva Zaporiyia' },
  { name: 'Mar del Sur de China',       coords: [14.5, 115.8], threat: 'medium', type: 'maritime',  notes: 'Disputas Spratly — maniobras PLA-N' },
  { name: 'Corea del Norte',            coords: [40.0, 127.5], threat: 'medium', type: 'military',  notes: 'Ensayos misilísticos — satélites espías activos' },
  { name: 'Rusia — Engels Base',        coords: [51.5, 46.2],  threat: 'medium', type: 'air',       notes: 'Tu-160 activos — vuelos ELINT sobre Mar Negro' },
  { name: 'Sahel (Mali / Niger)',       coords: [16.0, 2.0],   threat: 'medium', type: 'political', notes: 'Golpes de estado — retirada misiones europeas, avance Wagner' },
  { name: 'Estrecho de Ormuz',          coords: [26.6, 56.3],  threat: 'medium', type: 'maritime',  notes: 'Actividad AIS anómala — 23 buques en espera' },
  { name: 'Venezuela / Guyana',         coords: [7.1, -63.5],  threat: 'low',    type: 'political', notes: 'Tensión diplomática por Esequibo — despliegue FANB' },
];

const THREAT_COLOR = { high: '#ef4444', medium: '#f59e0b', low: '#10b981' };
const THREAT_RADIUS = { high: 14, medium: 10, low: 7 };

const MAP_LAYERS = [
  { name: 'AIS — tráfico marítimo',  icon: Radio,         color: '#00e5ff'  },
  { name: 'ADS-B — aeronaves',       icon: Globe,         color: '#818cf8'  },
  { name: 'Infraestructura crítica', icon: Layers,        color: '#f59e0b'  },
  { name: 'Tensiones geopolíticas',  icon: AlertTriangle, color: '#ef4444'  },
];

// Leaflet CSS overrides for dark theme
const leafletDarkCss = `
  .leaflet-container { background: #030712 !important; font-family: 'Space Mono', monospace; }
  .leaflet-tile-pane { filter: brightness(0.85) contrast(1.1) saturate(0.8); }
  .leaflet-control-attribution { background: rgba(3,7,18,0.8) !important; color: rgba(0,229,255,0.4) !important; font-size: 9px; font-family: 'Space Mono', monospace; border-top: 1px solid rgba(0,229,255,0.1); }
  .leaflet-control-attribution a { color: rgba(0,229,255,0.5) !important; }
  .leaflet-control-zoom { border: 1px solid rgba(0,229,255,0.15) !important; }
  .leaflet-control-zoom a { background: rgba(3,7,18,0.92) !important; color: rgba(0,229,255,0.6) !important; border-bottom: 1px solid rgba(0,229,255,0.1) !important; font-family: 'Space Mono', monospace; }
  .leaflet-control-zoom a:hover { background: rgba(0,229,255,0.08) !important; color: #00e5ff !important; }
  .leaflet-popup-content-wrapper { background: rgba(3,7,18,0.96) !important; border: 1px solid rgba(0,229,255,0.2) !important; border-radius: 2px !important; color: #e2e8f0 !important; box-shadow: 0 0 24px rgba(0,229,255,0.1) !important; }
  .leaflet-popup-tip { background: rgba(3,7,18,0.96) !important; }
  .leaflet-popup-close-button { color: rgba(0,229,255,0.5) !important; }
  .leaflet-popup-close-button:hover { color: #00e5ff !important; }
`;

function PulseMarker({ zone, isActive, onClick }) {
  const color = THREAT_COLOR[zone.threat];
  const radius = THREAT_RADIUS[zone.threat];
  return (
    <CircleMarker
      center={zone.coords}
      radius={isActive ? radius + 4 : radius}
      pathOptions={{
        color,
        fillColor: color,
        fillOpacity: isActive ? 0.9 : 0.7,
        weight: isActive ? 2 : 1,
        opacity: 1,
      }}
      eventHandlers={{ click: onClick }}
    >
      <Popup>
        <div style={{ fontFamily: mono, minWidth: 200, padding: '4px 0' }}>
          <div style={{ fontSize: 11, color: '#e2e8f0', fontWeight: 700, marginBottom: 6 }}>{zone.name}</div>
          <div style={{ fontSize: 9, color: 'rgba(0,229,255,0.6)', marginBottom: 8 }}>
            {zone.coords[0].toFixed(1)}° · {zone.coords[1].toFixed(1)}°
          </div>
          <div style={{ fontSize: 10, color: '#94a3b8', lineHeight: 1.5, marginBottom: 8 }}>{zone.notes}</div>
          <div style={{ display: 'flex', gap: 6 }}>
            <span style={{ fontSize: 9, padding: '2px 8px', border: `1px solid ${color}30`, color, background: `${color}14`, textTransform: 'uppercase', letterSpacing: '.06em' }}>{zone.threat}</span>
            <span style={{ fontSize: 9, padding: '2px 8px', border: '1px solid rgba(0,229,255,0.2)', color: '#00e5ff', background: 'rgba(0,229,255,0.06)', textTransform: 'uppercase', letterSpacing: '.06em' }}>{zone.type}</span>
          </div>
        </div>
      </Popup>
    </CircleMarker>
  );
}

export default function Mapa() {
  const [activeZone, setActiveZone] = useState(null);
  const [activeLayers, setActiveLayers] = useState(['AIS — tráfico marítimo', 'Tensiones geopolíticas']);
  const [mapReady, setMapReady] = useState(false);

  const toggleLayer = (name) =>
    setActiveLayers(prev => prev.includes(name) ? prev.filter(x => x !== name) : [...prev, name]);

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1200, margin: '0 auto' }}>
      <style>{leafletDarkCss}</style>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <Map size={16} style={{ color: '#00e5ff' }} />
          <h1 style={{ fontFamily: mono, fontSize: 13, fontWeight: 700, color: 'var(--text)', letterSpacing: '.06em', textTransform: 'uppercase' }}>
            Monitor Global
          </h1>
          <span style={badge('#00e5ff')}>LIVE</span>
          <span style={badge('#f59e0b')}>{ZONES.filter(z => z.threat === 'high').length} CRÍTICOS</span>
        </div>
        <p style={{ fontFamily: mono, fontSize: 10, color: 'var(--dim)', letterSpacing: '.06em' }}>
          {ZONES.length} focos activos · AIS · ADS-B · Infraestructura crítica · Overpass API
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 20 }}>

        {/* Left — Map */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Real Leaflet Map */}
          <div style={{ ...card, padding: 0, overflow: 'hidden' }}>
            <div style={{ height: 440, position: 'relative' }}>
              <MapContainer
                center={[25, 30]}
                zoom={2}
                minZoom={2}
                maxZoom={10}
                style={{ height: '100%', width: '100%', background: '#030712' }}
                zoomControl={true}
                scrollWheelZoom={true}
                whenReady={() => setMapReady(true)}
              >
                {/* CartoDB Dark Matter — matches our aesthetic */}
                <TileLayer
                  url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'
                  subdomains="abcd"
                  maxZoom={20}
                />

                {/* Threat markers */}
                {ZONES.map(zone => (
                  <PulseMarker
                    key={zone.name}
                    zone={zone}
                    isActive={activeZone?.name === zone.name}
                    onClick={() => setActiveZone(prev => prev?.name === zone.name ? null : zone)}
                  />
                ))}
              </MapContainer>

              {/* Scan line overlay */}
              <div style={{
                position: 'absolute', top: 0, left: 0, right: 0, height: 2,
                background: 'linear-gradient(90deg, transparent, rgba(0,229,255,0.4), transparent)',
                animation: 'scan-h 4s linear infinite',
                zIndex: 1000, pointerEvents: 'none',
              }} />

              {/* HUD corners */}
              {[
                { top: 0, left: 0, borderTop: '2px solid rgba(0,229,255,0.3)', borderLeft: '2px solid rgba(0,229,255,0.3)' },
                { top: 0, right: 0, borderTop: '2px solid rgba(0,229,255,0.3)', borderRight: '2px solid rgba(0,229,255,0.3)' },
                { bottom: 0, left: 0, borderBottom: '2px solid rgba(0,229,255,0.3)', borderLeft: '2px solid rgba(0,229,255,0.3)' },
                { bottom: 0, right: 0, borderBottom: '2px solid rgba(0,229,255,0.3)', borderRight: '2px solid rgba(0,229,255,0.3)' },
              ].map((s, i) => (
                <div key={i} style={{ position: 'absolute', width: 20, height: 20, zIndex: 1001, pointerEvents: 'none', ...s }} />
              ))}

              {/* Live label */}
              <div style={{
                position: 'absolute', top: 12, left: 12, zIndex: 1001, pointerEvents: 'none',
                fontFamily: mono, fontSize: 9, color: '#00e5ff', letterSpacing: '.12em',
                background: 'rgba(3,7,18,0.85)', padding: '4px 10px',
                border: '1px solid rgba(0,229,255,0.2)',
                display: 'flex', alignItems: 'center', gap: 6,
              }}>
                <div style={{ width: 5, height: 5, borderRadius: '50%', background: '#10b981', animation: 'pulse-ring 1.5s ease-out infinite' }} />
                NEXO INTEL LIVE
              </div>
            </div>

            {/* Layer controls */}
            <div style={{ display: 'flex', gap: 8, padding: '12px 20px', borderTop: '1px solid var(--border)', flexWrap: 'wrap', background: 'var(--bg2)' }}>
              {MAP_LAYERS.map(({ name, icon: Icon, color }) => {
                const on = activeLayers.includes(name);
                return (
                  <button key={name} onClick={() => toggleLayer(name)} style={{
                    display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px',
                    fontFamily: mono, fontSize: 9, letterSpacing: '.06em', textTransform: 'uppercase',
                    border: `1px solid ${on ? `${color}50` : 'var(--border)'}`,
                    background: on ? `${color}10` : 'transparent',
                    color: on ? color : 'var(--dim)', cursor: 'pointer', borderRadius: 2, transition: 'all .15s',
                  }}>
                    <Icon size={11} />
                    {name}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Zone grid */}
          <div style={{ ...card }}>
            <div style={{ ...lbl(), marginBottom: 14, display: 'block' }}>Focos activos · {ZONES.length} zonas monitorizadas</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {ZONES.map(z => (
                <div key={z.name} onClick={() => setActiveZone(activeZone?.name === z.name ? null : z)}
                  style={{
                    display: 'flex', alignItems: 'flex-start', gap: 10, padding: '10px 12px',
                    border: `1px solid ${activeZone?.name === z.name ? `${THREAT_COLOR[z.threat]}30` : 'rgba(0,229,255,0.06)'}`,
                    background: activeZone?.name === z.name ? `${THREAT_COLOR[z.threat]}08` : 'rgba(255,255,255,0.01)',
                    cursor: 'pointer', transition: 'all .15s', borderRadius: 2,
                  }}
                  onMouseEnter={e => { if (activeZone?.name !== z.name) { e.currentTarget.style.background = 'rgba(255,255,255,0.02)'; e.currentTarget.style.borderColor = 'rgba(0,229,255,0.12)'; }}}
                  onMouseLeave={e => { if (activeZone?.name !== z.name) { e.currentTarget.style.background = 'rgba(255,255,255,0.01)'; e.currentTarget.style.borderColor = 'rgba(0,229,255,0.06)'; }}}
                >
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: THREAT_COLOR[z.threat], flexShrink: 0, marginTop: 2, boxShadow: `0 0 6px ${THREAT_COLOR[z.threat]}` }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontFamily: mono, fontSize: 10, color: 'var(--text)', marginBottom: 3, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{z.name}</div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <span style={badge(THREAT_COLOR[z.threat])}>{z.threat}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Active zone detail */}
          {activeZone && (
            <div style={{ ...card, border: `1px solid ${THREAT_COLOR[activeZone.threat]}30`, background: `${THREAT_COLOR[activeZone.threat]}06`, animation: 'stagger-in .3s ease' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                <div style={{ ...lbl(THREAT_COLOR[activeZone.threat]), display: 'block' }}>Zona seleccionada</div>
                <button onClick={() => setActiveZone(null)} style={{ background: 'none', border: 'none', color: 'var(--dim)', cursor: 'pointer', fontSize: 14, padding: 0 }}>×</button>
              </div>
              <div style={{ fontFamily: mono, fontSize: 12, color: 'var(--text)', fontWeight: 700, marginBottom: 6 }}>{activeZone.name}</div>
              <div style={{ fontFamily: mono, fontSize: 9, color: 'var(--dim)', marginBottom: 10 }}>
                {activeZone.coords[0].toFixed(1)}°N · {Math.abs(activeZone.coords[1]).toFixed(1)}°{activeZone.coords[1] < 0 ? 'W' : 'E'}
              </div>
              <div style={{ fontFamily: mono, fontSize: 10, color: 'var(--muted)', lineHeight: 1.6, marginBottom: 12 }}>{activeZone.notes}</div>
              <div style={{ display: 'flex', gap: 6 }}>
                <span style={badge(THREAT_COLOR[activeZone.threat])}>{activeZone.threat}</span>
                <span style={badge('#00e5ff')}>{activeZone.type}</span>
              </div>
            </div>
          )}

          {/* Signals */}
          <div style={card}>
            <div style={{ ...lbl(), marginBottom: 14, display: 'block' }}>Señales activas</div>
            {[
              { label: 'Aeronaves militares', value: '847',  color: '#818cf8' },
              { label: 'Portaaviones',         value: '23',   color: '#ef4444' },
              { label: 'Satélites Starlink',   value: '412',  color: '#00e5ff' },
              { label: 'Buques en tránsito',   value: '1.2k', color: '#f59e0b' },
              { label: 'Anomalías RF',         value: '14',   color: '#10b981' },
            ].map(({ label: l, value, color }) => (
              <div key={l} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid rgba(0,229,255,0.06)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  <div style={{ width: 4, height: 4, borderRadius: '50%', background: color, boxShadow: `0 0 4px ${color}` }} />
                  <span style={{ fontFamily: mono, fontSize: 10, color: 'var(--muted)' }}>{l}</span>
                </div>
                <span style={{ fontFamily: mono, fontSize: 13, fontWeight: 700, color }}>{value}</span>
              </div>
            ))}
          </div>

          {/* Fuentes */}
          <div style={card}>
            <div style={{ ...lbl(), marginBottom: 14, display: 'block' }}>Fuentes de datos</div>
            {[
              { name: 'CartoDB Dark Maps',  status: 'live',    color: '#10b981' },
              { name: 'Overpass API',       status: 'live',    color: '#10b981' },
              { name: 'AIS Marine',         status: 'live',    color: '#10b981' },
              { name: 'FlightAware',        status: 'live',    color: '#10b981' },
              { name: 'Satellite (SAR)',    status: 'pronto',  color: '#f59e0b' },
            ].map(({ name, status, color }) => (
              <div key={name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: '1px solid rgba(0,229,255,0.05)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: color, boxShadow: status === 'live' ? `0 0 5px ${color}` : 'none' }} />
                  <span style={{ fontFamily: mono, fontSize: 10, color: 'var(--muted)' }}>{name}</span>
                </div>
                <span style={badge(color)}>{status}</span>
              </div>
            ))}
          </div>

          {/* Endpoints */}
          <div style={{ ...card, background: 'rgba(0,229,255,0.03)', border: '1px solid rgba(0,229,255,0.12)' }}>
            <div style={{ ...lbl('#00e5ff'), marginBottom: 10, display: 'block' }}>Endpoints</div>
            {[
              'GET /api/eventos/infraestructura',
              'GET /api/tools/ais-feed',
              'GET /api/tools/adsb-feed',
              'GET /api/tools/overpass',
            ].map(ep => (
              <div key={ep} style={{ fontFamily: mono, fontSize: 9, color: '#00e5ff', padding: '5px 0', borderBottom: '1px solid rgba(0,229,255,0.06)' }}>
                {ep}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
