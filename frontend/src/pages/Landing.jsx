import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import Globe3D from '../components/Globe3D';

// ═══════════════════════════════════════════════════════════════
// CANVAS — Red neuronal con efecto de profundidad
// ═══════════════════════════════════════════════════════════════
function NeuralCanvas() {
  const ref = useRef(null);
  useEffect(() => {
    const c = ref.current; if (!c) return;
    const ctx = c.getContext('2d');
    let W, H, pts = [], id;
    const resize = () => { W = c.width = window.innerWidth; H = c.height = window.innerHeight; };
    resize();
    window.addEventListener('resize', resize);
    class P {
      constructor() { this.reset(); }
      reset() {
        this.x = Math.random() * W; this.y = Math.random() * H;
        this.r = Math.random() * 1.8 + 0.4;
        this.vx = (Math.random() - 0.5) * 0.35; this.vy = (Math.random() - 0.5) * 0.35;
        this.pulse = Math.random() * Math.PI * 2;
        this.pSpeed = 0.02 + Math.random() * 0.03;
      }
      move() {
        this.x += this.vx; this.y += this.vy; this.pulse += this.pSpeed;
        if (this.x < 0 || this.x > W) this.vx *= -1;
        if (this.y < 0 || this.y > H) this.vy *= -1;
      }
      get opacity() { return 0.3 + Math.sin(this.pulse) * 0.25; }
    }
    for (let i = 0; i < 90; i++) pts.push(new P());
    const draw = () => {
      ctx.clearRect(0, 0, W, H);
      for (let a = 0; a < pts.length; a++) {
        pts[a].move();
        // Node
        ctx.beginPath();
        ctx.arc(pts[a].x, pts[a].y, pts[a].r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0,229,255,${pts[a].opacity})`;
        ctx.fill();
        // Connections
        for (let b = a + 1; b < pts.length; b++) {
          const dx = pts[a].x - pts[b].x, dy = pts[a].y - pts[b].y;
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < 120) {
            const alpha = (1 - d / 120) * 0.22;
            ctx.strokeStyle = `rgba(0,229,255,${alpha})`;
            ctx.lineWidth = 0.5;
            ctx.beginPath(); ctx.moveTo(pts[a].x, pts[a].y); ctx.lineTo(pts[b].x, pts[b].y); ctx.stroke();
          }
        }
      }
      id = requestAnimationFrame(draw);
    };
    draw();
    return () => { window.removeEventListener('resize', resize); cancelAnimationFrame(id); };
  }, []);
  return <canvas ref={ref} style={{ position:'absolute', inset:0, opacity:0.3, zIndex:1, pointerEvents:'none' }} />;
}

// ═══════════════════════════════════════════════════════════════
// TYPEWRITER — Efecto letra por letra
// ═══════════════════════════════════════════════════════════════
function TypeWriter({ texts, speed = 60, pause = 2200 }) {
  const [display, setDisplay] = useState('');
  const [idx, setIdx] = useState(0);
  const [phase, setPhase] = useState('typing'); // typing | waiting | erasing

  useEffect(() => {
    const text = texts[idx];
    let timeout;
    if (phase === 'typing') {
      if (display.length < text.length) {
        timeout = setTimeout(() => setDisplay(text.slice(0, display.length + 1)), speed);
      } else {
        timeout = setTimeout(() => setPhase('waiting'), pause);
      }
    } else if (phase === 'waiting') {
      timeout = setTimeout(() => setPhase('erasing'), 200);
    } else {
      if (display.length > 0) {
        timeout = setTimeout(() => setDisplay(d => d.slice(0, -1)), speed / 2);
      } else {
        setIdx(i => (i + 1) % texts.length);
        setPhase('typing');
      }
    }
    return () => clearTimeout(timeout);
  }, [display, phase, idx, texts, speed, pause]);

  return <span className="typewriter-cursor">{display}</span>;
}

// ═══════════════════════════════════════════════════════════════
// CONTADOR ANIMADO — Números que suben
// ═══════════════════════════════════════════════════════════════
function AnimCounter({ target, suffix = '', prefix = '', dur = 1800 }) {
  const [val, setVal] = useState(0);
  const ref = useRef(null);
  const started = useRef(false);
  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting && !started.current) {
        started.current = true;
        const start = Date.now();
        const tick = () => {
          const p = Math.min((Date.now() - start) / dur, 1);
          const eased = 1 - Math.pow(1 - p, 3);
          setVal(Math.round(eased * target));
          if (p < 1) requestAnimationFrame(tick);
        };
        tick();
      }
    }, { threshold: 0.3 });
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, [target, dur]);
  return <span ref={ref}>{prefix}{val.toLocaleString()}{suffix}</span>;
}

// ═══════════════════════════════════════════════════════════════
// SCANLINE HUD — Línea de escaneo
// ═══════════════════════════════════════════════════════════════
function ScanLine() {
  return (
    <div style={{ position:'absolute', inset:0, overflow:'hidden', pointerEvents:'none', zIndex:2 }}>
      <div style={{
        position:'absolute', left:0, right:0, height:1,
        background:'linear-gradient(90deg,transparent,rgba(0,229,255,0.4),transparent)',
        animation:'scan-h 4s linear infinite',
        animationDelay:'-2s',
      }} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// LIVE TICKER — Banda inferior de señales
// ═══════════════════════════════════════════════════════════════
const SIGNALS = [
  { icon:'✈️', text:'ADS-B · 847 aeronaves militares activas', col:'#00e5ff' },
  { icon:'🚢', text:'AIS · 23 portaaviones en tránsito', col:'#f59e0b' },
  { icon:'📡', text:'SIGINT · Actividad RF elevada — Mar de China', col:'#ef4444' },
  { icon:'📊', text:'MERCADOS · S&P -1.4% · Petróleo +2.1%', col:'#10b981' },
  { icon:'🔴', text:'BREAKING · Movimiento de tropas — frontera bielorrusa', col:'#ef4444' },
  { icon:'🛰', text:'Starlink · 412 satélites sobre zona de conflicto', col:'#a5b4fc' },
  { icon:'🌐', text:'NEXO · 78 consultas procesadas hoy', col:'#00e5ff' },
  { icon:'⚠️', text:'ALERTA · Tensión geopolítica DEFCON-4 — región APAC', col:'#f59e0b' },
  { icon:'🔵', text:'IA · Línea de tiempo generada — Conflicto Sudán', col:'#a5b4fc' },
  { icon:'📰', text:'FEED · 2.4k fuentes OSINT activas', col:'#10b981' },
];

function LiveTicker() {
  const [idx, setIdx] = useState(0);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const iv = setInterval(() => {
      setVisible(false);
      setTimeout(() => { setIdx(i => (i + 1) % SIGNALS.length); setVisible(true); }, 300);
    }, 3800);
    return () => clearInterval(iv);
  }, []);

  const sig = SIGNALS[idx];
  return (
    <div style={{
      position:'fixed', bottom:0, left:0, right:0, zIndex:200,
      background:'rgba(3,7,18,0.97)', borderTop:'1px solid var(--border)',
      backdropFilter:'blur(16px)', display:'flex', alignItems:'center',
      padding:'9px 32px', gap:16,
    }}>
      <span style={{ fontFamily:"'Space Mono',monospace", fontSize:8, color:'var(--dim)', letterSpacing:'.2em', textTransform:'uppercase', whiteSpace:'nowrap', paddingRight:16, borderRight:'1px solid var(--border)', flexShrink:0 }}>
        SEÑAL OSINT
      </span>
      <div style={{
        flex:1, overflow:'hidden',
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(6px)',
        transition:'opacity 0.3s ease, transform 0.3s ease',
        display:'flex', alignItems:'center', gap:10,
      }}>
        <span style={{ fontSize:13 }}>{sig.icon}</span>
        <span style={{ fontFamily:"'Space Mono',monospace", fontSize:11, color:'var(--muted)' }}>
          <span style={{ color: sig.col, fontWeight:700 }}>{sig.text.split('·')[0]}·</span>
          {sig.text.split('·').slice(1).join('·')}
        </span>
      </div>
      <div style={{ display:'flex', alignItems:'center', gap:6, fontFamily:"'Space Mono',monospace", fontSize:8, color:'var(--green)', flexShrink:0 }}>
        <span style={{ width:5, height:5, borderRadius:'50%', background:'var(--green)', boxShadow:'0 0 6px var(--green)', animation:'blink-dot 1.5s infinite' }} />
        LIVE
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// CAPABILITY CARD
// ═══════════════════════════════════════════════════════════════
function CapCard({ icon, title, desc, tag, accent='var(--cyan)', delay=0 }) {
  return (
    <div className="card-hover animate-fade-up" style={{
      background:'var(--bg2)', border:'1px solid var(--border)',
      padding:'32px 28px', position:'relative', overflow:'hidden',
      display:'flex', flexDirection:'column', gap:14,
      animationDelay:`${delay}ms`,
    }}>
      {/* Corner accent */}
      <div style={{ position:'absolute', top:0, right:0, width:60, height:60, background:`radial-gradient(circle at top right, ${accent}18, transparent 70%)`, pointerEvents:'none' }} />
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
        <span style={{ fontSize:24 }}>{icon}</span>
        <span style={{ fontFamily:"'Space Mono',monospace", fontSize:8, color:accent, letterSpacing:'.18em', textTransform:'uppercase', border:`1px solid ${accent}30`, padding:'3px 8px', background:`${accent}08` }}>{tag}</span>
      </div>
      <h3 style={{ fontSize:14, fontWeight:700, color:'var(--text)', letterSpacing:'-0.01em' }}>{title}</h3>
      <p style={{ fontFamily:"'Space Mono',monospace", fontSize:11, color:'var(--muted)', lineHeight:1.8, flex:1 }}>{desc}</p>
      <div style={{ height:1, background:`linear-gradient(90deg,${accent}50,transparent)` }} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// ASSET TRACKER — Panel de rastreo en vivo
// ═══════════════════════════════════════════════════════════════
const ASSETS = [
  { icon:'✈️', type:'Aeronave Militar', id:'RQ-4B USAF', pos:'Mar Negro — 34,000 ft', col:'#ef4444', status:'SIGUIENDO' },
  { icon:'🚢', type:'Portaaviones',     id:'USS Gerald R. Ford', pos:'Mediterráneo Oriental', col:'#f59e0b', status:'EN ZONA' },
  { icon:'🛰', type:'Satélite ISR',     id:'KH-13 USA-290', pos:'Órbita baja — paso 14min', col:'#a5b4fc', status:'ACTIVO' },
  { icon:'✈️', type:'Carga Militar',    id:'C-17A 97-0046', pos:'Ramstein AB → Rzeszów', col:'#f59e0b', status:'EN TRÁNSITO' },
  { icon:'🚢', type:'Submarino Nuclear',id:'SSBN-740 Maine', pos:'Atlántico Norte [class.]', col:'#ef4444', status:'SIGILO' },
];

function AssetTracker() {
  const [active, setActive] = useState(0);
  useEffect(() => {
    const iv = setInterval(() => setActive(i => (i + 1) % ASSETS.length), 2200);
    return () => clearInterval(iv);
  }, []);

  return (
    <div style={{ background:'var(--bg2)', border:'1px solid var(--border)', padding:24 }} className="hud-bracket">
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20, paddingBottom:14, borderBottom:'1px solid var(--border)' }}>
        <span style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:'var(--dim)', letterSpacing:'.14em', textTransform:'uppercase' }}>Activos Globales</span>
        <span className="status-alert">TRACKING LIVE</span>
      </div>
      {ASSETS.map((a, i) => (
        <div key={i} style={{
          display:'flex', gap:12, alignItems:'center', padding:'10px 8px',
          borderBottom: i < ASSETS.length-1 ? '1px solid rgba(0,229,255,0.05)' : 'none',
          background: active===i ? `${a.col}08` : 'transparent',
          borderLeft: active===i ? `2px solid ${a.col}` : '2px solid transparent',
          transition:'all 0.4s var(--ease-out)',
          paddingLeft: active===i ? 16 : 8,
        }}>
          <span style={{ fontSize:16, flexShrink:0 }}>{a.icon}</span>
          <div style={{ flex:1, minWidth:0 }}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
              <span style={{ fontFamily:"'Space Mono',monospace", fontSize:11, color:'var(--text)', fontWeight:700 }}>{a.id}</span>
              <span style={{ fontFamily:"'Space Mono',monospace", fontSize:8, color:a.col, letterSpacing:'.1em', background:`${a.col}15`, padding:'2px 6px', border:`1px solid ${a.col}30` }}>{a.status}</span>
            </div>
            <div style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:'var(--dim)', marginTop:2 }}>{a.type} · {a.pos}</div>
          </div>
          <div style={{ width:6, height:6, borderRadius:'50%', background:a.col, boxShadow:`0 0 ${active===i?'10px':'4px'} ${a.col}`, transition:'box-shadow 0.4s', flexShrink:0 }} />
        </div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// THREAT MATRIX — Nivel de amenaza global
// ═══════════════════════════════════════════════════════════════
const THREAT_ZONES = [
  { region:'APAC', level:4, label:'DEFCON-4', color:'#ef4444' },
  { region:'Europa E.', level:3, label:'ELEVADO', color:'#f59e0b' },
  { region:'Medio Oriente', level:4, label:'CRÍTICO', color:'#ef4444' },
  { region:'África Sahel', level:2, label:'MODERADO', color:'#f59e0b' },
  { region:'Am. Latina', level:1, label:'BAJO', color:'#10b981' },
  { region:'Ártico', level:2, label:'VIGILANCIA', color:'#a5b4fc' },
];

function ThreatMatrix() {
  return (
    <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:6 }}>
      {THREAT_ZONES.map((z, i) => (
        <div key={i} className="animate-fade-up" style={{
          background:`${z.color}08`, border:`1px solid ${z.color}25`,
          padding:'12px 14px', animationDelay:`${i*80}ms`,
          transition:'all 0.3s ease',
        }}
          onMouseEnter={e => e.currentTarget.style.background=`${z.color}15`}
          onMouseLeave={e => e.currentTarget.style.background=`${z.color}08`}
        >
          <div style={{ fontFamily:"'Space Mono',monospace", fontSize:8, color:'var(--dim)', letterSpacing:'.12em', textTransform:'uppercase', marginBottom:4 }}>{z.region}</div>
          <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:6 }}>
            {[1,2,3,4,5].map(n => (
              <div key={n} style={{ flex:1, height:3, background: n<=z.level?z.color:'rgba(255,255,255,0.06)', borderRadius:2, transition:'all 0.3s' }} />
            ))}
          </div>
          <div style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:z.color, fontWeight:700, letterSpacing:'.08em' }}>{z.label}</div>
        </div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// INTELLIGENCE FEED — Noticias vivas
// ═══════════════════════════════════════════════════════════════
const FEED_ITEMS = [
  { tag:'MILITAR',   color:'#ef4444', hot:true,  title:'China despliega 3 portaaviones frente a Taiwán en maniobras no anunciadas', src:'OSINT / Sentinel-2',    time:'4 min' },
  { tag:'ECONÓMICO', color:'#10b981', hot:false, title:'S&P 500 cae 1.4% tras datos de empleo peor de lo esperado por la Fed',   src:'Bloomberg / Reuters',  time:'11 min' },
  { tag:'POLÍTICO',  color:'#f59e0b', hot:false, title:'Cumbre G20 Johannesburgo: borrador de acuerdo energético en circulación', src:'Reuters',               time:'23 min' },
  { tag:'OSINT',     color:'#a5b4fc', hot:true,  title:'Imágenes satelitales confirman movimiento de blindados en Darfur Norte',  src:'Planet Labs',           time:'38 min' },
  { tag:'GEOPOLÍTICA',color:'#00e5ff',hot:false, title:'Rusia activa ejercicios navales no programados en el Báltico',            src:'NATO Watch / OSINT',    time:'52 min' },
];

function IntelFeed() {
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:0 }}>
      {FEED_ITEMS.map((item, i) => (
        <Link key={i} to="/control" style={{ textDecoration:'none' }}>
          <div className="data-row animate-fade-up" style={{
            padding:'14px 0', animationDelay:`${i*100}ms`,
            borderBottom:'1px solid rgba(0,229,255,0.06)',
          }}
            onMouseEnter={e => e.currentTarget.style.background='rgba(0,229,255,0.02)'}
            onMouseLeave={e => e.currentTarget.style.background='transparent'}
          >
            <div style={{ display:'flex', alignItems:'flex-start', gap:12 }}>
              <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:6, flexShrink:0, paddingTop:2 }}>
                <span style={{ fontFamily:"'Space Mono',monospace", fontSize:8, color:item.color, letterSpacing:'.1em', background:`${item.color}12`, padding:'2px 6px', border:`1px solid ${item.color}25`, whiteSpace:'nowrap' }}>{item.tag}</span>
                {item.hot && <span style={{ fontFamily:"'Space Mono',monospace", fontSize:7, color:'#ef4444', letterSpacing:'.1em', animation:'blink-dot 1.5s infinite' }}>● HOT</span>}
              </div>
              <div style={{ flex:1, minWidth:0 }}>
                <div style={{ fontFamily:"'Space Mono',monospace", fontSize:12, color:'var(--text)', lineHeight:1.5, marginBottom:4 }}>{item.title}</div>
                <div style={{ display:'flex', gap:12, fontFamily:"'Space Mono',monospace", fontSize:9, color:'var(--dim)' }}>
                  <span>{item.src}</span>
                  <span>·</span>
                  <span>{item.time} atrás</span>
                </div>
              </div>
              <span style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:'var(--cyan)', flexShrink:0, marginTop:2 }}>→</span>
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// TIMELINE PREVIEW
// ═══════════════════════════════════════════════════════════════
const TL_EVENTS = [
  { date:'2024-10-07', label:'Ataque Hamas — Franja de Gaza', type:'militar', col:'#ef4444' },
  { date:'2024-11-05', label:'Elecciones EE.UU. — Trump vence', type:'político', col:'#f59e0b' },
  { date:'2025-01-20', label:'Inauguración — Nuevo gabinete EE.UU.', type:'político', col:'#f59e0b' },
  { date:'2025-03-12', label:'Crisis aranceles — Mercados caen 8%', type:'económico', col:'#10b981' },
  { date:'2025-06-01', label:'Tensión APAC — Maniobras navales PLA', type:'militar', col:'#ef4444' },
  { date:'2026-01-15', label:'Cumbre G20 — Acuerdo energético', type:'económico', col:'#10b981' },
];
function TimelinePreview() {
  return (
    <div style={{ position:'relative', paddingLeft:28 }}>
      <div style={{ position:'absolute', left:10, top:0, bottom:0, width:1, background:'var(--border)' }} />
      {TL_EVENTS.map((e, i) => (
        <div key={i} className="animate-fade-up" style={{ display:'flex', gap:16, marginBottom:18, alignItems:'flex-start', animationDelay:`${i*90}ms` }}>
          <div style={{ position:'absolute', left:6, width:9, height:9, borderRadius:'50%', background:e.col, boxShadow:`0 0 8px ${e.col}`, marginTop:3 }} />
          <div>
            <span style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:'var(--dim)', letterSpacing:'.1em' }}>{e.date}</span>
            <p style={{ fontFamily:"'Space Mono',monospace", fontSize:11, color:'var(--text)', marginTop:2 }}>{e.label}</p>
            <span style={{ fontFamily:"'Space Mono',monospace", fontSize:8, color:e.col, textTransform:'uppercase', letterSpacing:'.1em' }}>{e.type}</span>
          </div>
        </div>
      ))}
      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
        <span className="ping-wrapper" style={{ width:6, height:6, background:'var(--cyan)', borderRadius:'50%', display:'inline-block', position:'relative' }}>
          <span style={{ position:'absolute', inset:0, borderRadius:'50%', background:'var(--cyan)', animation:'pulse-ring 2s ease-out infinite' }} />
        </span>
        <span style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:'var(--cyan)' }}>IA generando eventos en tiempo real…</span>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN
// ═══════════════════════════════════════════════════════════════
export default function Landing() {
  const [scrolled, setScrolled] = useState(false);
  const [query, setQuery] = useState('');
  const [activeTab, setActiveTab] = useState('TODOS');
  const TABS = ['TODOS','MILITAR','POLÍTICO','ECONÓMICO','GEOPOLÍTICA','OSINT'];
  const SUGGESTIONS = ['Guerra en Ucrania','Crisis económica China','Movimientos navales OTAN','Elecciones Latinoamérica'];

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 60);
    window.addEventListener('scroll', fn);
    return () => window.removeEventListener('scroll', fn);
  }, []);

  useEffect(() => {
    const obs = new IntersectionObserver(
      es => es.forEach(e => { if (e.isIntersecting) e.target.classList.add('on'); }),
      { threshold: 0.08 }
    );
    document.querySelectorAll('.reveal,.reveal-left,.reveal-right').forEach(el => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  return (
    <div style={{ background:'var(--bg)', minHeight:'100vh', paddingBottom:52 }}>

      {/* ── NAV ── */}
      <nav style={{
        position:'fixed', top:0, left:0, right:0, zIndex:1000,
        padding: scrolled ? '10px 48px' : '16px 48px',
        display:'flex', alignItems:'center', justifyContent:'space-between',
        borderBottom:'1px solid var(--border)',
        background: scrolled ? 'rgba(3,7,18,0.98)' : 'rgba(3,7,18,0.82)',
        backdropFilter:'blur(24px)',
        transition:'padding 0.3s var(--ease-out), background 0.3s ease',
      }}>
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          <div className="ping-wrapper" style={{ width:7, height:7, position:'relative', flexShrink:0 }}>
            <span style={{ position:'absolute', inset:0, borderRadius:'50%', background:'var(--cyan)', animation:'pulse-ring 2s ease-out infinite' }} />
            <span style={{ position:'relative', width:7, height:7, borderRadius:'50%', background:'var(--cyan)', display:'block', boxShadow:'0 0 10px var(--cyan)' }} />
          </div>
          <span style={{ fontFamily:"'Space Mono',monospace", fontSize:13, fontWeight:700, color:'var(--cyan)', letterSpacing:'.2em', textTransform:'uppercase' }}>El Anarcocapital</span>
        </div>
        <div style={{ display:'flex', gap:28, alignItems:'center' }}>
          {[['#inteligencia','Inteligencia'],['#rastreo','Rastreo'],['#ia','IA'],['#comunidad','Comunidad']].map(([href,label]) => (
            <a key={href} href={href} style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:'var(--dim)', textDecoration:'none', letterSpacing:'.14em', textTransform:'uppercase', transition:'color 0.2s' }}
              onMouseEnter={e=>e.target.style.color='var(--cyan)'}
              onMouseLeave={e=>e.target.style.color='var(--dim)'}
            >{label}</a>
          ))}
          <Link to="/control" style={{
            fontFamily:"'Space Mono',monospace", fontSize:10,
            padding:'9px 22px', background:'var(--cyan)', color:'var(--bg)',
            textDecoration:'none', letterSpacing:'.1em', textTransform:'uppercase', fontWeight:700,
            transition:'box-shadow 0.3s ease',
          }}
            onMouseEnter={e=>e.currentTarget.style.boxShadow='0 0 24px rgba(0,229,255,0.5)'}
            onMouseLeave={e=>e.currentTarget.style.boxShadow='none'}
          >Warroom →</Link>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section style={{ minHeight:'100vh', display:'flex', alignItems:'center', position:'relative', padding:'140px 64px 140px', overflow:'hidden' }}>
        <NeuralCanvas />
        <ScanLine />

        {/* Globe */}
        <div style={{ position:'absolute', right:'2vw', top:'50%', transform:'translateY(-50%)', zIndex:2, opacity:0.65, pointerEvents:'none' }}>
          <Globe3D size={480} color="#00e5ff" speed={0.0025} />
        </div>

        <div style={{ maxWidth:860, position:'relative', zIndex:3 }}>
          {/* Eyebrow badge */}
          <div className="animate-fade-up delay-50" style={{ display:'inline-flex', alignItems:'center', gap:8, fontFamily:"'Space Mono',monospace", fontSize:9, color:'var(--cyan)', letterSpacing:'.2em', textTransform:'uppercase', border:'1px solid var(--border-hi)', padding:'7px 18px', marginBottom:40, background:'rgba(0,229,255,0.04)' }}>
            <span style={{ width:5, height:5, borderRadius:'50%', background:'var(--cyan)', animation:'blink-dot 1.5s infinite' }} />
            Plataforma de Inteligencia Soberana · OSINT · Tiempo Real
          </div>

          {/* Headline con typewriter */}
          <h1 className="animate-fade-up delay-150" style={{ fontSize:'clamp(48px,7.5vw,92px)', fontWeight:800, lineHeight:0.9, letterSpacing:'-0.04em', marginBottom:28 }}>
            <span style={{ color:'var(--text)' }}>VE LO QUE</span><br />
            <span className="gradient-text animate-glitch" style={{ display:'block', lineHeight:1 }}>EL MUNDO</span>
            <span style={{ color:'var(--text)' }}>NO VE.</span>
          </h1>

          {/* Typewriter subtitle */}
          <div className="animate-fade-up delay-300" style={{ fontFamily:"'Space Mono',monospace", fontSize:13, color:'var(--muted)', marginBottom:44, lineHeight:1.9, maxWidth:540 }}>
            Inteligencia en{' '}
            <span style={{ color:'var(--cyan)' }}>
              <TypeWriter
                texts={['tiempo real.','profundidad.','múltiples capas.','fuentes abiertas.','movimiento continuo.']}
                speed={55}
                pause={2000}
              />
            </span>
          </div>

          {/* Search */}
          <div className="animate-fade-up delay-400" style={{ marginBottom:16 }}>
            <div style={{ display:'flex', gap:0, maxWidth:580, border:'1px solid var(--border-hi)', background:'rgba(7,15,26,0.95)', transition:'box-shadow 0.3s ease' }}
              onMouseEnter={e=>e.currentTarget.style.boxShadow='0 0 30px rgba(0,229,255,0.12)'}
              onMouseLeave={e=>e.currentTarget.style.boxShadow='none'}
            >
              <span style={{ padding:'14px 16px', color:'var(--cyan)', fontSize:14, display:'flex', alignItems:'center' }}>⌕</span>
              <input value={query} onChange={e=>setQuery(e.target.value)}
                placeholder="Consulta un evento, conflicto o mercado…"
                style={{ flex:1, background:'transparent', border:'none', outline:'none', fontFamily:"'Space Mono',monospace", fontSize:11, color:'var(--text)', padding:'14px 0' }}
              />
              <Link to="/control" style={{ padding:'14px 24px', background:'var(--cyan)', color:'var(--bg)', fontFamily:"'Space Mono',monospace", fontSize:10, fontWeight:700, textDecoration:'none', display:'flex', alignItems:'center', letterSpacing:'.1em', whiteSpace:'nowrap' }}>ANALIZAR →</Link>
            </div>
            <div style={{ display:'flex', gap:8, marginTop:10, flexWrap:'wrap' }}>
              {SUGGESTIONS.map(s => (
                <button key={s} onClick={()=>setQuery(s)} style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:'var(--dim)', border:'1px solid var(--border)', background:'transparent', padding:'4px 10px', cursor:'pointer', letterSpacing:'.08em', transition:'all 0.2s' }}
                  onMouseEnter={e=>{e.target.style.color='var(--cyan)';e.target.style.borderColor='rgba(0,229,255,0.4)';}}
                  onMouseLeave={e=>{e.target.style.color='var(--dim)';e.target.style.borderColor='var(--border)';}}
                >{s}</button>
              ))}
            </div>
          </div>
        </div>

        {/* Hero stats strip */}
        <div style={{ position:'absolute', bottom:0, left:0, right:0, zIndex:4, borderTop:'1px solid var(--border)', background:'rgba(7,15,26,0.97)', backdropFilter:'blur(16px)', display:'flex', overflow:'hidden' }}>
          {[
            { icon:'✈️', label:'Aeronaves rastreadas', val:847,  suffix:'' },
            { icon:'🚢', label:'Buques en tránsito',   val:23412, suffix:'' },
            { icon:'📡', label:'Fuentes OSINT activas', val:2400, suffix:'+' },
            { icon:'🧠', label:'Consultas IA hoy',     val:78,   suffix:'' },
          ].map((s, i) => (
            <div key={i} style={{ flex:1, padding:'14px 20px', borderRight:i<3?'1px solid var(--border)':'none', display:'flex', alignItems:'center', gap:12 }}>
              <span style={{ fontSize:18 }}>{s.icon}</span>
              <div>
                <div style={{ fontFamily:"'Space Mono',monospace", fontSize:8, color:'var(--dim)', letterSpacing:'.1em', textTransform:'uppercase' }}>{s.label}</div>
                <div style={{ fontFamily:"'Space Mono',monospace", fontSize:16, color:'var(--cyan)', fontWeight:700, marginTop:1 }}>
                  <AnimCounter target={s.val} suffix={s.suffix} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── INTELLIGENCE FEED + THREAT MATRIX ── */}
      <section style={{ padding:'100px 64px', borderTop:'1px solid var(--border)', position:'relative', zIndex:2 }}>
        <div style={{ maxWidth:1280, margin:'0 auto', display:'grid', gridTemplateColumns:'1fr 380px', gap:40 }}>

          {/* Feed */}
          <div>
            <div className="reveal" style={{ marginBottom:24 }}>
              <div className="section-tag">Feed de Inteligencia</div>
              <div style={{ display:'flex', gap:6, flexWrap:'wrap' }}>
                {TABS.map(t => (
                  <button key={t} onClick={()=>setActiveTab(t)} style={{
                    fontFamily:"'Space Mono',monospace", fontSize:9, letterSpacing:'.1em', textTransform:'uppercase',
                    padding:'5px 14px', border:`1px solid ${activeTab===t?'rgba(0,229,255,0.5)':'var(--border)'}`,
                    background: activeTab===t?'rgba(0,229,255,0.08)':'transparent',
                    color: activeTab===t?'var(--cyan)':'var(--dim)', cursor:'pointer', transition:'all 0.2s',
                  }}>{t}</button>
                ))}
              </div>
            </div>
            <div className="reveal">
              <IntelFeed />
              <div style={{ marginTop:16, textAlign:'right' }}>
                <Link to="/control" style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:'var(--cyan)', textDecoration:'none', letterSpacing:'.1em' }}>
                  Ver todos los eventos →
                </Link>
              </div>
            </div>
          </div>

          {/* Threat matrix */}
          <div>
            <div className="reveal" style={{ marginBottom:24 }}>
              <div className="section-tag">Matriz de Amenazas</div>
            </div>
            <div className="reveal">
              <ThreatMatrix />
            </div>
            <div className="reveal" style={{ marginTop:20 }}>
              <div style={{ background:'var(--bg2)', border:'1px solid var(--border)', padding:18 }}>
                <div style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:'var(--dim)', letterSpacing:'.12em', textTransform:'uppercase', marginBottom:12 }}>Indicadores Macro</div>
                {[
                  { label:'Bitcoin',   val:'$66,891', chg:'-0.15%', up:false },
                  { label:'S&P 500',   val:'5,204',   chg:'-1.4%',  up:false },
                  { label:'Petróleo',  val:'$84.2',   chg:'+2.1%',  up:true  },
                  { label:'Oro',       val:'$2,318',  chg:'+0.8%',  up:true  },
                  { label:'USD/ARS',   val:'1,040',   chg:'+0.4%',  up:false },
                ].map(({label,val,chg,up})=>(
                  <div key={label} style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding:'6px 0', borderBottom:'1px solid rgba(0,229,255,0.05)' }}>
                    <span style={{ fontFamily:"'Space Mono',monospace", fontSize:10, color:'var(--muted)' }}>{label}</span>
                    <div style={{ display:'flex', gap:10, alignItems:'center' }}>
                      <span style={{ fontFamily:"'Space Mono',monospace", fontSize:11, color:'var(--text)', fontWeight:700 }}>{val}</span>
                      <span style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:up?'var(--green)':'var(--red)', background:up?'rgba(16,185,129,0.1)':'rgba(239,68,68,0.1)', padding:'1px 6px', border:`1px solid ${up?'rgba(16,185,129,0.2)':'rgba(239,68,68,0.2)'}` }}>{chg}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── CAPACIDADES ── */}
      <section id="inteligencia" style={{ padding:'100px 64px', borderTop:'1px solid var(--border)', position:'relative', zIndex:2 }}>
        <div style={{ maxWidth:1280, margin:'0 auto' }}>
          <div className="reveal" style={{ marginBottom:56 }}>
            <div className="section-tag">Capacidades</div>
            <h2 style={{ fontSize:'clamp(30px,4vw,52px)', fontWeight:800, letterSpacing:'-0.025em', lineHeight:1.05, maxWidth:640 }}>
              Una plataforma.<br /><span className="gradient-text">Inteligencia sin límites.</span>
            </h2>
          </div>
          <div className="reveal" style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:1, background:'var(--border)', border:'1px solid var(--border)' }}>
            <CapCard icon="🧠" tag="IA"             title="Análisis con IA"             desc="Pregunta sobre cualquier evento mundial. La IA consulta miles de fuentes, construye contexto y entrega análisis con evidencia verificable." accent="#a5b4fc" delay={0} />
            <CapCard icon="🗓" tag="Timeline"        title="Timelines con Evidencia"     desc="Visualiza la evolución de cualquier conflicto con una línea de tiempo generada desde fuentes abiertas y verificadas." accent="var(--cyan)" delay={80} />
            <CapCard icon="📡" tag="OSINT"           title="Fuentes Omnicanal"           desc="Tweets, cámaras en vivo, boletines gubernamentales, filtraciones, datos satelitales y foros — todo en un solo feed." accent="#10b981" delay={160} />
            <CapCard icon="✈️" tag="Rastreo ADS-B"  title="Rastreo de Activos Globales" desc="Seguimiento en tiempo real de aeronaves militares, buques, movimientos logísticos y posicionamiento de tropas." accent="#f59e0b" delay={240} />
            <CapCard icon="📊" tag="Mercados"        title="Inteligencia de Mercado"     desc="Indicadores macro, precios de commodities, flujos de capital, alertas de volatilidad correlacionadas con eventos geopolíticos." accent="#10b981" delay={320} />
            <CapCard icon="🗂" tag="RAG / Bóveda"   title="Bóveda de Inteligencia"      desc="Conocimiento acumulado, documentos Drive, análisis previos e inteligencia indexada con búsqueda vectorial semántica." accent="#a5b4fc" delay={400} />
          </div>
        </div>
      </section>

      {/* ── TIMELINE + RASTREO ── */}
      <section id="ia" style={{ padding:'100px 64px', borderTop:'1px solid var(--border)', position:'relative', zIndex:2 }}>
        <div style={{ maxWidth:1280, margin:'0 auto', display:'grid', gridTemplateColumns:'1fr 1fr', gap:72, alignItems:'center' }}>
          <div className="reveal-left">
            <div className="section-tag">IA + Evidencia</div>
            <h2 style={{ fontSize:'clamp(28px,4vw,50px)', fontWeight:800, letterSpacing:'-0.025em', lineHeight:1.05, marginBottom:20 }}>
              Cualquier evento.<br /><span className="gradient-text">Toda la historia.</span>
            </h2>
            <p style={{ fontFamily:"'Space Mono',monospace", fontSize:12, color:'var(--muted)', lineHeight:1.85, marginBottom:32 }}>
              Escribe el nombre de un conflicto, crisis o evento. NEXO recupera fuentes primarias, las ordena cronológicamente y genera una línea de tiempo con cada pieza de evidencia vinculada.
            </p>
            <div style={{ display:'flex', flexDirection:'column', gap:12 }} className="stagger">
              {['Fuentes primarias verificadas','Correlación con eventos simultáneos','Contexto histórico automático','Exportable a PDF / JSON'].map(f => (
                <div key={f} style={{ display:'flex', alignItems:'center', gap:10, fontFamily:"'Space Mono',monospace", fontSize:11, color:'var(--muted)' }}>
                  <span style={{ color:'var(--cyan)', fontSize:12 }}>◆</span>{f}
                </div>
              ))}
            </div>
            <Link to="/control" style={{ display:'inline-block', marginTop:36, fontFamily:"'Space Mono',monospace", fontSize:11, padding:'12px 28px', background:'var(--cyan)', color:'var(--bg)', textDecoration:'none', fontWeight:700, letterSpacing:'.1em', textTransform:'uppercase' }}>
              Crear Línea de Tiempo →
            </Link>
          </div>
          <div className="reveal-right" style={{ background:'var(--bg2)', border:'1px solid var(--border)', padding:28 }}>
            <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:22, paddingBottom:14, borderBottom:'1px solid var(--border)' }}>
              <span className="ping-wrapper" style={{ width:6, height:6, position:'relative', display:'inline-block', flexShrink:0 }}>
                <span style={{ position:'absolute', inset:0, borderRadius:'50%', background:'var(--cyan)', animation:'pulse-ring 2s ease-out infinite' }} />
                <span style={{ position:'relative', width:6, height:6, borderRadius:'50%', background:'var(--cyan)', display:'block' }} />
              </span>
              <span style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:'var(--cyan)', letterSpacing:'.15em', textTransform:'uppercase' }}>Timeline · Generado por IA</span>
              <span style={{ marginLeft:'auto', fontFamily:"'Space Mono',monospace", fontSize:8, padding:'2px 8px', border:'1px solid var(--green)', color:'var(--green)' }}>LIVE</span>
            </div>
            <TimelinePreview />
          </div>
        </div>
      </section>

      {/* ── RASTREO ── */}
      <section id="rastreo" style={{ padding:'100px 64px', borderTop:'1px solid var(--border)', position:'relative', zIndex:2 }}>
        <div style={{ maxWidth:1280, margin:'0 auto', display:'grid', gridTemplateColumns:'1fr 1fr', gap:72, alignItems:'center' }}>
          <div className="reveal-left">
            <AssetTracker />
          </div>
          <div className="reveal-right">
            <div className="section-tag">Rastreo Global</div>
            <h2 style={{ fontSize:'clamp(28px,4vw,50px)', fontWeight:800, letterSpacing:'-0.025em', lineHeight:1.05, marginBottom:20 }}>
              Ve los activos<br /><span className="gradient-text">antes que los medios.</span>
            </h2>
            <p style={{ fontFamily:"'Space Mono',monospace", fontSize:12, color:'var(--muted)', lineHeight:1.85, marginBottom:28 }}>
              ADS-B en tiempo real, AIS marítimo, movimientos de carga militar y logística de conflictos. Cuando algo se mueve en el mundo, NEXO lo detecta primero.
            </p>
            <div className="stagger">
              {[['✈️','Aeronaves militares y civiles (ADS-B)'],['🚢','Flota naval global (AIS)'],['🛰','Cobertura satelital ISR'],['📦','Logística de conflictos activos'],['🏗','Infraestructura crítica']].map(([icon,label])=>(
                <div key={label} style={{ display:'flex', gap:10, alignItems:'center', fontFamily:"'Space Mono',monospace", fontSize:11, color:'var(--muted)', marginBottom:10 }}>
                  <span>{icon}</span>{label}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA COMUNIDAD ── */}
      <section id="comunidad" style={{ padding:'100px 64px', borderTop:'1px solid var(--border)', position:'relative', zIndex:2 }}>
        <div style={{ maxWidth:1280, margin:'0 auto' }}>
          <div className="reveal" style={{ textAlign:'center', maxWidth:640, margin:'0 auto' }}>
            <div className="section-tag" style={{ justifyContent:'center' }}>Comunidad</div>
            <h2 style={{ fontSize:'clamp(32px,5vw,64px)', fontWeight:800, letterSpacing:'-0.03em', lineHeight:1, marginBottom:20 }}>
              Inteligencia<br /><span className="holo-text">colectiva.</span>
            </h2>
            <p style={{ fontFamily:"'Space Mono',monospace", fontSize:12, color:'var(--muted)', lineHeight:1.88, marginBottom:44 }}>
              Únete a analistas, periodistas y ciudadanos que usan NEXO para entender el mundo real. Comparte hallazgos, colabora en investigaciones y accede a la bóveda de inteligencia colectiva.
            </p>
            <div style={{ display:'flex', gap:12, justifyContent:'center', flexWrap:'wrap' }}>
              <Link to="/control" style={{ fontFamily:"'Space Mono',monospace", fontSize:11, padding:'14px 40px', background:'var(--cyan)', color:'var(--bg)', textDecoration:'none', fontWeight:700, letterSpacing:'.1em', textTransform:'uppercase', transition:'box-shadow 0.3s ease' }}
                onMouseEnter={e=>e.currentTarget.style.boxShadow='0 0 32px rgba(0,229,255,0.5)'}
                onMouseLeave={e=>e.currentTarget.style.boxShadow='none'}
              >Acceder al Sistema</Link>
              <a href="https://github.com/Reidskar/NEXO_SOBERANO" target="_blank" rel="noreferrer" style={{ fontFamily:"'Space Mono',monospace", fontSize:11, padding:'14px 40px', border:'1px solid var(--border-hi)', color:'var(--muted)', textDecoration:'none', letterSpacing:'.1em', textTransform:'uppercase', transition:'all 0.3s ease' }}
                onMouseEnter={e=>{e.currentTarget.style.color='var(--cyan)';e.currentTarget.style.borderColor='rgba(0,229,255,0.5)';}}
                onMouseLeave={e=>{e.currentTarget.style.color='var(--muted)';e.currentTarget.style.borderColor='var(--border-hi)';}}
              >GitHub ↗</a>
            </div>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer style={{ borderTop:'1px solid var(--border)', padding:'20px 64px', display:'flex', alignItems:'center', justifyContent:'space-between', background:'rgba(7,15,26,0.8)', position:'relative', zIndex:2 }}>
        <span style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:'var(--dim)', letterSpacing:'.06em' }}>El Anarcocapital · © 2026 Camilo Estefano · Inteligencia Soberana</span>
        <div style={{ display:'flex', gap:20 }}>
          {[['#inteligencia','Capacidades'],['#ia','IA'],['#rastreo','Rastreo'],['/control','Warroom']].map(([href,label])=>(
            <a key={href} href={href} style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:'var(--dim)', textDecoration:'none', transition:'color 0.2s' }}
              onMouseEnter={e=>e.target.style.color='var(--cyan)'}
              onMouseLeave={e=>e.target.style.color='var(--dim)'}
            >{label}</a>
          ))}
        </div>
      </footer>

      <LiveTicker />
    </div>
  );
}
