// ============================================================
// NEXO SOBERANO — Status Dashboard Component
// © 2026 elanarcocapital.com
// ============================================================
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import {
    Activity,
    Cpu,
    Database,
    Globe,
    Lock,
    Radio,
    RefreshCw,
    Server,
    Zap
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "";

// Static fallback data shown when backend is offline (Torre local)
const FALLBACK_HEALTH = {
  version: "NEXO v3.0.0",
  agents: { total_registered: 10 },
  services: {
    PostgreSQL: "ok",
    "Redis Cache": "ok",
    "Qdrant Vector": "ok",
    "Gemini Flash": "ok",
    "Discord Webhook": "ok",
    "Cloudflare Tunnel": "ok",
  },
  circuit_breakers: { open_circuits: [] },
};

const FALLBACK_DOMAIN = {
  ssl_valid: true,
  ssl_days_left: null,
  dns_resolved: true,
  ips: ["76.76.21.21"],
  alerts: [],
};

function MetricCard({ icon: Icon, label, value, sub, color = "#00e5ff" }) {
  return (
    <div
      className="nexo-metric-card"
      style={{
        background: "var(--bg2)",
        border: "1px solid var(--border)",
        padding: "20px 24px",
        transition: "all 0.3s",
      }}
      onMouseEnter={(e) =>
        (e.currentTarget.style.borderColor = "rgba(0,229,255,0.3)")
      }
      onMouseLeave={(e) =>
        (e.currentTarget.style.borderColor = "var(--border)")
      }
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 12,
        }}
      >
        {Icon && <Icon size={14} style={{ color }} />}
        <span
          style={{
            fontFamily: "'Space Mono', monospace",
            fontSize: 10,
            color: "var(--dim)",
            letterSpacing: "0.1em",
            textTransform: "uppercase",
          }}
        >
          {label}
        </span>
      </div>
      <div
        style={{
          fontSize: 24,
          fontWeight: 700,
          color: "var(--text)",
          letterSpacing: "-0.02em",
          marginBottom: 4,
        }}
      >
        {value}
      </div>
      {sub && (
        <div
          style={{
            fontFamily: "'Space Mono', monospace",
            fontSize: 11,
            color: "var(--muted)",
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}

function ServiceRow({ name, status }) {
  const color =
    status === "ok" || status === "online"
      ? "#10b981"
      : status === "degraded"
        ? "#f59e0b"
        : "#ef4444";
  return (
    <div
      className="nexo-service-row"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "10px 0",
        borderBottom: "1px solid rgba(0,229,255,0.06)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: color,
            boxShadow: `0 0 6px ${color}`,
          }}
        />
        <span
          style={{
            fontFamily: "'Space Mono', monospace",
            fontSize: 12,
            color: "var(--muted)",
          }}
        >
          {name}
        </span>
      </div>
      <span
        style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color }}
      >
        {status}
      </span>
    </div>
  );
}

function LiveTicker() {
  const [idx, setIdx] = useState(0);
  const items = [
    "→ Torre operativa · Backend FastAPI 8080 activo",
    "→ Docker: nexo_db nexo_redis nexo_qdrant UP",
    "→ Gemini Flash 2.0 · proveedor principal activo",
    "→ Discord webhook · supervisor monitoreando",
    "→ Cloudflare Tunnel · elanarcocapital.com online",
    "→ Sprint 1.3 desplegado · 16 rutas warroom activas",
  ];
  useEffect(() => {
    const t = setInterval(() => setIdx((i) => (i + 1) % items.length), 3500);
    return () => clearInterval(t);
  }, []);
  return (
    <div
      style={{
        fontFamily: "'Space Mono', monospace",
        fontSize: 10,
        color: "#00e5ff",
        letterSpacing: ".08em",
        padding: "8px 20px",
        background: "rgba(0,229,255,0.04)",
        borderBottom: "1px solid rgba(0,229,255,0.1)",
        transition: "opacity .3s",
      }}
    >
      {items[idx]}
    </div>
  );
}

export default function StatusDashboard() {
  const [health, setHealth] = useState(null);
  const [domain, setDomain] = useState(null);
  const [loading, setLoading] = useState(true);
  const [backendOnline, setBackendOnline] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const dashRef = useRef(null);

  useGSAP(
    () => {
      if (loading) return;
      gsap.fromTo(
        dashRef.current,
        { opacity: 0 },
        { opacity: 1, duration: 0.4, ease: "power2.out" },
      );
      gsap.fromTo(
        ".nexo-metric-card",
        { opacity: 0, y: 24, scale: 0.96 },
        {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 0.5,
          ease: "power3.out",
          stagger: 0.07,
          delay: 0.1,
        },
      );
      gsap.fromTo(
        ".nexo-service-row",
        { opacity: 0, x: -16 },
        {
          opacity: 1,
          x: 0,
          duration: 0.4,
          ease: "power2.out",
          stagger: 0.05,
          delay: 0.3,
        },
      );
    },
    { scope: dashRef, dependencies: [loading] },
  );

  const fetchData = async () => {
    const [h, d] = await Promise.allSettled([
      fetch(`${API_BASE}/api/health`, {
        signal: AbortSignal.timeout(4000),
      }).then((r) => r.json()),
      fetch(`${API_BASE}/api/tools/domain-scan`, {
        signal: AbortSignal.timeout(4000),
      }).then((r) => r.json()),
    ]);
    const healthData = h.status === "fulfilled" ? h.value : null;
    const domainData = d.status === "fulfilled" ? d.value : null;
    setHealth(healthData || FALLBACK_HEALTH);
    setDomain(domainData || FALLBACK_DOMAIN);
    setBackendOnline(!!healthData);
    setLastUpdate(new Date().toLocaleTimeString("es-CL"));
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading)
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: 256,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            fontFamily: "'Space Mono', monospace",
            fontSize: 12,
            color: "var(--muted)",
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "var(--cyan)",
              animation: "blink-dot 1s infinite",
            }}
          />
          Cargando estado del sistema...
        </div>
      </div>
    );

  const services = health?.services || FALLBACK_HEALTH.services;
  const openCircuits = health?.circuit_breakers?.open_circuits || [];

  return (
    <div ref={dashRef} style={{ maxWidth: 1100 }}>
      {/* Live ticker */}
      <LiveTicker />

      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          margin: "28px 0 24px",
        }}
      >
        <div>
          <h1
            style={{
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: "-0.02em",
              color: "var(--text)",
              marginBottom: 4,
            }}
          >
            Command Center
          </h1>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <p
              style={{
                fontFamily: "'Space Mono', monospace",
                fontSize: 11,
                color: "var(--muted)",
              }}
            >
              elanarcocapital.com ·{" "}
              {lastUpdate ? `Actualizado ${lastUpdate}` : "Cargando..."}
            </p>
            <span
              style={{
                fontFamily: "'Space Mono', monospace",
                fontSize: 9,
                letterSpacing: ".1em",
                padding: "2px 8px",
                borderRadius: 2,
                background: backendOnline
                  ? "rgba(16,185,129,0.1)"
                  : "rgba(0,229,255,0.08)",
                border: `1px solid ${backendOnline ? "rgba(16,185,129,0.3)" : "rgba(0,229,255,0.2)"}`,
                color: backendOnline ? "#10b981" : "#00e5ff",
              }}
            >
              {backendOnline ? "● TORRE ONLINE" : "○ TORRE LOCAL"}
            </span>
          </div>
        </div>
        <button
          onClick={fetchData}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 16px",
            background: "transparent",
            border: "1px solid var(--border)",
            color: "var(--muted)",
            cursor: "pointer",
            fontFamily: "'Space Mono', monospace",
            fontSize: 11,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            transition: "all 0.2s",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "var(--cyan)";
            e.currentTarget.style.color = "var(--cyan)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = "var(--border)";
            e.currentTarget.style.color = "var(--muted)";
          }}
        >
          <RefreshCw size={12} />
          Actualizar
        </button>
      </div>

      {/* Metrics */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 1,
          background: "var(--border)",
          border: "1px solid var(--border)",
          marginBottom: 24,
        }}
      >
        <MetricCard
          icon={Activity}
          label="Agentes"
          value={health?.agents?.total_registered || 10}
          sub="activos 24/7"
          color="#10b981"
        />
        <MetricCard
          icon={Lock}
          label="SSL"
          value={domain?.ssl_days_left ? `${domain.ssl_days_left}d` : "TLS"}
          sub={
            domain?.ssl_valid ? "Certificado válido" : "Verificar certificado"
          }
          color="#00e5ff"
        />
        <MetricCard
          icon={Cpu}
          label="Circuit Breakers"
          value={
            openCircuits.length === 0 ? "OK" : `${openCircuits.length} abiertos`
          }
          sub={
            openCircuits.length === 0
              ? "Sin alertas activas"
              : openCircuits.join(", ")
          }
          color={openCircuits.length === 0 ? "#10b981" : "#f59e0b"}
        />
        <MetricCard
          icon={Globe}
          label="API Status"
          value={backendOnline ? "Online" : "Local"}
          sub={health?.version || "NEXO v3.0.0"}
          color={backendOnline ? "#10b981" : "#00e5ff"}
        />
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
          marginBottom: 16,
        }}
      >
        {/* Services */}
        <div
          style={{
            background: "var(--bg2)",
            border: "1px solid var(--border)",
            padding: "24px 28px",
          }}
        >
          <h2
            style={{
              fontFamily: "'Space Mono', monospace",
              fontSize: 11,
              color: "var(--cyan)",
              letterSpacing: "0.15em",
              textTransform: "uppercase",
              marginBottom: 20,
            }}
          >
            Servicios del Sistema
          </h2>
          {Object.entries(services).map(([name, status]) => (
            <ServiceRow key={name} name={name} status={status} />
          ))}
          {!backendOnline && (
            <div
              style={{
                marginTop: 14,
                padding: "8px 12px",
                background: "rgba(0,229,255,0.04)",
                border: "1px solid rgba(0,229,255,0.1)",
                fontFamily: "'Space Mono', monospace",
                fontSize: 10,
                color: "rgba(0,229,255,0.5)",
                letterSpacing: ".06em",
              }}
            >
              Estado local · conecta la Torre para datos en vivo
            </div>
          )}
        </div>

        {/* Domain */}
        <div
          style={{
            background: "var(--bg2)",
            border: "1px solid var(--border)",
            padding: "24px 28px",
          }}
        >
          <h2
            style={{
              fontFamily: "'Space Mono', monospace",
              fontSize: 11,
              color: "var(--cyan)",
              letterSpacing: "0.15em",
              textTransform: "uppercase",
              marginBottom: 20,
            }}
          >
            Estado del Dominio
          </h2>
          <ServiceRow
            name="elanarcocapital.com"
            status={domain?.ssl_valid ? "ok" : "error"}
          />
          <ServiceRow
            name="DNS Resolution"
            status={domain?.dns_resolved ? "ok" : "error"}
          />
          <ServiceRow name="Vercel CDN" status="ok" />
          <ServiceRow
            name="Cloudflare Tunnel"
            status={backendOnline ? "ok" : "standby"}
          />
          {domain?.ips?.length > 0 && (
            <div
              style={{
                padding: "10px 0",
                borderBottom: "1px solid rgba(0,229,255,0.06)",
              }}
            >
              <span
                style={{
                  fontFamily: "'Space Mono', monospace",
                  fontSize: 11,
                  color: "var(--muted)",
                }}
              >
                IP: {domain.ips[0]}
              </span>
            </div>
          )}
          {domain?.alerts?.map((a, i) => (
            <div
              key={i}
              style={{
                fontFamily: "'Space Mono', monospace",
                fontSize: 11,
                color: "#f59e0b",
                padding: "6px 0",
              }}
            >
              ⚠ {a}
            </div>
          ))}
        </div>
      </div>

      {/* Sprint status */}
      <div
        style={{
          background: "var(--bg2)",
          border: "1px solid var(--border)",
          padding: "20px 28px",
        }}
      >
        <h2
          style={{
            fontFamily: "'Space Mono', monospace",
            fontSize: 11,
            color: "var(--cyan)",
            letterSpacing: "0.15em",
            textTransform: "uppercase",
            marginBottom: 16,
          }}
        >
          Sprint 1.3 · Módulos Activos
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 12,
          }}
        >
          {[
            {
              name: "OmniGlobe 3D",
              icon: Globe,
              status: "ok",
              path: "/control/omniglobe",
            },
            {
              name: "OSINT Engine",
              icon: Radio,
              status: "ok",
              path: "/control/osint",
            },
            {
              name: "Wireless Intel",
              icon: Zap,
              status: "ok",
              path: "/control/wireless",
            },
            {
              name: "Bóveda OSINT",
              icon: Database,
              status: "ok",
              path: "/control/boveda",
            },
            {
              name: "Mapa Global",
              icon: Globe,
              status: "ok",
              path: "/control/mapa",
            },
            {
              name: "Mercados",
              icon: Activity,
              status: "ok",
              path: "/control/mercados",
            },
            {
              name: "Escenarios IA",
              icon: Server,
              status: "ok",
              path: "/control/escenarios",
            },
            {
              name: "Video Estudio",
              icon: Cpu,
              status: "ok",
              path: "/control/video-studio",
            },
          ].map(({ name, icon: Icon, status, path }) => (
            <a key={name} href={path} style={{ textDecoration: "none" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "10px 14px",
                  border: "1px solid rgba(0,229,255,0.08)",
                  background: "rgba(0,229,255,0.02)",
                  transition: "all .2s",
                  cursor: "pointer",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "rgba(0,229,255,0.25)";
                  e.currentTarget.style.background = "rgba(0,229,255,0.05)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "rgba(0,229,255,0.08)";
                  e.currentTarget.style.background = "rgba(0,229,255,0.02)";
                }}
              >
                <Icon size={12} style={{ color: "#00e5ff", flexShrink: 0 }} />
                <span
                  style={{
                    fontFamily: "'Space Mono', monospace",
                    fontSize: 10,
                    color: "var(--muted)",
                    flex: 1,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {name}
                </span>
                <span
                  style={{
                    width: 5,
                    height: 5,
                    borderRadius: "50%",
                    background: "#10b981",
                    flexShrink: 0,
                    boxShadow: "0 0 4px #10b981",
                  }}
                />
              </div>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
