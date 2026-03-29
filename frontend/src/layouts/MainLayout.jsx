import React, { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, FileText, Clock, Settings, Zap, ArrowLeft, BrainCircuit, Globe, Users, Map, Database, BarChart2, Network, Film } from 'lucide-react';
import AIPanel from '../components/AIPanel';

const NAV = [
  { section: 'INTELIGENCIA' },
  { name:'Command Center',    path:'/control',             icon:LayoutDashboard },
  { name:'Sesión de Análisis',path:'/control/sesion',      icon:BrainCircuit    },
  { name:'Memoria Visual',    path:'/control/memoria',     icon:Network         },
  { name:'Mapa Global',       path:'/control/mapa',        icon:Map             },
  { name:'Escenarios',        path:'/control/escenarios',  icon:Globe           },
  { section: 'EVIDENCIAS' },
  { name:'Bóveda OSINT',      path:'/control/boveda',      icon:Database        },
  { name:'Bóveda Drive',      path:'/control/documents',   icon:FileText        },
  { name:'Timeline Global',   path:'/control/timeline/Global', icon:Clock       },
  { name:'Mercados',          path:'/control/mercados',    icon:BarChart2       },
  { section: 'OPERACIONES' },
  { name:'Video Estudio',     path:'/control/video-studio',icon:Film            },
  { name:'Terminal Omnicanal',path:'/control/comunidad',   icon:Users           },
  { name:'Control Sistema',   path:'/control/system',      icon:Settings        },
];

const MainLayout = () => {
  const location = useLocation();
  const [isAIOpen, setAIOpen] = useState(false);
  const [aiContext, setAIContext] = useState('');

  const triggerAI = (ctx) => { setAIContext(ctx); setAIOpen(true); };

  return (
    <div style={{ display:'flex', height:'100vh', background:'var(--bg)', color:'var(--text)', fontFamily:"'DM Sans', sans-serif", overflow:'hidden' }}>

      {/* ── Sidebar ── */}
      <aside style={{ width:220, borderRight:'1px solid var(--border)', background:'var(--bg2)', display:'flex', flexDirection:'column', justifyContent:'space-between', flexShrink:0, overflowY:'auto' }}>
        <div>
          {/* Brand */}
          <div style={{ height:60, display:'flex', flexDirection:'column', justifyContent:'center', padding:'0 20px', borderBottom:'1px solid var(--border)' }}>
            <div style={{ display:'flex', alignItems:'center', gap:8 }}>
              <span style={{ width:7, height:7, borderRadius:'50%', background:'var(--green)', boxShadow:'0 0 8px var(--green)', animation:'blink-dot 1.8s infinite', flexShrink:0 }}/>
              <span style={{ fontFamily:"'Space Mono', monospace", fontSize:11, fontWeight:700, letterSpacing:'.12em', textTransform:'uppercase', color:'var(--text)' }}>NEXO SOBERANO</span>
            </div>
            <span style={{ fontFamily:"'Space Mono', monospace", fontSize:8, color:'var(--cyan)', letterSpacing:'.1em', marginTop:3, marginLeft:15 }}>WARROOM v3.0</span>
          </div>

          {/* Navigation */}
          <nav style={{ padding:'12px 10px', display:'flex', flexDirection:'column', gap:2 }}>
            {NAV.map((item, idx) => {
              if (item.section) return (
                <div key={idx} style={{ fontFamily:"'Space Mono', monospace", fontSize:7, color:'var(--dim)', letterSpacing:'.18em', textTransform:'uppercase', padding:'12px 10px 4px' }}>{item.section}</div>
              );
              const Icon = item.icon;
              const isActive = location.pathname === item.path || (item.path !== '/control' && location.pathname.startsWith(item.path));
              return (
                <Link key={item.path} to={item.path} style={{ display:'flex', alignItems:'center', gap:10, padding:'8px 12px', borderRadius:3, textDecoration:'none', transition:'all 0.15s', background: isActive?'rgba(74,222,128,0.08)':'transparent', border: isActive?'1px solid rgba(74,222,128,0.15)':'1px solid transparent', color: isActive?'var(--green)':'var(--muted)' }}
                  onMouseEnter={e=>{ if(!isActive) e.currentTarget.style.background='rgba(255,255,255,0.04)'; }}
                  onMouseLeave={e=>{ if(!isActive) e.currentTarget.style.background='transparent'; }}>
                  <Icon size={14}/>
                  <span style={{ fontFamily:"'Space Mono', monospace", fontSize:10, letterSpacing:'.03em' }}>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Bottom */}
        <div style={{ padding:'10px', borderTop:'1px solid var(--border)', display:'flex', flexDirection:'column', gap:6 }}>
          <button onClick={()=>triggerAI('Consulta global.')} style={{ width:'100%', display:'flex', alignItems:'center', gap:10, padding:'8px 12px', borderRadius:3, cursor:'pointer', background:'rgba(124,58,237,0.08)', color:'var(--indigo)', border:'1px solid rgba(124,58,237,0.2)', transition:'all .15s' }}
            onMouseEnter={e=>e.currentTarget.style.background='rgba(124,58,237,0.16)'}
            onMouseLeave={e=>e.currentTarget.style.background='rgba(124,58,237,0.08)'}>
            <Zap size={14}/>
            <span style={{ fontFamily:"'Space Mono', monospace", fontSize:10, letterSpacing:'.06em', textTransform:'uppercase' }}>AI Copilot</span>
          </button>
          <Link to="/" style={{ display:'flex', alignItems:'center', gap:10, padding:'8px 12px', borderRadius:3, textDecoration:'none', color:'var(--dim)', border:'1px solid transparent', transition:'all .15s' }}
            onMouseEnter={e=>{ e.currentTarget.style.color='var(--muted)'; e.currentTarget.style.background='rgba(255,255,255,0.04)'; }}
            onMouseLeave={e=>{ e.currentTarget.style.color='var(--dim)'; e.currentTarget.style.background='transparent'; }}>
            <ArrowLeft size={14}/>
            <span style={{ fontFamily:"'Space Mono', monospace", fontSize:10, letterSpacing:'.03em' }}>Volver al Inicio</span>
          </Link>
        </div>
      </aside>

      {/* ── Main Content ── */}
      <main style={{ flex:1, overflowY:'auto', background:'var(--bg)', position:'relative' }}>
        <Outlet context={{ openAI: triggerAI }} />
      </main>

      {/* ── AI Panel ── */}
      <AIPanel isOpen={isAIOpen} onClose={()=>setAIOpen(false)} contextData={aiContext}/>
    </div>
  );
};

export default MainLayout;
