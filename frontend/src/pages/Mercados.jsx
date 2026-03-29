import React, { useState, useEffect, useCallback } from 'react';
import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';
import { TrendingUp, TrendingDown, RefreshCw, Activity } from 'lucide-react';

// ── Paleta ───────────────────────────────────────────────────────────────────
const C = {
  bg:    '#080808', bg2:   '#0f0f0f', bg3:   '#141414',
  border:'#1a1a1a', green: '#4ade80', red:   '#c0392b',
  amber: '#d4a017', cyan:  '#22d3ee', dim:   '#444',
  muted: '#888',    text:  '#e5e5e5',
};

const mono = "'Space Mono', monospace";

// ── Datos históricos mock (últimas 24 puntos ~1h) ─────────────────────────────
function genHistory(base, vol, len = 24) {
  const d = [];
  let v = base;
  const now = Date.now();
  for (let i = len; i >= 0; i--) {
    v = +(v + (Math.random() - 0.49) * vol).toFixed(2);
    if (v < base * 0.92) v = base * 0.92;
    if (v > base * 1.08) v = base * 1.08;
    const t = new Date(now - i * 3600000);
    d.push({ t: `${t.getHours()}:00`, v });
  }
  return d;
}

// ── Snapshot de activos ───────────────────────────────────────────────────────
const INIT_ASSETS = {
  forex: [
    { sym: 'EUR/USD', base: 1.0832, vol: 0.004 },
    { sym: 'USD/JPY', base: 149.72, vol: 0.35  },
    { sym: 'GBP/USD', base: 1.2641, vol: 0.005 },
    { sym: 'USD/CHF', base: 0.9024, vol: 0.003 },
    { sym: 'AUD/USD', base: 0.6531, vol: 0.003 },
    { sym: 'USD/CAD', base: 1.3612, vol: 0.004 },
    { sym: 'USD/CLP', base: 948.5,  vol: 2.5   },
    { sym: 'USD/ARS', base: 1040.0, vol: 8.0   },
  ],
  indices: [
    { sym: 'S&P 500',    base: 5204.34, vol: 18  },
    { sym: 'NASDAQ',     base: 16284.5, vol: 55  },
    { sym: 'DOW JONES',  base: 38974.0, vol: 80  },
    { sym: 'DAX',        base: 18120.0, vol: 40  },
    { sym: 'NIKKEI 225', base: 38950.0, vol: 90  },
    { sym: 'FTSE 100',   base: 7990.0,  vol: 22  },
    { sym: 'MERVAL',     base: 1520000, vol: 8000 },
    { sym: 'IBOVESPA',   base: 127400,  vol: 400  },
  ],
  commodities: [
    { sym: 'GOLD',        base: 2315.4, vol: 6.0, unit: 'XAU/USD' },
    { sym: 'SILVER',      base: 27.32,  vol: 0.3, unit: 'XAG/USD' },
    { sym: 'WTI OIL',     base: 81.44,  vol: 0.5, unit: 'USD/bbl' },
    { sym: 'BRENT',       base: 85.12,  vol: 0.5, unit: 'USD/bbl' },
    { sym: 'COPPER',      base: 4.42,   vol: 0.04,unit: 'USD/lb'  },
    { sym: 'NATURAL GAS', base: 1.98,   vol: 0.03,unit: 'USD/MMBtu'},
    { sym: 'WHEAT',       base: 554.0,  vol: 4.0, unit: 'USd/bu'  },
    { sym: 'CORN',        base: 438.0,  vol: 3.0, unit: 'USd/bu'  },
  ],
};

function buildTicker(assets) {
  return Object.fromEntries(
    Object.entries(assets).flatMap(([cat, list]) =>
      list.map(a => {
        const price   = +(a.base + (Math.random() - 0.5) * a.vol * 2).toFixed(a.base > 100 ? 2 : 4);
        const change  = +(((price - a.base) / a.base) * 100).toFixed(3);
        const history = genHistory(a.base, a.vol);
        return [a.sym, { sym: a.sym, cat, price, change, prev: a.base, history, unit: a.unit || '' }];
      })
    )
  );
}

// ── Helpers UI ────────────────────────────────────────────────────────────────
const fmt = (v, sym) => {
  if (sym && (sym.includes('JPY') || sym.includes('CLP') || sym.includes('ARS') || sym.includes('MERVAL') || sym.includes('IBOVESPA') || sym.includes('DOW') || sym.includes('NASDAQ') || sym.includes('NIKKEI') || sym.includes('DAX') || sym.includes('FTSE') || sym.includes('S&P')))
    return v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return v.toFixed(4);
};

const ChgBadge = ({ v }) => (
  <span style={{
    display:'inline-flex', alignItems:'center', gap:3,
    fontSize:10, fontFamily:mono,
    color: v >= 0 ? C.green : C.red,
  }}>
    {v >= 0 ? <TrendingUp size={10}/> : <TrendingDown size={10}/>}
    {v >= 0 ? '+' : ''}{v.toFixed(3)}%
  </span>
);

const MiniChart = ({ data, change }) => {
  const color = change >= 0 ? C.green : C.red;
  return (
    <ResponsiveContainer width="100%" height={36}>
      <AreaChart data={data} margin={{ top:2, right:0, left:0, bottom:2 }}>
        <defs>
          <linearGradient id={`g${change > 0 ? 'up' : 'dn'}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor={color} stopOpacity={0.25}/>
            <stop offset="95%" stopColor={color} stopOpacity={0}/>
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="v" stroke={color} strokeWidth={1.2}
          fill={`url(#g${change > 0 ? 'up' : 'dn'})`} dot={false} isAnimationActive={false}/>
      </AreaChart>
    </ResponsiveContainer>
  );
};

const BigChart = ({ data, sym, change }) => {
  const color = change >= 0 ? C.green : C.red;
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top:8, right:16, left:0, bottom:0 }}>
        <CartesianGrid strokeDasharray="2 4" stroke={C.border}/>
        <XAxis dataKey="t" tick={{ fill: C.dim, fontSize:9, fontFamily:mono }} tickLine={false} axisLine={false} interval={3}/>
        <YAxis domain={['auto','auto']} tick={{ fill: C.dim, fontSize:9, fontFamily:mono }} tickLine={false} axisLine={false} width={60}
          tickFormatter={v => fmt(v, sym)}/>
        <Tooltip
          contentStyle={{ background:C.bg2, border:`1px solid ${C.border}`, borderRadius:2, fontFamily:mono, fontSize:10 }}
          labelStyle={{ color:C.muted }} itemStyle={{ color }}
          formatter={v => [fmt(v, sym), sym]}/>
        <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} dot={false} isAnimationActive={false}/>
      </LineChart>
    </ResponsiveContainer>
  );
};

// ── Row de activo ─────────────────────────────────────────────────────────────
const AssetRow = ({ d, onClick, selected }) => (
  <div onClick={() => onClick(d.sym)}
    style={{
      display:'grid', gridTemplateColumns:'1fr 110px 90px 100px',
      alignItems:'center', padding:'7px 12px',
      cursor:'pointer', borderBottom:`1px solid ${C.border}`,
      background: selected ? 'rgba(74,222,128,0.05)' : 'transparent',
      borderLeft: selected ? `2px solid ${C.green}` : '2px solid transparent',
      transition:'background .12s',
    }}
    onMouseEnter={e => { if (!selected) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
    onMouseLeave={e => { if (!selected) e.currentTarget.style.background = 'transparent'; }}
  >
    <div style={{ fontFamily:mono, fontSize:11, color: selected ? C.green : C.text }}>{d.sym}</div>
    <div style={{ fontFamily:mono, fontSize:11, color:C.text, textAlign:'right' }}>{fmt(d.price, d.sym)}</div>
    <div style={{ textAlign:'right' }}><ChgBadge v={d.change}/></div>
    <div style={{ height:36 }}><MiniChart data={d.history} change={d.change}/></div>
  </div>
);

// ── Cabecera de sección ───────────────────────────────────────────────────────
const SectionHead = ({ label, icon: Icon }) => (
  <div style={{
    display:'flex', alignItems:'center', gap:8,
    padding:'8px 14px', background:C.bg3,
    borderBottom:`1px solid ${C.border}`,
    fontFamily:mono, fontSize:9, letterSpacing:'.12em',
    textTransform:'uppercase', color:C.cyan,
  }}>
    <Icon size={12}/> {label}
  </div>
);

// ── Componente principal ──────────────────────────────────────────────────────
export default function Mercados() {
  const [ticker, setTicker]     = useState(() => buildTicker(INIT_ASSETS));
  const [selected, setSelected] = useState('EUR/USD');
  const [lastUp, setLastUp]     = useState(new Date());
  const [tab, setTab]           = useState('forex'); // forex | indices | commodities

  // Refresca precios cada 8 segundos (simulación en tiempo real)
  const refresh = useCallback(() => {
    setTicker(prev => {
      const next = { ...prev };
      Object.keys(next).forEach(sym => {
        const a = INIT_ASSETS[next[sym].cat]?.find(x => x.sym === sym);
        if (!a) return;
        const price  = +(a.base + (Math.random() - 0.5) * a.vol * 2).toFixed(a.base > 100 ? 2 : 4);
        const change = +(((price - a.base) / a.base) * 100).toFixed(3);
        const hist   = [...next[sym].history.slice(1), { t: new Date().toLocaleTimeString('en',{hour:'2-digit',minute:'2-digit'}), v: price }];
        next[sym] = { ...next[sym], price, change, history: hist };
      });
      return next;
    });
    setLastUp(new Date());
  }, []);

  useEffect(() => {
    const id = setInterval(refresh, 8000);
    return () => clearInterval(id);
  }, [refresh]);

  const sel = ticker[selected];
  const cats = { forex: 'FOREX', indices: 'ÍNDICES', commodities: 'COMMODITIES' };

  // top movers
  const movers = Object.values(ticker).sort((a,b) => Math.abs(b.change) - Math.abs(a.change)).slice(0, 5);

  return (
    <div style={{ height:'100vh', display:'flex', flexDirection:'column', background:C.bg, color:C.text, overflow:'hidden' }}>

      {/* ── Header ── */}
      <div style={{ padding:'12px 20px', borderBottom:`1px solid ${C.border}`, display:'flex', alignItems:'center', justifyContent:'space-between', flexShrink:0 }}>
        <div style={{ display:'flex', alignItems:'center', gap:12 }}>
          <Activity size={16} color={C.green}/>
          <span style={{ fontFamily:mono, fontSize:12, fontWeight:700, letterSpacing:'.1em', color:C.text }}>MERCADOS</span>
          <span style={{ fontFamily:mono, fontSize:9, color:C.dim, letterSpacing:'.08em' }}>TIEMPO REAL · SIMULADO</span>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:12 }}>
          <span style={{ fontFamily:mono, fontSize:9, color:C.dim }}>
            UPD {lastUp.toLocaleTimeString('es')}
          </span>
          <button onClick={refresh} style={{ display:'flex', alignItems:'center', gap:5, padding:'4px 10px', background:'rgba(74,222,128,0.08)', border:`1px solid rgba(74,222,128,0.2)`, borderRadius:3, color:C.green, cursor:'pointer', fontFamily:mono, fontSize:9 }}>
            <RefreshCw size={11}/> REFRESH
          </button>
        </div>
      </div>

      {/* ── Body ── */}
      <div style={{ flex:1, display:'flex', overflow:'hidden' }}>

        {/* ── Panel izquierdo: lista ── */}
        <div style={{ width:420, borderRight:`1px solid ${C.border}`, display:'flex', flexDirection:'column', overflow:'hidden' }}>

          {/* Tabs */}
          <div style={{ display:'flex', borderBottom:`1px solid ${C.border}`, flexShrink:0 }}>
            {Object.entries(cats).map(([k,v]) => (
              <button key={k} onClick={() => setTab(k)} style={{
                flex:1, padding:'8px 4px', cursor:'pointer', border:'none',
                background: tab===k ? 'rgba(74,222,128,0.06)' : 'transparent',
                borderBottom: tab===k ? `2px solid ${C.green}` : '2px solid transparent',
                color: tab===k ? C.green : C.muted,
                fontFamily:mono, fontSize:9, letterSpacing:'.08em',
              }}>{v}</button>
            ))}
          </div>

          {/* Col headers */}
          <div style={{ display:'grid', gridTemplateColumns:'1fr 110px 90px 100px', padding:'5px 12px', borderBottom:`1px solid ${C.border}`, flexShrink:0 }}>
            {['SÍMBOLO','PRECIO','CAMBIO','24H'].map((h,i) => (
              <div key={i} style={{ fontFamily:mono, fontSize:8, color:C.dim, letterSpacing:'.1em', textAlign: i===0?'left':'right' }}>{h}</div>
            ))}
          </div>

          {/* Rows */}
          <div style={{ overflowY:'auto', flex:1 }}>
            {INIT_ASSETS[tab].map(a => (
              <AssetRow key={a.sym} d={ticker[a.sym] || {}} onClick={setSelected} selected={selected===a.sym}/>
            ))}
          </div>
        </div>

        {/* ── Panel derecho: detalle ── */}
        <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>

          {sel && (
            <>
              {/* Precio principal */}
              <div style={{ padding:'16px 20px', borderBottom:`1px solid ${C.border}`, flexShrink:0 }}>
                <div style={{ display:'flex', alignItems:'baseline', gap:14, flexWrap:'wrap' }}>
                  <span style={{ fontFamily:mono, fontSize:11, color:C.dim, letterSpacing:'.1em' }}>{sel.sym}</span>
                  {sel.unit && <span style={{ fontFamily:mono, fontSize:9, color:C.dim }}>{sel.unit}</span>}
                </div>
                <div style={{ display:'flex', alignItems:'baseline', gap:16, marginTop:6 }}>
                  <span style={{ fontFamily:mono, fontSize:28, fontWeight:700, color: sel.change >= 0 ? C.green : C.red, letterSpacing:'.02em' }}>
                    {fmt(sel.price, sel.sym)}
                  </span>
                  <ChgBadge v={sel.change}/>
                  <span style={{ fontFamily:mono, fontSize:10, color:C.dim }}>
                    prev {fmt(sel.prev, sel.sym)}
                  </span>
                </div>
              </div>

              {/* Big chart */}
              <div style={{ padding:'12px 8px 4px', flexShrink:0 }}>
                <div style={{ fontFamily:mono, fontSize:8, color:C.dim, letterSpacing:'.1em', marginBottom:4, paddingLeft:12 }}>EVOLUCIÓN 24H</div>
                <BigChart data={sel.history} sym={sel.sym} change={sel.change}/>
              </div>
            </>
          )}

          {/* ── Top movers ── */}
          <div style={{ flex:1, overflow:'hidden', display:'flex', flexDirection:'column' }}>
            <SectionHead label="Top Movers" icon={Activity}/>
            <div style={{ overflowY:'auto', flex:1 }}>
              {movers.map(d => (
                <div key={d.sym} onClick={() => { setSelected(d.sym); setTab(d.cat); }}
                  style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'8px 16px', borderBottom:`1px solid ${C.border}`, cursor:'pointer' }}
                  onMouseEnter={e => e.currentTarget.style.background='rgba(255,255,255,0.03)'}
                  onMouseLeave={e => e.currentTarget.style.background='transparent'}
                >
                  <div style={{ display:'flex', gap:10, alignItems:'center' }}>
                    <span style={{ fontFamily:mono, fontSize:9, color:C.dim, letterSpacing:'.06em', width:90, textTransform:'uppercase' }}>{d.cat}</span>
                    <span style={{ fontFamily:mono, fontSize:11, color:C.text }}>{d.sym}</span>
                  </div>
                  <div style={{ display:'flex', alignItems:'center', gap:16 }}>
                    <span style={{ fontFamily:mono, fontSize:11 }}>{fmt(d.price, d.sym)}</span>
                    <ChgBadge v={d.change}/>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ── Stats rápidas ── */}
          {sel && (
            <div style={{ padding:'10px 16px', borderTop:`1px solid ${C.border}`, display:'flex', gap:24, flexShrink:0, flexWrap:'wrap' }}>
              {[
                { label:'MAX 24H', val: fmt(Math.max(...sel.history.map(x=>x.v)), sel.sym) },
                { label:'MIN 24H', val: fmt(Math.min(...sel.history.map(x=>x.v)), sel.sym) },
                { label:'APERTURA', val: fmt(sel.history[0]?.v ?? sel.prev, sel.sym) },
                { label:'SPREAD',   val: ((Math.max(...sel.history.map(x=>x.v)) - Math.min(...sel.history.map(x=>x.v))) / sel.price * 100).toFixed(3) + '%' },
              ].map(s => (
                <div key={s.label} style={{ display:'flex', flexDirection:'column', gap:2 }}>
                  <span style={{ fontFamily:mono, fontSize:8, color:C.dim, letterSpacing:'.1em' }}>{s.label}</span>
                  <span style={{ fontFamily:mono, fontSize:11, color:C.amber }}>{s.val}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
