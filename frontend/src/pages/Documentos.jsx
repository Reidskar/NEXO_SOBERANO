import { useEffect, useState } from "react";

function Documentos() {
  const [status, setStatus] = useState(null);
  const [presupuesto, setPresupuesto] = useState(null);

  useEffect(() => {
    Promise.all([
      fetch("/agente/health").then(r => r.json()).catch(() => null),
      fetch("/agente/presupuesto").then(r => r.json()).catch(() => null),
    ]).then(([h, p]) => {
      if (h) setStatus(h);
      if (p) setPresupuesto(p);
    });
  }, []);

  const ragPct = status?.rag_loaded ? 100 : 0;

  return (
    <div className="p-4 space-y-4">
      <div>
        <h2 className="text-lg font-bold text-nexo-text">Bóveda de Documentos</h2>
        <p className="text-xs text-nexo-dim">Motor RAG: indexación, búsqueda semántica y análisis</p>
      </div>

      {/* Métricas principales */}
      <div className="grid grid-cols-3 gap-3">
        <div className="nexo-card p-4 text-center">
          <p className="text-2xl font-bold text-blue-400">{status?.total_documentos ?? "—"}</p>
          <p className="text-[11px] text-nexo-muted mt-1">Documentos</p>
        </div>
        <div className="nexo-card p-4 text-center">
          <div className="flex items-center justify-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${status?.rag_loaded ? "bg-emerald-400 nexo-pulse" : "bg-red-400"}`} />
            <p className={`text-lg font-bold ${status?.rag_loaded ? "text-emerald-400" : "text-red-400"}`}>
              {status?.rag_loaded ? "Activo" : "Inactivo"}
            </p>
          </div>
          <p className="text-[11px] text-nexo-muted mt-1">Estado RAG</p>
        </div>
        <div className="nexo-card p-4 text-center">
          <p className="text-2xl font-bold text-amber-400">
            {presupuesto?.tokens_hoy?.toLocaleString() ?? "—"}
          </p>
          <p className="text-[11px] text-nexo-muted mt-1">Tokens usados hoy</p>
        </div>
      </div>

      {/* Barra de progreso RAG */}
      <div className="nexo-card p-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs text-nexo-muted font-medium">Estado del motor de búsqueda</span>
          <span className="text-xs text-nexo-dim">{ragPct}%</span>
        </div>
        <div className="w-full h-1.5 bg-nexo-dark rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-nexo-green to-nexo-green-l rounded-full transition-all duration-700"
            style={{ width: `${ragPct}%` }}
          />
        </div>
      </div>

      {/* Formatos soportados */}
      <div className="nexo-card p-4">
        <h3 className="text-sm font-semibold text-nexo-text mb-3 flex items-center gap-2">
          <span className="text-nexo-dim">◫</span> Formatos soportados
        </h3>
        <div className="flex flex-wrap gap-2">
          {[".pdf", ".txt", ".md", ".docx", ".csv", ".jpg", ".jpeg", ".png"].map(ext => (
            <span key={ext} className="nexo-badge bg-nexo-surface text-nexo-muted border border-nexo-border">
              {ext}
            </span>
          ))}
        </div>
      </div>

      {/* Instrucciones */}
      <div className="nexo-card p-4">
        <h3 className="text-sm font-semibold text-nexo-text mb-2 flex items-center gap-2">
          <span className="text-nexo-dim">△</span> Indexar documentos
        </h3>
        <p className="text-xs text-nexo-muted leading-relaxed">
          Sube archivos a la carpeta <code className="text-nexo-green-l bg-nexo-dark px-1 py-0.5 rounded text-[10px]">documentos/</code> del
          proyecto o utiliza el endpoint{" "}
          <code className="text-nexo-green-l bg-nexo-dark px-1 py-0.5 rounded text-[10px]">POST /agente/ingesta/subir</code> para
          indexar nuevos documentos al motor RAG. El sistema clasificará automáticamente por categoría geopolítica.
        </p>
      </div>
    </div>
  );
}

export default Documentos;
