import { useState, useRef, useEffect } from "react";

function ChatBox() {
  const [pregunta, setPregunta] = useState("");
  const [categoria, setCategoria] = useState("");
  const [mensajes, setMensajes] = useState([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [mensajes, loading]);

  const sendMessage = async () => {
    if (!pregunta.trim() || loading) return;
    const userMsg = { role: "user", text: pregunta, time: new Date() };
    setMensajes(prev => [...prev, userMsg]);
    const q = pregunta;
    setPregunta("");
    setLoading(true);

    try {
      const res = await fetch("/agente/consultar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, mode: "normal", categoria: categoria || undefined }),
      });
      const data = await res.json();
      if (res.ok) {
        setMensajes(prev => [...prev, {
          role: "ai",
          text: data.answer || "Sin respuesta",
          sources: data.sources || [],
          chunks: data.chunks_used,
          ms: data.execution_time_ms,
          time: new Date(),
        }]);
      } else {
        setMensajes(prev => [...prev, { role: "error", text: data.detail || `Error ${res.status}`, time: new Date() }]);
      }
    } catch {
      setMensajes(prev => [...prev, { role: "error", text: "No se pudo conectar con el backend", time: new Date() }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  const categorias = [
    { value: "", label: "Todas" },
    { value: "GEO", label: "GEO" }, { value: "ECO", label: "ECO" },
    { value: "PSI", label: "PSI" }, { value: "TEC", label: "TEC" },
    { value: "COM", label: "COM" }, { value: "ADM", label: "ADM" },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-nexo-border flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-nexo-text">Agente RAG</h3>
          <p className="text-[10px] text-nexo-dim">Consulta la bóveda de inteligencia</p>
        </div>
        <select
          className="text-xs bg-nexo-dark border border-nexo-border rounded px-2 py-1 text-nexo-muted focus:outline-none focus:border-nexo-green-h"
          value={categoria}
          onChange={e => setCategoria(e.target.value)}
        >
          {categorias.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-auto px-4 py-3 space-y-3">
        {mensajes.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-10 h-10 rounded-lg bg-nexo-green/20 flex items-center justify-center mb-3">
              <span className="text-nexo-green-l text-lg">◉</span>
            </div>
            <p className="text-sm text-nexo-muted">Escribe una pregunta para consultar</p>
            <p className="text-xs text-nexo-dim mt-1">Enter para enviar · Shift+Enter nueva línea</p>
          </div>
        )}

        {mensajes.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-lg px-3.5 py-2.5 text-sm ${
              msg.role === "user"
                ? "bg-nexo-green text-white"
                : msg.role === "error"
                ? "bg-red-500/10 border border-red-500/20 text-red-300"
                : "bg-nexo-surface border border-nexo-border text-nexo-text"
            }`}>
              <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>
              {msg.sources?.length > 0 && (
                <div className="mt-2 pt-2 border-t border-nexo-border/50">
                  <p className="text-[10px] text-nexo-dim font-semibold uppercase mb-1">Fuentes</p>
                  {msg.sources.map((s, j) => (
                    <p key={j} className="text-xs text-nexo-muted">• {s}</p>
                  ))}
                </div>
              )}
              {(msg.chunks != null || msg.ms != null) && (
                <div className="mt-1.5 flex gap-3 text-[10px] text-nexo-dim">
                  {msg.chunks != null && <span>◫ {msg.chunks} chunks</span>}
                  {msg.ms != null && <span>⏱ {msg.ms}ms</span>}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-nexo-surface border border-nexo-border rounded-lg px-4 py-3 flex items-center gap-2">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-nexo-green-l animate-bounce" style={{animationDelay: "0ms"}} />
                <span className="w-1.5 h-1.5 rounded-full bg-nexo-green-l animate-bounce" style={{animationDelay: "150ms"}} />
                <span className="w-1.5 h-1.5 rounded-full bg-nexo-green-l animate-bounce" style={{animationDelay: "300ms"}} />
              </div>
              <span className="text-xs text-nexo-muted">Procesando…</span>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-nexo-border bg-nexo-panel">
        <div className="flex gap-2">
          <textarea
            className="nexo-input resize-none text-sm flex-1"
            placeholder="Escribe tu consulta…"
            value={pregunta}
            onChange={e => setPregunta(e.target.value)}
            onKeyDown={handleKey}
            rows={1}
            style={{ minHeight: "40px", maxHeight: "100px" }}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !pregunta.trim()}
            className="nexo-btn px-4 shrink-0 text-sm"
          >
            {loading ? "…" : "Enviar"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatBox;
