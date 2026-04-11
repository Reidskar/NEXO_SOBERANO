import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import Globe3D from '../components/Globe3D';

// ─── Neural Canvas ─────────────────────────────────────────────────────────────
function NeuralCanvas() {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let W, H, pts = [], animId;
    const resize = () => { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; };
    resize();
    window.addEventListener('resize', resize);
    class P {
      constructor() { this.x = Math.random() * W; this.y = Math.random() * H; this.r = Math.random() * 1.5 + 0.5; this.vx = (Math.random() - 0.5) * 0.4; this.vy = (Math.random() - 0.5) * 0.4; }
      move() { this.x += this.vx; this.y += this.vy; if (this.x < 0 || this.x > W) this.vx *= -1; if (this.y < 0 || this.y > H) this.vy *= -1; }
    }
    for (let i = 0; i < 80; i++) pts.push(new P());
    const draw = () => {
      ctx.clearRect(0, 0, W, H);
      pts.forEach(p => { p.move(); ctx.fillStyle = 'rgba(0,229,255,0.5)'; ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill(); });
      for (let a = 0; a < pts.length; a++) for (let b = a + 1; b < pts.length; b++) {
        const dx = pts[a].x - pts[b].x, dy = pts[a].y - pts[b].y, d = Math.sqrt(dx * dx + dy * dy);
        if (d < 130) { ctx.strokeStyle = `rgba(0,229,255,${(1 - d / 130) * 0.3})`; ctx.lineWidth = 0.6; ctx.beginPath(); ctx.moveTo(pts[a].x, pts[a].y); ctx.lineTo(pts[b].x, pts[b].y); ctx.stroke(); }
      }
      animId = requestAnimationFrame(draw);
    };
    draw();
    return () => { window.removeEventListener('resize', resize); cancelAnimationFrame(animId); };
  }, []);
  return <canvas ref={canvasRef} style={{ position: 'absolute', inset: 0, opacity: 0.35, zIndex: 1, pointerEvents: 'none' }} />;
}

// ─── Live ticker ──────────────────────────────────────────────────────────────
const SIGNALS = [
  '🛩  ADS-B · 847 aeronaves militares activas',
  '🚢  AIS · 23 portaaviones en tránsito',
  '📡  SIGINT · Actividad RF elevada — Mar de China',
  '📊  MERCADOS · S&P -1.4% · Petróleo +2.1%',
  '🔴  BREAKING · Movimiento de tropas — frontera bielorrusa',
  '🛰  Starlink · 412 satélites sobre zona de conflicto',
  '🌐  NEXO · 78 consultas procesadas hoy',
  '⚠️  ALERTA · Tensión geopolítica DEFCON-4 — región APAC',
  '🔵  IA · Línea de tiempo generada — Conflicto Sudán',
  '📰  FEED · 2.4k fuentes OSINT activas',
];

function LiveTicker() {
  const [idx, setIdx] = useState(0);
  useEffect(() => { const iv = setInterval(() => setIdx(i => (i + 1) % SIGNALS.length), 3500); return () => clearInterval(iv); }, []);
  return (
    <div style={{
      position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 100,
      background: 'rgba(3,7,18,0.97)', borderTop: '1px solid var(--border)',
      padding: '10px 32px', display: 'flex', alignItems: 'center', gap: 16
    }}>
      <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 9, color: 'var(--cyan)', letterSpacing: '0.2em', textTransform: 'uppercase', whiteSpace: 'nowrap', borderRight: '1px solid var(--border)', paddingRight: 16 }}>SEÑALES EN VIVO</span>
      <span key={idx} style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: 'var(--muted)', animation: 'fade-up 0.4s var(--ease-out) both' }}>{SIGNALS[idx]}</span>
      <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6, fontFamily: "'Space Mono', monospace", fontSize: 9, color: 'var(--green)' }}>
        <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--green)', animation: 'blink-dot 1.5s infinite' }} />
        LIVE
      </span>
    </div>
  );
}

// ─── Capability Card ──────────────────────────────────────────────────────────
function CapCard({ icon, title, desc, tag, accent = 'var(--cyan)' }) {
  return (
    <div className="card-hover" style={{
      background: 'var(--bg2)', border: '1px solid var(--border)',
      padding: '32px 28px', position: 'relative', overflow: 'hidden',
      display: 'flex', flexDirection: 'column', gap: 14
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <span style={{ fontSize: 26 }}>{icon}</span>
        <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 9, color: accent, letterSpacing: '0.18em', textTransform: 'uppercase', border: `1px solid ${accent}30`, padding: '3px 8px' }}>{tag}</span>
      </div>
      <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.01em' }}>{title}</h3>
      <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: 'var(--muted)', lineHeight: 1.75, flex: 1 }}>{desc}</p>
      <div style={{ height: 1, background: `linear-gradient(90deg, ${accent}40, transparent)` }} />
    </div>
  );
}

// ─── Timeline preview ─────────────────────────────────────────────────────────
const TL_EVENTS = [
  { date: '2024-10-07', label: 'Ataque Hamas — Gaza', type: 'militar', col: '#ef4444' },
  { date: '2024-11-05', label: 'Elecciones EE.UU. — Trump vence', type: 'político', col: '#f59e0b' },
  { date: '2025-01-20', label: 'Inaugaración — Nuevo gabinete', type: 'político', col: '#f59e0b' },
  { date: '2025-03-12', label: 'Crisis aranceles — Mercados caen 8%', type: 'económico', col: '#10b981' },
  { date: '2025-06-01', label: 'Tensión APAC — Maniobras navales', type: 'militar', col: '#ef4444' },
  { date: '2026-01-15', label: 'Cumbre G20 — Acuerdo energético', type: 'económico', col: '#10b981' },
];

function TimelinePreview() {
  return (
    <div style={{ position: 'relative', paddingLeft: 28 }}>
      <div style={{ position: 'absolute', left: 10, top: 0, bottom: 0, width: 1, background: 'var(--border)' }} />
      {TL_EVENTS.map((e, i) => (
        <div key={i} style={{ display: 'flex', gap: 16, marginBottom: 20, alignItems: 'flex-start', animation: `fade-up 0.4s var(--ease-out) ${i * 80}ms both` }}>
          <div style={{ position: 'absolute', left: 6, width: 9, height: 9, borderRadius: '50%', background: e.col, boxShadow: `0 0 8px ${e.col}`, marginTop: 3 }} />
          <div>
            <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 9, color: 'var(--dim)', letterSpacing: '0.1em' }}>{e.date}</span>
            <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: 'var(--text)', marginTop: 2 }}>{e.label}</p>
            <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 9, color: e.col, textTransform: 'uppercase', letterSpacing: '0.1em' }}>{e.type}</span>
          </div>
        </div>
      ))}
      <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: 'var(--cyan)', display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--cyan)', animation: 'blink-dot 1.5s infinite' }} />
        IA generando eventos en tiempo real...
      </div>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function Landing() {
  const [scrolled, setScrolled] = useState(false);
  const [query, setQuery] = useState('');
  const SUGGESTIONS = ['Guerra en Ucrania', 'Crisis económica China', 'Movimientos navales OTAN', 'Elecciones Latinoamérica'];

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 60);
    window.addEventListener('scroll', fn);
    return () => window.removeEventListener('scroll', fn);
  }, []);

  useEffect(() => {
    const obs = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) e.target.classList.add('on'); }), { threshold: 0.1 });
    document.querySelectorAll('.reveal').forEach(el => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh', paddingBottom: 48 }}>

      {/* ── NAV ── */}
      <nav style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1000,
        padding: scrolled ? '12px 48px' : '18px 48px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        borderBottom: '1px solid var(--border)',
        background: scrolled ? 'rgba(3,7,18,0.98)' : 'rgba(3,7,18,0.85)',
        backdropFilter: 'blur(24px)',
        transition: 'padding 0.3s var(--ease-out)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--cyan)', boxShadow: '0 0 10px var(--cyan)', animation: 'blink-dot 2s infinite' }} />
          <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 13, fontWeight: 700, color: 'var(--cyan)', letterSpacing: '0.2em', textTransform: 'uppercase' }}>El Anarcocapital</span>
        </div>
        <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
          {[['#inteligencia', 'Inteligencia'], ['#rastreo', 'Rastreo'], ['#ia', 'IA'], ['#comunidad', 'Comunidad']].map(([href, label]) => (
            <a key={href} href={href} style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: 'var(--dim)', textDecoration: 'none', letterSpacing: '0.12em', textTransform: 'uppercase', transition: 'color 0.2s' }}
              onMouseEnter={e => e.target.style.color = 'var(--cyan)'}
              onMouseLeave={e => e.target.style.color = 'var(--dim)'}
            >{label}</a>
          ))}
          <a href="/omniglobe" style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: 'var(--dim)', textDecoration: 'none', letterSpacing: '0.12em', textTransform: 'uppercase', transition: 'color 0.2s', display: 'flex', alignItems: 'center', gap: 5 }}
            onMouseEnter={e => { e.currentTarget.style.color = 'var(--cyan)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--dim)'; }}
          >
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'currentColor', display: 'inline-block' }} />
            OmniGlobe
          </a>
          <a href="/flowmap" style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: 'var(--dim)', textDecoration: 'none', letterSpacing: '0.12em', textTransform: 'uppercase', transition: 'color 0.2s' }}
            onMouseEnter={e => { e.currentTarget.style.color = 'var(--cyan)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--dim)'; }}
          >FlowMap</a>
          <Link to="/control" style={{
            fontFamily: "'Space Mono', monospace", fontSize: 10,
            padding: '8px 20px', background: 'var(--cyan)', color: 'var(--bg)',
            textDecoration: 'none', letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 700
          }}>Warroom →</Link>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center',
        position: 'relative', padding: '140px 48px 120px', overflow: 'hidden'
      }}>
        <NeuralCanvas />
        <a href="/omniglobe" style={{ position: 'absolute', right: '3vw', top: '50%', transform: 'translateY(-50%)', zIndex: 2, opacity: 0.72, textDecoration: 'none', display: 'block', transition: 'opacity 0.3s' }}
          onMouseEnter={e => { e.currentTarget.style.opacity = '1'; }}
          onMouseLeave={e => { e.currentTarget.style.opacity = '0.72'; }}
          title="Abrir OmniGlobe 3D Interactivo"
        >
          <Globe3D size={460} color="#00e5ff" speed={0.003} />
          <div style={{ position: 'absolute', bottom: 20, left: '50%', transform: 'translateX(-50%)', fontFamily: "'Space Mono', monospace", fontSize: 9, color: '#00e5ff', letterSpacing: '0.2em', textTransform: 'uppercase', whiteSpace: 'nowrap', opacity: 0, transition: 'opacity 0.2s' }}
            onMouseEnter={e => { e.currentTarget.style.opacity = '1'; }}
          >◈ VER OMNIGLOBE →</div>
        </a>

        <div style={{ maxWidth: 820, position: 'relative', zIndex: 3 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontFamily: "'Space Mono', monospace", fontSize: 10, color: 'var(--cyan)', letterSpacing: '0.2em', textTransform: 'uppercase', border: '1px solid var(--border-hi)', padding: '6px 16px', marginBottom: 36, background: 'rgba(0,229,255,0.05)', animation: 'fade-up 0.5s var(--ease-out) 0.1s both' }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--cyan)', animation: 'blink-dot 1.5s infinite' }} />
            Plataforma de Inteligencia Soberana · OSINT · Tiempo Real
          </div>

          <h1 style={{ fontSize: 'clamp(48px,8vw,96px)', fontWeight: 800, lineHeight: 0.92, letterSpacing: '-0.04em', marginBottom: 24, animation: 'fade-up 0.6s var(--ease-out) 0.25s both' }}>
            <span style={{ color: 'var(--text)' }}>VE LO QUE</span><br />
            <span className="gradient-text">EL MUNDO</span><br />
            <span style={{ color: 'var(--text)' }}>NO VE.</span>
          </h1>

          <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 13, lineHeight: 1.85, color: 'var(--muted)', maxWidth: 520, marginBottom: 44, animation: 'fade-up 0.6s var(--ease-out) 0.4s both' }}>
            Inteligencia geopolítica, económica y militar en tiempo real. Rastreo de activos globales, análisis con IA y líneas de tiempo construidas con evidencia. Todo en un solo lugar.
          </p>

          {/* Search bar */}
          <div style={{ animation: 'fade-up 0.6s var(--ease-out) 0.55s both', marginBottom: 20 }}>
            <div style={{ display: 'flex', gap: 0, maxWidth: 560, border: '1px solid var(--border-hi)', background: 'rgba(7,15,26,0.95)' }}>
              <span style={{ padding: '14px 16px', color: 'var(--cyan)', fontSize: 14, display: 'flex', alignItems: 'center' }}>🔍</span>
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Consulta un evento, conflicto o mercado..."
                style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', fontFamily: "'Space Mono', monospace", fontSize: 12, color: 'var(--text)', padding: '14px 0' }}
              />
              <Link to="/control" style={{ padding: '14px 24px', background: 'var(--cyan)', color: 'var(--bg)', fontFamily: "'Space Mono', monospace", fontSize: 11, fontWeight: 700, textDecoration: 'none', display: 'flex', alignItems: 'center', letterSpacing: '0.1em', whiteSpace: 'nowrap' }}>ANALIZAR →</Link>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
              {SUGGESTIONS.map(s => (
                <button key={s} onClick={() => setQuery(s)} style={{ fontFamily: "'Space Mono', monospace", fontSize: 9, color: 'var(--dim)', border: '1px solid var(--border)', background: 'transparent', padding: '4px 10px', cursor: 'pointer', letterSpacing: '0.08em', transition: 'color 0.2s, border-color 0.2s' }}
                  onMouseEnter={e => { e.target.style.color = 'var(--cyan)'; e.target.style.borderColor = 'var(--cyan)'; }}
                  onMouseLeave={e => { e.target.style.color = 'var(--dim)'; e.target.style.borderColor = 'var(--border)'; }}
                >{s}</button>
              ))}
            </div>
          </div>
        </div>

        {/* Status strip */}
        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, zIndex: 4, borderTop: '1px solid var(--border)', background: 'rgba(7,15,26,0.97)', backdropFilter: 'blur(16px)', display: 'flex', overflow: 'hidden' }}>
          {[
            { icon: '✈️', label: 'Aeronaves rastreadas', val: '847' },
            { icon: '🚢', label: 'Buques en tránsito', val: '23,412' },
            { icon: '📡', label: 'Fuentes OSINT activas', val: '2,400+' },
            { icon: '🧠', label: 'Consultas IA hoy', val: '78' },
          ].map((s, i) => (
            <div key={i} style={{ flex: 1, padding: '14px 22px', borderRight: i < 3 ? '1px solid var(--border)' : 'none', display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontSize: 18 }}>{s.icon}</span>
              <div>
                <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 9, color: 'var(--dim)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>{s.label}</div>
                <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 15, color: 'var(--cyan)', fontWeight: 700, marginTop: 1 }}>{s.val}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── CAPACIDADES ── */}
      <section id="inteligencia" style={{ padding: '120px 48px', borderTop: '1px solid var(--border)', position: 'relative', zIndex: 2 }}>
        <div style={{ maxWidth: 1240, margin: '0 auto' }}>
          <div className="reveal" style={{ marginBottom: 56 }}>
            <div className="section-tag">Capacidades</div>
            <h2 style={{ fontSize: 'clamp(30px,4vw,52px)', fontWeight: 800, letterSpacing: '-0.025em', lineHeight: 1.1, maxWidth: 640 }}>
              Una plataforma.<br /><span className="gradient-text">Inteligencia sin límites.</span>
            </h2>
          </div>
          <div className="reveal" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1, background: 'var(--border)', border: '1px solid var(--border)' }}>
            <CapCard icon="🧠" tag="IA" title="Análisis con IA" desc="Pregunta sobre cualquier evento mundial. La IA consulta miles de fuentes, construye contexto y te entrega un análisis con evidencia verificable." accent="#a5b4fc" />
            <CapCard icon="🗓" tag="Línea de tiempo" title="Timelines con Evidencia" desc="Visualiza la evolución de cualquier conflicto, crisis o evento con una línea de tiempo generada automáticamente desde fuentes abiertas." accent="var(--cyan)" />
            <CapCard icon="📡" tag="OSINT" title="Fuentes Omnicanal" desc="Tweets, cámaras en vivo, boletines gubernamentales, filtraciones, datos satelitales y foros — todo integrado en un solo feed." accent="#10b981" />
            <CapCard icon="✈️" tag="Rastreo" title="Rastreo de Activos Globales" desc="Seguimiento ADS-B de aeronaves militares y civiles, AIS de buques, movimientos logísticos y posicionamiento de tropas en tiempo real." accent="#f59e0b" />
            <CapCard icon="📊" tag="Mercados" title="Inteligencia de Mercado" desc="Indicadores macro, precios de commodities, flujos de capital, alertas de volatilidad y correlación con eventos geopolíticos." accent="#10b981" />
            <CapCard icon="🗂" tag="Base de Conocimiento" title="Bóveda de Inteligencia" desc="Todo el conocimiento acumulado, documentos del Drive, análisis previos y evidencia indexada con búsqueda vectorial semántica." accent="#a5b4fc" />
          </div>
        </div>
      </section>

      {/* ── TIMELINE DEMO ── */}
      <section id="ia" style={{ padding: '120px 48px', borderTop: '1px solid var(--border)', position: 'relative', zIndex: 2 }}>
        <div style={{ maxWidth: 1240, margin: '0 auto', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 72, alignItems: 'center' }}>
          <div className="reveal">
            <div className="section-tag">IA + Evidencia</div>
            <h2 style={{ fontSize: 'clamp(30px,4vw,50px)', fontWeight: 800, letterSpacing: '-0.025em', lineHeight: 1.1, marginBottom: 20 }}>
              Cualquier evento.<br /><span className="gradient-text">Toda la historia.</span>
            </h2>
            <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: 'var(--muted)', lineHeight: 1.82, marginBottom: 32 }}>
              Escribe el nombre de un conflicto, crisis o evento. NEXO recupera fuentes primarias, las ordena cronológicamente y genera una línea de tiempo con cada pieza de evidencia vinculada.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {['Fuentes primarias verificadas', 'Correlación con eventos simultáneos', 'Contexto histórico automático', 'Exportable a PDF / JSON'].map((f, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, fontFamily: "'Space Mono', monospace", fontSize: 11, color: 'var(--muted)' }}>
                  <span style={{ color: 'var(--cyan)', fontSize: 14 }}>◆</span> {f}
                </div>
              ))}
            </div>
            <Link to="/control" style={{ display: 'inline-block', marginTop: 36, fontFamily: "'Space Mono', monospace", fontSize: 11, padding: '12px 28px', background: 'var(--cyan)', color: 'var(--bg)', textDecoration: 'none', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
              Crear Línea de Tiempo →
            </Link>
          </div>

          <div className="reveal" style={{ background: 'var(--bg2)', border: '1px solid var(--border)', padding: 32 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24, paddingBottom: 16, borderBottom: '1px solid var(--border)' }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--cyan)', animation: 'blink-dot 1.5s infinite' }} />
              <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: 'var(--cyan)', letterSpacing: '0.15em', textTransform: 'uppercase' }}>Timeline · Generado por IA</span>
              <span style={{ marginLeft: 'auto', fontFamily: "'Space Mono', monospace", fontSize: 9, padding: '2px 8px', border: '1px solid var(--green)', color: 'var(--green)' }}>LIVE</span>
            </div>
            <TimelinePreview />
          </div>
        </div>
      </section>

      {/* ── RASTREO ── */}
      <section id="rastreo" style={{ padding: '120px 48px', borderTop: '1px solid var(--border)', position: 'relative', zIndex: 2 }}>
        <div style={{ maxWidth: 1240, margin: '0 auto' }}>
          <div className="reveal" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 72, alignItems: 'center' }}>
            <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', padding: 32 }}>
              <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: 'var(--dim)', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 20, paddingBottom: 14, borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between' }}>
                <span>Activos Globales en Tiempo Real</span>
                <span style={{ color: '#ef4444', animation: 'blink-dot 1.5s infinite' }}>● LIVE</span>
              </div>
              {[
                { icon: '✈️', type: 'Aeronave Militar', id: 'RQ-4B USAF', pos: 'Mar Negro — 34,000 ft', col: '#ef4444' },
                { icon: '🚢', type: 'Portaaviones', id: 'USS Gerald R. Ford', pos: 'Mediterráneo Oriental', col: '#f59e0b' },
                { icon: '🛰', type: 'Satélite ISR', id: 'KH-13 USA-290', pos: 'Órbita baja — paso 14min', col: '#a5b4fc' },
                { icon: '✈️', type: 'Avión de Carga', id: 'C-17A 97-0046', pos: 'Ramstein AB → Rzeszów', col: '#f59e0b' },
                { icon: '🚢', type: 'Submarino Nuclear', id: 'SSBN-740 Maine', pos: 'Atlántico Norte [clasificado]', col: '#ef4444' },
              ].map((a, i) => (
                <div key={i} style={{ display: 'flex', gap: 14, alignItems: 'center', padding: '10px 0', borderBottom: i < 4 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}>
                  <span style={{ fontSize: 18, flexShrink: 0 }}>{a.icon}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: 'var(--text)', fontWeight: 700 }}>{a.id}</span>
                      <span style={{ width: 5, height: 5, borderRadius: '50%', background: a.col, animation: 'blink-dot 2s infinite', flexShrink: 0 }} />
                    </div>
                    <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: 'var(--dim)', marginTop: 2 }}>{a.type} · {a.pos}</div>
                  </div>
                </div>
              ))}
            </div>
            <div>
              <div className="section-tag">Rastreo Global</div>
              <h2 style={{ fontSize: 'clamp(30px,4vw,50px)', fontWeight: 800, letterSpacing: '-0.025em', lineHeight: 1.1, marginBottom: 20 }}>
                Ve los activos<br /><span className="gradient-text">antes que los medios.</span>
              </h2>
              <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: 'var(--muted)', lineHeight: 1.82, marginBottom: 28 }}>
                ADS-B en tiempo real, AIS marítimo, movimientos de carga militar y logística de conflictos. Cuando algo se mueve en el mundo, NEXO lo detecta primero.
              </p>
              {[
                ['✈️', 'Aeronaves militares y civiles (ADS-B)'],
                ['🚢', 'Flota naval global (AIS)'],
                ['🛰', 'Cobertura satelital ISR'],
                ['📦', 'Logística de conflictos activos'],
                ['🏗', 'Infraestructura crítica'],
              ].map(([icon, label], i) => (
                <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'center', fontFamily: "'Space Mono', monospace", fontSize: 11, color: 'var(--muted)', marginBottom: 10 }}>
                  <span>{icon}</span> {label}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── OMNIGLOBE FEATURE ── */}
      <section id="omniglobe" style={{ padding: '120px 48px', borderTop: '1px solid var(--border)', position: 'relative', zIndex: 2, background: 'linear-gradient(180deg, var(--bg) 0%, rgba(0,20,40,0.4) 50%, var(--bg) 100%)' }}>
        <div style={{ maxWidth: 1240, margin: '0 auto' }}>
          <div className="reveal" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 72, alignItems: 'center' }}>
            <div>
              <div className="section-tag">OmniGlobe · 3D en Vivo</div>
              <h2 style={{ fontSize: 'clamp(30px,4vw,50px)', fontWeight: 800, letterSpacing: '-0.025em', lineHeight: 1.1, marginBottom: 20 }}>
                El mundo completo<br /><span className="gradient-text">en tiempo real.</span>
              </h2>
              <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: 'var(--muted)', lineHeight: 1.82, marginBottom: 28 }}>
                OmniGlobe integra 5 capas de inteligencia en un globo 3D interactivo: buques (AIS), aeronaves militares (ADS-B), eventos geopolíticos con severidad ciudad, arcos de flujo logístico e infraestructura crítica global.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 32 }}>
                {[
                  ['⛵', 'Vessels', '15 buques activos — militares, cargueros, tankers'],
                  ['✈', 'Aircraft', '8 aeronaves ISR/SIGINT — RQ-4B, RC-135W, P-8A'],
                  ['⚠', 'Events', 'Zonas de impacto con radio ciudad, no país'],
                  ['↗', 'Flows', 'Arcos animados — rutas logísticas y militares'],
                  ['⚡', 'CritInfra', 'Plantas nucleares, represas, gasoductos estratégicos'],
                ].map(([icon, label, desc]) => (
                  <div key={label} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', fontFamily: "'Space Mono', monospace", fontSize: 11 }}>
                    <span style={{ color: 'var(--cyan)', minWidth: 18 }}>{icon}</span>
                    <span style={{ color: 'var(--text)', fontWeight: 700, minWidth: 80 }}>{label}</span>
                    <span style={{ color: 'var(--dim)' }}>{desc}</span>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <a href="/omniglobe" style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, padding: '12px 28px', background: 'var(--cyan)', color: 'var(--bg)', textDecoration: 'none', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                  Abrir OmniGlobe →
                </a>
                <a href="/flowmap" style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, padding: '12px 28px', border: '1px solid var(--border-hi)', color: 'var(--muted)', textDecoration: 'none', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                  Ver Arquitectura
                </a>
              </div>
            </div>

            {/* Globe preview card */}
            <a href="/omniglobe" style={{ textDecoration: 'none', display: 'block' }}>
              <div className="card-hover" style={{ background: 'var(--bg2)', border: '1px solid var(--border)', padding: 0, overflow: 'hidden', cursor: 'pointer', position: 'relative' }}>
                {/* Header */}
                <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10, background: 'rgba(0,0,0,0.4)' }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981', animation: 'blink-dot 1.5s infinite' }} />
                  <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: 'var(--cyan)', letterSpacing: '0.15em' }}>◎ OMNIGLOBE · INTELLIGENCE LAYER · LIVE</span>
                  <span style={{ marginLeft: 'auto', fontFamily: "'Space Mono', monospace", fontSize: 9, color: '#ef4444', animation: 'blink-dot 1.5s infinite' }}>● LIVE</span>
                </div>
                {/* Stats grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1, background: 'var(--border)', margin: '1px 0' }}>
                  {[
                    { label: 'VESSELS', val: '15', color: '#00e5ff' },
                    { label: 'AIRCRAFT', val: '8', color: '#f59e0b' },
                    { label: 'EVENTS', val: '8', color: '#ef4444' },
                  ].map(s => (
                    <div key={s.label} style={{ background: 'var(--bg2)', padding: '14px 18px', fontFamily: "'Space Mono', monospace" }}>
                      <div style={{ fontSize: 9, color: 'var(--dim)', letterSpacing: '0.1em' }}>{s.label}</div>
                      <div style={{ fontSize: 22, color: s.color, fontWeight: 700, marginTop: 4 }}>{s.val}</div>
                    </div>
                  ))}
                </div>
                {/* Scenario list */}
                <div style={{ padding: '16px 18px', fontFamily: "'Space Mono', monospace" }}>
                  <div style={{ fontSize: 9, color: 'var(--dim)', letterSpacing: '0.1em', marginBottom: 10, textTransform: 'uppercase' }}>Escenarios activos</div>
                  {[
                    { name: 'CIERRE HORMUZ', sev: 'CRITICAL', col: '#ef4444', lat: '26.6°N 56.5°E' },
                    { name: 'EJERCICIOS PLA — TAIWÁN', sev: 'CRITICAL', col: '#ef4444', lat: '24.5°N 120.5°E' },
                    { name: 'GRID STRIKE UCRANIA', sev: 'HIGH', col: '#f97316', lat: '50.4°N 30.5°E' },
                  ].map(s => (
                    <div key={s.name} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <span style={{ width: 6, height: 6, borderRadius: '50%', background: s.col, flexShrink: 0 }} />
                      <span style={{ fontSize: 10, color: 'var(--text)', flex: 1 }}>{s.name}</span>
                      <span style={{ fontSize: 9, color: s.col, letterSpacing: '0.06em' }}>{s.sev}</span>
                      <span style={{ fontSize: 9, color: 'var(--dim)', fontVariantNumeric: 'tabular-nums' }}>{s.lat}</span>
                    </div>
                  ))}
                </div>
                {/* CTA overlay */}
                <div style={{ padding: '12px 18px', textAlign: 'center', borderTop: '1px solid var(--border)', background: 'rgba(0,229,255,0.04)' }}>
                  <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: 'var(--cyan)', letterSpacing: '0.1em' }}>◈ CLICK PARA ABRIR GLOBO INTERACTIVO →</span>
                </div>
              </div>
            </a>
          </div>
        </div>
      </section>

      {/* ── COMUNIDAD ── */}
      <section id="comunidad" style={{ padding: '120px 48px', borderTop: '1px solid var(--border)', position: 'relative', zIndex: 2 }}>
        <div style={{ maxWidth: 1240, margin: '0 auto' }}>
          <div className="reveal" style={{ textAlign: 'center', maxWidth: 640, margin: '0 auto' }}>
            <div className="section-tag" style={{ justifyContent: 'center' }}>Comunidad</div>
            <h2 style={{ fontSize: 'clamp(32px,5vw,64px)', fontWeight: 800, letterSpacing: '-0.03em', lineHeight: 1, marginBottom: 20 }}>
              Inteligencia<br /><span className="gradient-text">colectiva.</span>
            </h2>
            <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: 'var(--muted)', lineHeight: 1.85, marginBottom: 44 }}>
              Únete a analistas, periodistas y ciudadanos que usan NEXO para entender el mundo real. Comparte hallazgos, colabora en investigaciones y accede a la bóveda de inteligencia colectiva.
            </p>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
              <Link to="/control" style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, padding: '14px 36px', background: 'var(--cyan)', color: 'var(--bg)', textDecoration: 'none', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                Acceder al Sistema
              </Link>
              <a href="https://github.com/Reidskar/NEXO_SOBERANO" target="_blank" rel="noreferrer" style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, padding: '14px 36px', border: '1px solid var(--border-hi)', color: 'var(--muted)', textDecoration: 'none', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                GitHub ↗
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer style={{ borderTop: '1px solid var(--border)', padding: '20px 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(7,15,26,0.8)', position: 'relative', zIndex: 2 }}>
        <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: 'var(--dim)' }}>El Anarcocapital · © 2026 Camilo Estefano · Inteligencia Soberana</span>
        <div style={{ display: 'flex', gap: 20 }}>
          {[['#inteligencia', 'Capacidades'], ['#ia', 'IA'], ['#rastreo', 'Rastreo'], ['/omniglobe', 'OmniGlobe'], ['/flowmap', 'FlowMap'], ['/control', 'Warroom']].map(([href, label]) => (
            <a key={href} href={href} style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: 'var(--dim)', textDecoration: 'none', transition: 'color 0.2s' }}
              onMouseEnter={e => e.target.style.color = 'var(--cyan)'}
              onMouseLeave={e => e.target.style.color = 'var(--dim)'}
            >{label}</a>
          ))}
        </div>
      </footer>

      <LiveTicker />
    </div>
  );
}
