import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import Globe3D from '../components/Globe3D';

// ─── Neural Canvas Background ─────────────────────────────────────────────────
function NeuralCanvas() {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let W, H, pts = [], animId;
    const resize = () => {
      W = canvas.width = window.innerWidth;
      H = canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);
    class P {
      constructor() {
        this.x = Math.random() * W;
        this.y = Math.random() * H;
        this.r = Math.random() * 2 + 0.8;
        this.vx = (Math.random() - 0.5) * 0.5;
        this.vy = (Math.random() - 0.5) * 0.5;
      }
      move() {
        this.x += this.vx; this.y += this.vy;
        if (this.x < 0 || this.x > W) this.vx *= -1;
        if (this.y < 0 || this.y > H) this.vy *= -1;
      }
    }
    for (let i = 0; i < 90; i++) pts.push(new P());
    const draw = () => {
      ctx.clearRect(0, 0, W, H);
      pts.forEach(p => {
        p.move();
        ctx.fillStyle = 'rgba(0,229,255,0.65)';
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill();
      });
      for (let a = 0; a < pts.length; a++) {
        for (let b = a + 1; b < pts.length; b++) {
          const dx = pts[a].x - pts[b].x, dy = pts[a].y - pts[b].y;
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < 140) {
            ctx.strokeStyle = `rgba(0,229,255,${(1 - d / 140) * 0.45})`;
            ctx.lineWidth = 0.7;
            ctx.beginPath(); ctx.moveTo(pts[a].x, pts[a].y); ctx.lineTo(pts[b].x, pts[b].y); ctx.stroke();
          }
        }
      }
      animId = requestAnimationFrame(draw);
    };
    draw();
    return () => { window.removeEventListener('resize', resize); cancelAnimationFrame(animId); };
  }, []);
  return <canvas ref={canvasRef} style={{ position: 'absolute', inset: 0, opacity: 0.45, zIndex: 1 }} />;
}

// ─── Status Dot ───────────────────────────────────────────────────────────────
function StatusDot({ color = '#10b981', pulse = true }) {
  return (
    <span style={{
      display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
      background: color, boxShadow: `0 0 10px ${color}`,
      animation: pulse ? 'blink-dot 1.8s ease-in-out infinite' : 'none'
    }} />
  );
}

// ─── Feature Card ─────────────────────────────────────────────────────────────
function FeatureCard({ icon, title, desc, num }) {
  return (
    <div className="card-hover" style={{
      background: 'var(--bg2)', border: '1px solid var(--border)',
      padding: '36px 28px', position: 'relative', overflow: 'hidden'
    }}>
      <span style={{
        position: 'absolute', top: 16, right: 16,
        fontFamily: "'Space Mono', monospace", fontSize: 10,
        color: 'rgba(0,229,255,0.25)', letterSpacing: '0.15em'
      }}>{num}</span>
      <span style={{ fontSize: 28, display: 'block', marginBottom: 18, color: 'var(--dim)' }}>{icon}</span>
      <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 10, letterSpacing: '-0.01em', color: 'var(--text)' }}>{title}</h3>
      <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 11.5, color: 'var(--muted)', lineHeight: 1.72 }}>{desc}</p>
    </div>
  );
}

// ─── Stat ─────────────────────────────────────────────────────────────────────
function Stat({ value, label }) {
  return (
    <div style={{ borderLeft: '2px solid var(--cyan)', paddingLeft: 24 }}>
      <div style={{ fontSize: 38, fontWeight: 800, color: 'var(--cyan)', letterSpacing: '-0.04em', lineHeight: 1 }}>{value}</div>
      <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>{label}</div>
    </div>
  );
}

// ─── Live Activity Feed ───────────────────────────────────────────────────────
const EVENTS = [
  { col: '#10b981', msg: 'Backend heartbeat OK' },
  { col: '#00e5ff', msg: 'Celery task procesado' },
  { col: '#a5b4fc', msg: 'Embedding almacenado en Qdrant' },
  { col: '#f59e0b', msg: 'Agente móvil ping recibido' },
  { col: '#10b981', msg: 'Webhook ingest procesado' },
  { col: '#00e5ff', msg: 'Discord supervisor activo' },
  { col: '#10b981', msg: 'Supabase RLS validado' },
  { col: '#a5b4fc', msg: 'RAG query ejecutada' },
  { col: '#00e5ff', msg: 'n8n workflow completado' },
  { col: '#10b981', msg: 'Health check OK — 12ms' },
];

function ActivityFeed() {
  const [items, setItems] = useState([]);
  const idxRef = useRef(0);
  useEffect(() => {
    const add = () => {
      const ev = EVENTS[idxRef.current++ % EVENTS.length];
      const now = new Date();
      const t = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
      setItems(prev => [{ t, col: ev.col, msg: ev.msg, id: Date.now() }, ...prev].slice(0, 10));
    };
    add();
    const iv = setInterval(add, 3200);
    return () => clearInterval(iv);
  }, []);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {items.map(item => (
        <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: 10, animation: 'fade-up 0.3s ease both' }}>
          <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: 'var(--dim)', minWidth: 60 }}>{item.t}</span>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: item.col, flexShrink: 0 }} />
          <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: 'var(--muted)' }}>{item.msg}</span>
        </div>
      ))}
    </div>
  );
}

// ─── Main Landing Component ───────────────────────────────────────────────────
export default function Landing() {
  const [scrolled, setScrolled] = useState(false);
  const [backendStatus, setBackendStatus] = useState('loading');

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 80);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch('/api/health/', { signal: AbortSignal.timeout(4000) });
        setBackendStatus(r.ok ? 'online' : 'degraded');
      } catch {
        setBackendStatus('offline');
      }
    };
    check();
    const iv = setInterval(check, 15000);
    return () => clearInterval(iv);
  }, []);

  // Scroll reveal
  useEffect(() => {
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('on'); });
    }, { threshold: 0.1 });
    document.querySelectorAll('.reveal').forEach(el => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  const statusColor = backendStatus === 'online' ? '#10b981' : backendStatus === 'degraded' ? '#f59e0b' : '#ef4444';
  const statusLabel = backendStatus === 'online' ? 'Sistema Operacional' : backendStatus === 'degraded' ? 'Degradado' : 'Backend Offline';

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh', position: 'relative', zIndex: 2 }}>

      {/* ── PROGRESS BAR ── */}
      <div id="pbar" style={{
        position: 'fixed', top: 0, left: 0, height: 2,
        background: 'linear-gradient(90deg,var(--cyan),var(--indigo),var(--purple))',
        zIndex: 99999, width: '0%', transition: 'width 0.08s linear'
      }} />

      {/* ── NAV ── */}
      <nav style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1000,
        padding: scrolled ? '14px 48px' : '20px 48px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        borderBottom: '1px solid var(--border)',
        background: scrolled ? 'rgba(3,7,18,0.97)' : 'rgba(3,7,18,0.88)',
        backdropFilter: 'blur(24px)',
        boxShadow: scrolled ? '0 8px 40px -12px var(--cyan-glow)' : 'none',
        transition: 'all 0.3s'
      }}>
        <a href="#hero" style={{
          fontFamily: "'Space Mono', monospace", fontSize: 13, fontWeight: 700,
          color: 'var(--cyan)', letterSpacing: '0.18em', textTransform: 'uppercase',
          textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 10
        }}>
          <StatusDot />
          EL ANARCOCAPITAL
        </a>
        <div style={{ display: 'flex', gap: 32, alignItems: 'center' }}>
          {['Sistema', 'Capacidades', 'Arquitectura', 'Estado'].map(item => (
            <a key={item} href={`#${item.toLowerCase()}`} style={{
              fontFamily: "'Space Mono', monospace", fontSize: 11,
              color: 'var(--dim)', textDecoration: 'none', letterSpacing: '0.12em',
              textTransform: 'uppercase', transition: 'color 0.2s'
            }}
              onMouseEnter={e => e.target.style.color = 'var(--cyan)'}
              onMouseLeave={e => e.target.style.color = 'var(--dim)'}
            >{item}</a>
          ))}
          <Link to="/control" style={{
            fontFamily: "'Space Mono', monospace", fontSize: 11,
            padding: '9px 22px', border: '1px solid var(--border-hi)',
            color: 'var(--cyan)', textDecoration: 'none', letterSpacing: '0.1em',
            textTransform: 'uppercase', transition: 'all 0.25s',
            background: 'transparent'
          }}
            onMouseEnter={e => { e.target.style.background = 'var(--cyan)'; e.target.style.color = 'var(--bg)'; }}
            onMouseLeave={e => { e.target.style.background = 'transparent'; e.target.style.color = 'var(--cyan)'; }}
          >
            Warroom →
          </Link>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section id="hero" style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center',
        position: 'relative', padding: '130px 48px 100px', overflow: 'hidden'
      }}>
        <NeuralCanvas />

        {/* Globe 3D flotante */}
        <div style={{
          position: 'absolute', right: '5vw', top: '50%', transform: 'translateY(-50%)',
          zIndex: 2, opacity: 0.85, display: 'flex', alignItems: 'center', justifyContent: 'center',
          pointerEvents: 'none',
        }}>
          <Globe3D size={420} color="#00e5ff" speed={0.004} />
        </div>

        <div style={{ maxWidth: 860, position: 'relative', zIndex: 3 }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 9,
            fontFamily: "'Space Mono', monospace", fontSize: 11,
            color: 'var(--cyan)', letterSpacing: '0.18em', textTransform: 'uppercase',
            border: '1px solid var(--border-hi)', padding: '7px 18px',
            marginBottom: 40, background: 'rgba(0,229,255,0.05)',
            animation: 'fade-up 0.6s ease 0.1s both'
          }}>
            <StatusDot color={statusColor} />
            {statusLabel} — v3.0.0
          </div>

          <h1 style={{
            fontSize: 'clamp(52px,9vw,104px)', fontWeight: 800,
            lineHeight: 0.93, letterSpacing: '-0.04em', marginBottom: 28,
            animation: 'fade-up 0.7s ease 0.3s both'
          }}>
            <span className="gradient-text">NEXO</span><br />
            <span style={{ color: 'var(--text)' }}>SOBERANO</span>
          </h1>

          <p style={{
            fontFamily: "'Space Mono', monospace", fontSize: 14,
            lineHeight: 1.82, color: 'var(--muted)', maxWidth: 560,
            marginBottom: 52, animation: 'fade-up 0.7s ease 0.5s both'
          }}>
            Infraestructura de inteligencia híbrida soberana. RAG vectorial,
            agentes autónomos, orquestación n8n y memoria persistente.
            Tu sistema. Tu control. Sin intermediarios.
          </p>

          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', animation: 'fade-up 0.7s ease 0.7s both' }}>
            <Link to="/control" style={{
              fontFamily: "'Space Mono', monospace", fontSize: 12,
              padding: '15px 38px', background: 'var(--cyan)', color: 'var(--bg)',
              letterSpacing: '0.09em', textTransform: 'uppercase', fontWeight: 700,
              textDecoration: 'none', transition: 'all 0.3s'
            }}
              onMouseEnter={e => { e.target.style.boxShadow = '0 0 50px rgba(0,229,255,0.45)'; e.target.style.transform = 'translateY(-2px)'; }}
              onMouseLeave={e => { e.target.style.boxShadow = 'none'; e.target.style.transform = 'none'; }}
            >
              Abrir Warroom
            </Link>
            <a href="#sistema" style={{
              fontFamily: "'Space Mono', monospace", fontSize: 12,
              padding: '15px 38px', border: '1px solid var(--border-hi)',
              color: 'var(--muted)', letterSpacing: '0.09em', textTransform: 'uppercase',
              textDecoration: 'none', transition: 'all 0.25s'
            }}
              onMouseEnter={e => { e.target.style.borderColor = 'var(--cyan)'; e.target.style.color = 'var(--cyan)'; }}
              onMouseLeave={e => { e.target.style.borderColor = 'var(--border-hi)'; e.target.style.color = 'var(--muted)'; }}
            >
              Ver Sistema
            </a>
            <a href="https://github.com/Reidskar/NEXO_SOBERANO" target="_blank" rel="noreferrer" style={{
              fontFamily: "'Space Mono', monospace", fontSize: 12,
              padding: '15px 38px', border: '1px solid var(--border)',
              color: 'var(--dim)', letterSpacing: '0.09em', textTransform: 'uppercase',
              textDecoration: 'none', transition: 'all 0.25s'
            }}
              onMouseEnter={e => { e.target.style.borderColor = 'var(--indigo)'; e.target.style.color = 'var(--indigo)'; }}
              onMouseLeave={e => { e.target.style.borderColor = 'var(--border)'; e.target.style.color = 'var(--dim)'; }}
            >
              GitHub ↗
            </a>
          </div>
        </div>

        {/* Status Bar */}
        <div style={{
          position: 'absolute', bottom: 0, left: 0, right: 0, zIndex: 4,
          borderTop: '1px solid var(--border)',
          background: 'rgba(7,15,26,0.96)', backdropFilter: 'blur(16px)',
          display: 'flex', overflow: 'hidden'
        }}>
          {[
            { dot: '#10b981', label: 'Backend', val: 'FastAPI · NEXO_CORE' },
            { dot: '#00e5ff', label: 'Agentes IA', val: 'Discord + Web Supervisor' },
            { dot: '#a5b4fc', label: 'RAG Engine', val: 'Qdrant + ChromaDB' },
            { dot: '#f59e0b', label: 'Orquestación', val: 'n8n + Make' },
          ].map((s, i) => (
            <div key={i} style={{
              flex: 1, padding: '16px 22px', borderRight: i < 3 ? '1px solid var(--border)' : 'none',
              display: 'flex', alignItems: 'center', gap: 12
            }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: s.dot, boxShadow: `0 0 8px ${s.dot}`, animation: 'blink-dot 2s infinite', flexShrink: 0 }} />
              <div>
                <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: 'var(--dim)', letterSpacing: '0.09em', textTransform: 'uppercase' }}>{s.label}</div>
                <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>{s.val}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── SISTEMA / FEATURES ── */}
      <section id="sistema" style={{ position: 'relative', zIndex: 2, padding: '120px 48px', borderTop: '1px solid var(--border)' }}>
        <div style={{ maxWidth: 1240, margin: '0 auto' }}>
          <div className="reveal" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 80, alignItems: 'end', marginBottom: 64 }}>
            <div>
              <div className="section-tag">Sistema</div>
              <h2 style={{ fontSize: 'clamp(32px,4.5vw,54px)', fontWeight: 800, letterSpacing: '-0.025em', lineHeight: 1.08, marginBottom: 18 }}>
                Infraestructura<br /><span className="gradient-text">Soberana</span>
              </h2>
            </div>
            <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 13, color: 'var(--muted)', lineHeight: 1.78 }}>
              Un backend unificado construido sobre FastAPI, con agentes autónomos, memoria vectorial y orquestación de flujos. Diseñado para operar 24/7 sin intervención manual.
            </p>
          </div>

          <div className="reveal" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1, background: 'var(--border)', border: '1px solid var(--border)' }}>
            <FeatureCard icon="🧠" num="01" title="RAG Vectorial" desc="Memoria persistente con ChromaDB y Qdrant. Consultas semánticas sobre tu base de conocimiento." />
            <FeatureCard icon="🤖" num="02" title="Agentes Autónomos" desc="Supervisores de Discord y Web IA que operan en segundo plano, detectan anomalías y actúan." />
            <FeatureCard icon="⚡" num="03" title="Orquestación n8n" desc="Flujos de automatización complejos con n8n y Make. Webhooks, triggers y pipelines de datos." />
            <FeatureCard icon="🎙️" num="04" title="Pipeline de Voz" desc="Integración con ElevenLabs para síntesis de voz y procesamiento de audio en tiempo real." />
            <FeatureCard icon="📡" num="05" title="Discord Integration" desc="Bot de Discord con comandos slash, gestión de canales de voz y moderación automática." />
            <FeatureCard icon="🔒" num="06" title="Seguridad Soberana" desc="Rate limiting, API key protection, CORS configurado y headers de seguridad en todas las rutas." />
          </div>
        </div>
      </section>

      {/* ── ARQUITECTURA / STATS ── */}
      <section id="arquitectura" style={{ position: 'relative', zIndex: 2, padding: '120px 48px', borderTop: '1px solid var(--border)' }}>
        <div style={{ maxWidth: 1240, margin: '0 auto' }}>
          <div className="reveal section-tag">Arquitectura</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 72, alignItems: 'center', marginTop: 16 }}>
            <div>
              <h2 className="reveal" style={{ fontSize: 'clamp(32px,4.5vw,54px)', fontWeight: 800, letterSpacing: '-0.025em', lineHeight: 1.08, marginBottom: 40 }}>
                Stack Técnico<br /><span className="gradient-text">de Producción</span>
              </h2>
              <div className="reveal" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                <Stat value="FastAPI" label="Backend unificado NEXO_CORE" />
                <Stat value="React" label="Frontend Vite + TailwindCSS" />
                <Stat value="Celery" label="Worker asíncrono de tareas" />
                <Stat value="Docker" label="Contenedores de producción" />
              </div>
            </div>
            <div className="reveal" style={{
              background: 'var(--bg2)', border: '1px solid var(--border)',
              padding: '28px', fontFamily: "'Space Mono', monospace"
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20, paddingBottom: 16, borderBottom: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', gap: 6 }}>
                  {['#ef4444', '#f59e0b', '#10b981'].map((c, i) => (
                    <div key={i} style={{ width: 10, height: 10, borderRadius: '50%', background: c }} />
                  ))}
                </div>
                <span style={{ fontSize: 11, color: 'var(--cyan)', letterSpacing: '0.15em', marginLeft: 8 }}>NEXO_CORE — stack</span>
              </div>
              {[
                { k: 'backend', v: 'FastAPI + Uvicorn', c: '#00e5ff' },
                { k: 'database', v: 'PostgreSQL + Redis', c: '#a5b4fc' },
                { k: 'vector_db', v: 'Qdrant + ChromaDB', c: '#10b981' },
                { k: 'ai_models', v: 'GPT-4 + Gemini + Claude', c: '#f59e0b' },
                { k: 'workers', v: 'Celery + Beat', c: '#a5b4fc' },
                { k: 'deploy', v: 'Railway + Vercel + CF', c: '#00e5ff' },
                { k: 'mobile', v: 'React Native / Expo', c: '#10b981' },
                { k: 'automation', v: 'n8n + Make + Zapier', c: '#f59e0b' },
              ].map((row, i) => (
                <div key={i} style={{ display: 'flex', gap: 16, marginBottom: 10, fontSize: 12 }}>
                  <span style={{ color: 'var(--dim)', minWidth: 100 }}>{row.k}:</span>
                  <span style={{ color: row.c }}>{row.v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── ESTADO EN VIVO ── */}
      <section id="estado" style={{ position: 'relative', zIndex: 2, padding: '120px 48px', borderTop: '1px solid var(--border)' }}>
        <div style={{ maxWidth: 1240, margin: '0 auto' }}>
          <div className="reveal section-tag">Estado en Vivo</div>
          <h2 className="reveal" style={{ fontSize: 'clamp(32px,4.5vw,54px)', fontWeight: 800, letterSpacing: '-0.025em', lineHeight: 1.08, marginBottom: 48 }}>
            Sistema<br /><span className="gradient-text">Activo 24/7</span>
          </h2>

          <div className="reveal" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 28 }}>
            {/* Activity Feed */}
            <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', padding: 28 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20, paddingBottom: 14, borderBottom: '1px solid var(--border)' }}>
                <StatusDot />
                <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: 'var(--cyan)', letterSpacing: '0.15em', textTransform: 'uppercase' }}>Activity Feed</span>
                <span style={{ marginLeft: 'auto', fontFamily: "'Space Mono', monospace", fontSize: 10, padding: '2px 8px', border: '1px solid var(--green)', color: 'var(--green)' }}>LIVE</span>
              </div>
              <ActivityFeed />
            </div>

            {/* System Metrics */}
            <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', padding: 28 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20, paddingBottom: 14, borderBottom: '1px solid var(--border)' }}>
                <StatusDot color="#a5b4fc" />
                <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: 'var(--cyan)', letterSpacing: '0.15em', textTransform: 'uppercase' }}>Módulos del Sistema</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, background: 'var(--border)' }}>
                {[
                  { label: 'NEXO_CORE', status: 'ok', val: 'FastAPI v3' },
                  { label: 'Discord Bot', status: 'ok', val: 'Node.js + PM2' },
                  { label: 'RAG Engine', status: 'ok', val: 'Qdrant Online' },
                  { label: 'AI Router', status: 'ok', val: 'Multi-model' },
                  { label: 'Celery Worker', status: 'ok', val: 'Beat activo' },
                  { label: 'Voice Pipeline', status: 'ok', val: 'ElevenLabs' },
                ].map((m, i) => (
                  <div key={i} style={{ background: 'var(--bg2)', padding: '18px 20px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981', boxShadow: '0 0 6px #10b981' }} />
                      <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: 'var(--muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>{m.label}</span>
                    </div>
                    <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: 'var(--text)' }}>{m.val}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section style={{ position: 'relative', zIndex: 2, padding: '120px 48px', borderTop: '1px solid var(--border)', textAlign: 'center' }}>
        <div style={{ maxWidth: 700, margin: '0 auto' }}>
          <div className="reveal">
            <h2 style={{ fontSize: 'clamp(40px,6vw,72px)', fontWeight: 800, letterSpacing: '-0.03em', lineHeight: 1, marginBottom: 24 }}>
              El sistema<br />está <span className="gradient-text">vivo.</span>
            </h2>
            <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 13, color: 'var(--muted)', lineHeight: 1.78, marginBottom: 48 }}>
              Warroom, API, agentes y toda la infraestructura soberana lista para operar ahora mismo.
            </p>
            <div style={{ display: 'flex', gap: 14, justifyContent: 'center', flexWrap: 'wrap' }}>
              <Link to="/control" style={{
                fontFamily: "'Space Mono', monospace", fontSize: 12,
                padding: '15px 38px', background: 'var(--cyan)', color: 'var(--bg)',
                letterSpacing: '0.09em', textTransform: 'uppercase', fontWeight: 700,
                textDecoration: 'none', transition: 'all 0.3s'
              }}>Abrir Warroom</Link>
              <a href="/api/docs" style={{
                fontFamily: "'Space Mono', monospace", fontSize: 12,
                padding: '15px 38px', border: '1px solid var(--border-hi)',
                color: 'var(--muted)', letterSpacing: '0.09em', textTransform: 'uppercase',
                textDecoration: 'none', transition: 'all 0.25s'
              }}>API Docs</a>
              <a href="https://github.com/Reidskar/NEXO_SOBERANO" target="_blank" rel="noreferrer" style={{
                fontFamily: "'Space Mono', monospace", fontSize: 12,
                padding: '15px 38px', border: '1px solid var(--border)',
                color: 'var(--dim)', letterSpacing: '0.09em', textTransform: 'uppercase',
                textDecoration: 'none', transition: 'all 0.25s'
              }}>GitHub ↗</a>
            </div>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer style={{
        position: 'relative', zIndex: 2,
        borderTop: '1px solid var(--border)',
        padding: '24px 48px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: 'rgba(7,15,26,0.8)'
      }}>
        <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: 'var(--dim)' }}>
          El Anarcocapital v3.0.0 · © 2026 Camilo Estefano
        </span>
        <div style={{ display: 'flex', gap: 24 }}>
          {['elanarcocapital.com', 'GitHub', 'API Docs'].map((item, i) => (
            <a key={i} href={i === 0 ? '#' : i === 1 ? 'https://github.com/Reidskar/NEXO_SOBERANO' : '/api/docs'}
              style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: 'var(--dim)', textDecoration: 'none', transition: 'color 0.2s' }}
              onMouseEnter={e => e.target.style.color = 'var(--cyan)'}
              onMouseLeave={e => e.target.style.color = 'var(--dim)'}
            >{item}</a>
          ))}
        </div>
      </footer>
    </div>
  );
}
