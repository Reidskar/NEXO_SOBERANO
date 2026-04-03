import React, { useState } from 'react';
import { Map, Globe, Crosshair, Layers, AlertTriangle, Radio } from 'lucide-react';

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
  { name: 'Mar de China Meridional', lat: '14.5°N', lon: '115.8°E', threat: 'high',   type: 'maritime',  notes: 'Maniobras navales PLA — portaaviones activos', x: 75, y: 38 },
  { name: 'Frontera bielorrusa',      lat: '53.2°N', lon: '28.4°E', threat: 'medium', type: 'military',  notes: 'Concentración de tropas — actividad RF elevada', x: 52, y: 22 },
  { name: 'Estrecho de Ormuz',        lat: '26.6°N', lon: '56.3°E', threat: 'high',   type: 'maritime',  notes: 'Actividad AIS anómala — 23 buques en espera', x: 60, y: 40 },
  { name: 'Taiwán',                   lat: '23.7°N', lon: '121.0°E', threat: 'medium', type: 'air',      notes: 'Incursiones diarias ADIZ — interceptaciones', x: 79, y: 42 },
  { name: 'Venezuela / Guyana',       lat: '7.1°N',  lon: '63.5°W', threat: 'low',    type: 'political', notes: 'Tensión diplomática por Esequibo', x: 28, y: 50 },
  { name: 'Sahel (Mali / Niger)',     lat: '16.0°N', lon: '2.0°E',  threat: 'medium', type: 'military',  notes: 'Golpes de estado — retiro misiones europeas', x: 45, y: 46 },
];

const THREAT_COLOR = { high: '#ef4444', medium: 'var(--amber)', low: '#10b981' };
const TYPE_COLOR   = { maritime: 'var(--cyan)', military: '#ef4444', air: 'var(--indigo)', political: 'var(--amber)' };

const MAP_LAYERS = [
  { name: 'AIS — tráfico marítimo',   icon: Radio,         color: 'var(--cyan)'   },
  { name: 'ADS-B — aeronaves',        icon: Globe,         color: 'var(--indigo)' },
  { name: 'Infraestructura crítica',  icon: Layers,        color: 'var(--amber)'  },
  { name: 'Tensiones geopolíticas',   icon: AlertTriangle, color: '#ef4444'       },
];

export default function Mapa() {
  const [activeZone, setActiveZone] = useState(null);
  const [activeLayers, setActiveLayers] = useState(['AIS — tráfico marítimo']);

  const toggleLayer = (name) =>
    setActiveLayers(prev => prev.includes(name) ? prev.filter(x => x !== name) : [...prev, name]);

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1100, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <Map size={16} style={{ color: 'var(--cyan)' }} />
          <h1 style={{ fontFamily: mono, fontSize: 13, fontWeight: 700, color: 'var(--text)', letterSpacing: '.06em', textTransform: 'uppercase' }}>
            Mapa Geopolítico
          </h1>
          <span style={badge('var(--cyan)')}>LIVE</span>
          <span style={badge('var(--amber)')}>BETA</span>
        </div>
        <p style={{ fontFamily: mono, fontSize: 10, color: 'var(--dim)', letterSpacing: '.06em' }}>
          Zonas de interés · AIS · ADS-B · Infraestructura crítica · Overpass API
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 20 }}>

        {/* Left col */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Map canvas */}
          <div style={{ ...card, padding: 0, overflow: 'hidden' }}>
            <div style={{
              height: 380,
              background: 'linear-gradient(135deg, #030712 0%, #070f1a 50%, #030712 100%)',
              position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              {/* Grid */}
              <div style={{
                position: 'absolute', inset: 0, opacity: 0.06,
                backgroundImage: 'linear-gradient(rgba(0,229,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(0,229,255,1) 1px, transparent 1px)',
                backgroundSize: '60px 40px',
              }} />
              {/* Glow */}
              <div style={{
                position: 'absolute', inset: 0, opacity: 0.04,
                background: 'radial-gradient(ellipse 80% 50% at 50% 50%, rgba(0,229,255,1) 0%, transparent 70%)',
              }} />

              {/* Hotspots */}
              {ZONES.map(z => {
                const color = THREAT_COLOR[z.threat];
                const isActive = activeZone?.name === z.name;
                return (
                  <button key={z.name} onClick={() => setActiveZone(isActive ? null : z)}
                    style={{
                      position: 'absolute', left: `${z.x}%`, top: `${z.y}%`,
                      background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                      transform: 'translate(-50%, -50%)', zIndex: 2,
                    }}>
                    <div style={{
                      width: isActive ? 18 : 12, height: isActive ? 18 : 12,
                      borderRadius: '50%', background: color,
                      boxShadow: `0 0 ${isActive ? 18 : 10}px ${color}`,
                      transition: 'all .2s', position: 'relative',
                    }}>
                      {isActive && (
                        <div style={{ position: 'absolute', inset: -5, borderRadius: '50%', border: `1px solid ${color}`, opacity: 0.5 }} />
                      )}
                    </div>
                  </button>
                );
              })}

              {/* Center placeholder */}
              {!activeZone && (
                <div style={{ textAlign: 'center', zIndex: 1, pointerEvents: 'none' }}>
                  <Globe size={32} style={{ color: 'rgba(0,229,255,0.15)', margin: '0 auto 10px' }} />
                  <div style={{ fontFamily: mono, fontSize: 10, color: 'rgba(0,229,255,0.3)', letterSpacing: '.1em' }}>
                    INTEGRACIÓN LEAFLET · PRÓXIMAMENTE
                  </div>
                  <div style={{ fontFamily: mono, fontSize: 9, color: 'rgba(0,229,255,0.18)', marginTop: 6 }}>
                    Selecciona un punto para ver detalles
                  </div>
                </div>
              )}

              {/* Zone detail */}
              {activeZone && (
                <div style={{
                  position: 'absolute', bottom: 16, left: 16, right: 16,
                  background: 'rgba(3,7,18,0.92)',
                  border: `1px solid ${THREAT_COLOR[activeZone.threat]}40`,
                  padding: '14px 18px', zIndex: 10,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                    <div style={{ fontFamily: mono, fontSize: 12, color: 'var(--text)', fontWeight: 600 }}>{activeZone.name}</div>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <span style={badge(TYPE_COLOR[activeZone.type])}>{activeZone.type}</span>
                      <span style={badge(THREAT_COLOR[activeZone.threat])}>{activeZone.threat}</span>
                    </div>
                  </div>
                  <div style={{ fontFamily: mono, fontSize: 9, color: 'var(--dim)', marginBottom: 6 }}>
                    {activeZone.lat} · {activeZone.lon}
                  </div>
                  <div style={{ fontFamily: mono, fontSize: 10, color: 'var(--muted)' }}>{activeZone.notes}</div>
                </div>
              )}
            </div>

            {/* Layer controls */}
            <div style={{ display: 'flex', gap: 8, padding: '12px 20px', borderTop: '1px solid var(--border)', flexWrap: 'wrap' }}>
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

          {/* Zone list */}
          <div style={card}>
            <div style={{ ...lbl(), marginBottom: 14, display: 'block' }}>Zonas activas · {ZONES.length} focos</div>
            {ZONES.map(z => (
              <div key={z.name} onClick={() => setActiveZone(activeZone?.name === z.name ? null : z)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0',
                  borderBottom: '1px solid rgba(0,229,255,0.06)', cursor: 'pointer',
                  background: activeZone?.name === z.name ? 'rgba(0,229,255,0.02)' : 'transparent',
                  transition: 'background .15s',
                }}
                onMouseEnter={e => { if (activeZone?.name !== z.name) e.currentTarget.style.background = 'rgba(255,255,255,0.02)'; }}
                onMouseLeave={e => { if (activeZone?.name !== z.name) e.currentTarget.style.background = 'transparent'; }}
              >
                <Crosshair size={12} style={{ color: THREAT_COLOR[z.threat], flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontFamily: mono, fontSize: 11, color: 'var(--text)', marginBottom: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{z.name}</div>
                  <div style={{ fontFamily: mono, fontSize: 9, color: 'var(--dim)' }}>{z.notes}</div>
                </div>
                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                  <span style={badge(TYPE_COLOR[z.type])}>{z.type}</span>
                  <span style={badge(THREAT_COLOR[z.threat])}>{z.threat}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Signals */}
          <div style={card}>
            <div style={{ ...lbl(), marginBottom: 14, display: 'block' }}>Señales activas</div>
            {[
              { label: 'Aeronaves militares', value: '847',  color: 'var(--indigo)' },
              { label: 'Portaaviones',         value: '23',   color: '#ef4444'       },
              { label: 'Satélites Starlink',   value: '412',  color: 'var(--cyan)'   },
              { label: 'Buques en tránsito',   value: '1.2k', color: 'var(--amber)'  },
              { label: 'Anomalías RF',         value: '14',   color: '#10b981'       },
            ].map(({ label: l, value, color }) => (
              <div key={l} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid rgba(0,229,255,0.06)' }}>
                <span style={{ fontFamily: mono, fontSize: 10, color: 'var(--muted)' }}>{l}</span>
                <span style={{ fontFamily: mono, fontSize: 13, fontWeight: 700, color }}>{value}</span>
              </div>
            ))}
          </div>

          {/* Data sources */}
          <div style={card}>
            <div style={{ ...lbl(), marginBottom: 14, display: 'block' }}>Fuentes de datos</div>
            {[
              { name: 'Overpass API',    status: 'live',    color: '#10b981'       },
              { name: 'AIS Marine',      status: 'live',    color: '#10b981'       },
              { name: 'FlightAware',     status: 'live',    color: '#10b981'       },
              { name: 'Leaflet Maps',    status: 'soon',    color: 'var(--amber)'  },
              { name: 'Satellite (SAR)', status: 'planned', color: 'var(--dim)'    },
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
            <div style={{ ...lbl('var(--cyan)'), marginBottom: 10, display: 'block' }}>Endpoints</div>
            {[
              'GET /api/eventos/infraestructura',
              'GET /api/tools/ais-feed',
              'GET /api/tools/adsb-feed',
            ].map(ep => (
              <div key={ep} style={{ fontFamily: mono, fontSize: 9, color: 'var(--cyan)', padding: '5px 0', borderBottom: '1px solid rgba(0,229,255,0.06)' }}>
                {ep}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
