import React, { useState, useRef, useEffect } from 'react';
import { queryAI } from '../api/client';
import { X, Send, BrainCircuit, Activity, ChevronRight, MessageSquare } from 'lucide-react';

const AIPanel = ({ isOpen, onClose, contextData }) => {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if(isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const handleQuery = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    setLoading(true);
    setResponse(null);
    try {
      const fullPrompt = `${contextData ? `[Contexto actual del usuario: ${contextData}]\n\n` : ''}Consulta: ${query}`;
      const data = await queryAI({ prompt: fullPrompt, mode: "technical" });
      setResponse(data);
    } catch (e) {
      console.error(e);
      setResponse({ analysis: "Fallo de conexión neural. Servidor inaccesible." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity"
          onClick={onClose}
        />
      )}
      
      <div 
        className={`fixed top-0 right-0 h-full w-full max-w-[440px] bg-[#0d131a] border-l border-gray-800 z-50 transform transition-transform duration-300 ease-in-out flex flex-col shadow-2xl ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="px-6 py-4 border-b border-gray-800 flex justify-between items-center bg-[#111820]">
          <div className="flex items-center gap-3 text-indigo-400">
            <BrainCircuit size={20} />
            <span className="text-xs font-bold tracking-widest uppercase">NEXO AI Copilot</span>
          </div>
          <button onClick={onClose} className="p-1 text-gray-500 hover:text-gray-300 bg-gray-900 rounded-md border border-gray-800 hover:bg-gray-800 transition-colors">
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 scrollbar-thin flex flex-col">
          {contextData && !response && !loading && (
             <div className="mb-6 p-3 bg-indigo-900/10 border border-indigo-900/30 rounded-md text-xs text-indigo-400/80 font-mono">
               <strong>Contexto Inyectado:</strong> {contextData.substring(0, 100)}...
             </div>
          )}

          {response ? (
            <div className="space-y-8 animate-fade-in flex-1">
              <div className="space-y-3">
                <h4 className="flex items-center gap-2 text-[10px] uppercase font-bold tracking-widest text-indigo-400/80">
                  <Activity size={12} /> Análisis Contextual
                </h4>
                <div className="p-4 bg-[#111820] border border-gray-800 rounded-lg shadow-inner">
                  <p className="text-sm text-gray-300 leading-relaxed font-light">
                    {response.analysis}
                  </p>
                </div>
              </div>
              
              {response.outcomes && response.outcomes.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-[10px] uppercase font-bold tracking-widest text-gray-500">Proyecciones Vectoriales</h4>
                  <ul className="space-y-2">
                    {response.outcomes.map((out, i) => (
                      <li key={i} className="flex gap-3 text-xs text-gray-400 bg-[#0a0f16] p-3 rounded-md border border-gray-800/50">
                        <ChevronRight size={14} className="text-indigo-500 shrink-0 mt-0.5" />
                        <span className="leading-relaxed">{out}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            !loading && (
              <div className="flex-1 flex flex-col items-center justify-center text-gray-600 space-y-6">
                <div className="relative">
                  <BrainCircuit size={64} className="opacity-10" />
                  <div className="absolute inset-0 bg-indigo-500/10 blur-xl rounded-full" />
                </div>
                <p className="text-[10px] text-center max-w-[280px] leading-relaxed tracking-widest font-semibold uppercase text-gray-500">
                  Copiloto estratégico. Ingresa tu instrucción abajo.
                </p>
              </div>
            )
          )}
          
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-[#0d131a]/90 backdrop-blur-md z-10 transition-opacity">
              <div className="flex flex-col items-center gap-4 border border-indigo-900/30 bg-[#111820] px-6 py-4 rounded-lg shadow-2xl">
                <BrainCircuit size={24} className="text-indigo-500 animate-pulse" />
                <span className="text-xs tracking-widest uppercase font-bold text-indigo-400">Integrando Datos y Computando...</span>
              </div>
            </div>
          )}
        </div>

        <div className="p-5 border-t border-gray-800 bg-[#111820]">
          <form onSubmit={handleQuery} className="relative flex items-center">
            <MessageSquare size={16} className="absolute left-4 text-gray-600" />
            <input 
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ordena al IA..."
              className="w-full bg-[#0a0f16] border border-gray-700/80 rounded-lg py-3.5 pl-12 pr-14 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all shadow-inner"
              disabled={loading}
              autoComplete="off"
            />
            <button 
              type="submit"
              disabled={loading || !query.trim()}
              className="absolute right-2 p-2 bg-indigo-600/20 text-indigo-400 rounded-md hover:bg-indigo-600/30 transition-colors disabled:opacity-30 disabled:hover:bg-transparent"
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      </div>
    </>
  );
};

export default AIPanel;
