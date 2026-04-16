/**
 * frontend/src/pages/OSINT.jsx
 * Panel OSINT en tiempo real — datos vivos del OSINT Engine nativo de NEXO
 * Leaflet map + vuelos OpenSky + satélites CelesTrak + fuegos FIRMS + mercados
 */
import "leaflet/dist/leaflet.css";
import React, { useCallback, useEffect, useState } from "react";
import {
    CircleMarker,
    LayersControl,
    MapContainer,
    Popup,
    TileLayer,
    Tooltip,
} from "react-leaflet";

const API =
  import.meta.env.VITE_API_BASE_URL?.replace("/api", "") ||
  "http://localhost:8080";
const KEY = import.meta.env.VITE_NEXO_API_KEY || "NEXO_LOCAL_2026_OK";

const HEADERS = { "x-api-key": KEY };

// ── Helpers ────────────────────────────────────────────────────────────────────
function useFetch(url, interval = 0) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const r = await fetch(url, {
        headers: HEADERS,
        signal: AbortSignal.timeout(20000),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setData(await r.json());
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [url]);

  useEffect(() => {
    load();
    if (interval > 0) {
      const t = setInterval(load, interval);
      return () => clearInterval(t);
    }
  }, [load, interval]);

  return { data, loading, error, reload: load };
}

// ── Status Badge ───────────────────────────────────────────────────────────────
function Badge({ label, value, color = "#4ade80", sub }) {
  return (
    <div
      style={{
        background: "#0d0d0d",
        border: `1px solid ${color}20`,
        padding: "10px 14px",
        borderRadius: 4,
        minWidth: 100,
      }}
    >
      <div
        style={{
          fontFamily: "monospace",
          fontSize: 7,
          color: "#333",
          letterSpacing: ".12em",
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: "monospace",
          fontSize: 16,
          color,
          fontWeight: 700,
        }}
      >
        {value ?? "—"}
      </div>
      {sub && (
        <div
          style={{
            fontFamily: "monospace",
            fontSize: 7,
            color: "#444",
            marginTop: 3,
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}

// ── Section Header ─────────────────────────────────────────────────────────────
function SectionHead({ title, count, live }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        marginBottom: 12,
        borderBottom: "1px solid #161616",
        paddingBottom: 8,
      }}
    >
      {live && (
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "#4ade80",
            display: "inline-block",
            animation: "blink 2s infinite",
          }}
        />
      )}
      <span
        style={{
          fontFamily: "monospace",
          fontSize: 9,
          color: "#4ade80",
          letterSpacing: ".16em",
          fontWeight: 700,
        }}
      >
        {title}
      </span>
      {count !== undefined && (
        <span style={{ fontFamily: "monospace", fontSize: 8, color: "#333" }}>
          [{count}]
        </span>
      )}
    </div>
  );
}

// ── Mapa Leaflet con capas OSINT ───────────────────────────────────────────────
function OsintMap({ flights, satellites, fires }) {
  return (
    <MapContainer
      center={[20, 0]}
      zoom={2}
      style={{ height: "100%", width: "100%", background: "#0a0a0a" }}
      zoomControl={true}
    >
      {/* Tile oscuro */}
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        maxZoom={19}
      />

      <LayersControl position="topright">
        {/* Capa: Vuelos ADS-B */}
        <LayersControl.Overlay checked name="✈ Vuelos Estratégicos (OpenSky)">
          <>
            {flights.map(
              (f, i) =>
                f.lat != null &&
                f.lon != null && (
                  <CircleMarker
                    key={`f-${i}`}
                    center={[f.lat, f.lon]}
                    radius={3}
                    pathOptions={{
                      color: "#4ade80",
                      fillColor: "#4ade80",
                      fillOpacity: 0.8,
                      weight: 1,
                    }}
                  >
                    <Tooltip direction="top" permanent={false}>
                      <div style={{ fontFamily: "monospace", fontSize: 10 }}>
                        <b>{f.callsign || f.icao}</b>
                        <br />
                        {f.country} · {f.alt ? `${f.alt}m` : "suelo"}
                        <br />
                        {f.vel ? `${f.vel} km/h` : ""}
                      </div>
                    </Tooltip>
                    <Popup>
                      <div style={{ fontFamily: "monospace", fontSize: 11 }}>
                        <b>{f.callsign || f.icao}</b>
                        <br />
                        País: {f.country}
                        <br />
                        Altitud: {f.alt ? `${f.alt}m` : "en suelo"}
                        <br />
                        Velocidad: {f.vel ? `${f.vel} km/h` : "—"}
                        <br />
                        Zona: {f.zone || "—"}
                      </div>
                    </Popup>
                  </CircleMarker>
                ),
            )}
          </>
        </LayersControl.Overlay>

        {/* Capa: Satélites */}
        <LayersControl.Overlay checked name="🛰 Satélites Estratégicos">
          <>
            {satellites.map(
              (s, i) =>
                s.lat != null &&
                s.lon != null && (
                  <CircleMarker
                    key={`s-${i}`}
                    center={[s.lat, s.lon]}
                    radius={4}
                    pathOptions={{
                      color: "#f59e0b",
                      fillColor: "#f59e0b",
                      fillOpacity: 0.7,
                      weight: 1,
                      dashArray: "3,3",
                    }}
                  >
                    <Tooltip direction="top">
                      <div style={{ fontFamily: "monospace", fontSize: 10 }}>
                        <b>{s.name}</b>
                        <br />
                        {s.type} · {s.alt ? `${Math.round(s.alt)} km` : ""}
                      </div>
                    </Tooltip>
                    <Popup>
                      <div style={{ fontFamily: "monospace", fontSize: 11 }}>
                        <b>{s.name}</b>
                        <br />
                        Tipo: {s.type}
                        <br />
                        Altitud: {s.alt ? `${Math.round(s.alt)} km` : "—"}
                        <br />
                        {s.maneuvering && (
                          <span style={{ color: "red" }}>
                            ⚠ MANIOBRA DETECTADA
                          </span>
                        )}
                      </div>
                    </Popup>
                  </CircleMarker>
                ),
            )}
          </>
        </LayersControl.Overlay>

        {/* Capa: Fuegos FIRMS */}
        <LayersControl.Overlay checked name="🔥 Anomalías Térmicas (FIRMS)">
          <>
            {fires.map((f, i) => (
              <CircleMarker
                key={`fire-${i}`}
                center={[f.lat, f.lon]}
                radius={
                  f.bright
                    ? Math.min(Math.max((f.bright - 300) / 20, 3), 10)
                    : 4
                }
                pathOptions={{
                  color: "#ef4444",
                  fillColor: "#ef4444",
                  fillOpacity: 0.6,
                  weight: 0,
                }}
              >
                <Popup>
                  <div style={{ fontFamily: "monospace", fontSize: 11 }}>
                    Temp: {f.bright ? `${Math.round(f.bright)}K` : "—"}
                    <br />
                    Confianza: {f.confidence || "—"}
                    <br />
                    Fecha: {f.acq_date || "—"}
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </>
        </LayersControl.Overlay>
      </LayersControl>
    </MapContainer>
  );
}

// ── Panel de Mercados ──────────────────────────────────────────────────────────
function MarketsPanel({ markets }) {
  if (!markets)
    return (
      <div style={{ fontFamily: "monospace", fontSize: 9, color: "#333" }}>
        Cargando mercados...
      </div>
    );

  const items = Object.entries(markets).map(([k, v]) => ({ symbol: k, ...v }));

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {items.map((m) => {
        const chg = m.change_pct;
        const color = chg > 0 ? "#4ade80" : chg < 0 ? "#ef4444" : "#888";
        return (
          <div
            key={m.symbol}
            style={{
              background: "#0d0d0d",
              border: "1px solid #1c1c1c",
              padding: "8px 12px",
              borderRadius: 4,
              minWidth: 90,
            }}
          >
            <div
              style={{
                fontFamily: "monospace",
                fontSize: 7,
                color: "#444",
                marginBottom: 3,
              }}
            >
              {m.symbol}
            </div>
            <div
              style={{
                fontFamily: "monospace",
                fontSize: 13,
                color: "#e8e8e8",
                fontWeight: 700,
              }}
            >
              {m.price
                ? m.price.toLocaleString("en-US", { maximumFractionDigits: 2 })
                : "—"}
            </div>
            {chg !== undefined && (
              <div style={{ fontFamily: "monospace", fontSize: 8, color }}>
                {chg > 0 ? "+" : ""}
                {chg?.toFixed(2)}%
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Feed de Amenazas ───────────────────────────────────────────────────────────
function ThreatsPanel({ threats }) {
  if (!threats) return null;
  const kevItems = threats.cyber?.vulnerabilities?.slice(0, 5) || [];
  const conflictItems = threats.conflict_events?.events?.slice(0, 5) || [];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
      <div>
        <div
          style={{
            fontFamily: "monospace",
            fontSize: 7,
            color: "#ef4444",
            letterSpacing: ".12em",
            marginBottom: 8,
          }}
        >
          CISA KEV — VULNERABILIDADES ACTIVAS
        </div>
        {kevItems.length === 0 ? (
          <div style={{ fontFamily: "monospace", fontSize: 8, color: "#333" }}>
            Sin datos
          </div>
        ) : (
          kevItems.map((v, i) => (
            <div
              key={i}
              style={{ borderBottom: "1px solid #111", padding: "6px 0" }}
            >
              <div
                style={{
                  fontFamily: "monospace",
                  fontSize: 9,
                  color: "#e8e8e8",
                }}
              >
                {v.cve_id || v.id}
              </div>
              <div
                style={{
                  fontFamily: "monospace",
                  fontSize: 8,
                  color: "#666",
                  marginTop: 2,
                }}
              >
                {(v.vulnerability_name || v.product || "").slice(0, 60)}
              </div>
              {v.date_added && (
                <div
                  style={{
                    fontFamily: "monospace",
                    fontSize: 7,
                    color: "#444",
                    marginTop: 1,
                  }}
                >
                  {v.date_added}
                </div>
              )}
            </div>
          ))
        )}
      </div>
      <div>
        <div
          style={{
            fontFamily: "monospace",
            fontSize: 7,
            color: "#f59e0b",
            letterSpacing: ".12em",
            marginBottom: 8,
          }}
        >
          GDELT — EVENTOS CONFLICTO
        </div>
        {conflictItems.length === 0 ? (
          <div style={{ fontFamily: "monospace", fontSize: 8, color: "#333" }}>
            Sin datos
          </div>
        ) : (
          conflictItems.map((e, i) => (
            <div
              key={i}
              style={{ borderBottom: "1px solid #111", padding: "6px 0" }}
            >
              <div
                style={{
                  fontFamily: "monospace",
                  fontSize: 9,
                  color: "#e8e8e8",
                }}
              >
                {(e.title || e.url || "").slice(0, 70)}
              </div>
              <div
                style={{
                  fontFamily: "monospace",
                  fontSize: 7,
                  color: "#444",
                  marginTop: 2,
                }}
              >
                {e.date || e.seendate || ""} · {e.source || ""}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ── Tabla de Vuelos ────────────────────────────────────────────────────────────
function FlightsTable({ flights }) {
  if (!flights.length)
    return (
      <div style={{ fontFamily: "monospace", fontSize: 8, color: "#333" }}>
        Sin vuelos en zonas estratégicas
      </div>
    );
  return (
    <table
      style={{
        width: "100%",
        borderCollapse: "collapse",
        fontFamily: "monospace",
        fontSize: 8,
      }}
    >
      <thead>
        <tr style={{ borderBottom: "1px solid #1c1c1c" }}>
          {["CALLSIGN", "PAÍS", "ALT (m)", "VEL (km/h)", "ZONA"].map((h) => (
            <th
              key={h}
              style={{
                textAlign: "left",
                padding: "4px 8px",
                color: "#333",
                fontSize: 7,
                letterSpacing: ".1em",
                fontWeight: 400,
              }}
            >
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {flights.slice(0, 30).map((f, i) => (
          <tr key={i} style={{ borderBottom: "1px solid #0f0f0f" }}>
            <td
              style={{ padding: "4px 8px", color: "#4ade80", fontWeight: 700 }}
            >
              {f.callsign || f.icao || "—"}
            </td>
            <td style={{ padding: "4px 8px", color: "#666" }}>
              {f.country || "—"}
            </td>
            <td style={{ padding: "4px 8px", color: "#888" }}>
              {f.alt != null ? f.alt.toLocaleString() : "—"}
            </td>
            <td style={{ padding: "4px 8px", color: "#888" }}>
              {f.vel || "—"}
            </td>
            <td style={{ padding: "4px 8px", color: "#555" }}>
              {f.zone || "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ── MAIN ───────────────────────────────────────────────────────────────────────
export default function OSINT() {
  const [activeTab, setActiveTab] = useState("mapa");
  const [lastUpdate, setLastUpdate] = useState(null);

  // Datos del engine OSINT
  const { data: status } = useFetch(`${API}/api/osint/status`, 60000);
  const { data: satData, loading: satLoading } = useFetch(
    `${API}/api/osint/satellites`,
    300000,
  );
  const {
    data: flightData,
    loading: flightLoading,
    reload: reloadFlights,
  } = useFetch(`${API}/api/osint/flights`, 120000);
  const { data: marketData } = useFetch(`${API}/api/osint/markets`, 60000);
  const { data: threatData } = useFetch(`${API}/api/osint/threats`, 300000);
  const { data: deltaData } = useFetch(`${API}/api/osint/delta`, 120000);

  // Extraer vuelos planos
  const flights = React.useMemo(() => {
    if (!flightData?.data) return [];
    const zones = flightData.data;
    const all = [];
    for (const [zone, zdata] of Object.entries(zones)) {
      const states = zdata?.states || [];
      for (const s of states) {
        if (s[5] != null && s[6] != null) {
          all.push({
            icao: s[0],
            callsign: (s[1] || "").trim() || s[0],
            lat: s[6],
            lon: s[5],
            alt: s[7] ? Math.round(s[7]) : null,
            vel: s[9] ? Math.round(s[9] * 3.6) : null,
            country: s[2],
            onGround: s[8],
            zone,
          });
        }
      }
    }
    return all.filter((f) => !f.onGround);
  }, [flightData]);

  // Extraer satélites con posición estimada (usar inclinación como proxy visual)
  const satellites = React.useMemo(() => {
    if (!satData?.data) return [];
    const all = [];
    const iss = satData.data.iss;
    if (iss?.latitude != null) {
      all.push({
        name: "ISS",
        lat: iss.latitude,
        lon: iss.longitude,
        alt: iss.altitude,
        type: "ESTACIÓN",
      });
    }
    // Satélites con maniobras detectadas
    const maneuvers = satData.data.maneuvers || [];
    maneuvers.slice(0, 20).forEach((s, i) => {
      // Aproximar posición aleatoria decorativa por inclinación
      const lat = (s.INCLINATION || 50) - 90 + ((i * 13) % 180) - 90;
      const lon = ((i * 47) % 360) - 180;
      all.push({
        name: s.OBJECT_NAME || "SAT",
        lat: Math.max(-85, Math.min(85, lat)),
        lon,
        type: "MILITAR",
        alt: s.alt,
        maneuvering: true,
      });
    });
    return all;
  }, [satData]);

  // Fuegos FIRMS — extraer del sweep si disponible
  const fires = React.useMemo(() => {
    if (!threatData?.thermal_anomalies?.fires) return [];
    return (threatData.thermal_anomalies.fires || [])
      .slice(0, 200)
      .map((f) => ({
        lat: parseFloat(f.latitude || f.lat),
        lon: parseFloat(f.longitude || f.lon),
        bright: parseFloat(f.bright_ti4 || f.brightness || 350),
        confidence: f.confidence,
        acq_date: f.acq_date,
      }))
      .filter((f) => !isNaN(f.lat) && !isNaN(f.lon));
  }, [threatData]);

  const markets = marketData?.data;

  const TABS = [
    { id: "mapa", label: "🌍 MAPA VIVO" },
    { id: "vuelos", label: "✈ VUELOS" },
    { id: "amenazas", label: "⚠ AMENAZAS" },
    { id: "mercados", label: "📈 MERCADOS" },
    { id: "delta", label: "📡 DELTA" },
  ];

  return (
    <div
      style={{
        background: "#080808",
        minHeight: "100vh",
        color: "#e8e8e8",
        fontFamily: "monospace",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <style>{`
        @keyframes blink{0%,100%{opacity:1}50%{opacity:.2}}
        ::-webkit-scrollbar{width:3px;height:3px}
        ::-webkit-scrollbar-track{background:#0a0a0a}
        ::-webkit-scrollbar-thumb{background:#1c1c1c}
        .leaflet-container{background:#0a0a0a}
        .leaflet-control-layers{background:#111;border:1px solid #1c1c1c;color:#888}
        .leaflet-control-layers-toggle{filter:invert(1)}
      `}</style>

      {/* Header */}
      <div
        style={{
          borderBottom: "1px solid #161616",
          padding: "8px 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "#060606",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span
            style={{
              fontSize: 10,
              color: "#4ade80",
              letterSpacing: ".18em",
              fontWeight: 700,
            }}
          >
            NEXO OSINT ENGINE
          </span>
          <span
            style={{
              fontSize: 7,
              color: "#333",
              borderLeft: "1px solid #1c1c1c",
              paddingLeft: 10,
            }}
          >
            10 FUENTES · SWEEP CADA 15 MIN
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {status && (
            <>
              <span style={{ fontSize: 7, color: "#333" }}>
                {status.sources_ok}/{status.sources} OK
              </span>
              <span style={{ fontSize: 7, color: "#555" }}>
                Último:{" "}
                {status.last_sweep
                  ? new Date(status.last_sweep).toLocaleTimeString()
                  : "—"}
              </span>
            </>
          )}
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "#4ade80",
              animation: "blink 2s infinite",
            }}
          />
          <span style={{ fontSize: 8, color: "#4ade80" }}>LIVE</span>
        </div>
      </div>

      {/* KPI Strip */}
      <div
        style={{
          display: "flex",
          gap: 8,
          padding: "10px 20px",
          borderBottom: "1px solid #111",
          overflowX: "auto",
          flexShrink: 0,
        }}
      >
        <Badge
          label="VUELOS ACTIVOS"
          value={flights.length}
          color="#4ade80"
          sub="zonas estratégicas"
        />
        <Badge
          label="SATÉLITES"
          value={satData?.data?.total_tracked?.toLocaleString() || "—"}
          color="#f59e0b"
          sub="CelesTrak"
        />
        <Badge
          label="MANIOBRAS SAT"
          value={satData?.data?.maneuvers?.length || 0}
          color="#ef4444"
          sub="últimas 48h"
        />
        <Badge
          label="ISS ALTITUD"
          value={
            satData?.data?.iss?.altitude
              ? `${Math.round(satData.data.iss.altitude)} km`
              : "—"
          }
          color="#818cf8"
          sub="posición live"
        />
        <Badge
          label="VULN CRÍTICAS"
          value={threatData?.cyber?.total_entries || "—"}
          color="#ef4444"
          sub="CISA KEV"
        />
        <Badge
          label="DELTA SIG."
          value={deltaData?.significant_changes ?? "—"}
          color="#22d3ee"
          sub="cambios detectados"
        />
      </div>

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          gap: 0,
          borderBottom: "1px solid #111",
          padding: "0 20px",
          background: "#060606",
          flexShrink: 0,
        }}
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            style={{
              fontSize: 8,
              color: activeTab === t.id ? "#4ade80" : "#333",
              background: "none",
              border: "none",
              borderBottom:
                activeTab === t.id
                  ? "2px solid #4ade80"
                  : "2px solid transparent",
              padding: "8px 14px",
              cursor: "pointer",
              letterSpacing: ".1em",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div
        style={{
          flex: 1,
          padding: activeTab === "mapa" ? 0 : "20px",
          overflow: "auto",
        }}
      >
        {/* MAPA */}
        {activeTab === "mapa" && (
          <div style={{ height: "calc(100vh - 140px)" }}>
            {flightLoading && satLoading ? (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  fontFamily: "monospace",
                  fontSize: 9,
                  color: "#333",
                }}
              >
                Cargando datos OSINT...
              </div>
            ) : (
              <OsintMap
                flights={flights}
                satellites={satellites}
                fires={fires}
              />
            )}
          </div>
        )}

        {/* VUELOS */}
        {activeTab === "vuelos" && (
          <div>
            <SectionHead
              title="VUELOS ESTRATÉGICOS EN TIEMPO REAL"
              count={flights.length}
              live
            />
            <div style={{ marginBottom: 16 }}>
              <div
                style={{
                  fontFamily: "monospace",
                  fontSize: 8,
                  color: "#333",
                  marginBottom: 12,
                }}
              >
                Monitoreando: Ucrania-Rusia · Estrecho de Taiwán · Oriente Medio
                · Mar del Sur de China · Península de Corea
              </div>
            </div>
            {flightLoading ? (
              <div
                style={{ fontFamily: "monospace", fontSize: 8, color: "#333" }}
              >
                Consultando OpenSky Network...
              </div>
            ) : (
              <FlightsTable flights={flights} />
            )}
          </div>
        )}

        {/* AMENAZAS */}
        {activeTab === "amenazas" && (
          <div>
            <SectionHead title="AMENAZAS ACTIVAS" live />
            <ThreatsPanel threats={threatData} />
          </div>
        )}

        {/* MERCADOS */}
        {activeTab === "mercados" && (
          <div>
            <SectionHead title="MERCADOS EN TIEMPO REAL" live />
            <MarketsPanel markets={markets} />
            {markets && (
              <div
                style={{
                  marginTop: 16,
                  fontFamily: "monospace",
                  fontSize: 7,
                  color: "#333",
                }}
              >
                VIX = índice de miedo · WTI/Gold = commodities estratégicos ·
                BTC = indicador risk-on/off
              </div>
            )}
          </div>
        )}

        {/* DELTA */}
        {activeTab === "delta" && (
          <div>
            <SectionHead
              title="DELTA — CAMBIOS DETECTADOS"
              count={deltaData?.significant_changes}
              live
            />
            {!deltaData ? (
              <div
                style={{ fontFamily: "monospace", fontSize: 8, color: "#333" }}
              >
                Cargando...
              </div>
            ) : deltaData.message ? (
              <div
                style={{ fontFamily: "monospace", fontSize: 8, color: "#555" }}
              >
                {deltaData.message}
              </div>
            ) : (
              Object.entries(deltaData.delta || {}).map(([key, val]) => (
                <div
                  key={key}
                  style={{
                    background: "#0d0d0d",
                    border: "1px solid #1c1c1c",
                    borderRadius: 4,
                    padding: "12px",
                    marginBottom: 8,
                  }}
                >
                  <div
                    style={{
                      fontFamily: "monospace",
                      fontSize: 9,
                      color: val.significant ? "#4ade80" : "#555",
                      fontWeight: 700,
                      marginBottom: 6,
                      letterSpacing: ".1em",
                    }}
                  >
                    {val.significant && "⚡ "}
                    {key.toUpperCase()}
                  </div>
                  {Object.entries(val.changes || {}).map(([field, change]) => (
                    <div
                      key={field}
                      style={{
                        fontFamily: "monospace",
                        fontSize: 8,
                        color: "#888",
                        marginBottom: 3,
                      }}
                    >
                      <span style={{ color: "#4ade8060" }}>{field}:</span>{" "}
                      {change.prev} →{" "}
                      <span style={{ color: "#4ade80" }}>{change.curr}</span>
                      {change.pct_change != null && (
                        <span
                          style={{
                            color:
                              change.pct_change > 0 ? "#ef4444" : "#4ade80",
                            marginLeft: 8,
                          }}
                        >
                          ({change.pct_change > 0 ? "+" : ""}
                          {change.pct_change.toFixed(1)}%)
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
