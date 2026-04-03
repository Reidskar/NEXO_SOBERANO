import React, { useState, useEffect } from 'react';

/**
 * EventTimeline — Phase 13 Pilar 5
 * Collapsible lateral panel showing chronological OSINT simulation events.
 * Click → globe pans to the event. Includes "Replay All" button.
 */

const EVENT_TYPE_STYLE = {
  strike:         { color: '#ef4444', icon: '⚡' },
  naval_movement: { color: '#06b6d4', icon: '⚓' },
  deployment:     { color: '#f97316', icon: '🚛' },
  diplomatic:     { color: '#a855f7', icon: '🏛️' },
};

const formatTime = (ts) => {
  try {
    return new Date(ts).toLocaleString('es-AR', {
      day: '2-digit', month: '2-digit',
      hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return '—';
  }
};

const formatVol = (v) => {
  if (!v || v < 1000) return v || '—';
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  return `$${(v / 1000).toFixed(0)}K`;
};

export default function EventTimeline({
  events = [],
  onEventClick,
  onReplayAll,
  onSaveSimulation,
  visible = true,
}) {
  const [expanded, setExpanded] = useState(true);
  const [replayActive, setReplayActive] = useState(false);

  const handleReplay = async () => {
    if (replayActive || !onReplayAll) return;
    setReplayActive(true);
    await onReplayAll();
    setReplayActive(false);
  };

  if (!visible) return null;

  return (
    <div style={{
      position: 'absolute',
      top: 60,
      left: expanded ? 0 : -264,
      width: 280,
      maxHeight: 'calc(100vh - 120px)',
      zIndex: 50,
      transition: 'left 0.35s cubic-bezier(0.23, 1, 0.32, 1)',
      display: 'flex',
      alignItems: 'flex-start',
    }}>
      {/* Toggle tab */}
      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          position: 'absolute',
          right: -28,
          top: 0,
          width: 28,
          height: 80,
          background: 'rgba(7,10,18,0.9)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(6,182,212,0.2)',
          borderLeft: 'none',
          borderRadius: '0 8px 8px 0',
          color: '#06b6d4',
          cursor: 'pointer',
          fontSize: 12,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 2,
          fontFamily: 'monospace',
          writingMode: 'vertical-rl',
          letterSpacing: 2,
        }}
        title={expanded ? 'Colapsar timeline' : 'Expandir timeline'}
      >
        {expanded ? '◀' : '▶'} <span style={{ fontSize: 9 }}>TIMELINE</span>
      </button>

      {/* Panel */}
      <div style={{
        width: 280,
        background: 'rgba(7,10,18,0.93)',
        backdropFilter: 'blur(20px)',
        borderRight: '1px solid rgba(6,182,212,0.2)',
        borderBottom: '1px solid rgba(6,182,212,0.15)',
        display: 'flex',
        flexDirection: 'column',
        maxHeight: 'calc(100vh - 120px)',
        fontFamily: "'Space Mono', monospace",
      }}>
        {/* Header */}
        <div style={{
          padding: '12px 16px',
          borderBottom: '1px solid rgba(6,182,212,0.12)',
          background: 'linear-gradient(135deg, rgba(6,182,212,0.08), transparent)',
        }}>
          <div style={{ fontSize: 10, color: '#06b6d4', letterSpacing: 2, marginBottom: 8 }}>
            📡 EVENTOS OSINT — VIVO
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              onClick={handleReplay}
              disabled={replayActive || events.length === 0}
              style={{
                flex: 1, padding: '5px 0', borderRadius: 4,
                background: replayActive ? 'rgba(6,182,212,0.3)' : 'rgba(6,182,212,0.1)',
                border: '1px solid rgba(6,182,212,0.4)', color: '#06b6d4',
                fontSize: 9, cursor: events.length > 0 ? 'pointer' : 'not-allowed',
                fontFamily: 'inherit', letterSpacing: 1,
                transition: 'background 0.2s',
              }}
            >
              {replayActive ? '⏳ REPLAY…' : '▶ REPLAY ALL'}
            </button>
            <button
              onClick={onSaveSimulation}
              disabled={events.length === 0}
              style={{
                flex: 1, padding: '5px 0', borderRadius: 4,
                background: 'rgba(168,85,247,0.1)',
                border: '1px solid rgba(168,85,247,0.4)', color: '#a855f7',
                fontSize: 9, cursor: events.length > 0 ? 'pointer' : 'not-allowed',
                fontFamily: 'inherit', letterSpacing: 1,
              }}
            >
              💾 GUARDAR
            </button>
          </div>
        </div>

        {/* Event list */}
        <div style={{ overflowY: 'auto', flex: 1 }}>
          {events.length === 0 ? (
            <div style={{
              padding: 24, textAlign: 'center',
              color: '#334155', fontSize: 11,
            }}>
              Sin eventos registrados.<br />
              <span style={{ fontSize: 9, color: '#1e293b' }}>
                Envía un TACTICAL_SIMULATION para comenzar.
              </span>
            </div>
          ) : (
            [...events].reverse().map((ev, i) => {
              const style = EVENT_TYPE_STYLE[ev.event_type] || { color: '#94a3b8', icon: '📌' };
              return (
                <div
                  key={ev.id || i}
                  onClick={() => onEventClick?.(ev)}
                  style={{
                    padding: '10px 16px',
                    borderBottom: '1px solid rgba(255,255,255,0.04)',
                    cursor: 'pointer',
                    transition: 'background 0.15s',
                    display: 'flex',
                    gap: 10,
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(6,182,212,0.06)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  {/* Type icon dot */}
                  <div style={{
                    width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
                    background: `${style.color}22`,
                    border: `1px solid ${style.color}55`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 12,
                  }}>
                    {style.icon}
                  </div>
                  {/* Content */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 11, color: '#e2e8f0', fontWeight: 600, marginBottom: 2 }} className="truncate">
                      {ev.target || ev.titulo || 'Evento OSINT'}
                    </div>
                    <div style={{ fontSize: 9, color: '#64748b' }}>
                      {ev.country || '—'} · {ev.event_type || '—'}
                    </div>
                    <div style={{ fontSize: 9, color: '#334155', marginTop: 2 }}>
                      {formatTime(ev.timestamp)}
                    </div>
                  </div>
                  {/* Severity dot */}
                  <div style={{
                    width: 8, height: 8, borderRadius: '50%', flexShrink: 0, marginTop: 3,
                    background: (ev.severity || 0) >= 0.8 ? '#ef4444'
                      : (ev.severity || 0) >= 0.5 ? '#f97316' : '#eab308',
                    boxShadow: `0 0 6px ${(ev.severity || 0) >= 0.8 ? '#ef4444' : '#f97316'}`,
                  }} />
                </div>
              );
            })
          )}
        </div>

        {/* Footer count */}
        <div style={{
          padding: '8px 16px',
          borderTop: '1px solid rgba(255,255,255,0.04)',
          fontSize: 9, color: '#334155', textAlign: 'center',
        }}>
          {events.length} evento{events.length !== 1 ? 's' : ''} registrado{events.length !== 1 ? 's' : ''}
        </div>
      </div>
    </div>
  );
}
