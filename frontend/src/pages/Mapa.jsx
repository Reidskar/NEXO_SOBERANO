import { useState } from 'react';
import OmniGlobe from '../components/OmniGlobe';

const NAV_LINKS = [
  { label: 'OMNIGLOBE',     href: '/omniglobe', external: false },
  { label: 'FLOWMAP',       href: '/flowmap',   external: false },
  { label: 'DASHBOARD',     href: '/control',   external: false },
];

export default function Mapa() {
  const [fullscreen, setFullscreen] = useState(false);

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0,
      background: '#040810', color: '#e2e8f0',
      fontFamily: "'JetBrains Mono','Courier New',monospace",
    }}>
      {/* Header bar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 14px', background: 'rgba(8,12,20,0.95)',
        borderBottom: '1px solid #1a2540', flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 11, color: '#00e5ff', fontWeight: 700, letterSpacing: '0.12em' }}>◎ OMNIGLOBE</span>
          <span style={{ fontSize: 10, color: '#334155', margin: '0 4px' }}>|</span>
          <span style={{ fontSize: 10, color: '#475569' }}>INTELLIGENCE LAYER · LIVE</span>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#10b981', display: 'inline-block', marginLeft: 6, boxShadow: '0 0 6px #10b981' }} />
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {NAV_LINKS.map(l => (
            <a key={l.label} href={l.href}
              style={{
                fontSize: 10, color: '#475569', textDecoration: 'none',
                padding: '3px 8px', border: '1px solid #1a2540', borderRadius: 4,
                letterSpacing: '0.06em', transition: 'all 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.color = '#00e5ff'; e.currentTarget.style.borderColor = '#00e5ff40'; }}
              onMouseLeave={e => { e.currentTarget.style.color = '#475569'; e.currentTarget.style.borderColor = '#1a2540'; }}
            >
              {l.label}
            </a>
          ))}
          <button
            onClick={() => setFullscreen(f => !f)}
            style={{
              fontSize: 10, color: '#475569', background: 'none',
              padding: '3px 8px', border: '1px solid #1a2540', borderRadius: 4,
              cursor: 'pointer', letterSpacing: '0.06em',
            }}
          >
            {fullscreen ? '⊡ EXIT' : '⊞ EXPAND'}
          </button>
        </div>
      </div>

      {/* Globe fills remaining space */}
      <div style={{ flex: 1, minHeight: 0, position: 'relative' }}>
        <OmniGlobe height={fullscreen ? window.innerHeight - 45 : '100%'} />
      </div>

      {/* Bottom status bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 16, padding: '5px 14px',
        background: 'rgba(8,12,20,0.95)', borderTop: '1px solid #1a2540',
        fontSize: 10, color: '#334155', flexShrink: 0,
        flexWrap: 'wrap',
      }}>
        <span style={{ color: '#475569' }}>SRC: AIS · ADS-B · SIGINT · OSINT</span>
        <span>|</span>
        <span>DOBLE CLICK para restablecer vista</span>
        <span>|</span>
        <span>CLICK en entidad para detalles</span>
        <span>|</span>
        <span style={{ marginLeft: 'auto', color: '#1e3a5f' }}>
          {new Date().toUTCString().replace('GMT', 'UTC')}
        </span>
      </div>
    </div>
  );
}
