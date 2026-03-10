import { useState } from "react";

function Inteligencia() {
  const [query, setQuery] = useState("");
  const [resultado, setResultado] = useState(null);
  const [loading, setLoading] = useState(false);
  const [historial, setHistorial] = useState([]);

  const analizar = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await fetch("/agente/consultar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, mode: "high" }),
      });
      const data = await res.json();
      const entry = { query, result: data, time: new Date() };
      setResultado(data);
      setHistorial(prev => [entry, ...prev].slice(0, 10));
    } catch {
      setResultado({ answer: "Error conectando al backend", error: true });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 space-y-4 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-nexo-text">Análisis de Inteligencia</h2>
          <p className="text-xs text-nexo-dim">Consultas en modo PRO con fuentes geopolíticas</p>
        </div>
        <span className="nexo-badge bg-purple-500/15 text-purple-400">Modo PRO</span>
      </div>

      {/* Input */}
      <div className="nexo-card p-4">
        <textarea
          className="nexo-input text-sm resize-none"
          placeholder="Ej: Analiza la posición de OTAN respecto a la expansión china en África…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          rows={3}
        />
        <div className="flex justify-between items-center mt-3">
          <span className="text-[10px] text-nexo-dim">Usa el modelo más potente disponible</span>
          <button
            onClick={analizar}
            disabled={loading || !query.trim()}
            className="nexo-btn text-sm"
          >
            {loading ? "Analizando…" : "Analizar"}
          </button>
        </div>
      </div>

      {/* Resultado */}
      {resultado && (
        <div className="nexo-card p-4 flex-1 min-h-0 overflow-auto">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs text-nexo-green-l">◉</span>
            <h3 className="text-sm font-semibold text-nexo-text">Resultado del análisis</h3>
          </div>
          <div className={`text-sm leading-relaxed whitespace-pre-wrap ${resultado.error ? "text-red-300" : "text-nexo-text"}`}>
            {resultado.answer}
          </div>
          {resultado.sources?.length > 0 && (
            <div className="mt-3 pt-3 border-t border-nexo-border">
              <p className="text-[10px] text-nexo-dim font-semibold uppercase mb-1.5">Fuentes utilizadas</p>
              <ul className="space-y-0.5">
                {resultado.sources.map((s, i) => (
                  <li key={i} className="text-xs text-nexo-muted flex items-start gap-1.5">
                    <span className="text-nexo-dim mt-0.5">•</span> {s}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {(resultado.chunks_used || resultado.execution_time_ms) && (
            <div className="mt-2 flex gap-4 text-[10px] text-nexo-dim">
              {resultado.chunks_used && <span>◫ {resultado.chunks_used} chunks</span>}
              {resultado.execution_time_ms && <span>⏱ {resultado.execution_time_ms}ms</span>}
            </div>
          )}
        </div>
      )}

      {/* Historial compacto */}
      {historial.length > 0 && !resultado && (
        <div className="nexo-card p-4">
          <p className="text-[10px] text-nexo-dim font-semibold uppercase mb-2">Consultas recientes</p>
          {historial.map((h, i) => (
            <div key={i} className="flex items-center justify-between py-1.5 border-b border-nexo-border/30 last:border-0">
              <span className="text-xs text-nexo-muted truncate max-w-[80%]">{h.query}</span>
              <span className="text-[10px] text-nexo-dim">{h.time.toLocaleTimeString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Inteligencia;
