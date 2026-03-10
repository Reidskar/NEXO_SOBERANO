import { useEffect, useState } from "react";
import ChatBox from "../components/ChatBox";

function Dashboard() {
  const [estado, setEstado] = useState(null);
  const [costos, setCostos] = useState(null);
  const [budget, setBudget] = useState(null);

  useEffect(() => {
    const cargar = async () => {
      const [health, cosReport, bud] = await Promise.all([
        fetch("/agente/health").then(r => r.json()).catch(() => null),
        fetch("/agente/costs/report?period=today").then(r => r.json()).catch(() => null),
        fetch("/agente/costs/budget").then(r => r.json()).catch(() => null),
      ]);
      if (health) setEstado(health);
      if (cosReport) setCostos(cosReport);
      if (bud) setBudget(bud);
    };
    cargar();
    const interval = setInterval(cargar, 15000);
    return () => clearInterval(interval);
  }, []);

  const metrics = [
    {
      label: "Documentos indexados",
      value: estado?.total_documentos ?? "—",
      icon: "◫",
      color: "text-blue-400",
    },
    {
      label: "Estado RAG",
      value: estado?.rag_loaded ? "Activo" : "Inactivo",
      icon: "◉",
      color: estado?.rag_loaded ? "text-emerald-400" : "text-red-400",
    },
    {
      label: "Tokens hoy",
      value: budget?.tokens_used_today?.toLocaleString() ?? "—",
      icon: "△",
      color: "text-amber-400",
    },
    {
      label: "Presupuesto restante",
      value: budget?.tokens_remaining != null
        ? `${Math.round((budget.tokens_remaining / (budget.tokens_limit || 900000)) * 100)}%`
        : "—",
      icon: "◈",
      color: "text-nexo-green-l",
    },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 p-4 h-full">
      {/* Panel principal */}
      <div className="lg:col-span-2 flex flex-col gap-4 min-h-0">
        {/* Métricas */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
          {metrics.map((m, i) => (
            <div key={i} className="nexo-card p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-xs ${m.color}`}>{m.icon}</span>
                <span className="text-[11px] text-nexo-muted font-medium">{m.label}</span>
              </div>
              <p className={`text-xl font-bold ${m.color}`}>{m.value}</p>
            </div>
          ))}
        </div>

        {/* Info de costos */}
        <div className="nexo-card p-4 flex-1 min-h-0 overflow-auto">
          <h3 className="text-sm font-semibold text-nexo-text mb-3 flex items-center gap-2">
            <span className="text-nexo-dim">△</span> Resumen operacional
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Proveedores IA */}
            <div className="bg-nexo-dark rounded-lg p-3 border border-nexo-border/50">
              <p className="text-[10px] text-nexo-dim font-semibold uppercase tracking-wider mb-2">Proveedores IA</p>
              {["Gemini", "Claude", "OpenAI", "Grok"].map(name => {
                const key = name.toLowerCase();
                const calls = costos?.breakdown?.[key]?.calls ?? 0;
                return (
                  <div key={name} className="flex items-center justify-between py-1 text-xs">
                    <span className="text-nexo-muted">{name}</span>
                    <span className={`font-medium ${calls > 0 ? "text-nexo-green-l" : "text-nexo-dim"}`}>
                      {calls > 0 ? `${calls} llamadas` : "—"}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Servicios */}
            <div className="bg-nexo-dark rounded-lg p-3 border border-nexo-border/50">
              <p className="text-[10px] text-nexo-dim font-semibold uppercase tracking-wider mb-2">Servicios activos</p>
              {[
                { name: "Google Drive", env: "GOOGLE_CLIENT_ID" },
                { name: "Discord", env: "DISCORD_ENABLED" },
                { name: "OBS WebSocket", env: "OBS_ENABLED" },
                { name: "SMTP Mail", env: "SMTP_HOST" },
              ].map(svc => (
                <div key={svc.name} className="flex items-center justify-between py-1 text-xs">
                  <span className="text-nexo-muted">{svc.name}</span>
                  <span className="nexo-badge bg-nexo-surface text-nexo-dim">Configurado</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Chat panel */}
      <div className="nexo-card overflow-hidden flex flex-col min-h-[400px] lg:min-h-0">
        <ChatBox />
      </div>
    </div>
  );
}

export default Dashboard;
