/**
 * Wireless.jsx — NEXO SOBERANO
 * Inteligencia de señal inalámbrica pasiva.
 * Inspirado en WireTapper (h9zdev) + animaciones GSAP.
 *
 * Fuentes: Wigle.net (WiFi/BT) + OpenCellID (torres celulares)
 */
import { useGSAP } from "@gsap/react";
import axios from "axios";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import "leaflet/dist/leaflet.css";
import {
    Camera,
    Car,
    HelpCircle,
    Radio,
    RefreshCw,
    Router,
    Signal,
    Smartphone,
    Tv2,
    Wifi
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
    CircleMarker,
    LayersControl,
    MapContainer,
    TileLayer,
    Tooltip,
} from "react-leaflet";

gsap.registerPlugin(ScrollTrigger);

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8080";
const KEY = import.meta.env.VITE_API_KEY || "NEXO_LOCAL_2026_OK";

const CATEGORY_CONFIG = {
  camera: { color: "#ff00ff", icon: Camera, label: "Cámara/CCTV" },
  vehicle: { color: "#ff6b00", icon: Car, label: "Vehículo" },
  iot: { color: "#00ffd1", icon: Smartphone, label: "IoT" },
  router: { color: "#4ade80", icon: Router, label: "Router" },
  mobile: { color: "#818cf8", icon: Smartphone, label: "Móvil" },
  tv: { color: "#facc15", icon: Tv2, label: "Smart TV" },
  unknown: { color: "#64748b", icon: HelpCircle, label: "Desconocido" },
};

const RADIO_COLORS = {
  LTE: "#00ffd1",
  NR: "#ff00ff",
  UMTS: "#facc15",
  GSM: "#4ade80",
};

const formatAge = (dateStr) => {
  if (!dateStr) return "—";
  const diff = (Date.now() - new Date(dateStr)) / 1000;
  if (diff < 60) return `${Math.round(diff)}s AGO`;
  if (diff < 3600) return `${Math.round(diff / 60)}m AGO`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h AGO`;
  return `${Math.round(diff / 86400)}d AGO`;
};

export default function Wireless() {
  const containerRef = useRef(null);
  const titleRef = useRef(null);
  const kpiRef = useRef(null);
  const listRef = useRef(null);

  const [mode, setMode] = useState("wifi");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [activeFilter, setActiveFilter] = useState("all");
  const [mapCenter, setMapCenter] = useState([-33.45, -70.67]);

  // ── GSAP Animations ────────────────────────────────────────────────
  useGSAP(
    () => {
      // Title scan-in animation (from gsap-skills: fromTo + stagger)
      gsap.fromTo(
        titleRef.current,
        { opacity: 0, x: -40, skewX: -8 },
        { opacity: 1, x: 0, skewX: 0, duration: 0.7, ease: "power3.out" },
      );

      // KPI badges pop in with stagger
      gsap.fromTo(
        ".wl-kpi",
        { opacity: 0, scale: 0.7, y: 20 },
        {
          opacity: 1,
          scale: 1,
          y: 0,
          duration: 0.5,
          ease: "back.out(1.4)",
          stagger: 0.08,
          delay: 0.3,
        },
      );

      // Scan-line pulse on the map container
      gsap.to(".wl-scanline", {
        scaleX: 1,
        duration: 2.5,
        ease: "power1.inOut",
        repeat: -1,
        yoyo: true,
        transformOrigin: "left",
      });
    },
    { scope: containerRef },
  );

  // Animate list items whenever data changes
  useEffect(() => {
    if (!data) return;
    gsap.fromTo(
      ".wl-row",
      { opacity: 0, x: -20 },
      { opacity: 1, x: 0, duration: 0.35, ease: "power2.out", stagger: 0.04 },
    );
  }, [data, activeFilter]);

  // ── Data fetch ─────────────────────────────────────────────────────
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = { mode };
      if (lat) params.lat = parseFloat(lat);
      if (lon) params.lon = parseFloat(lon);
      if (lat && lon) setMapCenter([parseFloat(lat), parseFloat(lon)]);
      const r = await axios.get(`${API}/api/osint/wireless`, {
        params,
        headers: { "x-api-key": KEY },
        timeout: 25000,
      });
      setData(r.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  }, [mode, lat, lon]);

  useEffect(() => {
    fetchData();
  }, []);

  // ── Derived data ───────────────────────────────────────────────────
  const wireless = data?.wireless || {};
  const celltowers = data?.celltowers || {};
  const networks = wireless.networks || [];
  const towers = celltowers.towers || [];
  const categories = wireless.categories || {};

  const filtered =
    activeFilter === "all"
      ? networks
      : networks.filter((n) => n.category === activeFilter);

  const kpis = [
    {
      label: "Redes",
      value: wireless.count ?? "—",
      color: "#00ffd1",
      icon: Wifi,
    },
    {
      label: "Torres",
      value: celltowers.count ?? "—",
      color: "#ff00ff",
      icon: Radio,
    },
    {
      label: "Cámaras",
      value: categories.camera ?? 0,
      color: "#ff0055",
      icon: Camera,
    },
    {
      label: "IoT",
      value: categories.iot ?? 0,
      color: "#facc15",
      icon: Smartphone,
    },
    {
      label: "Móviles",
      value: categories.mobile ?? 0,
      color: "#818cf8",
      icon: Signal,
    },
  ];

  const mapPoints = [
    ...filtered
      .filter((n) => n.lat && n.lon)
      .map((n) => ({
        lat: n.lat,
        lon: n.lon,
        color: (CATEGORY_CONFIG[n.category] || CATEGORY_CONFIG.unknown).color,
        label: n.ssid || n.bssid,
        type: "wifi",
        radius: 6,
      })),
    ...towers
      .filter((t) => t.lat && t.lon)
      .map((t) => ({
        lat: t.lat,
        lon: t.lon,
        color: RADIO_COLORS[t.radio] || "#64748b",
        label: `${t.radio} · MCC${t.mcc}`,
        type: "tower",
        radius: 9,
      })),
  ];

  // ── Styles ──────────────────────────────────────────────────────────
  const S = {
    page: {
      display: "flex",
      flexDirection: "column",
      height: "100%",
      background: "#080d14",
      color: "#e2e8f0",
      fontFamily: "'Space Mono', monospace",
      overflow: "hidden",
    },
    header: {
      padding: "16px 24px 12px",
      borderBottom: "1px solid rgba(0,255,209,0.15)",
      flexShrink: 0,
    },
    title: {
      fontSize: 13,
      fontWeight: 700,
      letterSpacing: ".2em",
      color: "#00ffd1",
      textTransform: "uppercase",
      margin: 0,
    },
    sub: {
      fontSize: 9,
      color: "#475569",
      letterSpacing: ".12em",
      marginTop: 3,
    },
    kpiRow: {
      display: "flex",
      gap: 12,
      padding: "12px 24px",
      flexShrink: 0,
      flexWrap: "wrap",
    },
    kpi: {
      flex: "0 0 auto",
      background: "rgba(0,255,209,0.05)",
      border: "1px solid rgba(0,255,209,0.15)",
      borderRadius: 4,
      padding: "8px 16px",
      minWidth: 80,
      textAlign: "center",
      cursor: "default",
    },
    body: { flex: 1, display: "flex", overflow: "hidden", gap: 0 },
    sidebar: {
      width: 300,
      borderRight: "1px solid rgba(0,255,209,0.1)",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      flexShrink: 0,
    },
    mapArea: { flex: 1, position: "relative", overflow: "hidden" },
    toolbar: {
      display: "flex",
      gap: 8,
      padding: "10px 16px",
      borderBottom: "1px solid rgba(0,255,209,0.1)",
      alignItems: "center",
      flexWrap: "wrap",
    },
    btn: (active) => ({
      padding: "4px 12px",
      borderRadius: 3,
      fontSize: 10,
      cursor: "pointer",
      border: `1px solid ${active ? "#00ffd1" : "rgba(0,255,209,0.2)"}`,
      background: active ? "rgba(0,255,209,0.1)" : "transparent",
      color: active ? "#00ffd1" : "#64748b",
      letterSpacing: ".08em",
      transition: "all .15s",
    }),
    input: {
      background: "rgba(255,255,255,0.04)",
      border: "1px solid rgba(0,255,209,0.15)",
      borderRadius: 3,
      color: "#94a3b8",
      padding: "4px 8px",
      fontSize: 10,
      width: 80,
      outline: "none",
      fontFamily: "'Space Mono', monospace",
    },
    list: { flex: 1, overflowY: "auto", padding: "8px 0" },
    row: {
      padding: "8px 16px",
      borderBottom: "1px solid rgba(255,255,255,0.04)",
      cursor: "default",
      transition: "background .15s",
      display: "flex",
      flexDirection: "column",
      gap: 3,
    },
    rowTop: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: 8,
    },
    badge: (color) => ({
      fontSize: 8,
      padding: "1px 6px",
      borderRadius: 2,
      background: `${color}22`,
      color,
      border: `1px solid ${color}44`,
      letterSpacing: ".06em",
      flexShrink: 0,
    }),
    bar: (pct, color) => ({
      height: 3,
      width: `${Math.min(pct, 100)}%`,
      background: color,
      borderRadius: 2,
      transition: "width .4s ease",
      marginTop: 2,
    }),
    scanline: {
      position: "absolute",
      top: 0,
      left: 0,
      right: 0,
      height: 2,
      background: "linear-gradient(90deg,transparent,#00ffd1,transparent)",
      opacity: 0.6,
      zIndex: 1000,
      transform: "scaleX(0)",
      transformOrigin: "left",
    },
  };

  const wigleConfigured = !wireless.error?.includes("WIGLE_API_KEY");
  const cellConfigured = !celltowers.error?.includes("OPENCELLID_API_KEY");

  return (
    <div ref={containerRef} style={S.page}>
      {/* Header */}
      <div style={S.header}>
        <p ref={titleRef} style={S.title}>
          📡 WIRELESS INTEL — OSINT PASIVO
        </p>
        <p style={S.sub}>WIGLE.NET · OPENCELLID · DISPOSITIVOS CERCANOS</p>
      </div>

      {/* KPI strip */}
      <div style={S.kpiRow} ref={kpiRef}>
        {kpis.map((k) => {
          const Icon = k.icon;
          return (
            <div
              key={k.label}
              className="wl-kpi"
              style={{ ...S.kpi, borderColor: `${k.color}33` }}
            >
              <Icon size={14} color={k.color} style={{ marginBottom: 4 }} />
              <div
                style={{
                  fontSize: 20,
                  fontWeight: 700,
                  color: k.color,
                  lineHeight: 1,
                }}
              >
                {k.value}
              </div>
              <div style={{ fontSize: 8, color: "#475569", marginTop: 3 }}>
                {k.label}
              </div>
            </div>
          );
        })}

        {/* Config warnings */}
        {!wigleConfigured && (
          <div
            className="wl-kpi"
            style={{
              ...S.kpi,
              borderColor: "#ff553344",
              background: "rgba(255,85,51,0.06)",
              textAlign: "left",
              minWidth: 200,
            }}
          >
            <div style={{ fontSize: 9, color: "#ff5533" }}>
              ⚠️ WIGLE_API_KEY no configurada
            </div>
            <div style={{ fontSize: 8, color: "#475569", marginTop: 2 }}>
              Registra en wigle.net → Account → API Token
            </div>
          </div>
        )}
        {!cellConfigured && (
          <div
            className="wl-kpi"
            style={{
              ...S.kpi,
              borderColor: "#ff553344",
              background: "rgba(255,85,51,0.06)",
              textAlign: "left",
              minWidth: 200,
            }}
          >
            <div style={{ fontSize: 9, color: "#ff5533" }}>
              ⚠️ OPENCELLID_API_KEY no configurada
            </div>
            <div style={{ fontSize: 8, color: "#475569", marginTop: 2 }}>
              Gratis en opencellid.org/downloads
            </div>
          </div>
        )}
      </div>

      {/* Body */}
      <div style={S.body}>
        {/* Sidebar — lista de dispositivos */}
        <div style={S.sidebar}>
          {/* Toolbar */}
          <div style={S.toolbar}>
            {/* Mode toggle */}
            <button
              style={S.btn(mode === "wifi")}
              onClick={() => setMode("wifi")}
            >
              WiFi
            </button>
            <button
              style={S.btn(mode === "bluetooth")}
              onClick={() => setMode("bluetooth")}
            >
              BT
            </button>
            <div style={{ flex: 1 }} />
            {/* Coords */}
            <input
              style={S.input}
              placeholder="lat"
              value={lat}
              onChange={(e) => setLat(e.target.value)}
            />
            <input
              style={S.input}
              placeholder="lon"
              value={lon}
              onChange={(e) => setLon(e.target.value)}
            />
            <button
              style={{
                ...S.btn(false),
                display: "flex",
                alignItems: "center",
                gap: 4,
              }}
              onClick={fetchData}
              disabled={loading}
            >
              <RefreshCw
                size={10}
                style={{
                  animation: loading ? "spin 1s linear infinite" : "none",
                }}
              />
              {loading ? "Escaneando..." : "Scan"}
            </button>
          </div>

          {/* Category filters */}
          <div
            style={{
              display: "flex",
              gap: 4,
              padding: "8px 16px",
              flexWrap: "wrap",
              borderBottom: "1px solid rgba(0,255,209,0.08)",
            }}
          >
            <button
              style={S.btn(activeFilter === "all")}
              onClick={() => setActiveFilter("all")}
            >
              Todo
            </button>
            {Object.entries(CATEGORY_CONFIG)
              .filter(([k]) => k !== "unknown")
              .map(([key, cfg]) => (
                <button
                  key={key}
                  style={{
                    ...S.btn(activeFilter === key),
                    borderColor: `${cfg.color}44`,
                    color: activeFilter === key ? cfg.color : "#475569",
                  }}
                  onClick={() => setActiveFilter(key)}
                >
                  {cfg.label.split("/")[0]}
                </button>
              ))}
          </div>

          {/* Error */}
          {error && (
            <div
              style={{ padding: "8px 16px", fontSize: 10, color: "#ef4444" }}
            >
              Error: {error}
            </div>
          )}

          {/* List */}
          <div style={S.list} ref={listRef}>
            {filtered.length === 0 && !loading && (
              <div
                style={{
                  padding: "20px 16px",
                  fontSize: 10,
                  color: "#334155",
                  textAlign: "center",
                }}
              >
                {wigleConfigured
                  ? "Sin resultados. Ajusta las coordenadas."
                  : "Configura WIGLE_API_KEY para ver dispositivos."}
              </div>
            )}
            {filtered.map((n, i) => {
              const cfg =
                CATEGORY_CONFIG[n.category] || CATEGORY_CONFIG.unknown;
              const Icon = cfg.icon;
              const strength = n.signal ? Math.min(100, 100 + n.signal) : 40;
              return (
                <div
                  key={i}
                  className="wl-row"
                  style={S.row}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.background =
                      "rgba(255,255,255,0.03)")
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.background = "transparent")
                  }
                >
                  <div style={S.rowTop}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                        minWidth: 0,
                      }}
                    >
                      <Icon
                        size={11}
                        color={cfg.color}
                        style={{ flexShrink: 0 }}
                      />
                      <span
                        style={{
                          fontSize: 10,
                          color: "#94a3b8",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {n.ssid || n.bssid || "(oculto)"}
                      </span>
                    </div>
                    <span style={S.badge(cfg.color)}>{cfg.label}</span>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      gap: 8,
                      fontSize: 8,
                      color: "#475569",
                    }}
                  >
                    <span>{n.encryption || "—"}</span>
                    {n.channel && <span>CH{n.channel}</span>}
                    {n.last_seen && (
                      <span style={{ marginLeft: "auto" }}>
                        {formatAge(n.last_seen)}
                      </span>
                    )}
                  </div>
                  {/* Signal bar */}
                  <div
                    style={{
                      background: "rgba(255,255,255,0.05)",
                      borderRadius: 2,
                      height: 3,
                      overflow: "hidden",
                    }}
                  >
                    <div style={S.bar(strength, cfg.color)} />
                  </div>
                </div>
              );
            })}

            {/* Cell towers section */}
            {towers.length > 0 && (
              <>
                <div
                  style={{
                    padding: "8px 16px 4px",
                    fontSize: 8,
                    color: "#334155",
                    letterSpacing: ".12em",
                    textTransform: "uppercase",
                    borderTop: "1px solid rgba(255,0,255,0.1)",
                    marginTop: 8,
                  }}
                >
                  Torres Celulares ({towers.length})
                </div>
                {towers.slice(0, 20).map((t, i) => {
                  const color = RADIO_COLORS[t.radio] || "#64748b";
                  return (
                    <div
                      key={`t${i}`}
                      className="wl-row"
                      style={S.row}
                      onMouseEnter={(e) =>
                        (e.currentTarget.style.background =
                          "rgba(255,255,255,0.03)")
                      }
                      onMouseLeave={(e) =>
                        (e.currentTarget.style.background = "transparent")
                      }
                    >
                      <div style={S.rowTop}>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 6,
                          }}
                        >
                          <Radio size={11} color={color} />
                          <span style={{ fontSize: 10, color: "#94a3b8" }}>
                            MCC{t.mcc} · MNC{t.mnc}
                          </span>
                        </div>
                        <span style={S.badge(color)}>{t.radio}</span>
                      </div>
                      <div style={{ fontSize: 8, color: "#475569" }}>
                        Cell {t.cellid} · LAC {t.lac} · {t.samples || "?"}{" "}
                        muestras
                      </div>
                    </div>
                  );
                })}
              </>
            )}
          </div>
        </div>

        {/* Map */}
        <div style={S.mapArea}>
          <div className="wl-scanline" style={S.scanline} />
          <MapContainer
            center={mapCenter}
            zoom={14}
            style={{ height: "100%", width: "100%", background: "#0a0f1a" }}
            zoomControl={true}
          >
            <LayersControl position="topright">
              <LayersControl.BaseLayer checked name="CyberMap">
                <TileLayer
                  url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                  attribution="&copy; CartoDB"
                  maxZoom={19}
                />
              </LayersControl.BaseLayer>
              <LayersControl.BaseLayer name="Satélite">
                <TileLayer
                  url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                  attribution="Esri"
                  maxZoom={19}
                />
              </LayersControl.BaseLayer>
            </LayersControl>

            {mapPoints.map((p, i) => (
              <CircleMarker
                key={i}
                center={[p.lat, p.lon]}
                radius={p.radius}
                pathOptions={{
                  color: p.color,
                  fillColor: p.color,
                  fillOpacity: 0.6,
                  weight: 1.5,
                }}
              >
                <Tooltip sticky>
                  <span style={{ fontSize: 11, fontFamily: "monospace" }}>
                    {p.type === "tower" ? "📡 " : "📶 "}
                    {p.label}
                  </span>
                </Tooltip>
              </CircleMarker>
            ))}
          </MapContainer>

          {/* Bottom legend */}
          <div
            style={{
              position: "absolute",
              bottom: 12,
              left: 12,
              zIndex: 1000,
              display: "flex",
              gap: 8,
              flexWrap: "wrap",
            }}
          >
            {Object.entries(CATEGORY_CONFIG)
              .filter(([k]) => k !== "unknown")
              .map(([key, cfg]) => (
                <div
                  key={key}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                    background: "rgba(8,13,20,0.85)",
                    border: `1px solid ${cfg.color}44`,
                    borderRadius: 3,
                    padding: "3px 8px",
                  }}
                >
                  <div
                    style={{
                      width: 7,
                      height: 7,
                      borderRadius: "50%",
                      background: cfg.color,
                    }}
                  />
                  <span
                    style={{
                      fontSize: 8,
                      color: "#94a3b8",
                      fontFamily: "Space Mono, monospace",
                    }}
                  >
                    {cfg.label}
                  </span>
                </div>
              ))}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        .wl-row:hover { background: rgba(0,255,209,0.03) !important; }
        .leaflet-container { background: #080d14 !important; }
        .leaflet-control-zoom a { background: #0d1520 !important; color: #00ffd1 !important; border-color: rgba(0,255,209,0.2) !important; }
      `}</style>
    </div>
  );
}
