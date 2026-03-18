import React, { useState, useEffect, useRef } from 'react';
import api from '../api/client';
import { Settings, Cpu, Send, CheckCircle, AlertOctagon, Terminal, Activity } from 'lucide-react';

const SystemControl = () => {
  const [config, setConfig] = useState(null);
  const [command, setCommand] = useState("");
  const [log, setLog] = useState([]);
  const [loading, setLoading] = useState(false);
  const logEndRef = useRef(null);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const { data } = await api.get('/config');
      setConfig(data);
    } catch (e) {
      console.error("No se pudo cargar la config:", e);
    }
  };

  const handleCommand = async (e) => {
    e.preventDefault();
    if (!command.trim()) return;

    setLoading(true);
    const currentCmd = command;
    setCommand("");

    try {
      const { data } = await api.post('/ai/control', { command: currentCmd });
      
      const newEntry = {
        time: new Date().toLocaleTimeString(),
        command: currentCmd,
        action: data.action,
        newConfig: data.current_config || data.new_config,
        error: data.error
      };

      setLog(prev => [...prev, newEntry]);

      if (data.current_config || data.new_config) {
        setConfig(data.current_config || data.new_config);
      }
    } catch (e) {
      setLog(prev => [...prev, {
        time: new Date().toLocaleTimeString(),
        command: currentCmd,
        action: "error",
        error: e.response?.data?.detail || e.message
      }]);
    } finally {
      setLoading(false);
      setTimeout(() => logEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl animate-fade-in">
      <header className="mb-8">
        <h2 className="text-3xl font-light text-white tracking-widest uppercase flex items-center gap-3">
          <Settings size={28} className="text-indigo-500" />
          Terminal de Control Autónomo
        </h2>
        <p className="text-sm text-gray-400 mt-2 font-mono">Capa de mutación inteligente. Modifica el comportamiento de todo el pipeline vía NLP.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Col: Config View */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-[#111820] border border-gray-800 rounded-lg p-6 shadow-2xl">
            <h3 className="text-xs uppercase font-bold tracking-widest text-indigo-400 mb-4 flex items-center gap-2">
              <Cpu size={14} /> Estado Actual del Sistema
            </h3>
            {config ? (
              <pre className="bg-[#0a0f16] p-4 rounded-md border border-gray-800 text-[10px] text-emerald-400 font-mono overflow-auto max-h-[400px] scrollbar-thin">
                {JSON.stringify(config, null, 2)}
              </pre>
            ) : (
              <div className="text-gray-500 animate-pulse text-xs font-mono">Extrayendo config...</div>
            )}
          </div>
        </div>

        {/* Right Col: Terminal & NLP Input */}
        <div className="lg:col-span-2 space-y-6 flex flex-col h-[520px]">
          
          {/* Terminal Log View */}
          <div className="flex-1 bg-[#0a0f16] border border-gray-800 rounded-lg p-6 shadow-inset overflow-y-auto scrollbar-thin flex flex-col gap-4 font-mono text-xs">
            <div className="text-gray-500 border-b border-gray-800 pb-2 mb-2">
              <span className="text-indigo-500">NEXO_ROOT@SYSTEM:~$</span> Inicializando log de mutaciones NLP...
            </div>
            
            {log.map((entry, i) => (
              <div key={i} className="space-y-2 p-3 bg-[#111820] border border-gray-800/60 rounded">
                <div className="text-gray-400">
                  <span className="text-emerald-500">[{entry.time}] </span>
                  &gt; Instrucción: <span className="text-white">"{entry.command}"</span>
                </div>
                
                {entry.action === 'error' ? (
                  <div className="flex items-start gap-2 text-rose-400 bg-rose-950/20 p-2 rounded">
                    <AlertOctagon size={14} className="mt-0.5 shrink-0" />
                    <span className="leading-relaxed">Fallo de Ejecución: {entry.error}</span>
                  </div>
                ) : (
                  <div className="flex items-start gap-2 text-indigo-300 bg-indigo-900/10 p-2 rounded">
                    <CheckCircle size={14} className="mt-0.5 shrink-0 text-emerald-500" />
                    <div>
                      <span className="block mb-1 text-emerald-500">Mutación Aplicada Exitosamente.</span>
                      <pre className="text-[9px] text-gray-500 mt-2">
                        + Configuración reescrita en caliente.
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            ))}
            <div ref={logEndRef} />
            {loading && (
              <div className="text-indigo-400 animate-pulse flex items-center gap-2 mt-4 p-2">
                <Activity size={12} /> Interpretando instrucción y calculando mutación estructural...
              </div>
            )}
          </div>

          {/* Input Layer */}
          <form onSubmit={handleCommand} className="relative mt-auto">
            <Terminal size={18} className="absolute left-4 top-4 text-gray-500" />
            <input 
              type="text"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              placeholder="Ej: 'haz los videos más agresivos', 'reduce el costo de IA', 'prioriza eventos militares'..."
              className="w-full bg-[#111820] border border-gray-700/80 rounded-lg py-4 pl-12 pr-14 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 transition-all shadow-lg font-mono"
              disabled={loading}
              autoComplete="off"
            />
            <button 
              type="submit"
              disabled={loading || !command.trim()}
              className="absolute right-3 top-2.5 p-2 bg-emerald-600/20 text-emerald-400 rounded-md hover:bg-emerald-600/30 transition-colors disabled:opacity-30 disabled:hover:bg-transparent"
            >
              <Send size={16} />
            </button>
          </form>

        </div>
      </div>
    </div>
  );
};

export default SystemControl;
