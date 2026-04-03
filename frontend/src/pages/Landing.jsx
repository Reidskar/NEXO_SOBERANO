import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';

// ─── Config ───────────────────────────────────────────────────────────────────
const API = import.meta.env.VITE_API_BASE_URL?.replace('/api','') || '';

// ─── Static feed ──────────────────────────────────────────────────────────────
const STATIC_FEED = [
  { id:1,  cat:'MILITAR',     region:'APAC',           title:'China despliega 3 portaaviones frente a Taiwán en maniobras no anunciadas',  src:'OSINT / Sentinel-2',  time:'04m', hot:true  },
  { id:2,  cat:'ECONÓMICO',   region:'EE.UU.',          title:'S&P 500 cae 1.4% tras datos de empleo peor de lo esperado por la Fed',        src:'Bloomberg / Reuters', time:'08m', hot:false },
  { id:3,  cat:'POLÍTICO',    region:'G20',             title:'Cumbre G20 Johannesburgo: borrador de acuerdo energético en circulación',      src:'Reuters',             time:'12m', hot:false },
  { id:4,  cat:'OSINT',       region:'Sudán',           title:'Imágenes satelitales confirman movimiento de blindados en Darfur Norte',       src:'NEXO IA / Planet',    time:'18m', hot:true  },
  { id:5,  cat:'GEOPOLÍTICO', region:'Europa',          title:'OTAN activa protocolo de vigilancia reforzada en el Mar Báltico',             src:'DW / NEXO OSINT',     time:'25m', hot:false },
  { id:6,  cat:'MILITAR',     region:'Medio Oriente',   title:'Intercepción registrada sobre espacio aéreo libanés — fuentes regionales',    src:'OSINT',               time:'31m', hot:true  },
  { id:7,  cat:'ECONÓMICO',   region:'China',           title:'Yuan bajo presión: PBoC fija tasa referencia en mínimo de 14 meses',          src:'Caixin / Xinhua',     time:'40m', hot:false },
  { id:8,  cat:'POLÍTICO',    region:'Latinoamérica',   title:'Venezuela: oposición rechaza decreto de emergencia emitido anoche',           src:'NEXO OSINT',           time:'55m', hot:false },
  { id:9,  cat:'OSINT',       region:'Rusia',           title:'Actividad inusual detectada cerca de base aérea Engels-2 — ADSB oscuro',      src:'OSINT / FlightAware', time:'1h',  hot:true  },
  { id:10, cat:'GEOPOLÍTICO', region:'África',          title:'Junta militar de Mali expulsa embajador francés — escalada diplomática',      src:'AFP / Le Monde',      time:'1h20',hot:false },
];

const CATS = ['TODOS','MILITAR','POLÍTICO','ECONÓMICO','GEOPOLÍTICO','OSINT'];

const TICKER = [
  'BREAKING · Maniobras navales APAC en curso — 3 CVN desplegados',
  'OSINT · 2,400+ fuentes sincronizadas · latencia 1.2s',
  'IA · 78 consultas procesadas hoy · RAG vectorial activo',
  'ALERTA · Tensión elevada — estrecho de Taiwán y Mar Báltico',
  'ADS-B · 12,480 aeronaves monitoreadas en tiempo real',
  'NEXO · 3 agentes autónomos activos · memoria Qdrant online',
];

// Hotspots mapa (lat/lon + datos)
const HOTSPOTS = [
  { id:'apac',    name:'Estrecho de Taiwán', lat:24,   lon:120,  threat:5, cat:'MILITAR',     events:7,  desc:'3 CVN + maniobras anfibias'      },
  { id:'baltico', name:'Mar Báltico',        lat:57,   lon:21,   threat:4, cat:'MILITAR',     events:4,  desc:'OTAN protocolo reforzado'        },
  { id:'oriente', name:'Líbano / Siria',     lat:33,   lon:35.5, threat:4, cat:'MILITAR',     events:5,  desc:'Intercepción espacio aéreo'      },
  { id:'darfur',  name:'Darfur Norte',       lat:14,   lon:24,   threat:3, cat:'OSINT',       events:3,  desc:'Blindados confirmar sat. Planet'  },
  { id:'engels',  name:'Engels-2 Base',      lat:51.4, lon:46.1, threat:3, cat:'OSINT',       events:2,  desc:'ADSB oscuro — actividad anómala'  },
  { id:'venezuel',name:'Venezuela',          lat:8,    lon:-66,  threat:2, cat:'POLÍTICO',    events:3,  desc:'Decreto emergencia rechazado'     },
  { id:'mali',    name:'Mali',               lat:17,   lon:-4,   threat:2, cat:'GEOPOLÍTICO', events:2,  desc:'Expulsión embajador francés'     },
  { id:'scs',     name:'Mar del Sur China',  lat:15,   lon:115,  threat:4, cat:'MILITAR',     events:6,  desc:'Patrullaje conflictivo SCS'       },
];

// Amenaza → color
const THREAT_COLOR = { 5:'#c0392b', 4:'#c77d28', 3:'#d4a017', 2:'#6b7240', 1:'#3a5436' };
function catColor(c) {
  return { MILITAR:'#c0392b', POLÍTICO:'#94a3a8', ECONÓMICO:'#4ade80', GEOPOLÍTICO:'#d4a017', OSINT:'#9ca3af' }[c] ?? '#888888';
}
function threatLabel(t) { return ['BAJO','BAJO','MEDIO','ELEVADO','ALTO','CRÍTICO'][t] ?? 'N/A'; }
function latLonToXY(lat, lon, w, h) {
  const x = ((lon + 180) / 360) * w;
  const y = ((90 - lat) / 180) * h;
  return { x, y };
}

function useIsMobile() {
  const [m, setM] = useState(window.innerWidth < 1024);
  useEffect(() => { const fn=()=>setM(window.innerWidth<1024); window.addEventListener('resize',fn); return()=>window.removeEventListener('resize',fn); },[]);
  return m;
}
function useNow() {
  const [t, setT] = useState(new Date());
  useEffect(() => { const iv=setInterval(()=>setT(new Date()),1000); return()=>clearInterval(iv); },[]);
  return t.toLocaleString('es-CL',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit'});
}

// ─── Ticker ───────────────────────────────────────────────────────────────────
function Ticker() {
  const [i,setI]=useState(0);
  useEffect(()=>{const t=setInterval(()=>setI(x=>(x+1)%TICKER.length),3800);return()=>clearInterval(t);},[]);
  return (
    <div style={{background:'#060606',borderBottom:'1px solid #161616',padding:'5px 20px',display:'flex',alignItems:'center',gap:14,overflow:'hidden'}}>
      <span style={{fontFamily:'monospace',fontSize:9,color:'#c0392b',letterSpacing:'.2em',whiteSpace:'nowrap',borderRight:'1px solid #1c1c1c',paddingRight:12,flexShrink:0}}>SEÑAL</span>
      <span key={i} style={{fontFamily:'monospace',fontSize:11,color:'#555555',flex:1,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{TICKER[i]}</span>
      <span style={{fontFamily:'monospace',fontSize:9,color:'#333333',whiteSpace:'nowrap',display:'flex',alignItems:'center',gap:5,flexShrink:0}}>
        <span style={{width:5,height:5,borderRadius:'50%',background:'#4ade80',display:'inline-block',animation:'blink-dot 1.5s infinite'}}/>LIVE
      </span>
    </div>
  );
}

// ─── World Threat Map ─────────────────────────────────────────────────────────
function WorldMap({ onSelect, selected }) {
  const containerRef = useRef(null);
  const [dims, setDims] = useState({ w: 600, h: 300 });
  const [tooltip, setTooltip] = useState(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect;
      setDims({ w: width, h: height });
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  const spots = HOTSPOTS.map(h => ({ ...h, ...latLonToXY(h.lat, h.lon, dims.w, dims.h) }));

  return (
    <div ref={containerRef} style={{ position:'relative', width:'100%', height:240, background:'#080808', borderBottom:'1px solid #1c1c1c', overflow:'hidden', cursor:'crosshair' }}>
      {/* Grid lines */}
      <svg width="100%" height="100%" style={{position:'absolute',top:0,left:0,opacity:0.15}}>
        {[0,30,60,90,120,150].map(lon => (
          <line key={lon} x1={`${((lon+180)/360)*100}%`} y1="0" x2={`${((lon+180)/360)*100}%`} y2="100%" stroke="#2a2a2a" strokeWidth="0.5"/>
        ))}
        {[-60,-30,0,30,60].map(lat => (
          <line key={lat} x1="0" y1={`${((90-lat)/180)*100}%`} x2="100%" y2={`${((90-lat)/180)*100}%`} stroke="#2a2a2a" strokeWidth="0.5"/>
        ))}
        {/* Equator */}
        <line x1="0" y1="50%" x2="100%" y2="50%" stroke="#2a4a2a" strokeWidth="0.8"/>
        {/* Prime meridian */}
        <line x1="50%" y1="0" x2="50%" y2="100%" stroke="#2a4a2a" strokeWidth="0.8"/>
      </svg>

      {/* Labels */}
      <div style={{position:'absolute',bottom:4,left:8,fontFamily:'monospace',fontSize:8,color:'#222222',letterSpacing:'.1em'}}>MAPA GLOBAL · AMENAZAS ACTIVAS · {HOTSPOTS.length} ZONAS MONITOREADAS</div>

      {/* Hotspot markers */}
      {spots.map(h => {
        const isSelected = selected?.id === h.id;
        const color = THREAT_COLOR[h.threat] || '#4ade80';
        return (
          <div
            key={h.id}
            style={{ position:'absolute', left: h.x - 8, top: h.y - 8, width:16, height:16, cursor:'pointer', zIndex:10 }}
            onClick={() => onSelect(isSelected ? null : h)}
            onMouseEnter={() => setTooltip(h)}
            onMouseLeave={() => setTooltip(null)}
          >
            {/* Pulse ring */}
            <div style={{
              position:'absolute', width:16, height:16, borderRadius:'50%',
              border:`1.5px solid ${color}`, opacity: isSelected ? 1 : 0.6,
              animation: h.threat >= 4 ? 'pulse-ring 2s infinite' : 'none'
            }}/>
            {/* Dot */}
            <div style={{
              position:'absolute', left:'50%', top:'50%', transform:'translate(-50%,-50%)',
              width: isSelected ? 8 : 6, height: isSelected ? 8 : 6,
              borderRadius:'50%', background: color,
              boxShadow: `0 0 ${h.threat * 3}px ${color}`,
              transition:'all .2s'
            }}/>
          </div>
        );
      })}

      {/* Tooltip */}
      {tooltip && (
        <div style={{
          position:'absolute',
          left: Math.min(tooltip.x + 14, dims.w - 180),
          top: Math.max(tooltip.y - 40, 4),
          background:'#0f0f0f', border:`1px solid ${THREAT_COLOR[tooltip.threat]}40`,
          padding:'6px 10px', pointerEvents:'none', zIndex:20, minWidth:160
        }}>
          <div style={{fontFamily:'monospace',fontSize:9,color:THREAT_COLOR[tooltip.threat],letterSpacing:'.1em',marginBottom:2}}>{tooltip.name}</div>
          <div style={{fontFamily:'monospace',fontSize:8,color:'#666666'}}>{tooltip.desc}</div>
          <div style={{fontFamily:'monospace',fontSize:8,color:'#444444',marginTop:2}}>{tooltip.events} eventos · Amenaza {threatLabel(tooltip.threat)}</div>
        </div>
      )}
    </div>
  );
}

// ─── AI Command Panel ─────────────────────────────────────────────────────────
function AICommandPanel() {
  const [messages, setMessages] = useState([
    { role:'system', text:'NEXO IA operativo. Motor RAG + Qdrant activo. Listo para consultas de inteligencia estratégica.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState({ total:0, active:0 });
  const msgEnd = useRef(null);

  useEffect(() => {
    msgEnd.current?.scrollIntoView({ behavior:'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!API) return;
    fetch(`${API}/api/health`, { signal: AbortSignal.timeout(5000) })
      .then(r => r.json())
      .then(d => setAgents({ total: d?.agents?.total_registered || 10, active: d?.agents?.active || 3 }))
      .catch(() => setAgents({ total: 10, active: 3 }));
  }, []);

  const sendQuery = async (text) => {
    if (!text?.trim() || loading) return;
    const q = text.trim();
    setInput('');
    setMessages(m => [...m, { role:'user', text: q }]);
    setLoading(true);
    try {
      const endpoint = API ? `${API}/api/agente/chat` : null;
      if (!endpoint) throw new Error('no-api');
      const r = await fetch(endpoint, {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ message: q, mode:'intelligence' }),
        signal: AbortSignal.timeout(15000)
      });
      const data = await r.json();
      const reply = data?.response || data?.analysis || data?.message || JSON.stringify(data).substring(0,200);
      setMessages(m => [...m, { role:'ai', text: reply }]);
    } catch {
      setMessages(m => [...m, { role:'ai', text:'Backend desconectado. Modo local activo. Conecta el servidor para análisis en tiempo real.' }]);
    } finally {
      setLoading(false);
    }
  };

  const QUICK = ['Situación APAC', 'Análisis mercados', 'Estado del sistema', 'Últimas alertas OSINT'];

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%' }}>
      {/* Header */}
      <div style={{ padding:'10px 14px', borderBottom:'1px solid #1c1c1c', display:'flex', alignItems:'center', justifyContent:'space-between', background:'#0a0a0a' }}>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ width:6, height:6, borderRadius:'50%', background: API ? '#4ade80' : '#c0392b', animation:'blink-dot 2s infinite' }}/>
          <span style={{ fontFamily:'monospace', fontSize:9, color:'#444444', letterSpacing:'.15em', textTransform:'uppercase' }}>NEXO IA · COMANDO</span>
        </div>
        <div style={{ display:'flex', gap:12, alignItems:'center' }}>
          <span style={{ fontFamily:'monospace', fontSize:8, color:'#4ade80' }}>{agents.active} agentes</span>
          <span style={{ fontFamily:'monospace', fontSize:8, color:'#444444' }}>RAG activo</span>
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex:1, overflowY:'auto', padding:'10px 14px', display:'flex', flexDirection:'column', gap:8, maxHeight:220 }}>
        {messages.map((m, i) => (
          <div key={i} style={{
            fontFamily:'monospace', fontSize:11, lineHeight:1.55,
            color: m.role==='user' ? '#e8e8e8' : m.role==='system' ? '#4ade8080' : '#888888',
            padding: m.role==='user' ? '6px 10px' : '0',
            background: m.role==='user' ? '#0f1a0f' : 'transparent',
            borderLeft: m.role==='user' ? '2px solid #4ade8030' : m.role==='ai' ? '2px solid #1c1c1c' : 'none',
            paddingLeft: m.role==='ai' ? 10 : m.role==='user' ? 10 : 0
          }}>
            {m.role === 'user' && <span style={{ color:'#4ade80', marginRight:6, fontSize:9 }}>›</span>}
            {m.role === 'ai' && <span style={{ color:'#444444', marginRight:6, fontSize:9 }}>NEXO</span>}
            {m.role === 'system' && <span style={{ color:'#2a4a2a', marginRight:6, fontSize:9 }}>SYS</span>}
            {m.text}
          </div>
        ))}
        {loading && (
          <div style={{ fontFamily:'monospace', fontSize:10, color:'#4ade8040', paddingLeft:10, borderLeft:'2px solid #1c1c1c' }}>
            <span style={{ animation:'blink-dot 0.8s infinite', display:'inline-block' }}>procesando consulta...</span>
          </div>
        )}
        <div ref={msgEnd}/>
      </div>

      {/* Quick prompts */}
      <div style={{ padding:'6px 14px', display:'flex', gap:4, flexWrap:'wrap', borderTop:'1px solid #111111' }}>
        {QUICK.map(q => (
          <button key={q} onClick={() => sendQuery(q)} style={{
            fontFamily:'monospace', fontSize:8, color:'#444444', background:'none',
            border:'1px solid #1c1c1c', padding:'3px 7px', cursor:'pointer', letterSpacing:'.05em',
            transition:'all .15s'
          }}
            onMouseEnter={e=>{e.currentTarget.style.borderColor='#4ade8040';e.currentTarget.style.color='#4ade80';}}
            onMouseLeave={e=>{e.currentTarget.style.borderColor='#1c1c1c';e.currentTarget.style.color='#444444';}}
          >{q}</button>
        ))}
      </div>

      {/* Input */}
      <div style={{ padding:'8px 14px', borderTop:'1px solid #1c1c1c', background:'#0a0a0a' }}>
        <form onSubmit={e=>{e.preventDefault();sendQuery(input);}} style={{ display:'flex', gap:6 }}>
          <input
            value={input} onChange={e=>setInput(e.target.value)}
            placeholder="Consulta al sistema de inteligencia..."
            disabled={loading}
            style={{
              flex:1, fontFamily:'monospace', fontSize:11, background:'#0f0f0f',
              border:'1px solid #1c1c1c', color:'#e8e8e8', padding:'7px 10px',
              outline:'none', transition:'border-color .15s'
            }}
            onFocus={e=>e.target.style.borderColor='#4ade8040'}
            onBlur={e=>e.target.style.borderColor='#1c1c1c'}
          />
          <button type="submit" disabled={loading || !input.trim()} style={{
            fontFamily:'monospace', fontSize:9, padding:'7px 12px', background:'#4ade8012',
            border:'1px solid #4ade8030', color:'#4ade80', cursor:'pointer', letterSpacing:'.1em',
            transition:'all .15s', opacity: loading || !input.trim() ? 0.4 : 1
          }}>ENVIAR</button>
        </form>
      </div>
    </div>
  );
}

// ─── Live Metrics ─────────────────────────────────────────────────────────────
function LiveMetrics() {
  const [crypto, setCrypto] = useState(null);
  const [flights, setFlights] = useState(null);
  const [health, setHealth] = useState(null);

  const fetchCrypto = useCallback(async () => {
    try {
      const r = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true', { signal: AbortSignal.timeout(6000) });
      if (r.ok) setCrypto(await r.json());
    } catch {}
  }, []);

  useEffect(() => {
    fetchCrypto();
    const iv = setInterval(fetchCrypto, 60000);
    return () => clearInterval(iv);
  }, [fetchCrypto]);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch('https://opensky-network.org/api/states/all?lamin=-60&lomin=-180&lamax=85&lomax=180', { signal: AbortSignal.timeout(8000) });
        if (r.ok) { const d = await r.json(); setFlights(d?.states?.length ?? null); }
      } catch {}
    })();
  }, []);

  useEffect(() => {
    if (!API) return;
    fetch(`${API}/api/health`, { signal: AbortSignal.timeout(5000) })
      .then(r => r.json()).then(setHealth).catch(() => {});
  }, []);

  const coins = [
    { id:'bitcoin', label:'BTC', color:'#d4a017' },
    { id:'ethereum', label:'ETH', color:'#9ca3af' },
    { id:'solana', label:'SOL', color:'#4ade80' },
  ];

  return (
    <div style={{ padding:'10px 14px' }}>
      <div style={{ fontFamily:'monospace', fontSize:8, color:'#333333', letterSpacing:'.15em', textTransform:'uppercase', marginBottom:10 }}>INDICADORES EN VIVO</div>

      {/* API Health row */}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'5px 0', borderBottom:'1px solid #111111' }}>
        <span style={{ fontFamily:'monospace', fontSize:9, color:'#555555' }}>Backend API</span>
        <span style={{ fontFamily:'monospace', fontSize:9, color: health ? '#4ade80' : API ? '#d4a017' : '#666666' }}>
          {health ? `v${health.version || '3.0'} · ONLINE` : API ? 'CONECTANDO' : 'LOCAL MODE'}
        </span>
      </div>
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'5px 0', borderBottom:'1px solid #111111' }}>
        <span style={{ fontFamily:'monospace', fontSize:9, color:'#555555' }}>Agentes IA</span>
        <span style={{ fontFamily:'monospace', fontSize:9, color:'#4ade80' }}>{health?.agents?.total_registered || '10'} registrados</span>
      </div>
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'5px 0', borderBottom:'1px solid #111111' }}>
        <span style={{ fontFamily:'monospace', fontSize:9, color:'#555555' }}>✈ Vuelos activos</span>
        <span style={{ fontFamily:'monospace', fontSize:12, color:'#4ade80', fontWeight:700 }}>{flights ? flights.toLocaleString() : '—'}</span>
      </div>

      {/* Crypto */}
      <div style={{ marginTop:8 }}>
        {coins.map(c => {
          const d = crypto?.[c.id]; const chg = d?.usd_24h_change;
          return (
            <div key={c.id} style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'4px 0', borderBottom:'1px solid #111111' }}>
              <span style={{ fontFamily:'monospace', fontSize:9, color:c.color, fontWeight:700 }}>{c.label}</span>
              <span style={{ fontFamily:'monospace', fontSize:10, color:'#666666' }}>
                {d ? `$${d.usd.toLocaleString('en-US',{maximumFractionDigits:0})}` : '—'}
              </span>
              <span style={{ fontFamily:'monospace', fontSize:9, color: chg>0?'#4ade80':'#c0392b' }}>
                {d ? `${chg>0?'+':''}${chg?.toFixed(2)}%` : '—'}
              </span>
            </div>
          );
        })}
        {!crypto && <span style={{ fontFamily:'monospace', fontSize:8, color:'#333333' }}>Conectando a CoinGecko...</span>}
      </div>
    </div>
  );
}

// ─── System Supervision ────────────────────────────────────────────────────────
function SystemSupervision() {
  const [health, setHealth] = useState(null);
  const [domain, setDomain] = useState(null);
  const [lastUpd, setLastUpd] = useState(null);

  const fetchAll = useCallback(async () => {
    if (!API) return;
    try {
      const [h, d] = await Promise.allSettled([
        fetch(`${API}/api/health`, { signal: AbortSignal.timeout(5000) }).then(r => r.json()),
        fetch(`${API}/api/tools/domain-scan`, { signal: AbortSignal.timeout(6000) }).then(r => r.json()),
      ]);
      if (h.status === 'fulfilled') setHealth(h.value);
      if (d.status === 'fulfilled') setDomain(d.value);
      setLastUpd(new Date().toLocaleTimeString('es-CL'));
    } catch {}
  }, []);

  useEffect(() => {
    fetchAll();
    const iv = setInterval(fetchAll, 30000);
    return () => clearInterval(iv);
  }, [fetchAll]);

  const services = health?.services || {};
  const openCircuits = health?.circuit_breakers?.open_circuits || [];

  const serviceList = Object.keys(services).length > 0
    ? Object.entries(services).map(([k,v]) => [k, v])
    : [
        ['RAG Vectorial', 'online'],
        ['Qdrant DB', API ? 'online' : 'local'],
        ['Google Drive', 'online'],
        ['Social Monitor', 'online'],
        ['ADS-B Feed', 'standby'],
        ['AIS Maritime', 'standby'],
      ];

  return (
    <div style={{ padding:'10px 14px' }}>
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:10 }}>
        <span style={{ fontFamily:'monospace', fontSize:8, color:'#333333', letterSpacing:'.15em', textTransform:'uppercase' }}>SUPERVISIÓN DEL SISTEMA</span>
        <button onClick={fetchAll} style={{ fontFamily:'monospace', fontSize:8, color:'#333333', background:'none', border:'1px solid #1c1c1c', padding:'2px 7px', cursor:'pointer', letterSpacing:'.08em' }}
          onMouseEnter={e=>{e.currentTarget.style.borderColor='#4ade8040';e.currentTarget.style.color='#4ade80';}}
          onMouseLeave={e=>{e.currentTarget.style.borderColor='#1c1c1c';e.currentTarget.style.color='#333333';}}>REFR</button>
      </div>

      {/* Circuit breakers */}
      <div style={{ padding:'5px 0', borderBottom:'1px solid #111111', display:'flex', justifyContent:'space-between' }}>
        <span style={{ fontFamily:'monospace', fontSize:9, color:'#555555' }}>Circuit breakers</span>
        <span style={{ fontFamily:'monospace', fontSize:9, color: openCircuits.length===0 ? '#4ade80':'#c0392b' }}>
          {openCircuits.length===0 ? 'OK · sin alertas' : `${openCircuits.length} abiertos`}
        </span>
      </div>

      {/* Domain */}
      {domain && (
        <div style={{ padding:'5px 0', borderBottom:'1px solid #111111', display:'flex', justifyContent:'space-between' }}>
          <span style={{ fontFamily:'monospace', fontSize:9, color:'#555555' }}>SSL elanarcocapital.com</span>
          <span style={{ fontFamily:'monospace', fontSize:9, color: domain.ssl_valid ? '#4ade80' : '#c0392b' }}>
            {domain.ssl_valid ? `${domain.ssl_days_left}d válido` : 'REVISAR'}
          </span>
        </div>
      )}

      {/* Services */}
      {serviceList.map(([name, status]) => {
        const color = status==='online'||status==='ok' ? '#4ade80' : status==='standby'||status==='local' ? '#444444' : status==='degraded' ? '#d4a017' : '#c0392b';
        return (
          <div key={name} style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'4px 0', borderBottom:'1px solid #0f0f0f' }}>
            <div style={{ display:'flex', alignItems:'center', gap:7 }}>
              <span style={{ width:5, height:5, borderRadius:'50%', background:color, flexShrink:0 }}/>
              <span style={{ fontFamily:'monospace', fontSize:9, color:'#555555' }}>{name}</span>
            </div>
            <span style={{ fontFamily:'monospace', fontSize:8, color, letterSpacing:'.06em' }}>{status.toUpperCase()}</span>
          </div>
        );
      })}

      {lastUpd && <div style={{ fontFamily:'monospace', fontSize:8, color:'#222222', marginTop:8 }}>act. {lastUpd}</div>}
      {!API && <div style={{ fontFamily:'monospace', fontSize:8, color:'#333333', marginTop:6 }}>⚠ Backend offline — datos simulados</div>}
    </div>
  );
}

// ─── Feed Card ────────────────────────────────────────────────────────────────
function FeedCard({ item }) {
  const cc = catColor(item.cat);
  return (
    <div style={{ background:'#0f0f0f', borderLeft:`2px solid ${item.hot?cc:'#1a1a1a'}`, borderBottom:'1px solid #111111', padding:'10px 14px', cursor:'pointer', transition:'background .15s' }}
      onMouseEnter={e=>e.currentTarget.style.background='#141414'}
      onMouseLeave={e=>e.currentTarget.style.background='#0f0f0f'}>
      <div style={{ display:'flex', alignItems:'center', gap:7, marginBottom:4 }}>
        <span style={{ fontFamily:'monospace', fontSize:7, color:cc, letterSpacing:'.14em', border:`1px solid ${cc}25`, padding:'1px 5px', flexShrink:0 }}>{item.cat}</span>
        <span style={{ fontFamily:'monospace', fontSize:7, color:'#333333', letterSpacing:'.08em', flexShrink:0 }}>{item.region}</span>
        {item.hot && <span style={{ marginLeft:'auto', fontFamily:'monospace', fontSize:7, color:'#c0392b', display:'flex', alignItems:'center', gap:3 }}>
          <span style={{ width:4, height:4, borderRadius:'50%', background:'#c0392b', display:'inline-block', animation:'blink-dot 1s infinite' }}/>HOT
        </span>}
      </div>
      <p style={{ fontFamily:'monospace', fontSize:11, color: item.hot?'#dddddd':'#777777', lineHeight:1.5, margin:'0 0 4px', fontWeight: item.hot?600:400 }}>{item.title}</p>
      <div style={{ display:'flex', justifyContent:'space-between' }}>
        <span style={{ fontFamily:'monospace', fontSize:8, color:'#4ade8060' }}>{item.src}</span>
        <span style={{ fontFamily:'monospace', fontSize:8, color:'#2a2a2a' }}>+{item.time}</span>
      </div>
    </div>
  );
}

// ─── Selected Hotspot Detail ───────────────────────────────────────────────────
function HotspotDetail({ spot, onClose }) {
  if (!spot) return null;
  const color = THREAT_COLOR[spot.threat] || '#4ade80';
  return (
    <div style={{ background:'#0a0a0a', borderTop:`1px solid ${color}25`, padding:'10px 14px', display:'flex', justifyContent:'space-between', alignItems:'center' }}>
      <div>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ width:6, height:6, borderRadius:'50%', background:color }}/>
          <span style={{ fontFamily:'monospace', fontSize:10, color, letterSpacing:'.1em', fontWeight:700 }}>{spot.name}</span>
          <span style={{ fontFamily:'monospace', fontSize:8, color:'#444444', border:`1px solid ${color}20`, padding:'1px 5px' }}>AMENAZA {threatLabel(spot.threat)}</span>
        </div>
        <div style={{ fontFamily:'monospace', fontSize:9, color:'#555555', marginTop:4 }}>{spot.desc} · {spot.events} eventos registrados</div>
      </div>
      <button onClick={onClose} style={{ fontFamily:'monospace', fontSize:9, color:'#333333', background:'none', border:'1px solid #1c1c1c', padding:'3px 8px', cursor:'pointer' }}>✕</button>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function Landing() {
  const [cat, setCat] = useState('TODOS');
  const [menuOpen, setMenuOpen] = useState(false);
  const [selectedSpot, setSelectedSpot] = useState(null);
  const mobile = useIsMobile();
  const now = useNow();

  const filtered = cat==='TODOS' ? STATIC_FEED : STATIC_FEED.filter(f => f.cat===cat);
  const hotCount = STATIC_FEED.filter(f => f.hot).length;

  return (
    <div style={{ background:'#080808', minHeight:'100vh', color:'#e8e8e8' }}>
      <style>{`
        @keyframes blink-dot { 0%,100%{opacity:1} 50%{opacity:.3} }
        @keyframes pulse-ring { 0%{transform:scale(1);opacity:.8} 50%{transform:scale(1.6);opacity:.2} 100%{transform:scale(1);opacity:.8} }
        @keyframes fade-up { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:none} }
        ::-webkit-scrollbar{width:3px;height:3px} ::-webkit-scrollbar-track{background:#0a0a0a} ::-webkit-scrollbar-thumb{background:#1c1c1c}
      `}</style>

      {/* ── HEADER ── */}
      <header style={{ background:'#060606', borderBottom:'1px solid #161616', padding: mobile?'0 16px':'0 20px', display:'flex', alignItems:'center', justifyContent:'space-between', height:44, position:'sticky', top:0, zIndex:200 }}>
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          <span style={{ width:6, height:6, borderRadius:'50%', background:'#4ade80', boxShadow:'0 0 6px #4ade80', animation:'blink-dot 2s infinite', flexShrink:0 }}/>
          <span style={{ fontFamily:'monospace', fontSize: mobile?11:13, fontWeight:700, color:'#4ade80', letterSpacing:'.18em', textTransform:'uppercase' }}>EL ANARCOCAPITAL</span>
          {!mobile && <span style={{ fontFamily:'monospace', fontSize:8, color:'#1c1c1c', letterSpacing:'.1em' }}>· INTELIGENCIA SOBERANA</span>}
        </div>
        <div style={{ display:'flex', alignItems:'center', gap: mobile?8:14 }}>
          {!mobile && <span style={{ fontFamily:'monospace', fontSize:9, color:'#222222' }}>{now}</span>}
          {!mobile && <div style={{ width:1, height:14, background:'#1c1c1c' }}/>}
          <div style={{ fontFamily:'monospace', fontSize:8, color:'#c0392b', display:'flex', alignItems:'center', gap:5, border:'1px solid #c0392b25', padding:'3px 8px' }}>
            <span style={{ width:4, height:4, borderRadius:'50%', background:'#c0392b', display:'inline-block', animation:'blink-dot 1s infinite' }}/>
            {hotCount} ALERTA{hotCount!==1?'S':''}
          </div>
          <Link to="/control" style={{ fontFamily:'monospace', fontSize: mobile?8:9, padding:'5px 12px', background:'#4ade80', color:'#080808', textDecoration:'none', fontWeight:700, letterSpacing:'.1em', textTransform:'uppercase' }}>WARROOM →</Link>
          {mobile && <button onClick={()=>setMenuOpen(o=>!o)} style={{ background:'none', border:'1px solid #1c1c1c', color:'#666666', padding:'4px 8px', cursor:'pointer', fontSize:13 }}>{menuOpen?'✕':'☰'}</button>}
        </div>
      </header>

      {mobile && menuOpen && (
        <div style={{ position:'fixed', top:44, left:0, right:0, zIndex:199, background:'#0a0a0a', borderBottom:'1px solid #1c1c1c', padding:'12px 16px', display:'flex', flexDirection:'column', gap:10 }}>
          <span style={{ fontFamily:'monospace', fontSize:9, color:'#333333' }}>{now}</span>
          <Link to="/control" onClick={()=>setMenuOpen(false)} style={{ fontFamily:'monospace', fontSize:11, padding:'10px', background:'#4ade80', color:'#080808', textDecoration:'none', fontWeight:700, textAlign:'center', letterSpacing:'.1em' }}>WARROOM →</Link>
        </div>
      )}

      {/* ── BREAKING BAR ── */}
      <div style={{ background:'#060606', borderBottom:'1px solid #c0392b20', padding:'6px 20px', display:'flex', alignItems:'center', gap:12, overflow:'hidden' }}>
        <span style={{ fontFamily:'monospace', fontSize:7, color:'#c0392b', fontWeight:700, letterSpacing:'.2em', whiteSpace:'nowrap', background:'#c0392b10', padding:'2px 7px', border:'1px solid #c0392b20', flexShrink:0 }}>BREAKING</span>
        <span style={{ fontFamily:'monospace', fontSize:10, color:'#7a3030', flex:1, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
          China despliega portaaviones Taiwán · S&amp;P -1.4% datos empleo · OTAN activa protocolo Mar Báltico · ADSB oscuro Engels-2
        </span>
      </div>

      {/* ── TICKER ── */}
      <Ticker/>

      {/* ── MAIN 3-PANEL GRID ── */}
      <div style={{ display:'grid', gridTemplateColumns: mobile ? '1fr' : '1fr 320px 280px', maxWidth:1600, margin:'0 auto', minHeight:'calc(100vh - 120px)', alignItems:'start' }}>

        {/* ═══ LEFT: MAP + FEED ═══ */}
        <div style={{ borderRight: mobile?'none':'1px solid #161616' }}>

          {/* World Map */}
          <WorldMap onSelect={setSelectedSpot} selected={selectedSpot}/>

          {/* Selected hotspot detail */}
          {selectedSpot && <HotspotDetail spot={selectedSpot} onClose={()=>setSelectedSpot(null)}/>}

          {/* Category filter */}
          <div style={{ borderBottom:'1px solid #161616', display:'flex', overflowX:'auto', scrollbarWidth:'none', background:'#060606' }}>
            {CATS.map(c => (
              <button key={c} onClick={()=>setCat(c)} style={{ fontFamily:'monospace', fontSize:8, color: cat===c?'#4ade80':'#333333', background:'none', border:'none', borderBottom: cat===c?'2px solid #4ade80':'2px solid transparent', padding:'9px 13px', cursor:'pointer', letterSpacing:'.1em', whiteSpace:'nowrap', transition:'color .15s', flexShrink:0 }}>
                {c}
              </button>
            ))}
          </div>

          {/* Feed header */}
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'7px 14px', borderBottom:'1px solid #111111', background:'#060606' }}>
            <span style={{ fontFamily:'monospace', fontSize:7, color:'#1c1c1c', letterSpacing:'.1em', textTransform:'uppercase' }}>FEED OSINT · {filtered.length} SEÑALES</span>
            <div style={{ display:'flex', alignItems:'center', gap:5 }}>
              <span style={{ width:4, height:4, borderRadius:'50%', background:'#4ade80', animation:'blink-dot 1.5s infinite' }}/>
              <span style={{ fontFamily:'monospace', fontSize:7, color:'#4ade80', letterSpacing:'.08em' }}>AUTO-ACTUALIZACIÓN</span>
            </div>
          </div>

          {/* Feed cards */}
          <div>{filtered.map(item => <FeedCard key={item.id} item={item}/>)}</div>

          <div style={{ padding:'14px', borderTop:'1px solid #161616', display:'flex', justifyContent:'center' }}>
            <Link to="/control" style={{ fontFamily:'monospace', fontSize:9, padding:'8px 24px', border:'1px solid #1c1c1c', color:'#444444', textDecoration:'none', letterSpacing:'.1em', textTransform:'uppercase', transition:'all .15s' }}
              onMouseEnter={e=>{e.currentTarget.style.borderColor='#4ade8040';e.currentTarget.style.color='#4ade80';}}
              onMouseLeave={e=>{e.currentTarget.style.borderColor='#1c1c1c';e.currentTarget.style.color='#444444';}}>
              VER TODO EN WARROOM →
            </Link>
          </div>
        </div>

        {/* ═══ CENTER: AI COMMAND + METRICS ═══ */}
        {!mobile && (
          <div style={{ borderRight:'1px solid #161616', display:'flex', flexDirection:'column', minHeight:'100%' }}>
            <div style={{ flex:1, borderBottom:'1px solid #161616' }}>
              <AICommandPanel/>
            </div>
            <LiveMetrics/>
          </div>
        )}

        {/* ═══ RIGHT: SYSTEM SUPERVISION ═══ */}
        {!mobile && (
          <aside style={{ display:'flex', flexDirection:'column' }}>
            <SystemSupervision/>

            {/* Threat levels */}
            <div style={{ padding:'10px 14px', borderTop:'1px solid #161616' }}>
              <div style={{ fontFamily:'monospace', fontSize:8, color:'#333333', letterSpacing:'.15em', textTransform:'uppercase', marginBottom:10 }}>NIVEL DE AMENAZA GLOBAL</div>
              {HOTSPOTS.sort((a,b)=>b.threat-a.threat).map(h => {
                const color = THREAT_COLOR[h.threat];
                return (
                  <div key={h.id} style={{ display:'flex', alignItems:'center', gap:8, padding:'4px 0', borderBottom:'1px solid #0f0f0f', cursor:'pointer' }}
                    onClick={()=>setSelectedSpot(h)}>
                    <div style={{ width:2, height:24, background:color, flexShrink:0, opacity:.7 }}/>
                    <div style={{ flex:1, minWidth:0 }}>
                      <div style={{ fontFamily:'monospace', fontSize:8, color:'#555555', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{h.name}</div>
                      <div style={{ display:'flex', gap:1.5, marginTop:2 }}>
                        {[1,2,3,4,5].map(i=>(
                          <div key={i} style={{ width:12, height:2, background: i<=h.threat?color:'#1a1a1a', borderRadius:1 }}/>
                        ))}
                      </div>
                    </div>
                    <div style={{ textAlign:'right', flexShrink:0 }}>
                      <div style={{ fontFamily:'monospace', fontSize:7, color, letterSpacing:'.06em' }}>{threatLabel(h.threat)}</div>
                      <div style={{ fontFamily:'monospace', fontSize:7, color:'#333333' }}>{h.events}ev</div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Quick access */}
            <div style={{ padding:'10px 14px', borderTop:'1px solid #161616' }}>
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:5 }}>
                {[['🧠','IA/RAG'],['🗓','Timeline'],['📡','OSINT'],['📁','Bóveda']].map(([icon, label]) => (
                  <Link key={label} to="/control" style={{ background:'#0a0a0a', border:'1px solid #161616', padding:'9px 6px', textDecoration:'none', display:'flex', flexDirection:'column', alignItems:'center', gap:3, transition:'border-color .15s' }}
                    onMouseEnter={e=>e.currentTarget.style.borderColor='#4ade8025'}
                    onMouseLeave={e=>e.currentTarget.style.borderColor='#161616'}>
                    <span style={{ fontSize:16 }}>{icon}</span>
                    <span style={{ fontFamily:'monospace', fontSize:7, color:'#444444', letterSpacing:'.06em', textTransform:'uppercase' }}>{label}</span>
                  </Link>
                ))}
              </div>
            </div>
          </aside>
        )}
      </div>

      {/* ── MOBILE: AI + Metrics ── */}
      {mobile && (
        <div style={{ borderTop:'1px solid #161616' }}>
          <div style={{ borderBottom:'1px solid #161616', maxHeight:420 }}>
            <AICommandPanel/>
          </div>
          <LiveMetrics/>
          <SystemSupervision/>
        </div>
      )}

      {/* ── TOOLS GRID ── */}
      <div style={{ borderTop:'1px solid #161616', background:'#060606' }}>
        <div style={{ maxWidth:1600, margin:'0 auto', padding: mobile?'20px 16px':'24px 20px' }}>
          <div style={{ fontFamily:'monospace', fontSize:8, color:'#2a2a2a', letterSpacing:'.2em', textTransform:'uppercase', marginBottom:12 }}>CAPACIDADES DEL SISTEMA</div>
          <div style={{ display:'grid', gridTemplateColumns: mobile?'1fr 1fr':'repeat(9,1fr)', gap:1, background:'#161616', border:'1px solid #161616', overflow:'hidden' }}>
            {[
              {icon:'🧠',label:'IA + RAG',    status:'live'},
              {icon:'📁',label:'Bóveda',      status:'live'},
              {icon:'🐦',label:'Monitor X',   status:'live'},
              {icon:'🗓',label:'Timelines',   status:'live'},
              {icon:'🎙',label:'Voz',         status:'live'},
              {icon:'📹',label:'Video OSINT', status:'live'},
              {icon:'✈️',label:'ADS-B',       status:'soon'},
              {icon:'🚢',label:'AIS Naval',   status:'soon'},
              {icon:'🛰',label:'Satélites',   status:'soon'},
            ].map(t => (
              <Link key={t.label} to="/control" style={{ background:'#0a0a0a', padding:'14px 10px', textDecoration:'none', display:'flex', flexDirection:'column', gap:5, transition:'background .15s', cursor:'pointer' }}
                onMouseEnter={e=>e.currentTarget.style.background='#0f0f0f'}
                onMouseLeave={e=>e.currentTarget.style.background='#0a0a0a'}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
                  <span style={{ fontSize:16 }}>{t.icon}</span>
                  <span style={{ fontFamily:'monospace', fontSize:6, color: t.status==='soon'?'#333333':'#4ade80', letterSpacing:'.1em', border:`1px solid ${t.status==='soon'?'#1c1c1c':'#4ade8030'}`, padding:'1px 4px' }}>{t.status==='soon'?'PRÓX':'LIVE'}</span>
                </div>
                <span style={{ fontFamily:'monospace', fontSize:8, color: t.status==='soon'?'#333333':'#666666', fontWeight:700, letterSpacing:'.04em' }}>{t.label}</span>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* ── FOOTER ── */}
      <footer style={{ borderTop:'1px solid #161616', padding: mobile?'10px 16px':'10px 20px', display:'flex', alignItems:'center', justifyContent:'space-between', flexWrap:'wrap', gap:8, background:'#060606' }}>
        <span style={{ fontFamily:'monospace', fontSize:8, color:'#1c1c1c' }}>EL ANARCOCAPITAL · Inteligencia Soberana · © 2026</span>
        <div style={{ display:'flex', gap:16 }}>
          <Link to="/control" style={{ fontFamily:'monospace', fontSize:8, color:'#4ade80', textDecoration:'none' }}>Warroom →</Link>
        </div>
      </footer>
    </div>
  );
}
