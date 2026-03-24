import React, { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, FileText, Clock, Settings, Zap, ArrowLeft } from 'lucide-react';
import AIPanel from '../components/AIPanel';

const MainLayout = () => {
  const location = useLocation();
  const [isAIOpen, setAIOpen] = useState(false);
  const [aiContext, setAIContext] = useState('');

  const navItems = [
    { name: 'Command Center', path: '/control', icon: LayoutDashboard },
    { name: 'Terminal NLP', path: '/control/system', icon: Settings },
    { name: 'Evidencias', path: '/control/documents', icon: FileText },
    { name: 'Timeline Global', path: '/control/timeline/Global', icon: Clock },
  ];

  const triggerAIContext = (contextString) => {
    setAIContext(contextString);
    setAIOpen(true);
  };

  return (
    <div style={{ display: 'flex', height: '100vh', background: 'var(--bg)', color: 'var(--text)', fontFamily: "'DM Sans', sans-serif" }}>

      {/* Sidebar */}
      <aside style={{
        width: 256, borderRight: '1px solid var(--border)',
        background: 'var(--bg2)', display: 'flex', flexDirection: 'column',
        justifyContent: 'space-between', flexShrink: 0
      }}>
        <div>
          {/* Brand */}
          <div style={{
            height: 72, display: 'flex', flexDirection: 'column', justifyContent: 'center',
            padding: '0 24px', borderBottom: '1px solid var(--border)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{
                width: 8, height: 8, borderRadius: '50%', background: 'var(--green)',
                boxShadow: '0 0 10px var(--green)', animation: 'blink-dot 1.8s infinite', flexShrink: 0
              }} />
              <span style={{
                fontFamily: "'Space Mono', monospace", fontSize: 12, fontWeight: 700,
                letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text)'
              }}>NEXO SOBERANO</span>
            </div>
            <span style={{
              fontFamily: "'Space Mono', monospace", fontSize: 9,
              color: 'var(--cyan)', letterSpacing: '0.12em', marginTop: 4, marginLeft: 18
            }}>WARROOM v3.0.0</span>
          </div>

          {/* Navigation */}
          <nav style={{ padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: 4 }}>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path ||
                (item.path !== '/control' && location.pathname.startsWith(item.path));
              return (
                <Link
                  key={item.name}
                  to={item.path}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '10px 14px', borderRadius: 4, textDecoration: 'none',
                    transition: 'all 0.2s',
                    background: isActive ? 'rgba(0,229,255,0.08)' : 'transparent',
                    border: isActive ? '1px solid rgba(0,229,255,0.2)' : '1px solid transparent',
                    color: isActive ? 'var(--cyan)' : 'var(--muted)',
                  }}
                  onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                  onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
                >
                  <Icon size={16} />
                  <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, letterSpacing: '0.05em' }}>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Bottom actions */}
        <div style={{ padding: '12px', borderTop: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <button
            onClick={() => { setAIContext('Consulta global del sistema.'); setAIOpen(!isAIOpen); }}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', gap: 12,
              padding: '10px 14px', borderRadius: 4, cursor: 'pointer',
              background: 'rgba(124,58,237,0.1)', color: 'var(--indigo)',
              border: '1px solid rgba(124,58,237,0.25)', transition: 'all 0.2s'
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(124,58,237,0.2)'}
            onMouseLeave={e => e.currentTarget.style.background = 'rgba(124,58,237,0.1)'}
          >
            <Zap size={16} />
            <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase' }}>AI Copilot</span>
          </button>
          <Link
            to="/"
            style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '10px 14px', borderRadius: 4, textDecoration: 'none',
              color: 'var(--dim)', border: '1px solid transparent', transition: 'all 0.2s'
            }}
            onMouseEnter={e => { e.currentTarget.style.color = 'var(--muted)'; e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--dim)'; e.currentTarget.style.background = 'transparent'; }}
          >
            <ArrowLeft size={16} />
            <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, letterSpacing: '0.05em' }}>Volver al Inicio</span>
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ flex: 1, overflowY: 'auto', background: 'var(--bg)', position: 'relative' }}>
        <div style={{ padding: '32px', maxWidth: 1400, margin: '0 auto' }}>
          <Outlet context={{ openAI: triggerAIContext }} />
        </div>
      </main>

      {/* AI Panel */}
      <AIPanel isOpen={isAIOpen} onClose={() => setAIOpen(false)} contextData={aiContext} />
    </div>
  );
};

export default MainLayout;
