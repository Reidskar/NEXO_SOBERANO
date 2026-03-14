// frontend/src/pages/Dashboard.jsx
import { useState, useEffect, useCallback } from "react";

const API = "http://localhost:8000";
const REFRESH_MS = 15000; // 15 segundos

function MetricCard({ title, value, unit, warn, crit }) {
  const num = parseFloat(value);
  const color = num >= crit ? "#ff4444" : num >= warn ? "#ffaa00" : "#44bb44";
  return (
    <div style={{
      background: "#1a1a2e", border: `2px solid ${color}`,
      borderRadius: 8, padding: "16px 20px", minWidth: 160
    }}>
      <div style={{ color: "#888", fontSize: 12, marginBottom: 4 }}>{title}</div>
      <div style={{ color, fontSize: 28, fontWeight: "bold", fontFamily: "monospace" }}>
        {value ?? "?"}<span style={{ fontSize: 14, color: "#888" }}> {unit}</span>
      </div>
    </div>
  );
}

function NodeCard({ title, data, online }) {
  return (
    <div style={{
      background: "#16213e", border: `1px solid ${online ? "#44bb44" : "#ff4444"}`,
      borderRadius: 12, padding: 20, marginBottom: 16
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
        <span style={{ fontSize: 10, color: online ? "#44bb44" : "#ff4444" }}>●</span>
        <h3 style={{ margin: 0, color: "#eee", fontFamily: "monospace" }}>{title}</h3>
        {!online && <span style={{ color: "#ff4444", fontSize: 12 }}>OFFLINE</span>}
      </div>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        {data.cpu !== undefined &&
          <MetricCard title="CPU" value={data.cpu} unit="%" warn={70} crit={90} />}
        {data.ram !== undefined &&
          <MetricCard title="RAM" value={data.ram} unit="%" warn={75} crit={90} />}
        {data.bat !== undefined && data.bat >= 0 &&
          <MetricCard title="BAT" value={data.bat} unit="%" warn={30} crit={15} />}
        {data.uptime &&
          <div style={{ background: "#1a1a2e", borderRadius: 8, padding: "16px 20px" }}>
            <div style={{ color: "#888", fontSize: 12 }}>Uptime</div>
            <div style={{ color: "#88aaff", fontSize: 18, fontFamily: "monospace" }}>
              {data.uptime}
            </div>
          </div>}
      </div>
      {data.extra && (
        <div style={{ marginTop: 12, color: "#666", fontSize: 12, fontFamily: "monospace" }}>
          {Object.entries(data.extra).map(([k, v]) => (
            <span key={k} style={{ marginRight: 16 }}>{k}: {String(v)}</span>
          ))}
        </div>
      )}
    </div>
  );
}


function FilesPanel() {
  const [catalog, setCatalog] = useState(null);
  
  useEffect(() => {
    fetch(`${API}/api/files/kindle/catalog`)
      .then(r => r.json())
      .then(setCatalog)
      .catch(() => {});
  }, []);

  if (!catalog || catalog.total === 0) return null;

  const porCategoria = catalog.libros.reduce((acc, l) => {
    acc[l.categoria] = (acc[l.categoria] || 0) + 1;
    return acc;
  }, {});

  return (
    <div style={{ background: "#16213e", border: "1px solid #334", borderRadius: 12, padding: 20, marginBottom: 16 }}>
      <h3 style={{ margin: "0 0 16px", color: "#eee", fontFamily: "monospace" }}>
        📚 Kindle Library — {catalog.total} libros
      </h3>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        {Object.entries(porCategoria).map(([cat, count]) => (
          <div key={cat} style={{
            background: "#1a1a2e", borderRadius: 8,
            padding: "8px 16px", fontFamily: "monospace"
          }}>
            <span style={{ color: "#888", fontSize: 12 }}>{cat}</span>
            <span style={{ color: "#88aaff", fontSize: 20, marginLeft: 8 }}>{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Detectar nodos por agent_id
const NODOS_CONOCIDOS = {
  'xiaomi-mobile-01': { 
    label: 'Xiaomi 14T Pro', 
    icon: '📱', 
    tipo: 'mobile' 
  },
  'dell-latitude-console': { 
    label: 'Dell Latitude (Consola)', 
    icon: '💻', 
    tipo: 'notebook' 
  },
};

export default function Dashboard() {
  const [pcMetrics, setPcMetrics]     = useState(null);
  const [mobileAgents, setMobileAgents] = useState({});
  const [lastUpdate, setLastUpdate]   = useState(null);
  const [error, setError]             = useState(null);

  const fetchAll = useCallback(async () => {
    try {
      const [mRes, aRes] = await Promise.all([
        fetch(`${API}/api/metrics/`),
        fetch(`${API}/api/mobile/agents`),
      ]);
      if (mRes.ok) setPcMetrics(await mRes.json());
      if (aRes.ok) {
        const d = await aRes.json();
        setMobileAgents(d.agentes || {});
      }
      setLastUpdate(new Date().toLocaleTimeString());
      setError(null);
    } catch (e) {
      setError(`Sin conexión al backend: ${e.message}`);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const t = setInterval(fetchAll, REFRESH_MS);
    return () => clearInterval(t);
  }, [fetchAll]);

  const sys = pcMetrics?.system || pcMetrics?.sistema || {};

  return (
    <div style={{
      minHeight: "100vh", background: "#0f0f23",
      color: "#eee", padding: 24, fontFamily: "sans-serif"
    }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, color: "#88aaff", fontFamily: "monospace", fontSize: 24 }}>
            ⬡ NEXO SOBERANO
          </h1>
          <div style={{ color: "#555", fontSize: 12, marginTop: 4 }}>
            Infrastructure Monitor v{pcMetrics?.version || pcMetrics?.nexo?.version || "..."}
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          {error
            ? <span style={{ color: "#ff4444", fontSize: 13 }}>⚠ {error}</span>
            : <span style={{ color: "#44bb44", fontSize: 13 }}>● Live — {lastUpdate}</span>
          }
          <div style={{ color: "#555", fontSize: 11, marginTop: 2 }}>
            Refresh cada {REFRESH_MS/1000}s
          </div>
        </div>
      </div>

      {/* Nodo PC */}
      <h2 style={{ color: "#888", fontSize: 13, textTransform: "uppercase",
                   letterSpacing: 2, marginBottom: 12 }}>Nodo Central</h2>
      <NodeCard
        title="PC Tower (i5-12600KF · 48GB · RTX 3060)"
        online={!!pcMetrics && !error}
        data={{
          cpu:    sys.cpu_percent ?? sys.uso_pct,
          ram:    sys.memory_percent ?? pcMetrics?.memoria?.uso_pct,
          uptime: pcMetrics?.uptime_legible,
          extra:  pcMetrics?.nexo
        }}
      />

      {/* Nodos móviles */}
      <h2 style={{ color: "#888", fontSize: 13, textTransform: "uppercase",
                   letterSpacing: 2, margin: "24px 0 12px" }}>
        Nodos Móviles ({Object.keys(mobileAgents).length})
      </h2>
      {Object.keys(mobileAgents).length === 0
        ? <div style={{ color: "#555", fontFamily: "monospace", padding: 20 }}>
            Sin agentes móviles conectados
          </div>
        : Object.entries(mobileAgents).map(([id, d]) => {
            const info = NODOS_CONOCIDOS[id] || { label: id, icon: '🔌', tipo: 'unknown' };
            const mins = d.ultimo_contacto
              ? Math.floor((Date.now() - new Date(d.ultimo_contacto)) / 60000)
              : 999;
            return (
              <NodeCard
                key={id}
                title={`${info.icon} ${info.label}`}
                online={mins < 3}
                data={{
                  cpu: d.cpu_pct,
                  ram: d.ram_pct,
                  bat: d.bateria_pct,
                  extra: {
                    Tipo: info.tipo,
                    WiFi: d.wifi_ssid,
                    "Último": `${mins}m ago`,
                    'IP Tailscale': d.tailscale_ip || 'N/A'
                  }
                }}
              />
            );
          })
      }

      {/* Biblioteca Kindle */}
      <h2 style={{ color: "#888", fontSize: 13, textTransform: "uppercase",
                   letterSpacing: 2, margin: "24px 0 12px" }}>Biblioteca Digital</h2>
      <FilesPanel />

      {/* Footer */}
      <div style={{ marginTop: 40, color: "#333", fontSize: 11, textAlign: "center" }}>
        github.com/Reidskar/NEXO_SOBERANO
      </div>
    </div>
  );
}
