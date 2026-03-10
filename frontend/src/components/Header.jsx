import { useEffect, useState } from "react";

function Header() {
  const [status, setStatus] = useState("loading");
  const [info, setInfo] = useState({});

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch("/agente/health");
        if (res.ok) {
          const data = await res.json();
          setStatus(data.status === "ok" ? "online" : "degraded");
          setInfo({
            rag: data.rag_loaded,
            docs: data.total_documentos,
          });
        } else {
          setStatus("offline");
        }
      } catch {
        setStatus("offline");
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 8000);
    return () => clearInterval(interval);
  }, []);

  const indicator = {
    online:   { dot: "bg-emerald-400", bg: "bg-emerald-500/10", label: "Operativo" },
    degraded: { dot: "bg-yellow-400",  bg: "bg-yellow-500/10",  label: "Degradado" },
    offline:  { dot: "bg-red-400",     bg: "bg-red-500/10",     label: "Offline" },
    loading:  { dot: "bg-nexo-muted",  bg: "bg-nexo-surface",   label: "Conectando…" },
  };

  const s = indicator[status] || indicator.loading;

  return (
    <header className="h-12 bg-nexo-panel border-b border-nexo-border flex items-center justify-between px-5 shrink-0">
      {/* Left side - breadcrumb / context */}
      <div className="flex items-center gap-2 text-sm">
        <span className="text-nexo-dim">Centro de Mando</span>
        <span className="text-nexo-dim">›</span>
        <span className="text-nexo-text font-medium">Operaciones</span>
      </div>

      {/* Right side - status indicators */}
      <div className="flex items-center gap-4">
        {status === "online" && info.docs != null && (
          <div className="flex items-center gap-1.5 text-xs text-nexo-muted">
            <span className="text-nexo-dim">◫</span>
            <span>{info.docs} docs</span>
          </div>
        )}

        <div className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium ${s.bg}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${s.dot} ${status === "online" ? "nexo-pulse" : ""}`} />
          <span className="text-nexo-text">{s.label}</span>
        </div>
      </div>
    </header>
  );
}

export default Header;
