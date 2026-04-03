import React, { useEffect, useRef, useState, lazy, Suspense } from 'react';

const ImpactScene = lazy(() => import('./ImpactScene'));

/**
 * EvidenceViewer — Phase 13 Upgraded
 * 3-tab glassmorphic panel:
 *  1. EVIDENCIA   — 3D mini impact scene + media gallery
 *  2. ANÁLISIS IA — AI brief + 4-dimension assessment
 *  3. SEGUIMIENTO — live tracking updates for the same zone
 */

const SEVERITY_COLOR = (s) =>
  s >= 0.8 ? '#ef4444' : s >= 0.5 ? '#f97316' : '#eab308';

const EVENT_ICON = {
  strike: '⚡', naval_movement: '⚓', deployment: '🚛', diplomatic: '🏛️',
};

const SOURCE_BADGE = (source = '') => {
  if (source.startsWith('telegram')) return { label: '📡 Telegram', color: '#2AABEE' };
  if (source.startsWith('twitter'))  return { label: '🐦 Twitter/X', color: '#1DA1F2' };
  if (source.startsWith('drive'))    return { label: '📁 Drive', color: '#34a853' };
  return { label: '🌐 OSINT', color: '#6366f1' };
};

const DIMENSION_LABELS = [
  { key: 'military',    label: 'MILITAR',     color: '#ef4444', icon: '⚔️' },
  { key: 'economic',    label: 'ECONÓMICO',   color: '#f97316', icon: '💰' },
  { key: 'diplomatic',  label: 'DIPLOMÁTICO', color: '#a855f7', icon: '🏛️' },
  { key: 'energy',      label: 'ENERGÉTICO',  color: '#eab308', icon: '⚡' },
];

// Rough impact scoring from event metadata
function estimateImpact(event) {
  const sev = event.severity || 0.5;
  const type = event.event_type || 'strike';
  return {
    military:   type === 'strike' ? sev : type === 'deployment' ? sev * 0.7 : sev * 0.3,
    economic:   type === 'oil_strike' ? 0.95 : sev * 0.5,
    diplomatic: type === 'diplomatic' ? 0.9 : sev * 0.2,
    energy:     (event.target || '').toLowerCase().includes('refin') ||
                (event.target || '').toLowerCase().includes('oil') ? 0.9 : sev * 0.3,
  };
}

const TABS = ['EVIDENCIA', 'ANÁLISIS', 'SEGUIMIENTO'];

export default function EvidenceViewer({ event, relatedEvents = [], onClose }) {
  const [activeTab, setActiveTab] = useState(0);

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  if (!event) return null;

  const badge   = SOURCE_BADGE(event.source);
  const icon    = EVENT_ICON[event.event_type] || '📌';
  const sevPct  = Math.round((event.severity || 0.7) * 100);
  const sevClr  = SEVERITY_COLOR(event.severity || 0.7);
  const impact  = estimateImpact(event);
  const coords  = event.lat && event.lng
    ? `${event.lat.toFixed(4)}°, ${event.lng.toFixed(4)}°`
    : 'Coordenadas no disponibles';

  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, zIndex: 999,
          background: 'rgba(0,0,0,0.4)',
          backdropFilter: 'blur(2px)',
        }}
      />
      <div style={{
        position: 'fixed',
        top: 0, right: 0,
        width: 420, height: '100vh',
        zIndex: 1000,
        background: 'rgba(7, 10, 18, 0.95)',
        backdropFilter: 'blur(24px)',
        borderLeft: '1px solid rgba(6,182,212,0.2)',
        display: 'flex', flexDirection: 'column',
        fontFamily: "'Space Mono', monospace",
        color: '#e2e8f0',
        boxShadow: '-20px 0 60px rgba(0,0,0,0.6)',
        animation: 'slideInRight 0.35s cubic-bezier(0.23, 1, 0.32, 1)',
        overflowY: 'hidden',
      }}>
        {/* ── Header ─────────────────────────────────────────────────────── */}
        <div style={{
          padding: '18px 22px 14px',
          borderBottom: '1px solid rgba(6,182,212,0.12)',
          background: 'linear-gradient(135deg, rgba(6,182,212,0.07), transparent)',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 10, color: '#06b6d4', letterSpacing: 2, marginBottom: 3 }}>
                EVIDENCIA TÁCTICA · NEXO SOBERANO
              </div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#fff', lineHeight: 1.3 }}>
                {icon} {event.target || event.event_type?.toUpperCase() || 'EVENTO OSINT'}
              </div>
              <div style={{ fontSize: 10, color: '#475569', marginTop: 3 }}>
                {event.country || '—'} · {coords}
              </div>
            </div>
            <button onClick={onClose} style={{
              background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: 6, color: '#ef4444', cursor: 'pointer',
              fontSize: 13, padding: '4px 10px', fontFamily: 'inherit', flexShrink: 0,
            }}>✕</button>
          </div>

          {/* Severity bar */}
          <div style={{ marginTop: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: '#64748b', marginBottom: 4 }}>
              <span>NIVEL DE AMENAZA</span>
              <span style={{ color: sevClr, fontWeight: 700 }}>{sevPct}%</span>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: 3, height: 4 }}>
              <div style={{
                width: `${sevPct}%`, height: '100%',
                background: `linear-gradient(90deg, ${sevClr}66, ${sevClr})`,
                borderRadius: 3,
                transition: 'width 1.2s ease-out',
              }} />
            </div>
          </div>

          {/* Source */}
          <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{
              padding: '2px 10px', borderRadius: 20, fontSize: 9, fontWeight: 600,
              background: `${badge.color}18`, border: `1px solid ${badge.color}33`, color: badge.color,
            }}>{badge.label}</span>
            <span style={{ fontSize: 9, color: '#334155' }}>
              {event.timestamp ? new Date(event.timestamp).toLocaleString('es-AR') : '—'}
            </span>
          </div>
        </div>

        {/* ── Tabs ──────────────────────────────────────────────────────── */}
        <div style={{
          display: 'flex', borderBottom: '1px solid rgba(255,255,255,0.06)',
          flexShrink: 0,
        }}>
          {TABS.map((tab, i) => (
            <button
              key={tab}
              onClick={() => setActiveTab(i)}
              style={{
                flex: 1, padding: '9px 0', fontSize: 9, letterSpacing: 1.5,
                fontFamily: 'inherit', cursor: 'pointer', border: 'none',
                background: activeTab === i ? 'rgba(6,182,212,0.1)' : 'transparent',
                color: activeTab === i ? '#06b6d4' : '#475569',
                borderBottom: activeTab === i ? '2px solid #06b6d4' : '2px solid transparent',
                transition: 'all 0.2s',
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* ── Tab Content ───────────────────────────────────────────────── */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 22px' }}>

          {/* TAB 0: EVIDENCIA */}
          {activeTab === 0 && (
            <div>
              {/* Mini 3D Impact Scene */}
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 9, color: '#06b6d4', letterSpacing: 1.5, marginBottom: 8 }}>
                  VISUALIZACIÓN DEL OBJETIVO
                </div>
                <Suspense fallback={
                  <div style={{ height: 200, background: '#020917', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#1e293b', fontSize: 11 }}>
                    Cargando escena 3D...
                  </div>
                }>
                  <ImpactScene
                    eventType={event.event_type || 'strike'}
                    targetType={event.target_type}
                  />
                </Suspense>
              </div>

              {/* Media Gallery */}
              {event.media_urls?.length > 0 ? (
                <div>
                  <div style={{ fontSize: 9, color: '#06b6d4', letterSpacing: 1.5, marginBottom: 10 }}>
                    EVIDENCIA MULTIMEDIA ({event.media_urls.length})
                  </div>
                  {event.media_urls.map((url, i) => (
                    <div key={i} style={{ marginBottom: 10 }}>
                      {url.includes('youtube') || url.includes('youtu.be') ? (
                        <iframe
                          src={url.replace('watch?v=', 'embed/')}
                          style={{ width: '100%', height: 160, borderRadius: 6, border: 'none' }}
                          allowFullScreen title={`media-${i}`}
                        />
                      ) : (
                        <a href={url} target="_blank" rel="noopener noreferrer">
                          <img
                            src={url} alt={`Evidencia ${i + 1}`}
                            style={{ width: '100%', borderRadius: 6, border: '1px solid rgba(6,182,212,0.15)', cursor: 'pointer' }}
                            onError={e => { e.target.style.display = 'none'; }}
                          />
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ textAlign: 'center', color: '#334155', fontSize: 10, paddingTop: 10 }}>
                  Sin evidencia multimedia adjunta.
                </div>
              )}
            </div>
          )}

          {/* TAB 1: ANÁLISIS */}
          {activeTab === 1 && (
            <div>
              {/* AI Brief */}
              <div style={{ marginBottom: 18 }}>
                <div style={{ fontSize: 9, color: '#06b6d4', letterSpacing: 1.5, marginBottom: 8 }}>ANÁLISIS IA</div>
                <div style={{
                  fontSize: 12, color: '#cbd5e1', lineHeight: 1.8,
                  padding: '12px 14px',
                  background: 'rgba(6,182,212,0.04)',
                  border: '1px solid rgba(6,182,212,0.1)',
                  borderRadius: 6,
                }}>
                  {event.brief || event.descripcion || 'Sin análisis disponible.'}
                </div>
              </div>

              {/* 4-Dimension Impact Assessment */}
              <div>
                <div style={{ fontSize: 9, color: '#06b6d4', letterSpacing: 1.5, marginBottom: 12 }}>
                  IMPACTO ESTIMADO (4 DIMENSIONES)
                </div>
                {DIMENSION_LABELS.map(dim => (
                  <div key={dim.key} style={{ marginBottom: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: '#64748b', marginBottom: 4 }}>
                      <span>{dim.icon} {dim.label}</span>
                      <span style={{ color: dim.color }}>{Math.round((impact[dim.key] || 0) * 100)}%</span>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.04)', borderRadius: 3, height: 4 }}>
                      <div style={{
                        width: `${Math.round((impact[dim.key] || 0) * 100)}%`,
                        height: '100%',
                        background: dim.color,
                        borderRadius: 3,
                        transition: 'width 1.5s ease-out',
                        opacity: 0.8,
                      }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 2: SEGUIMIENTO */}
          {activeTab === 2 && (
            <div>
              <div style={{ fontSize: 9, color: '#06b6d4', letterSpacing: 1.5, marginBottom: 12 }}>
                SEGUIMIENTO EN VIVO — {event.country || 'ZONA'}
              </div>
              {relatedEvents.length === 0 ? (
                <div style={{ color: '#334155', fontSize: 10, textAlign: 'center', paddingTop: 20 }}>
                  Sin eventos relacionados registrados.
                </div>
              ) : (
                relatedEvents.map((ev, i) => (
                  <div key={i} style={{
                    padding: '10px 12px', marginBottom: 8,
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.06)',
                    borderRadius: 6,
                  }}>
                    <div style={{ fontSize: 11, color: '#e2e8f0', marginBottom: 3 }}>
                      {EVENT_ICON[ev.event_type] || '📌'} {ev.target || ev.titulo || 'Evento'}
                    </div>
                    <div style={{ fontSize: 9, color: '#475569' }}>
                      {ev.country} · {ev.timestamp ? new Date(ev.timestamp).toLocaleString('es-AR') : '—'}
                    </div>
                    {ev.brief && (
                      <div style={{ fontSize: 10, color: '#64748b', marginTop: 4, lineHeight: 1.6 }}>
                        {ev.brief.slice(0, 120)}...
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); opacity: 0; }
          to   { transform: translateX(0);   opacity: 1; }
        }
      `}</style>
    </>
  );
}
