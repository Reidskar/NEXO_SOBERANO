import React, { useState, useEffect } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, FileText, Clock, Settings, Zap, ArrowLeft,
  BrainCircuit, Globe, Users, Map, Database, BarChart2, Network,
  Film, Radar, Wifi, Activity, ChevronRight,
} from 'lucide-react';
import AIPanel from '../components/AIPanel';

const mono = "'Space Mono', monospace";

const NAV = [
  { section: 'INTELIGENCIA' },
  { name: 'Command Center',     path: '/control',                icon: LayoutDashboard },
  { name: 'Sesión de Análisis', path: '/control/sesion',         icon: BrainCircuit    },
  { name: 'Memoria Visual',     path: '/control/memoria',        icon: Network         },
  { name: 'Mapa Global',        path: '/control/mapa',           icon: Map             },
  { name: 'OmniGlobe 3D',       path: '/control/omniglobe',      icon: Activity        },
  { name: 'Escenarios',         path: '/control/escenarios',     icon: Globe           },
  { name: 'OSINT Engine',       path: '/control/osint',          icon: Radar           },
  { name: 'Wireless Intel',     path: '/control/wireless',       icon: Wifi            },
  { section: 'EVIDENCIAS' },
  { name: 'Bóveda OSINT',       path: '/control/boveda',         icon: Database        },
  { name: 'Bóveda Drive',       path: '/control/documents',      icon: FileText        },
  { name: 'Timeline Global',    path: '/control/timeline/Global',icon: Clock           },
  { name: 'Mercados',           path: '/control/mercados',       icon: BarChart2       },
  { section: 'OPERACIONES' },
  { name: 'Video Estudio',      path: '/control/video-studio',   icon: Film            },
  { name: 'Terminal Omnicanal', path: '/control/comunidad',      icon: Users           },
  { name: 'Control Sistema',    path: '/control/system',         icon: Settings        },
];

// ── Live system stats en sidebar ──────────────────────────────
function SidebarStats() {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const iv = setInterval(() => setTick(t => t + 1), 3000);
    return () => clearInterval(iv);
  }, []);

  const cpu  = 18 + Math.sin(tick * 0.7) * 8 | 0;
  const mem  = 62 + Math.sin(tick * 0.4) * 5 | 0;
  const ping = 12 + Math.abs(Math.sin(tick * 1.1) * 8) | 0;

  return (
    <div style={{ padding:'10px 14px', borderTop:'1px solid var(--border)', background:'rgba(0,229,255,0.02)' }}>
      <div style={{ fontFamily:mono, fontSize:7, color:'var(--dim)', letterSpacing:'.18em', textTransform:'uppercase', marginBottom:8 }}>
        Sistema
      </div>
      {[
        { label:'CPU',  val:`${cpu}%`,   bar:cpu/100,  color:'#10b981' },
        { label:'RAM',  val:`${mem}%`,   bar:mem/100,  color:'#a5b4fc' },
        { label:'PING', val:`${ping}ms`, bar:ping/100, color:'var(--cyan)' },
      ].map(({ label, val, bar, color }) => (
        <div key={label} style={{ marginBottom:7 }}>
          <div style={{ display:'flex', justifyContent:'space-between', marginBottom:3 }}>
            <span style={{ fontFamily:mono, fontSize:8, color:'var(--dim)' }}>{label}</span>
            <span style={{ fontFamily:mono, fontSize:8, color }}>{val}</span>
          </div>
          <div style={{ height:2, background:'rgba(255,255,255,0.06)', borderRadius:2, overflow:'hidden' }}>
            <div style={{
              height:'100%', width:`${bar * 100}%`, background:color,
              boxShadow:`0 0 6px ${color}`,
              transition:'width 1.2s cubic-bezier(0.23,1,0.32,1)',
            }} />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Transition wrapper para páginas ──────────────────────────
function PageTransition({ children, locationKey }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(false); const t = setTimeout(() => setMounted(true), 30); return () => clearTimeout(t); }, [locationKey]);
  return (
    <div style={{
      opacity: mounted ? 1 : 0,
      transform: mounted ? 'translateY(0)' : 'translateY(12px)',
      filter: mounted ? 'blur(0)' : 'blur(3px)',
      transition: 'opacity 0.45s cubic-bezier(0.16,1,0.3,1), transform 0.45s cubic-bezier(0.16,1,0.3,1), filter 0.45s ease',
      height: '100%',
    }}>
      {children}
    </div>
  );
}

// ── Main Layout ───────────────────────────────────────────────
const MainLayout = () => {
  const location = useLocation();
  const [isAIOpen, setAIOpen] = useState(false);
  const [aiContext, setAIContext] = useState('');
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const iv = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(iv);
  }, []);

  const triggerAI = (ctx) => { setAIContext(ctx); setAIOpen(true); };

  const timeStr = time.toLocaleTimeString('es-CL', { hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false });
  const dateStr = time.toLocaleDateString('es-CL', { weekday:'short', day:'2-digit', month:'short' });

  return (
    <div style={{ display:'flex', height:'100vh', background:'var(--bg)', color:'var(--text)', fontFamily:"'DM Sans',sans-serif", overflow:'hidden' }}>

      {/* ── SIDEBAR ── */}
      <aside style={{
        width: 224, borderRight:'1px solid var(--border)', background:'var(--bg2)',
        display:'flex', flexDirection:'column', justifyContent:'space-between',
        flexShrink:0, overflowY:'auto', position:'relative',
      }}>
        {/* Scanline on sidebar */}
        <div style={{ position:'absolute', inset:0, pointerEvents:'none', overflow:'hidden', zIndex:0 }}>
          <div style={{ position:'absolute', left:0, right:0, height:1, background:'linear-gradient(90deg,transparent,rgba(0,229,255,0.15),transparent)', animation:'scan-h 6s linear infinite', animationDelay:'-3s' }} />
        </div>

        <div style={{ position:'relative', zIndex:1 }}>
          {/* Brand + clock */}
          <div style={{ height:64, display:'flex', flexDirection:'column', justifyContent:'center', padding:'0 18px', borderBottom:'1px solid var(--border)' }}>
            <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:2 }}>
              <div style={{ position:'relative', flexShrink:0 }}>
                <span style={{ width:7, height:7, borderRadius:'50%', background:'var(--cyan)', boxShadow:'0 0 10px var(--cyan)', display:'block', animation:'blink-dot 1.8s infinite' }} />
                <span style={{ position:'absolute', inset:-2, borderRadius:'50%', border:'1px solid var(--cyan)', opacity:.3, animation:'pulse-ring 2s ease-out infinite' }} />
              </div>
              <span style={{ fontFamily:mono, fontSize:10, fontWeight:700, letterSpacing:'.14em', textTransform:'uppercase', color:'var(--text)' }}>NEXO SOBERANO</span>
            </div>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', paddingLeft:15 }}>
              <span style={{ fontFamily:mono, fontSize:7, color:'var(--cyan)', letterSpacing:'.1em' }}>WARROOM v3.0</span>
              <span style={{ fontFamily:mono, fontSize:7, color:'var(--dim)', letterSpacing:'.05em' }}>{timeStr}</span>
            </div>
          </div>

          {/* Date strip */}
          <div style={{ padding:'6px 18px', borderBottom:'1px solid var(--border)', background:'rgba(0,229,255,0.02)' }}>
            <span style={{ fontFamily:mono, fontSize:8, color:'var(--dim)', letterSpacing:'.1em', textTransform:'uppercase' }}>{dateStr} UTC-3</span>
          </div>

          {/* Navigation */}
          <nav style={{ padding:'10px 8px', display:'flex', flexDirection:'column', gap:1 }}>
            {NAV.map((item, idx) => {
              if (item.section) return (
                <div key={idx} style={{ fontFamily:mono, fontSize:7, color:'var(--dim)', letterSpacing:'.2em', textTransform:'uppercase', padding:'10px 10px 4px', marginTop:idx>0?6:0 }}>
                  {item.section}
                </div>
              );
              const Icon = item.icon;
              const isActive = location.pathname === item.path || (item.path !== '/control' && location.pathname.startsWith(item.path));
              return (
                <Link key={item.path} to={item.path} style={{
                  display:'flex', alignItems:'center', gap:10, padding:'7px 10px',
                  borderRadius:2, textDecoration:'none', transition:'all 0.15s var(--ease-out)',
                  background: isActive ? 'rgba(0,229,255,0.07)' : 'transparent',
                  borderLeft: isActive ? '2px solid var(--cyan)' : '2px solid transparent',
                  color: isActive ? 'var(--cyan)' : 'var(--muted)',
                  paddingLeft: isActive ? 12 : 10,
                }}
                  onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = 'var(--text)'; } }}
                  onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--muted)'; } }}
                >
                  <Icon size={13} style={{ flexShrink:0 }} />
                  <span style={{ fontFamily:mono, fontSize:9, letterSpacing:'.04em', flex:1 }}>{item.name}</span>
                  {isActive && <ChevronRight size={10} style={{ opacity:0.5 }} />}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Bottom section */}
        <div style={{ position:'relative', zIndex:1, display:'flex', flexDirection:'column' }}>
          <SidebarStats />
          <div style={{ padding:'10px 8px', display:'flex', flexDirection:'column', gap:5 }}>
            <button onClick={() => triggerAI('Consulta global.')} style={{
              width:'100%', display:'flex', alignItems:'center', gap:10, padding:'9px 12px',
              borderRadius:2, cursor:'pointer',
              background:'rgba(124,58,237,0.08)', color:'var(--indigo)',
              border:'1px solid rgba(124,58,237,0.2)', transition:'all .2s',
              fontFamily:mono, fontSize:9, letterSpacing:'.08em', textTransform:'uppercase',
            }}
              onMouseEnter={e => { e.currentTarget.style.background='rgba(124,58,237,0.18)'; e.currentTarget.style.boxShadow='0 0 16px rgba(124,58,237,0.25)'; }}
              onMouseLeave={e => { e.currentTarget.style.background='rgba(124,58,237,0.08)'; e.currentTarget.style.boxShadow='none'; }}
            >
              <Zap size={13} /><span>AI Copilot</span>
            </button>
            <Link to="/" style={{
              display:'flex', alignItems:'center', gap:10, padding:'7px 12px',
              borderRadius:2, textDecoration:'none', color:'var(--dim)', border:'1px solid transparent',
              transition:'all .15s', fontFamily:mono, fontSize:9,
            }}
              onMouseEnter={e => { e.currentTarget.style.color='var(--muted)'; e.currentTarget.style.background='rgba(255,255,255,0.04)'; }}
              onMouseLeave={e => { e.currentTarget.style.color='var(--dim)'; e.currentTarget.style.background='transparent'; }}
            >
              <ArrowLeft size={13} /><span>Volver al Inicio</span>
            </Link>
          </div>
        </div>
      </aside>

      {/* ── MAIN CONTENT ── */}
      <main style={{ flex:1, overflowY:'auto', background:'var(--bg)', position:'relative' }}>
        <PageTransition locationKey={location.pathname}>
          <Outlet context={{ openAI: triggerAI }} />
        </PageTransition>
      </main>

      {/* ── AI PANEL ── */}
      <AIPanel isOpen={isAIOpen} onClose={() => setAIOpen(false)} contextData={aiContext} />
    </div>
  );
};

export default MainLayout;
