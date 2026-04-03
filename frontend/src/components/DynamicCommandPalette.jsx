import React, { useState, useEffect, useRef } from 'react';

export default function DynamicCommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState(null); // 'loading', 'success', 'error'
  const inputRef = useRef(null);

  // Lista de comandos operativos y de marketing
  const commands = [
    { id: 'sync_all', icon: '🔄', label: 'Sincronizar Bóveda de Datos (Drive/Local)' },
    { id: 'check_health', icon: '🩺', label: 'Diagnóstico del Sistema (Sensores Móviles)' },
    { id: 'generate_social', icon: '🚀', label: 'Marketing: Generar Borradores RRSS' },
    { id: 'cut_video', icon: '✂️', label: 'Multimedia: Extraer Shorts de Último Video' }
  ];

  // Escuchar Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
      if (e.key === 'Escape') setIsOpen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Auto-focus cuando se abre
  useEffect(() => {
    if (isOpen && inputRef.current) inputRef.current.focus();
    if (!isOpen) { setQuery(''); setStatus(null); }
  }, [isOpen]);

  const executeCommand = async (slug) => {
    setStatus('loading');
    try {
      // Llamada al backend unificado
      const response = await fetch('/agente/execute-command', {
        method: 'POST', 
        headers: {
          'Content-Type': 'application/json',
          'X-NEXO-API-KEY': 'nexo_dev_key_2025' // Reemplazar con env var en prod
        },
        body: JSON.stringify({ command: slug })
      });
      
      if (response.ok) {
        setStatus('success');
        setTimeout(() => setIsOpen(false), 1500); // Cierra tras éxito
      } else {
        setStatus('error');
      }
    } catch (error) {
      setStatus('error');
    }
  };

  const filteredCommands = commands.filter(c => c.label.toLowerCase().includes(query.toLowerCase()));

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh] bg-slate-900/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl bg-slate-800 rounded-xl shadow-[0_0_30px_rgba(34,211,238,0.15)] border border-cyan-500/30 overflow-hidden">
        {/* Input Area */}
        <div className="flex items-center px-4 py-4 border-b border-slate-700">
          <span className="text-cyan-400 text-xl mr-3">⚡</span>
          <input
            ref={inputRef}
            type="text"
            className="w-full bg-transparent text-slate-200 placeholder-slate-500 text-lg outline-none"
            placeholder="Escribe un comando o busca una acción..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div className="flex gap-2">
            <kbd className="px-2 py-1 text-xs text-slate-400 bg-slate-900 rounded border border-slate-700">ESC</kbd>
          </div>
        </div>

        {/* Command List */}
        <div className="max-h-96 overflow-y-auto p-2">
          {status === 'loading' && <div className="p-4 text-cyan-400 text-center animate-pulse">Ejecutando protocolo...</div>}
          {status === 'success' && <div className="p-4 text-green-400 text-center">¡Comando ejecutado con éxito!</div>}
          {status === 'error' && <div className="p-4 text-red-400 text-center">Error en la ejecución. Revisa los logs.</div>}
          
          {!status && filteredCommands.map((cmd) => (
            <button
              key={cmd.id}
              onClick={() => executeCommand(cmd.id)}
              className="w-full flex items-center px-4 py-3 text-left text-slate-300 hover:bg-slate-700/50 hover:text-cyan-300 rounded-lg group transition-colors active:scale-[0.98]"
            >
              <span className="mr-3 text-xl">{cmd.icon}</span>
              <span className="flex-grow font-medium">{cmd.label}</span>
              <span className="opacity-0 group-hover:opacity-100 text-cyan-500 text-sm">Ejecutar ↵</span>
            </button>
          ))}
          {!status && filteredCommands.length === 0 && (
            <div className="p-4 text-slate-500 text-center">No se encontraron comandos para "{query}"</div>
          )}
        </div>
      </div>
    </div>
  );
}
