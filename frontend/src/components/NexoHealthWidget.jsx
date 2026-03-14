import React, { useState, useEffect } from 'react';

export default function NexoHealthWidget() {
  const [status, setStatus] = useState({ 
    xiaomi: 'offline', 
    db: 'offline', 
    ai: 'checking...' 
  });

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const r = await fetch('/api/health/');
        if (!r.ok) throw new Error('Health check failed');
        const data = await r.json();
        setStatus({
          xiaomi: data.xiaomi || 'offline',
          db: data.db || 'offline',
          ai: data.ai || 'degraded'
        });
      } catch (err) {
        setStatus({ xiaomi: 'error', db: 'error', ai: 'error' });
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (val) => {
    if (val === 'online' || val === 'operational') return 'bg-cyan-400';
    if (val === 'degraded' || val === 'partial') return 'bg-amber-400';
    return 'bg-red-500';
  };

  return (
    <div className="grid grid-cols-3 gap-4 p-4 bg-slate-900/80 backdrop-blur-lg rounded-xl border border-cyan-500/20 shadow-[0_0_20px_rgba(34,211,238,0.15)] mb-6">
      <div className="flex flex-col items-center">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${getStatusColor(status.db)} ${status.db === 'online' ? 'animate-pulse' : ''}`}></div>
          <span className="text-slate-200 text-xs font-bold tracking-widest uppercase">CORE / DB</span>
        </div>
        <p className="text-[10px] text-cyan-400/60 mt-1 font-mono">{status.db.toUpperCase()}</p>
      </div>
      
      <div className="flex flex-col items-center border-l border-r border-slate-700/50">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${getStatusColor(status.xiaomi)} ${status.xiaomi === 'online' ? 'animate-pulse' : ''}`}></div>
          <span className="text-slate-200 text-xs font-bold tracking-widest uppercase">XIAOMI 14T PRO</span>
        </div>
        <p className="text-[10px] text-cyan-400/60 mt-1 font-mono">{status.xiaomi.toUpperCase()}</p>
      </div>
      
      <div className="flex flex-col items-center">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${getStatusColor(status.ai)} ${status.ai === 'operational' ? 'animate-pulse shadow-[0_0_10px_rgba(34,211,238,0.5)]' : ''}`}></div>
          <span className="text-slate-200 text-xs font-bold tracking-widest uppercase">IA ORCHESTRATOR</span>
        </div>
        <p className="text-[10px] text-cyan-400/60 mt-1 font-mono">{status.ai.toUpperCase()}</p>
      </div>
    </div>
  );
}
