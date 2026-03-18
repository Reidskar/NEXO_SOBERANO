import React, { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, FileText, Clock, Brain, Settings } from 'lucide-react';
import AIPanel from '../components/AIPanel';

const MainLayout = () => {
  const location = useLocation();
  const [isAIOpen, setAIOpen] = useState(false);
  const [aiContext, setAIContext] = useState("");

  const navItems = [
    { name: 'Command Center', path: '/', icon: LayoutDashboard },
    { name: 'Terminal NLP', path: '/control', icon: Settings },
    { name: 'Evidencias', path: '/documents', icon: FileText },
    { name: 'Timeline Global', path: '/timeline/Global', icon: Clock },
  ];

  const triggerAIContext = (contextString) => {
    setAIContext(contextString);
    setAIOpen(true);
  };

  return (
    <div className="flex h-screen bg-[#0a0f16] text-gray-200 font-sans selection:bg-indigo-900">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-800 bg-[#0d131a] flex flex-col justify-between shrink-0">
        <div>
          <div className="h-20 flex flex-col justify-center px-6 border-b border-gray-800">
            <h1 className="text-lg font-bold tracking-widest text-gray-100 uppercase">Nexo Soberano</h1>
            <div className="flex items-center gap-2 mt-1">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[9px] font-mono tracking-widest text-emerald-500/80">SYSTEM ACTIVE</span>
            </div>
          </div>
          <nav className="p-4 space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
              return (
                <Link
                  key={item.name}
                  to={item.path}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-md transition-colors ${
                    isActive ? 'bg-indigo-900/20 text-indigo-400 border border-indigo-900/30' : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200 border border-transparent'
                  }`}
                >
                  <Icon size={18} />
                  <span className="text-sm font-medium">{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="p-4 border-t border-gray-800">
          <button 
            onClick={() => { setAIContext("Consulta global del sistema."); setAIOpen(!isAIOpen); }}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-md bg-indigo-600/10 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-600/20 hover:border-indigo-500/40 transition-colors"
          >
            <Brain size={18} />
            <span className="text-sm font-medium uppercase tracking-wider">AI Copilot</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto relative bg-[#0a0f16] scrollbar-thin">
        <div className="p-8 max-w-[1400px] mx-auto">
          <Outlet context={{ openAI: triggerAIContext }} />
        </div>
      </main>

      {/* Slide-out AI Panel */}
      <AIPanel isOpen={isAIOpen} onClose={() => setAIOpen(false)} contextData={aiContext} />
    </div>
  );
};

export default MainLayout;
