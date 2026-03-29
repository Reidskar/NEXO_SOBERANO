import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Search, GitBranch, Clock, List, Brain } from 'lucide-react';

const API = import.meta.env.VITE_API_BASE_URL?.replace('/api','') || '';

const DOMAIN_COLORS = {
  geo:      '#22d3ee',
  conducta: '#a78bfa',
  masas:    '#d4a017',
  eco_aus:  '#4ade80',
  poder:    '#c0392b',
  osint:    '#fbbf24',
  libre:    '#888888',
};
const DOMAIN_LABELS = {
  geo:'Geopolítica', conducta:'Conducta', masas:'Control Masas',
  eco_aus:'Economía Aus.', poder:'Poder', osint:'OSINT', libre:'Libre',
};

const mono = "'Space Mono', monospace";
const C = {
  bg:'#080808', bg2:'#0f0f0f', bg3:'#141414',
  border:'#1a1a1a', green:'#4ade80', red:'#c0392b',
  amber:'#d4a017', cyan:'#22d3ee', text:'#e5e5e5', muted:'#888', dim:'#444',
};

function loadSessions() {
  try { return JSON.parse(localStorage.getItem('nexo_sessions') || '[]'); } catch { return []; }
}

// Posición determinística radial para grafo
function nodePos(index, total, cx = 380, cy = 240, r = 190) {
  if (total === 0) return { x: cx, y: cy };
  if (total === 1) return { x: cx, y: cy };
  const angle = (index / total) * 2 * Math.PI - Math.PI / 2;
  const jitter = ((index * 7919) % 40) - 20; // pseudo-random jitter
  return {
    x: cx + (r + jitter) * Math.cos(angle),
    y: cy + (r * 0.75 + jitter * 0.5) * Math.sin(angle),
  };
}

// ── Componente Grafo SVG ──────────────────────────────────────────────────────
function SessionGraph({ sessions, selected, onSelect }) {
  const total = sessions.length;

  if (total === 0) {
    return (
      <div style={{ flex:1, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:12 }}>
        <Brain size={32} color={C.dim}/>
        <div style={{ fontFamily:mono, fontSize:10, color:C.dim, textAlign:'center', lineHeight:1.8 }}>
          Sin sesiones indexadas.<br/>
          <Link to="/control/sesion" style={{ color:C.green, textDecoration:'none' }}>→ Crear primera sesión</Link>
        </div>
      </div>
    );
  }

  const positions = sessions.map((_, i) => nodePos(i, total));

  return (
    <div style={{ flex:1, position:'relative', overflow:'hidden' }}>
      <svg viewBox="0 0 760 480" style={{ width:'100%', height:'100%' }} preserveAspectRatio="xMidYMid meet">
        {/* Conexiones entre mismos dominios */}
        {sessions.map((s, i) =>
          sessions.slice(i + 1).map((t, j) => {
            const ti = i + 1 + j;
            if (s.domain !== t.domain) return null;
            const p1 = positions[i], p2 = positions[ti];
            const color = DOMAIN_COLORS[s.domain] || C.dim;
            return (
              <line key={`${i}-${ti}`}
                x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                stroke={color} strokeOpacity={0.12} strokeWidth={1}
                strokeDasharray="3 4"/>
            );
          })
        )}

        {/* Nodos */}
        {sessions.map((s, i) => {
          const { x, y } = positions[i];
          const color = DOMAIN_COLORS[s.domain] || C.dim;
          const isSel = selected?.id === s.id;
          const label = (s.nombre || '').slice(0, 13);
          const r = isSel ? 22 : 17;
          return (
            <g key={s.id} onClick={() => onSelect(s)} style={{ cursor:'pointer' }}>
              {isSel && (
                <circle cx={x} cy={y} r={r + 6} fill="none" stroke={color} strokeWidth={1} strokeOpacity={0.3}
                  style={{ animation:'pulse-ring 2s infinite' }}/>
              )}
              <circle cx={x} cy={y} r={r}
                fill={`${color}18`} stroke={color}
                strokeWidth={isSel ? 2 : 1}
                strokeOpacity={isSel ? 1 : 0.5}/>
              <text x={x} y={y + 1} textAnchor="middle" dominantBaseline="middle"
                style={{ fontFamily:mono, fontSize: isSel ? 8 : 7, fill: isSel ? color : '#888', pointerEvents:'none' }}>
                {label}
              </text>
              <text x={x} y={y + r + 10} textAnchor="middle"
                style={{ fontFamily:mono, fontSize:6, fill:'#444', pointerEvents:'none' }}>
                {DOMAIN_LABELS[s.domain] || s.domain}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Leyenda */}
      <div style={{ position:'absolute', bottom:12, right:12, display:'flex', flexDirection:'column', gap:4 }}>
        {Object.entries(DOMAIN_COLORS).map(([d, color]) => {
          const count = sessions.filter(s => s.domain === d).length;
          if (count === 0) return null;
          return (
            <div key={d} style={{ display:'flex', alignItems:'center', gap:5 }}>
              <span style={{ width:7, height:7, borderRadius:'50%', background:color, flexShrink:0 }}/>
              <span style={{ fontFamily:mono, fontSize:7, color:'#555' }}>{DOMAIN_LABELS[d]} ({count})</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Componente Timeline ───────────────────────────────────────────────────────
function SessionTimeline({ sessions, selected, onSelect }) {
  const sorted = [...sessions].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

  if (sorted.length === 0) {
    return (
      <div style={{ flex:1, display:'flex', alignItems:'center', justifyContent:'center' }}>
        <span style={{ fontFamily:mono, fontSize:10, color:C.dim }}>Sin sesiones</span>
      </div>
    );
  }

  return (
    <div style={{ flex:1, overflowY:'auto', padding:'16px 24px' }}>
      {sorted.map((s, i) => {
        const color = DOMAIN_COLORS[s.domain] || C.dim;
        const isSel = selected?.id === s.id;
        const firstUserMsg = (s.messages || []).find(m => m.role === 'user');
        const dt = new Date(s.created_at);
        const dateStr = dt.toLocaleDateString('es-CL', { day:'2-digit', month:'short' });
        const timeStr = dt.toLocaleTimeString('es-CL', { hour:'2-digit', minute:'2-digit' });
        const msgCount = (s.messages || []).filter(m => m.role !== 'system').length;

        return (
          <div key={s.id} style={{ display:'flex', gap:16, marginBottom:0 }}>
            {/* Línea temporal */}
            <div style={{ display:'flex', flexDirection:'column', alignItems:'center', flexShrink:0, width:60 }}>
              <div style={{ fontFamily:mono, fontSize:8, color:C.dim, textAlign:'right', lineHeight:1.4 }}>
                <div>{dateStr}</div>
                <div>{timeStr}</div>
              </div>
            </div>
            <div style={{ display:'flex', flexDirection:'column', alignItems:'center', flexShrink:0 }}>
              <div style={{ width:10, height:10, borderRadius:'50%', background:color, border:`2px solid ${color}`, flexShrink:0, marginTop:2 }}/>
              {i < sorted.length - 1 && <div style={{ width:1, flex:1, background:`${color}30`, minHeight:20 }}/>}
            </div>
            {/* Card */}
            <div onClick={() => onSelect(s)}
              style={{ flex:1, padding:'8px 12px', marginBottom:12, cursor:'pointer',
                background: isSel ? `${color}08` : C.bg2,
                border:`1px solid ${isSel ? color : C.border}`,
                borderRadius:2, transition:'all .12s' }}
              onMouseEnter={e => { if (!isSel) e.currentTarget.style.background = C.bg3; }}
              onMouseLeave={e => { if (!isSel) e.currentTarget.style.background = C.bg2; }}
            >
              <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:4 }}>
                <span style={{ fontFamily:mono, fontSize:10, color: isSel ? color : C.text }}>{s.nombre}</span>
                <div style={{ display:'flex', gap:6, alignItems:'center' }}>
                  <span style={{ fontFamily:mono, fontSize:7, color, border:`1px solid ${color}30`, padding:'1px 6px' }}>{DOMAIN_LABELS[s.domain] || s.domain}</span>
                  <span style={{ fontFamily:mono, fontSize:7, color:C.dim }}>{msgCount} msg</span>
                </div>
              </div>
              {firstUserMsg && (
                <div style={{ fontFamily:mono, fontSize:9, color:C.muted, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                  {firstUserMsg.text?.substring(0, 80)}...
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Componente Índice ─────────────────────────────────────────────────────────
function SessionIndex({ sessions, selected, onSelect }) {
  const [expanded, setExpanded] = useState(null);

  if (sessions.length === 0) {
    return (
      <div style={{ flex:1, display:'flex', alignItems:'center', justifyContent:'center' }}>
        <span style={{ fontFamily:mono, fontSize:10, color:C.dim }}>Sin sesiones</span>
      </div>
    );
  }

  return (
    <div style={{ flex:1, overflowY:'auto', padding:16 }}>
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:8 }}>
        {sessions.map(s => {
          const color = DOMAIN_COLORS[s.domain] || C.dim;
          const isSel = selected?.id === s.id;
          const isExp = expanded === s.id;
          const userMsgs = (s.messages || []).filter(m => m.role === 'user');
          const lastMsg = userMsgs[userMsgs.length - 1];

          return (
            <div key={s.id}
              style={{ background: isSel ? `${color}08` : C.bg2, border:`1px solid ${isSel ? color : C.border}`, borderRadius:2, overflow:'hidden' }}>
              <div onClick={() => { onSelect(s); setExpanded(isExp ? null : s.id); }}
                style={{ padding:'10px 12px', cursor:'pointer' }}
                onMouseEnter={e => e.currentTarget.style.background = `${color}06`}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:4 }}>
                  <span style={{ fontFamily:mono, fontSize:10, color: isSel ? color : C.text, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap', maxWidth:120 }}>{s.nombre}</span>
                  <span style={{ fontFamily:mono, fontSize:7, color:C.dim }}>{isExp ? '▲' : '▼'}</span>
                </div>
                <div style={{ display:'flex', gap:6, marginBottom:4 }}>
                  <span style={{ fontFamily:mono, fontSize:7, color, border:`1px solid ${color}25`, padding:'1px 5px' }}>{DOMAIN_LABELS[s.domain] || s.domain}</span>
                  <span style={{ fontFamily:mono, fontSize:7, color: s.estado==='activa' ? C.green : C.dim }}>● {s.estado}</span>
                </div>
                {lastMsg && (
                  <div style={{ fontFamily:mono, fontSize:8, color:C.muted, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                    {lastMsg.text?.substring(0, 60)}...
                  </div>
                )}
              </div>

              {isExp && (
                <div style={{ borderTop:`1px solid ${C.border}`, maxHeight:180, overflowY:'auto' }}>
                  {(s.messages || []).filter(m => m.role !== 'system').map((m, mi) => (
                    <div key={mi} style={{ padding:'6px 12px', borderBottom:`1px solid ${C.border}` }}>
                      <div style={{ fontFamily:mono, fontSize:7, color: m.role==='user' ? C.green : C.muted, marginBottom:2 }}>
                        {m.role === 'user' ? '› ANALISTA' : '◈ NEXO'}
                      </div>
                      <div style={{ fontFamily:mono, fontSize:8, color:'#666', lineHeight:1.5 }}>
                        {m.text?.substring(0, 120)}{m.text?.length > 120 ? '...' : ''}
                      </div>
                    </div>
                  ))}
                  {(s.messages || []).filter(m => m.role !== 'system').length === 0 && (
                    <div style={{ padding:'8px 12px', fontFamily:mono, fontSize:8, color:C.dim }}>Sin mensajes</div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Panel de detalle de sesión ────────────────────────────────────────────────
function DetailPanel({ session, onSearch }) {
  if (!session) return (
    <div style={{ width:280, borderLeft:`1px solid ${C.border}`, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
      <div style={{ fontFamily:mono, fontSize:9, color:C.dim, textAlign:'center', padding:16, lineHeight:1.8 }}>
        Selecciona una sesión<br/>para ver el detalle
      </div>
    </div>
  );

  const color = DOMAIN_COLORS[session.domain] || C.dim;
  const msgs = (session.messages || []).filter(m => m.role !== 'system');

  return (
    <div style={{ width:280, borderLeft:`1px solid ${C.border}`, display:'flex', flexDirection:'column', flexShrink:0, overflow:'hidden' }}>
      {/* Header */}
      <div style={{ padding:'12px 14px', borderBottom:`1px solid ${C.border}`, flexShrink:0 }}>
        <div style={{ fontFamily:mono, fontSize:11, color, marginBottom:4, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{session.nombre}</div>
        <div style={{ display:'flex', gap:6 }}>
          <span style={{ fontFamily:mono, fontSize:7, color, border:`1px solid ${color}30`, padding:'1px 6px' }}>{DOMAIN_LABELS[session.domain]}</span>
          <span style={{ fontFamily:mono, fontSize:7, color: session.estado==='activa' ? C.green : C.dim }}>● {session.estado}</span>
        </div>
        {session.tema && (
          <div style={{ fontFamily:mono, fontSize:8, color:C.muted, marginTop:6, lineHeight:1.5 }}>{session.tema}</div>
        )}
        <div style={{ fontFamily:mono, fontSize:7, color:C.dim, marginTop:4 }}>
          {new Date(session.created_at).toLocaleString('es-CL')}
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex:1, overflowY:'auto', padding:'8px 0' }}>
        {msgs.length === 0 && (
          <div style={{ padding:'12px 14px', fontFamily:mono, fontSize:9, color:C.dim }}>Sin mensajes</div>
        )}
        {msgs.map((m, i) => (
          <div key={i} style={{ padding:'6px 14px', borderBottom:`1px solid ${C.border}` }}>
            <div style={{ fontFamily:mono, fontSize:7, color: m.role==='user' ? C.green : '#a78bfa', marginBottom:2 }}>
              {m.role === 'user' ? '› ANALISTA' : '◈ NEXO'}
            </div>
            <div style={{ fontFamily:mono, fontSize:9, color:'#666', lineHeight:1.5 }}>
              {m.text?.substring(0, 150)}{m.text?.length > 150 ? '…' : ''}
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div style={{ padding:'10px 14px', borderTop:`1px solid ${C.border}`, flexShrink:0 }}>
        <button onClick={() => onSearch(session.tema || session.nombre)}
          style={{ width:'100%', padding:'6px', fontFamily:mono, fontSize:8, color:C.cyan, background:`rgba(34,211,238,0.06)`, border:`1px solid rgba(34,211,238,0.2)`, cursor:'pointer', letterSpacing:'.08em' }}>
          BUSCAR SIMILARES →
        </button>
      </div>
    </div>
  );
}

// ── Componente principal ──────────────────────────────────────────────────────
export default function Memoria() {
  const [sessions, setSessions]       = useState(loadSessions);
  const [selected, setSelected]       = useState(null);
  const [tab, setTab]                 = useState('grafo');
  const [searchQ, setSearchQ]         = useState('');
  const [searchRes, setSearchRes]     = useState([]);
  const [searching, setSearching]     = useState(false);

  // Refresh desde localStorage cada 5s
  useEffect(() => {
    const id = setInterval(() => setSessions(loadSessions()), 5000);
    return () => clearInterval(id);
  }, []);

  const doSearch = useCallback(async (q = searchQ) => {
    if (!q.trim()) return;
    setSearching(true);
    try {
      if (API) {
        const r = await fetch(`${API}/api/sesiones/buscar`, {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ query: q }),
          signal: AbortSignal.timeout(8000)
        });
        if (r.ok) {
          const d = await r.json();
          setSearchRes(d.resultados || []);
          setSearching(false);
          return;
        }
      }
    } catch {}
    // Fallback local
    const qL = q.toLowerCase();
    const res = sessions.flatMap(s =>
      (s.messages || [])
        .filter(m => m.text?.toLowerCase().includes(qL))
        .slice(0, 2)
        .map(m => ({ sesion_nombre: s.nombre, contenido: m.text, domain: s.domain }))
    );
    setSearchRes(res.slice(0, 15));
    setSearching(false);
  }, [searchQ, sessions]);

  const totalMsgs = sessions.reduce((a, s) => a + (s.messages || []).filter(m => m.role !== 'system').length, 0);
  const activeSessions = sessions.filter(s => s.estado === 'activa').length;

  const TABS = [
    { id:'grafo',    label:'GRAFO',    icon:GitBranch },
    { id:'timeline', label:'TIMELINE', icon:Clock     },
    { id:'indice',   label:'ÍNDICE',   icon:List      },
  ];

  return (
    <div style={{ height:'100vh', display:'flex', flexDirection:'column', background:C.bg, color:C.text, overflow:'hidden' }}>
      <style>{`
        @keyframes pulse-ring { 0%,100%{opacity:0.4;r:26} 50%{opacity:0.1;r:30} }
        ::-webkit-scrollbar{width:3px} ::-webkit-scrollbar-track{background:#0a0a0a} ::-webkit-scrollbar-thumb{background:#1c1c1c}
      `}</style>

      {/* Header */}
      <div style={{ padding:'10px 20px', borderBottom:`1px solid ${C.border}`, display:'flex', alignItems:'center', gap:12, flexShrink:0 }}>
        <Brain size={15} color={C.green}/>
        <span style={{ fontFamily:mono, fontSize:12, fontWeight:700, letterSpacing:'.1em' }}>MEMORIA SEMÁNTICA</span>
        <span style={{ fontFamily:mono, fontSize:8, color:C.dim }}>NEXO SOBERANO · GRAFO COGNITIVO</span>
      </div>

      <div style={{ flex:1, display:'flex', overflow:'hidden' }}>

        {/* ── Panel izquierdo ── */}
        <div style={{ width:280, borderRight:`1px solid ${C.border}`, display:'flex', flexDirection:'column', overflow:'hidden', flexShrink:0 }}>

          {/* Búsqueda */}
          <div style={{ padding:'12px 12px 8px', borderBottom:`1px solid ${C.border}`, flexShrink:0 }}>
            <div style={{ fontFamily:mono, fontSize:7, color:C.dim, letterSpacing:'.15em', marginBottom:8 }}>BÚSQUEDA SEMÁNTICA</div>
            <div style={{ display:'flex', gap:4 }}>
              <input value={searchQ} onChange={e=>setSearchQ(e.target.value)}
                onKeyDown={e=>e.key==='Enter'&&doSearch()}
                placeholder="buscar en memoria..." style={{ flex:1, background:C.bg2, border:`1px solid ${C.border}`, color:C.text, padding:'6px 8px', fontSize:9, outline:'none', fontFamily:mono }}
                onFocus={e=>e.target.style.borderColor=C.cyan+'40'}
                onBlur={e=>e.target.style.borderColor=C.border}/>
              <button onClick={()=>doSearch()} style={{ padding:'6px 10px', background:`rgba(34,211,238,0.08)`, border:`1px solid rgba(34,211,238,0.2)`, color:C.cyan, cursor:'pointer', fontSize:9 }}>
                <Search size={11}/>
              </button>
            </div>
          </div>

          {/* Resultados */}
          {searchRes.length > 0 && (
            <div style={{ borderBottom:`1px solid ${C.border}`, flexShrink:0, maxHeight:200, overflowY:'auto' }}>
              <div style={{ padding:'6px 12px', fontFamily:mono, fontSize:7, color:C.dim, letterSpacing:'.1em' }}>
                {searching ? 'BUSCANDO...' : `${searchRes.length} RESULTADOS`}
              </div>
              {searchRes.map((r, i) => {
                const color = DOMAIN_COLORS[r.domain] || C.dim;
                return (
                  <div key={i} style={{ padding:'6px 12px', borderBottom:`1px solid ${C.border}` }}>
                    <div style={{ fontFamily:mono, fontSize:8, color, marginBottom:2 }}>{r.sesion_nombre}</div>
                    <div style={{ fontFamily:mono, fontSize:8, color:'#555', lineHeight:1.4 }}>
                      {(r.contenido || r.text || '').substring(0, 90)}...
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Lista sesiones */}
          <div style={{ flex:1, overflowY:'auto' }}>
            <div style={{ padding:'8px 12px', fontFamily:mono, fontSize:7, color:C.dim, letterSpacing:'.15em', borderBottom:`1px solid ${C.border}` }}>
              SESIONES ({sessions.length})
            </div>
            {sessions.length === 0 && (
              <div style={{ padding:'16px 12px', fontFamily:mono, fontSize:9, color:C.dim, lineHeight:1.7 }}>
                Sin sesiones.<br/>
                <Link to="/control/sesion" style={{ color:C.green, textDecoration:'none' }}>→ Crear sesión</Link>
              </div>
            )}
            {[...sessions].sort((a,b) => new Date(b.created_at)-new Date(a.created_at)).map(s => {
              const color = DOMAIN_COLORS[s.domain] || C.dim;
              const isSel = selected?.id === s.id;
              return (
                <div key={s.id} onClick={() => setSelected(s)}
                  style={{ padding:'8px 12px', borderBottom:`1px solid ${C.border}`, cursor:'pointer',
                    background: isSel ? `${color}08` : 'transparent',
                    borderLeft: isSel ? `2px solid ${color}` : '2px solid transparent',
                    transition:'all .1s' }}
                  onMouseEnter={e => { if (!isSel) e.currentTarget.style.background = C.bg3; }}
                  onMouseLeave={e => { if (!isSel) e.currentTarget.style.background = 'transparent'; }}
                >
                  <div style={{ fontFamily:mono, fontSize:10, color: isSel ? color : C.text, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap', marginBottom:3 }}>{s.nombre}</div>
                  <div style={{ display:'flex', gap:5, alignItems:'center' }}>
                    <span style={{ fontFamily:mono, fontSize:7, color, border:`1px solid ${color}25`, padding:'1px 5px' }}>{DOMAIN_LABELS[s.domain] || s.domain}</span>
                    <span style={{ fontFamily:mono, fontSize:7, color:C.dim }}>{new Date(s.created_at).toLocaleDateString('es-CL')}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Stats */}
          <div style={{ padding:'10px 12px', borderTop:`1px solid ${C.border}`, display:'flex', flexDirection:'column', gap:4, flexShrink:0 }}>
            {[
              { label:'SESIONES TOTALES', val: sessions.length, color:C.green },
              { label:'INTERCAMBIOS',     val: totalMsgs,       color:C.amber },
              { label:'ACTIVAS',          val: activeSessions,  color:C.cyan  },
            ].map(s => (
              <div key={s.label} style={{ display:'flex', justifyContent:'space-between' }}>
                <span style={{ fontFamily:mono, fontSize:7, color:C.dim, letterSpacing:'.08em' }}>{s.label}</span>
                <span style={{ fontFamily:mono, fontSize:7, color:s.color }}>{s.val}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ── Panel principal ── */}
        <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
          {/* Tabs */}
          <div style={{ display:'flex', borderBottom:`1px solid ${C.border}`, flexShrink:0 }}>
            {TABS.map(t => {
              const Icon = t.icon;
              return (
                <button key={t.id} onClick={() => setTab(t.id)} style={{
                  display:'flex', alignItems:'center', gap:6,
                  padding:'9px 18px', cursor:'pointer', border:'none',
                  background: tab===t.id ? `rgba(74,222,128,0.05)` : 'transparent',
                  borderBottom: tab===t.id ? `2px solid ${C.green}` : '2px solid transparent',
                  color: tab===t.id ? C.green : C.muted,
                  fontFamily:mono, fontSize:9, letterSpacing:'.08em',
                }}>
                  <Icon size={11}/> {t.label}
                </button>
              );
            })}
          </div>

          {/* Vista */}
          <div style={{ flex:1, display:'flex', overflow:'hidden' }}>
            <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
              {tab === 'grafo'    && <SessionGraph    sessions={sessions} selected={selected} onSelect={setSelected}/>}
              {tab === 'timeline' && <SessionTimeline sessions={sessions} selected={selected} onSelect={setSelected}/>}
              {tab === 'indice'   && <SessionIndex    sessions={sessions} selected={selected} onSelect={setSelected}/>}
            </div>

            {/* Panel detalle */}
            <DetailPanel session={selected} onSearch={q => { setSearchQ(q); doSearch(q); }}/>
          </div>
        </div>
      </div>
    </div>
  );
}
