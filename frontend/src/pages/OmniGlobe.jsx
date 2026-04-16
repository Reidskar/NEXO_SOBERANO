import {
    FileText,
    Minus,
    Plane,
    Plus,
    RefreshCw,
    ShieldAlert,
    Wifi,
    WifiOff
} from "lucide-react";
import {
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
} from "react";
import { renderToString } from "react-dom/server";
import Globe from "react-globe.gl";
import * as satellite from "satellite.js";
import * as THREE from "three";
import DestructionOverlay from "../components/DestructionOverlay";
import EventTimeline from "../components/EventTimeline";
import EvidenceViewer from "../components/EvidenceViewer";
import GlobeMaplibre from "../components/GlobeMaplibre";
import OmniGlobeHUD from "../components/OmniGlobeHUD";
import {
    CITY_COLORS,
    CITY_RING_CONFIG,
    COUNTRY_NAMES,
    STRATEGIC_CITIES,
    getNearestCity,
} from "../data/strategicCities";
import {
    TACTICAL_AA_SYSTEMS,
    TACTICAL_BASES,
    TACTICAL_DRONES_HELICOPTERS,
    TACTICAL_EXECUTIVE_JETS,
    TACTICAL_FLIGHTS,
    TACTICAL_GOALS,
    TACTICAL_INFRASTRUCTURE,
    TACTICAL_MILITARY_AIRCRAFT,
    TACTICAL_MISSILES,
    TACTICAL_OIL_TANKERS,
    TACTICAL_SHIPS,
    TACTICAL_STRIKES,
    TACTICAL_WARSHIPS,
    create3DAssetNode,
    getInterpolatedPosition,
    update3DAssetNode,
} from "../data/tacticalAssets";
import { useAISStream } from "../hooks/useAISStream";
import { useGlobeAI } from "../hooks/useGlobeAI";
import { useOsintLive } from "../hooks/useOsintLive";
import { usePolymarket } from "../hooks/usePolymarket";
import { useSatellites } from "../hooks/useSatellites";

// ─── Minimalist Political Map Textures ─────────────────────────────────────────
// Using a black/transparent base to let the JSON borders shine
const GLOBE_IMG_URL = null;
const GLOBE_BUMP_URL = null;
const GLOBE_SKY_URL = null;

// ─── Custom atmosphere material for glow effect ────────────────────────────
const buildAtmosphereMaterial = () => {
  const mat = new THREE.MeshLambertMaterial({
    color: new THREE.Color(0x0033aa),
    transparent: true,
    opacity: 0.12,
    side: THREE.FrontSide,
  });
  return mat;
};

const OmniGlobe = () => {
  const globeEl = useRef(); // kept for future use
  const maplibreRef = useRef();
  const containerRef = useRef();
  const [countries, setCountries] = useState({ features: [] });
  const [satTile, setSatTile] = useState(false);
  const [timelineDay, setTimelineDay] = useState(-30);
  const [activeRings, setActiveRings] = useState([]);
  const [activeObjects, setActiveObjects] = useState([]);
  const [activeArcs, setActiveArcs] = useState([]);
  const [activePaths, setActivePaths] = useState([]);
  const [activeLabels, setActiveLabels] = useState([]);
  const [mapHtmlElements, setMapHtmlElements] = useState([]);
  const [globeSize, setGlobeSize] = useState({ w: 800, h: 600 });
  const [destructionEvent, setDestructionEvent] = useState(null);
  const [hideTimeline, setHideTimeline] = useState(false);

  // AIS live data
  const [aisApiKey] = useState(import.meta.env.VITE_AIS_API_KEY || "");
  const { vessels: liveVessels, connected: aisConnected } =
    useAISStream(aisApiKey);

  // Live OSINT: GDELT conflicts + FIRMS thermal + OpenSky flights + Drive docs
  const {
    conflictMarkers,
    thermalMarkers,
    liveFlights,
    driveMarkers,
    lastSweep,
    loading: osintLoading,
    refetch,
  } = useOsintLive(90000);

  // Contexto OSINT para la IA — ciudades más calientes + conteos
  const osintContext = useMemo(() => {
    const hotCities = conflictMarkers
      .filter((m) => m.severity === "critical")
      .map((m) => {
        const city = getNearestCity(m.lat, m.lng);
        return city ? city.name : null;
      })
      .filter(Boolean)
      .filter((v, i, a) => a.indexOf(v) === i) // unique
      .slice(0, 5);
    return {
      conflictCount: conflictMarkers.length,
      thermalCount: thermalMarkers.length,
      hotCities,
    };
  }, [conflictMarkers, thermalMarkers]);

  // AI tactical alerts
  const {
    alerts: aiAlerts,
    connected: aiConnected,
    wsMode,
    pushAlert,
  } = useGlobeAI(true, osintContext);

  // Real-time Satellite TLE Propagation (CelesTrak)
  const { satellites } = useSatellites(true);

  // ── Phase 12+13: OSINT Simulation State ────────────────────────────────
  const [activeSimulations, setActiveSimulations] = useState([]); // Descending missiles
  const [impactMarkers, setImpactMarkers] = useState([]); // Persistent evidence pins
  const [evidenceEvent, setEvidenceEvent] = useState(null);
  const simAltRef = useRef({});

  // Polymarket conflict odds
  const { markets: polyMarkets } = usePolymarket(true);

  // Intercept OSINT TACTICAL_SIMULATION events from WebSocket
  // → Trigger inteligente: vuela al punto + DestructionOverlay
  useEffect(() => {
    const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8080";
    const WS_URL = API_BASE.replace(/^http/, "ws") + "/ws/alerts/demo";
    const ws = new WebSocket(WS_URL);
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (
          data.tipo === "TACTICAL_SIMULATION" &&
          data.lat != null &&
          data.lng != null
        ) {
          const id = `sim-${Date.now()}`;
          simAltRef.current[id] = 1.5;
          setActiveSimulations((prev) => [...prev, { ...data, _simId: id }]);
          // Trigger inteligente: volar al evento y mostrar overal
          if (maplibreRef.current?.flyToEvent) {
            maplibreRef.current.flyToEvent(data.lat, data.lng, 15);
          }
          // DestructionOverlay con delay de 2.2s (tiempo del flyTo al nivel de calle)
          setTimeout(() => {
            setDestructionEvent({
              ...data,
              id,
              timestamp: new Date().toISOString(),
            });
          }, 2200);
        }
      } catch (_) {}
    };
    return () => ws.close();
  }, []);

  // Animate descending missiles — only runs when there are active simulations
  const activeSimRef = useRef(activeSimulations);
  useEffect(() => {
    activeSimRef.current = activeSimulations;
  }, [activeSimulations]);
  useEffect(() => {
    if (activeSimulations.length === 0) return;
    const interval = setInterval(() => {
      setActiveSimulations((prev) => {
        if (prev.length === 0) {
          clearInterval(interval);
          return prev;
        }
        const remaining = [];
        const impacts = [];
        prev.forEach((sim) => {
          const currentAlt = (simAltRef.current[sim._simId] ?? 1.5) - 0.02;
          simAltRef.current[sim._simId] = currentAlt;
          if (currentAlt <= 0) {
            impacts.push({
              ...sim,
              alt: 0,
              timestamp: new Date().toISOString(),
            });
          } else {
            remaining.push({ ...sim, alt: currentAlt });
          }
        });

        // ── Phase 13.2: RedAlert - Warning Zones for Incoming Missiles ────────
        const warningRings = remaining.map((sim) => {
          const progress = 1.0 - simAltRef.current[sim._simId] / 1.5; // 0 at start, 1 at impact
          return {
            lat: sim.lat,
            lng: sim.lng,
            maxR: 1.2,
            propagationSpeed: 0.5 + progress * 4.0, // Precess quicker
            repeatPeriod: 1000 - progress * 800, // Pulse faster
            color:
              progress > 0.8
                ? "rgba(255, 0, 0, 0.95)"
                : "rgba(255, 80, 0, 0.65)",
            _incoming: true,
            _simId: sim._simId,
          };
        });

        if (impacts.length > 0) {
          // Final impact ring (Slow, clean, persistent)
          setActiveRings((prev) => [
            ...prev.filter((r) => !impacts.some((i) => i._simId === r._simId)), // Remove active warnings for THIS impact
            ...impacts.map((e) => ({
              lat: e.lat,
              lng: e.lng,
              maxR: 0.8,
              propagationSpeed: 0.4,
              repeatPeriod: 1500,
              color: "rgba(239,68,68,0.7)",
            })),
          ]);
          // Ballistic arc...
          setActiveArcs((prev) => [
            ...prev,
            ...impacts.map((e) => ({
              startLat: e.lat + (Math.random() > 0.5 ? 8 : -8),
              startLng: e.lng + (Math.random() > 0.5 ? 12 : -12),
              endLat: e.lat,
              endLng: e.lng,
              color: "rgba(239,68,68,0.9)",
              _type: "missile_arc",
            })),
          ]);
          // Evidence pins
          setImpactMarkers((prev) => [
            ...prev,
            ...impacts.map((e) => ({ ...e, id: e._simId })),
          ]);
        }

        // Always update active warnings for the remaining missiles
        setActiveRings((prev) => [
          ...prev.filter(
            (r) => !r._incoming || remaining.some((s) => s._simId === r._simId),
          ),
          ...warningRings,
        ]);

        return remaining;
      });
    }, 100);
    return () => clearInterval(interval);
  }, [activeSimulations.length > 0]);

  // Responsive globe size — reads container dimensions
  useEffect(() => {
    const measure = () => {
      if (containerRef.current) {
        setGlobeSize({
          w: containerRef.current.clientWidth,
          h: containerRef.current.clientHeight,
        });
      }
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  // ── Phase 13: Clean Dot Markers ──────────────────────────────────────────
  const impactHtmlElements = useMemo(() => {
    return (impactMarkers || []).map((m) => ({
      ...m,
      html: `
        <div style="cursor: pointer; transform: translate(-50%, -50%);" title="${m.target || "Impacto"}">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="6" fill="#ef4444" fill-opacity="0.2" />
            <circle cx="12" cy="12" r="3" fill="#ef4444" stroke="white" stroke-width="1.5" />
            <path d="M12 2V5M12 19V22M2 12H5M19 12H22" stroke="#ef4444" stroke-width="1" stroke-linecap="round" />
          </svg>
        </div>
      `,
    }));
  }, [impactMarkers]);

  const handleSaveSimulation = () => {
    const session = {
      id: `sim-${Date.now()}`,
      name: `Simulación ${new Date().toLocaleString()}`,
      timestamp: new Date().toISOString(),
      events: impactMarkers,
    };
    const saved = JSON.parse(localStorage.getItem("nexo_simulations") || "[]");
    localStorage.setItem(
      "nexo_simulations",
      JSON.stringify([...saved, session]),
    );
    alert("Simulación guardada en panel local.");
  };

  const handleReplayAll = async () => {
    if (impactMarkers.length === 0) return;
    for (const m of impactMarkers) {
      if (globeEl.current) {
        globeEl.current.pointOfView(
          { lat: m.lat, lng: m.lng, altitude: 1.2 },
          1500,
        );
        await new Promise((r) => setTimeout(r, 2000));
      }
    }
  };

  // Layer channels
  const [channels, setChannels] = useState({
    bases: true,
    naval: true,
    flights: true,
    defense: true,
    tankers: true,
    milAir: true,
    execJets: true,
    dronesHelos: true,
    warships: true,
    aisLive: true,
    gdelt: true,
    firms: true,
    osintFlights: true,
    drive: true,
    satellites: true,
    cities: true,
  });

  // Scanner meridiano giratorio (efecto radar) — lento para no distraer
  const [scannerLng, setScannerLng] = useState(0);
  useEffect(() => {
    const iv = setInterval(() => setScannerLng((l) => (l + 1.5) % 360), 500);
    return () => clearInterval(iv);
  }, []);

  // Render satelites dynamically using frame time instead of states to avoid heavy re-renders
  const [satData, setSatData] = useState([]);
  const channelsRef = useRef(channels);
  const satellitesRef = useRef(satellites);
  useEffect(() => {
    channelsRef.current = channels;
  }, [channels]);
  useEffect(() => {
    satellitesRef.current = satellites;
  }, [satellites]);

  useEffect(() => {
    let animationFrameId;
    let current = -30;
    let lastTimestamp = 0;
    let frame = 0;

    const animate = (timestamp) => {
      if (!lastTimestamp) lastTimestamp = timestamp;
      const deltaTime = timestamp - lastTimestamp;

      current += (deltaTime / 1000) * 0.5; // Simulate 0.5 days per second

      if (current > 15) {
        current = -30; // Auto-loop
      }
      setTimelineDay(current);
      frame++;

      // Update satellite positions every ~30 frames (0.5s) to avoid React depth/performance issues
      if (
        channelsRef.current.satellites &&
        satellitesRef.current.length > 0 &&
        frame % 30 === 0
      ) {
        const now = new Date();
        const activeSats = satellitesRef.current
          .map((sat) => {
            const positionAndVelocity = satellite.propagate(sat.satrec, now);
            const positionEci = positionAndVelocity.position;
            if (!positionEci || typeof positionEci === "boolean") return null;

            const gmst = satellite.gstime(now);
            const positionGd = satellite.eciToGeodetic(positionEci, gmst);

            return {
              lat: satellite.degreesLat(positionGd.latitude),
              lng: satellite.degreesLong(positionGd.longitude),
              alt: (positionGd.height / 6371) * 1.5,
              name: sat.name,
            };
          })
          .filter(Boolean);
        setSatData(activeSats);
      }

      lastTimestamp = timestamp;
      animationFrameId = requestAnimationFrame(animate);
    };

    animationFrameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  useEffect(() => {
    fetch(
      "https://raw.githubusercontent.com/vasturiano/react-globe.gl/master/example/datasets/ne_110m_admin_0_countries.geojson",
    )
      .then((res) => res.json())
      .then(setCountries)
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (globeEl.current) {
      globeEl.current.pointOfView({ lat: 25.0, lng: 50.0, altitude: 1.5 });
    }
  }, []);

  // Actualizar capas del globo cuando cambian las fuentes de datos
  useEffect(() => {
    const elements = [];
    const rings = [];
    const objects = [];
    const arcs = [];
    const paths = [];
    const labels = [];

    // ── LIVE OSINT: GDELT Conflict Events ──────────────────────────────────
    if (channels.gdelt) {
      conflictMarkers.forEach((m) => {
        rings.push({
          lat: m.lat,
          lng: m.lng,
          maxR: 0.6,
          propagationSpeed: m.ringSpeed * 0.15,
          repeatPeriod: 4000,
          color: m.ringColor,
        });
        elements.push({
          lat: m.lat,
          lng: m.lng,
          html: renderToString(
            <div
              style={{
                transform: "translate(-50%,-50%)",
                pointerEvents: "auto",
                display: "flex",
                alignItems: "center",
                gap: 4,
                cursor: "pointer",
              }}
            >
              <div
                style={{
                  width: m.severity === "critical" ? 5 : 3,
                  height: m.severity === "critical" ? 5 : 3,
                  background: "#fff",
                  borderRadius: "50%",
                  border: `1.5px solid ${m.color}`,
                  boxShadow: `0 0 5px 1px ${m.color}`,
                }}
              />
              <span
                style={{
                  color: "#e2e8f0",
                  fontSize: 7,
                  fontFamily: "monospace",
                  fontWeight: "bold",
                  textShadow: "0 0 4px #000, 0 0 8px #000",
                }}
              >
                {m.label.split(" ").slice(0, 2).join(" ").toUpperCase()}
              </span>
            </div>,
          ),
        });
      });
    }

    // ── LIVE OSINT: FIRMS Thermal Anomalies (fires/explosions) ─────────────
    if (channels.firms) {
      thermalMarkers.forEach((m) => {
        rings.push({
          lat: m.lat,
          lng: m.lng,
          maxR: 0.5,
          propagationSpeed: m.ringSpeed * 0.15,
          repeatPeriod: 5000,
          color: m.ringColor,
        });
        elements.push({
          lat: m.lat,
          lng: m.lng,
          html: renderToString(
            <div
              style={{
                transform: "translate(-50%,-50%)",
                pointerEvents: "auto",
                display: "flex",
                alignItems: "center",
                gap: 3,
                cursor: "pointer",
              }}
            >
              <div
                style={{
                  width: 3,
                  height: 3,
                  background: "#fff",
                  borderRadius: "50%",
                  border: "1.5px solid #fb923c",
                  boxShadow: "0 0 4px 1px #fb923c",
                }}
              />
              <span
                style={{
                  color: "#fed7aa",
                  fontSize: 7,
                  fontFamily: "monospace",
                  fontWeight: "bold",
                  textShadow: "0 0 4px #000",
                }}
              >
                FIRE
              </span>
            </div>,
          ),
        });
      });
    }

    // ── LIVE OSINT: Drive docs as intelligence pins ─────────────────────────
    if (channels.drive) {
      driveMarkers.forEach((m) => {
        rings.push({
          lat: m.lat,
          lng: m.lng,
          maxR: 0.4,
          propagationSpeed: m.ringSpeed * 0.12,
          repeatPeriod: 7000,
          color: m.ringColor,
        });
        elements.push({
          lat: m.lat,
          lng: m.lng,
          html: renderToString(
            <a
              href={m.webViewLink || "#"}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                transform: "translate(-50%,-50%)",
                pointerEvents: "auto",
                display: "flex",
                alignItems: "center",
                gap: 4,
                textDecoration: "none",
                cursor: "pointer",
              }}
            >
              <div
                style={{
                  width: 4,
                  height: 4,
                  background: "#fff",
                  borderRadius: "50%",
                  border: "1.5px solid #a855f7",
                  boxShadow: "0 0 5px 1px #a855f7",
                }}
              />
              <span
                style={{
                  color: "#e9d5ff",
                  fontSize: 7,
                  fontFamily: "monospace",
                  fontWeight: "bold",
                  textShadow: "0 0 4px #000, 0 0 8px #000",
                }}
              >
                {m.label.split(" ")[0].toUpperCase()}
              </span>
            </a>,
          ),
        });
      });
    }

    // Only bases get HTML markers now
    if (channels.bases) {
      TACTICAL_BASES.forEach((base) => {
        elements.push({
          lat: base.lat,
          lng: base.lng,
          size: 20,
          color: base.type === "airbase" ? "#06b6d4" : "#3b82f6",
          html: renderToString(
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                transform: "translate(-50%, -50%)",
                pointerEvents: "none",
              }}
            >
              <div
                style={{
                  background: "rgba(0,0,0,0.8)",
                  border: `1px solid ${base.type === "airbase" ? "#06b6d4" : "#3b82f6"}`,
                  padding: 5,
                  borderRadius: "50%",
                }}
              >
                {base.type === "airbase" ? (
                  <Plane size={14} color="#06b6d4" />
                ) : (
                  <ShieldAlert size={14} color="#3b82f6" />
                )}
              </div>
              <div
                style={{
                  marginTop: 4,
                  background: "rgba(0,0,0,0.8)",
                  padding: "2px 6px",
                  borderRadius: 4,
                  color: "#fff",
                  fontSize: 10,
                  border: "1px solid rgba(255,255,255,0.2)",
                  whiteSpace: "nowrap",
                  fontFamily: "monospace",
                }}
              >
                {base.id.toUpperCase()}
              </div>
            </div>,
          ),
        });
        // Add radar ping to active headquarters — slow pulse
        if (base.type === "airbase") {
          rings.push({
            lat: base.lat,
            lng: base.lng,
            maxR: 0.4,
            propagationSpeed: 0.15,
            repeatPeriod: 5000,
          });
        }

        // Agregar información de tropas (tamaño ciudad)
        labels.push({
          lat: base.lat,
          lng: base.lng,
          text: `${base.troops} TROOPS`,
          color: "rgba(16, 185, 129, 0.5)",
          size: 0.22,
        });
      });
    }

    // Añadir Infraestructura Crítica y Zonas de Conflicto
    TACTICAL_INFRASTRUCTURE.forEach((infra) => {
      if (infra.type === "conflict") {
        // Red heat map rings for high conflict areas
        rings.push({
          lat: infra.lat,
          lng: infra.lng,
          maxR: 0.6,
          propagationSpeed: 0.05,
          repeatPeriod: 3500,
          color: "rgba(239, 68, 68, 0.4)",
        });
        elements.push({
          lat: infra.lat,
          lng: infra.lng,
          size: 20,
          html: renderToString(
            <div
              style={{
                color: "#ef4444",
                fontSize: 9,
                fontWeight: "bold",
                fontFamily: "monospace",
                textShadow: "0 0 5px red",
              }}
            >
              [ CONFLICT ZONE ]
            </div>,
          ),
        });
      } else {
        // Docks and Pipelines
        elements.push({
          lat: infra.lat,
          lng: infra.lng,
          size: 25,
          html: renderToString(
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "2px 6px",
                background: "rgba(5,5,10,0.7)",
                backdropFilter: "blur(4px)",
                border: "1px solid #eab308",
                borderRadius: 4,
                pointerEvents: "none",
                boxShadow: "0 0 10px rgba(234,179,8,0.3)",
              }}
            >
              <ShieldAlert size={10} color="#eab308" />
              <span
                style={{
                  color: "#eab308",
                  fontSize: 9,
                  fontFamily: "'Inter', monospace",
                  fontWeight: 600,
                  letterSpacing: 1,
                  whiteSpace: "nowrap",
                }}
              >
                {infra.name.toUpperCase()}
              </span>
            </div>,
          ),
        });
      }
    });

    // --- WebGL 3D Markers (Replacing messy HTML tags for cleaner look) ---

    // Military Bases
    if (channels.bases) {
      TACTICAL_BASES.forEach((base) => {
        objects.push({ ...base, heading: 0 }); // push to customLayerData eventually

        // Etiqueta legible a nivel ciudad
        const labelText = base.troops
          ? `${base.name.toUpperCase()} [${base.troops}]`
          : base.name.toUpperCase();
        labels.push({
          lat: base.lat,
          lng: base.lng,
          text: labelText,
          color: base.type === "airbase" ? "#06b6d4" : "#3b82f6",
          size: 0.28,
        });

        // Ping ring — slow
        if (base.type === "airbase")
          rings.push({
            lat: base.lat,
            lng: base.lng,
            maxR: 1.5,
            propagationSpeed: 0.18,
            repeatPeriod: 6000,
          });
      });
    }

    // Dynamic Fleet
    if (channels.naval) {
      TACTICAL_SHIPS.forEach((ship) => {
        const position = getInterpolatedPosition(ship.trajectory, timelineDay);
        objects.push({ ...position, ...ship });
        labels.push({
          lat: position.lat,
          lng: position.lng,
          text: ship.name,
          color: "#eab308",
          size: 0.28,
        });
        rings.push({
          lat: position.lat,
          lng: position.lng,
          maxR: 0.5,
          propagationSpeed: 0.12,
          repeatPeriod: 6000,
          color: "rgba(239, 68, 68, 0.4)",
        });
      });
    }

    // High-Value Maritime Assets (Oil Tankers)
    if (channels.tankers) {
      TACTICAL_OIL_TANKERS.forEach((t) => {
        objects.push({ ...t, heading: 45 });
        labels.push({
          lat: t.lat,
          lng: t.lng,
          text: `${t.flag} ${t.name.toUpperCase()}`,
          color: "#eab308",
          size: 0.28,
        });
        rings.push({
          lat: t.lat,
          lng: t.lng,
          maxR: 0.5,
          propagationSpeed: 0.08,
          repeatPeriod: 8000,
          color: "rgba(234,179,8,0.28)",
        });
      });
    }

    // Warships
    if (channels.warships) {
      TACTICAL_WARSHIPS.forEach((w) => {
        objects.push({ ...w, heading: 90 });
        labels.push({
          lat: w.lat,
          lng: w.lng,
          text: `${w.name.toUpperCase()} [${w.country}]`,
          color: "#3b82f6",
          size: 0.28,
        });
        rings.push({
          lat: w.lat,
          lng: w.lng,
          maxR: 0.6,
          propagationSpeed: 0.12,
          repeatPeriod: 7000,
          color: "rgba(59,130,246,0.3)",
        });
      });
    }

    // Military Aircraft
    if (channels.milAir) {
      TACTICAL_MILITARY_AIRCRAFT.forEach((a) => {
        objects.push({ ...a, alt: 0.08, heading: 30 });
        labels.push({
          lat: a.lat,
          lng: a.lng,
          text: `${a.name.toUpperCase()} · ${a.country}`,
          color: "#ef4444",
          size: 0.14,
        });
        rings.push({
          lat: a.lat,
          lng: a.lng,
          maxR: 1.2,
          propagationSpeed: 0.25,
          repeatPeriod: 5000,
          color: "rgba(239,68,68,0.45)",
        });
      });
    }

    // Executive Jets
    if (channels.execJets) {
      TACTICAL_EXECUTIVE_JETS.forEach((j) => {
        objects.push({ ...j, alt: 0.1, heading: 60 });
        labels.push({
          lat: j.lat,
          lng: j.lng,
          text: `${j.reg} — ${j.owner}`,
          color: "#a855f7",
          size: 0.24,
        });
      });
    }

    // Drones & Helicopters
    if (channels.dronesHelos) {
      TACTICAL_DRONES_HELICOPTERS.forEach((d) => {
        const isDrone = d.type === "drone";
        objects.push({
          ...d,
          alt: isDrone ? 0.15 : 0.05,
          heading: isDrone ? 120 : 80,
        });
        labels.push({
          lat: d.lat,
          lng: d.lng,
          text: d.callsign || d.name.toUpperCase(),
          color: isDrone ? "#06b6d4" : "#f59e0b",
          size: 0.26,
        });
        rings.push({
          lat: d.lat,
          lng: d.lng,
          maxR: isDrone ? 1.2 : 0.8,
          propagationSpeed: isDrone ? 0.2 : 0.15,
          repeatPeriod: isDrone ? 5000 : 6000,
          color: isDrone ? "rgba(6,182,212,0.4)" : "rgba(245,158,11,0.35)",
        });
      });
    }
    // --- AIS Live Vessel Feed (Real-time) ---
    if (channels.aisLive && liveVessels.length > 0) {
      const TYPE_EMOJI = {
        oil_tanker: "🛢️",
        warship: "⚓",
        cargo: "📦",
        passenger: "🚢",
        tug: "⛽",
        sar: "🆘",
        highspeed: "⚡",
        unknown: "🚢",
      };
      liveVessels.forEach((v) => {
        elements.push({
          lat: v.lat,
          lng: v.lng,
          size: 20,
          html: renderToString(
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 4,
                padding: "2px 6px",
                background: "rgba(5,5,10,0.6)",
                backdropFilter: "blur(4px)",
                border: `1px solid ${v.color || "#64748b"}`,
                borderRadius: 4,
                pointerEvents: "none",
              }}
            >
              <div
                style={{
                  width: 4,
                  height: 4,
                  borderRadius: "50%",
                  background: v.color || "#64748b",
                  boxShadow: `0 0 6px ${v.color || "#64748b"}`,
                }}
              />
              <span
                style={{
                  color: v.color || "#94a3b8",
                  fontSize: 8,
                  fontFamily: "'Inter', monospace",
                  fontWeight: 500,
                  letterSpacing: 0.5,
                  whiteSpace: "nowrap",
                }}
              >
                {v.name.slice(0, 16).toUpperCase()}
              </span>
            </div>,
          ),
        });
        // Speed-proportional ring: faster ships pulse quicker
        const speed = Math.max(v.sog || 0, 0.1);
        rings.push({
          lat: v.lat,
          lng: v.lng,
          maxR: v.category === "warship" ? 0.8 : 0.4,
          propagationSpeed: 0.1 + speed * 0.02,
          repeatPeriod: 4000 - Math.min(speed * 100, 3000),
          color: `${v.color || "#64748b"}55`,
        });
      });
    }

    // Add 3D OSINT Flight Radar
    if (channels.flights) {
      TACTICAL_FLIGHTS.forEach((flight) => {
        const position = getInterpolatedPosition(
          flight.trajectory,
          timelineDay,
        );
        objects.push({ ...position, ...flight });
        labels.push({
          lat: position.lat,
          lng: position.lng,
          text: flight.name,
          color: "#a855f7",
          size: 0.28,
          alt: (position.alt || 0) + 0.05,
        });
        rings.push({
          lat: position.lat,
          lng: position.lng,
          maxR: 0.4,
          propagationSpeed: 0.15,
          repeatPeriod: 5000,
          color: "rgba(6, 182, 212, 0.4)",
        });
        const trailPoints = flight.trajectory.filter(
          (p) => p.day <= timelineDay,
        );
        if (trailPoints.length > 1) {
          const coords = trailPoints.map((p) => [
            p.lat,
            p.lng,
            (p.alt || 0.1) + 0.01,
          ]);
          coords.push([
            position.lat,
            position.lng,
            (position.alt || 0.1) + 0.01,
          ]);
          paths.push({
            coords: coords,
            color:
              flight.type === "vip"
                ? "rgba(234, 179, 8, 0.5)"
                : "rgba(6, 182, 212, 0.5)",
          });
        }
      });
    }

    // Sistemas Antiaéreos y Bombardeos
    if (channels.defense) {
      TACTICAL_AA_SYSTEMS.forEach((aa) => {
        objects.push({
          lat: aa.lat,
          lng: aa.lng,
          alt: 0.02,
          heading: 0,
          ...aa,
        });
        // Scale down the SAM radar rings drastically to prevent graphic overlap on the globe surface
        const ringSize = Math.max(0.1, Math.min(aa.radius / 1200, 0.4));
        rings.push({
          lat: aa.lat,
          lng: aa.lng,
          maxR: ringSize,
          propagationSpeed: 0.2,
          repeatPeriod: 4000,
          color: "rgba(16, 185, 129, 0.2)",
        });
      });

      TACTICAL_STRIKES.forEach((strike) => {
        // Solo mostrar la explosión si el timelineDay está cerca de la fecha de ataque (+/- 1.5 días)
        if (Math.abs(timelineDay - strike.day) < 1.5) {
          // Anillo de explosión — calmado
          rings.push({
            lat: strike.lat,
            lng: strike.lng,
            maxR: 0.5,
            propagationSpeed: 0.3,
            repeatPeriod: 4000,
            color: "rgba(239, 68, 68, 0.6)",
          });

          elements.push({
            lat: strike.lat,
            lng: strike.lng,
            size: 35,
            color: "#ef4444",
            html: renderToString(
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  transform: "translate(-50%, -50%)",
                  pointerEvents: "none",
                }}
              >
                <style>{`@keyframes pinger { 0% { transform: scale(0.9); opacity: 0.8; } 100% { transform: scale(1.4); opacity: 0; } }`}</style>
                <div
                  style={{
                    background: "rgba(239, 68, 68, 0.8)",
                    border: "2px solid #fff",
                    padding: 8,
                    borderRadius: "50%",
                    boxShadow: "0 0 12px #ef444466",
                  }}
                >
                  <ShieldAlert size={20} color="#fff" />
                  <div
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      height: "100%",
                      borderRadius: "50%",
                      background: "rgba(239,68,68,0.3)",
                      animation: "pinger 3s ease-out infinite",
                    }}
                  ></div>
                </div>
                <div
                  style={{
                    marginTop: 4,
                    background: "rgba(0,0,0,0.9)",
                    padding: "2px 6px",
                    borderRadius: 4,
                    color: "#fca5a5",
                    fontSize: 13,
                    border: "1px solid rgba(239, 68, 68, 0.7)",
                    whiteSpace: "nowrap",
                    fontFamily: "monospace",
                    fontWeight: "bold",
                  }}
                >
                  [ BOMBARDEO: {strike.target.toUpperCase()} ]
                </div>
              </div>,
            ),
          });
        }
      });
    }

    // Misiles Balísticos e intercepciones en tiempo real
    if (channels.defense) {
      TACTICAL_MISSILES.forEach((missile) => {
        arcs.push(missile);
      });
    }
    // Añadir marcadores de objetivo estratégico
    if (channels.defense) {
      TACTICAL_GOALS.forEach((goal) => {
        elements.push({
          lat: goal.lat,
          lng: goal.lng,
          size: 12,
          html: renderToString(
            <div
              style={{
                color: "#ffd700",
                fontSize: 10,
                fontWeight: "bold",
                textShadow: "0 0 8px #ffd700",
                fontFamily: "'Space Mono', monospace",
              }}
            >
              OBJETIVO
            </div>,
          ),
        });
      });
    }

    // --- Phase 11: Geopolitical Nomenclature & Boundaries (Country Names) ---
    if (countries && countries.features) {
      countries.features.forEach((f) => {
        const p = f.properties;
        if (p.LABEL_Y && p.LABEL_X && p.ADMIN) {
          labels.push({
            lat: p.LABEL_Y,
            lng: p.LABEL_X,
            text: p.ADMIN.toUpperCase(),
            color: "rgba(255, 255, 255, 0.07)",
            size: 0.2,
            alt: 0.005,
            dotRadius: 0,
          });
        }
      });
    }

    // ── CAPA DE CIUDADES ESTRATÉGICAS ────────────────────────────────────
    if (channels.cities) {
      STRATEGIC_CITIES.forEach((city) => {
        const cityColor = CITY_COLORS[city.tier];
        const countryLabel = COUNTRY_NAMES[city.country] || city.country;
        // Label formato: CIUDAD · PAÍS
        labels.push({
          lat: city.lat,
          lng: city.lng,
          text: `${city.name.toUpperCase()} · ${countryLabel.toUpperCase()}`,
          color: cityColor,
          size:
            city.tier === "critical"
              ? 0.32
              : city.tier === "high"
                ? 0.24
                : 0.18,
          alt: 0.018,
          dotRadius: city.tier === "low" ? 0 : 0.12,
        });
        const ringCfg = CITY_RING_CONFIG[city.tier];
        if (ringCfg)
          rings.push({
            lat: city.lat,
            lng: city.lng,
            ...ringCfg,
            color: `${cityColor}55`,
          });
      });
    }

    setMapHtmlElements(elements);
    setActiveRings(rings);
    setActiveObjects(objects);
    setActiveArcs(arcs);
    setActivePaths(paths);
    setActiveLabels(labels);
  }, [
    timelineDay,
    channels,
    liveVessels,
    conflictMarkers,
    thermalMarkers,
    driveMarkers,
    countries,
  ]);

  // Globe: esfera semitransparente + glow atmosférico para el overlay
  const onGlobeReady = useCallback(() => {
    const globe = globeEl.current;
    if (!globe || !globe.scene) return;
    const scene = globe.scene();
    if (!scene) return;
    try {
      globe.renderer().setClearColor(0x000000, 0);
    } catch (_) {}
    const globeMaterial = globe.globeMaterial();
    globeMaterial.color = new THREE.Color(0x010308);
    globeMaterial.emissive = new THREE.Color(0x000000);
    globeMaterial.roughness = 1;
    globeMaterial.transparent = true;
    globeMaterial.opacity = 0.15;
    const geoAtm = new THREE.SphereGeometry(101.5, 64, 64);
    const glow = new THREE.Mesh(geoAtm, buildAtmosphereMaterial());
    glow.name = "nexo-atmosphere";
    if (!scene.getObjectByName("nexo-atmosphere")) scene.add(glow);
    const ambient = new THREE.AmbientLight(0x334466, 0.4);
    ambient.name = "nexo-ambient";
    if (!scene.getObjectByName("nexo-ambient")) scene.add(ambient);
    globe.controls().autoRotate = false;
    globe.controls().enableDamping = true;
    globe.controls().dampingFactor = 0.08;
  }, []);

  // Auto-cámara: volar a nuevo evento GDELT crítico (una vez cada 30s máximo)
  const lastAutoCamRef = useRef(0);
  useEffect(() => {
    if (!globeEl.current || conflictMarkers.length === 0) return;
    const now = Date.now();
    if (now - lastAutoCamRef.current < 30000) return;
    const critical = conflictMarkers.filter((m) => m.severity === "critical");
    if (critical.length === 0) return;
    const target = critical[Math.floor(Math.random() * critical.length)];
    lastAutoCamRef.current = now;
    globeEl.current.controls().autoRotate = false;
    globeEl.current.pointOfView(
      { lat: target.lat, lng: target.lng, altitude: 1.4 },
      2200,
    );
    // Reanudar rotación después de 8 segundos
    setTimeout(() => {
      if (globeEl.current) globeEl.current.controls().autoRotate = true;
    }, 8000);
  }, [conflictMarkers]);

  // AI alert ticker — rotate through alerts
  const [tickerIdx, setTickerIdx] = useState(0);
  useEffect(() => {
    const t = setInterval(
      () => setTickerIdx((i) => (i + 1) % Math.max(1, aiAlerts.length)),
      6000,
    );
    return () => clearInterval(t);
  }, [aiAlerts.length]);

  const currentAlert = aiAlerts[tickerIdx] || null;

  return (
    <div
      ref={containerRef}
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        minHeight: "100vh",
        background:
          "radial-gradient(ellipse at 40% 60%, #071428 0%, #020810 100%)",
        overflow: "hidden",
      }}
    >
      {/* Status bar — top right */}
      <div
        style={{
          position: "absolute",
          top: 16,
          right: 16,
          zIndex: 20,
          display: "flex",
          gap: 8,
          alignItems: "center",
          fontFamily: "monospace",
          fontSize: 10,
        }}
      >
        {/* OSINT live indicator */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 4,
            background: "rgba(0,0,0,0.7)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 4,
            padding: "4px 8px",
            color: osintLoading ? "#f59e0b" : "#22c55e",
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: osintLoading ? "#f59e0b" : "#22c55e",
              display: "inline-block",
              boxShadow: `0 0 6px ${osintLoading ? "#f59e0b" : "#22c55e"}`,
            }}
          />
          OSINT{" "}
          {osintLoading
            ? "SWEEP"
            : `${conflictMarkers.length + thermalMarkers.length} EVT`}
        </div>
        {/* AI indicator */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 4,
            background: "rgba(0,0,0,0.7)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 4,
            padding: "4px 8px",
            color: aiConnected ? "#a855f7" : "#64748b",
          }}
        >
          {aiConnected ? <Wifi size={10} /> : <WifiOff size={10} />}
          AI {wsMode ? "WS" : "POLL"}
        </div>
        {/* Drive indicator */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 4,
            background: "rgba(0,0,0,0.7)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 4,
            padding: "4px 8px",
            color: driveMarkers.length > 0 ? "#a855f7" : "#64748b",
          }}
        >
          <FileText size={10} />
          DRIVE {driveMarkers.length}
        </div>
        <button
          onClick={refetch}
          style={{
            background: "rgba(0,0,0,0.7)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 4,
            padding: "4px 8px",
            color: "#94a3b8",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          <RefreshCw size={10} />
        </button>
      </div>

      {/* ── MODO UNIFICADO: Maplibre (globo + ciudad + edificios 3D) ────────── */}
      <div style={{ position: "absolute", inset: 0, zIndex: 5 }}>
        <GlobeMaplibre
          ref={maplibreRef}
          conflictMarkers={conflictMarkers}
          thermalMarkers={thermalMarkers}
          liveVessels={liveVessels}
          liveFlights={liveFlights}
          driveMarkers={driveMarkers}
          tacticalBases={TACTICAL_BASES}
          channels={channels}
          satStyle={satTile}
          onMarkerClick={(ev) => {
            if (ev.severity === "critical" || ev.type === "conflict") {
              maplibreRef.current?.flyToEvent(ev.lat, ev.lng, 15);
              setTimeout(
                () =>
                  setDestructionEvent({
                    ...ev,
                    timestamp: new Date().toISOString(),
                  }),
                2200,
              );
            } else {
              setEvidenceEvent(ev);
            }
          }}
        />
      </div>

      {/* ── Capa Táctica 3D — Globe transparente sobre Maplibre ────────────────
          mix-blend-mode:screen hace que el negro del fondo desaparezca.
          Solo son visibles los rings, arcs, 3D objects y paths tácticos.
          pointer-events:none → todos los clicks llegan al Maplibre de abajo. */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          zIndex: 10,
          pointerEvents: "none",
          mixBlendMode: "screen",
        }}
      >
        <Globe
          ref={globeEl}
          onGlobeReady={onGlobeReady}
          globeImageUrl=""
          showAtmosphere={false}
          showGraticules={false}
          backgroundColor="rgba(0,0,0,0)"
          objectsData={[
            ...activeObjects,
            ...(activeSimulations || []).map((s) => ({
              ...s,
              _simMissile: true,
            })),
          ]}
          objectLat="lat"
          objectLng="lng"
          objectAltitude={(d) => (d.alt !== undefined ? d.alt : 0.02)}
          objectThreeObject={(d) => {
            if (d._simMissile) {
              const geo = new THREE.TetrahedronGeometry(0.18, 0);
              const mat = new THREE.MeshBasicMaterial({
                color: 0xff4444,
                wireframe: true,
              });
              return new THREE.Mesh(geo, mat);
            }
            return create3DAssetNode(d);
          }}
          customLayerData={[...activeObjects, ...satData]}
          customThreeObject={(d) => {
            if (d.satrec) {
              const group = new THREE.Group();
              const core = new THREE.Mesh(
                new THREE.SphereGeometry(1.5, 8, 8),
                new THREE.MeshBasicMaterial({ color: "#f59e0b" }),
              );
              group.add(core);
              return group;
            }
            return create3DAssetNode(d);
          }}
          customThreeObjectUpdate={(obj, d) => {
            if (d.satrec) {
              Object.assign(
                obj.position,
                globeEl.current.getCoords(d.lat, d.lng, d.alt),
              );
            } else {
              update3DAssetNode(obj, d, globeEl);
            }
          }}
          ringsData={activeRings}
          ringColor={(t) => t.color || "rgba(6, 182, 212, 0.5)"}
          ringMaxRadius="maxR"
          ringAltitude={0.015}
          ringPropagationSpeed="propagationSpeed"
          ringRepeatPeriod="repeatPeriod"
          arcsData={activeArcs}
          arcStartLat={(d) => d.startLat}
          arcStartLng={(d) => d.startLng}
          arcEndLat={(d) => d.endLat}
          arcEndLng={(d) => d.endLng}
          arcColor={(d) => [
            d.color || "rgba(239,68,68,0.2)",
            d.color || "rgba(234,179,8,1)",
          ]}
          arcDashLength={0.15}
          arcDashGap={1.5}
          arcDashInitialGap={(d) => d._arcGap ?? 0.5}
          arcDashAnimateTime={4000}
          arcAltitude={0.4}
          arcStroke={0.4}
          pathsData={[
            ...activePaths,
            {
              coords: Array.from({ length: 19 }, (_, i) => {
                const lat = -90 + i * 10;
                return [lat, ((scannerLng - 180 + 360) % 360) - 180, 0.008];
              }),
              color: [
                "rgba(6,182,212,0)",
                "rgba(6,182,212,0.3)",
                "rgba(6,182,212,0.6)",
                "rgba(6,182,212,0.3)",
                "rgba(6,182,212,0)",
              ],
            },
          ]}
          pathPoints="coords"
          pathPointLat={(p) => p[0]}
          pathPointLng={(p) => p[1]}
          pathPointAlt={(p) => p[2]}
          pathColor="color"
          pathStroke={1.5}
          pathResolution={2}
          htmlElementsData={[...mapHtmlElements, ...impactHtmlElements]}
          htmlAltitude={0.02}
          htmlElement={(d) => {
            const el = document.createElement("div");
            el.innerHTML = d.html;
            return el;
          }}
          animateIn={false}
          width={globeSize.w}
          height={globeSize.h}
          rendererConfig={{
            antialias: true,
            alpha: true,
            powerPreference: "high-performance",
          }}
        />
      </div>

      {/* Visual Overlay FX */}
      <div className="crt-vignette" />
      <div className="crt-overlay" />

      <OmniGlobeHUD currentAlert={currentAlert} />

      {/* Destruction Overlay — animación + evidencia Drive al detectar evento crítico */}
      {destructionEvent && (
        <DestructionOverlay
          event={destructionEvent}
          mapRef={{ current: maplibreRef.current?.getMap?.() }}
          driveMarkers={driveMarkers}
          onClose={() => setDestructionEvent(null)}
        />
      )}

      {/* AI Live Ticker — Pinned directly to the bottom edge */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: "50%",
          transform: "translateX(-50%)",
          width: "100%",
          borderTop: `1px solid ${currentAlert ? currentAlert.color.replace("0.9", "0.4").replace("0.85", "0.4") : "rgba(239,68,68,0.4)"}`,
          padding: "6px 30px",
          zIndex: 30,
          display: "flex",
          alignItems: "center",
          gap: 15,
          background: "rgba(5,10,15,0.95)",
          transition: "border-color 0.6s ease",
        }}
      >
        <div
          style={{
            width: 4,
            height: 20,
            background: currentAlert?.color || "#ef4444",
            borderRadius: 2,
            boxShadow: `0 0 10px ${currentAlert?.color || "#ef4444"}`,
            flexShrink: 0,
            transition: "background 0.6s ease",
          }}
        />
        <div
          style={{
            flex: 1,
            color: "#f8fafc",
            fontFamily: "'Space Mono', monospace",
            fontSize: 11,
            letterSpacing: 0.5,
          }}
        >
          <span
            style={{
              color: currentAlert?.color || "#ef4444",
              fontWeight: "bold",
              marginRight: 10,
              textShadow: `0 0 8px ${currentAlert?.color || "#ef4444"}88`,
            }}
          >
            {currentAlert?.prefix || "[ALERTA TÁCTICA]"}
          </span>
          {currentAlert
            ? currentAlert.text
            : "Sistema NEXO inicializando feeds de inteligencia en tiempo real..."}
          {lastSweep && (
            <span style={{ color: "#64748b", marginLeft: 15, fontSize: 10 }}>
              SWEEP{" "}
              {lastSweep.toLocaleTimeString("es-CL", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </span>
          )}
        </div>
        {aiAlerts.length > 0 && (
          <div
            style={{
              background: "rgba(168,85,247,0.15)",
              border: "1px solid #a855f7",
              borderRadius: 4,
              padding: "2px 8px",
              color: "#a855f7",
              fontSize: 10,
              fontFamily: "monospace",
              flexShrink: 0,
            }}
          >
            {aiAlerts.length} IA REPORTS
          </div>
        )}
      </div>

      {/* Timeline Slider HUD & Simulation Control — Compact above the ticker */}
      {hideTimeline ? (
        <button
          onClick={() => setHideTimeline(false)}
          style={{
            position: "absolute",
            bottom: 50,
            left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(5,10,15,0.9)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 6,
            padding: "5px 14px",
            cursor: "pointer",
            color: "#94a3b8",
            fontSize: 9,
            fontFamily: "'Space Mono', monospace",
            letterSpacing: "0.05em",
            zIndex: 20,
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <Plus size={10} /> TIMELINE
        </button>
      ) : (
        <div
          style={{
            position: "absolute",
            bottom: 50,
            left: "50%",
            transform: "translateX(-50%)",
            width: "80%",
            maxWidth: 900,
            background: "rgba(5,10,15,0.88)",
            padding: "8px 20px",
            borderRadius: 8,
            border: "1px solid rgba(255,255,255,0.08)",
            zIndex: 20,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: 10,
              fontFamily: "'Space Mono', monospace",
              color: "var(--text)",
              fontSize: 12,
            }}
          >
            <span>Pasado (-30d)</span>
            <span
              style={{
                color: timelineDay > 0 ? "#f97316" : "#22c55e",
                fontWeight: "bold",
              }}
            >
              {Math.abs(timelineDay) < 0.2
                ? "HOY (LIVE)"
                : timelineDay > 0
                  ? `SIMULADOR: DÍA +${timelineDay.toFixed(1)}`
                  : `DÍA ${timelineDay.toFixed(1)}`}
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ color: "#f97316" }}>Futuro (+15d)</span>
              <button
                onClick={() => setHideTimeline(true)}
                style={{
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 4,
                  width: 20,
                  height: 20,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                  color: "#64748b",
                  transition: "color 0.2s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "#f8fafc")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "#64748b")}
              >
                <Minus size={11} />
              </button>
            </div>
          </div>
          <input
            type="range"
            min="-30"
            max="15"
            step="0.01"
            value={timelineDay}
            readOnly
            style={{
              width: "100%",
              cursor: "default",
              pointerEvents: "none",
              accentColor: timelineDay > 0 ? "#f97316" : "#22c55e",
            }}
          />
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              marginTop: 15,
              gap: 8,
              flexWrap: "wrap",
            }}
          >
            {[
              { key: "naval", label: "NAVAL", color: "#f97316" },
              { key: "tankers", label: "TANKERS", color: "#eab308" },
              { key: "warships", label: "WARSHIPS", color: "#3b82f6" },
              { key: "milAir", label: "MIL AIR", color: "#ef4444" },
              { key: "execJets", label: "VIP JETS", color: "#a855f7" },
              { key: "dronesHelos", label: "DRONES/HELOS", color: "#06b6d4" },
              { key: "flights", label: "FLIGHT INTEL", color: "#06b6d4" },
              { key: "defense", label: "SAM/STRIKE", color: "#10b981" },
              {
                key: "aisLive",
                label: `AIS LIVE${liveVessels.length > 0 ? ` (${liveVessels.length})` : ""}`,
                color: aisConnected ? "#22c55e" : "#64748b",
              },
            ].map(({ key, label, color }) => (
              <button
                key={key}
                onClick={() => setChannels((c) => ({ ...c, [key]: !c[key] }))}
                style={{
                  background: channels[key]
                    ? `rgba(${color
                        .replace("#", "")
                        .match(/../g)
                        .map((h) => parseInt(h, 16))
                        .join(",")}, 0.18)`
                    : "transparent",
                  border: `1px solid ${color}`,
                  color,
                  padding: "5px 12px",
                  borderRadius: 4,
                  fontFamily: "'Space Mono', monospace",
                  fontSize: 9,
                  cursor: "pointer",
                  opacity: channels[key] ? 1 : 0.4,
                  transition: "opacity 0.2s",
                }}
              >
                {channels[key] ? `✔ ${label}` : label}
              </button>
            ))}
            <button
              onClick={() => {
                const g = TACTICAL_GOALS[0];
                if (globeEl.current && g)
                  globeEl.current.pointOfView(
                    { lat: g.lat, lng: g.lng, altitude: 2 },
                    2000,
                  );
              }}
              style={{
                background: "rgba(255,215,0,0.15)",
                border: "1px solid #ffd700",
                color: "#ffd700",
                padding: "5px 12px",
                borderRadius: 4,
                fontFamily: "'Space Mono', monospace",
                fontSize: 9,
                cursor: "pointer",
              }}
            >
              🎯 OBJETIVO
            </button>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                background: "transparent",
                border: "1px solid #10b981",
                color: "#10b981",
                padding: "5px 12px",
                borderRadius: 4,
                fontFamily: "'Space Mono', monospace",
                fontSize: 9,
              }}
            >
              <span
                style={{
                  display: "inline-block",
                  width: 6,
                  height: 6,
                  background: "#10b981",
                  borderRadius: "50%",
                  marginRight: 6,
                  animation: "blink-dot 4s ease-in-out infinite",
                }}
              />
              {timelineDay > 0 ? "PREDICCIÓN IA" : "HISTÓRICO LIVE"}
            </div>
          </div>

          {/* OSINT Live layer buttons — second row */}
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              marginTop: 8,
              gap: 6,
              flexWrap: "wrap",
            }}
          >
            {[
              {
                key: "cities",
                label: `CIUDADES (${STRATEGIC_CITIES.length})`,
                color: "#f97316",
              },
              {
                key: "gdelt",
                label: `GDELT (${conflictMarkers.length})`,
                color: "#ef4444",
              },
              {
                key: "firms",
                label: `THERMAL (${thermalMarkers.length})`,
                color: "#fb923c",
              },
              {
                key: "osintFlights",
                label: `OPENSKY (${liveFlights.length})`,
                color: "#06b6d4",
              },
              {
                key: "drive",
                label: `DRIVE (${driveMarkers.length})`,
                color: "#a855f7",
              },
            ].map(({ key, label, color }) => (
              <button
                key={key}
                onClick={() => setChannels((c) => ({ ...c, [key]: !c[key] }))}
                style={{
                  background: channels[key]
                    ? `rgba(${color
                        .replace("#", "")
                        .match(/../g)
                        .map((h) => parseInt(h, 16))
                        .join(",")}, 0.15)`
                    : "transparent",
                  border: `1px solid ${color}`,
                  color,
                  padding: "4px 10px",
                  borderRadius: 4,
                  fontFamily: "'Space Mono', monospace",
                  fontSize: 9,
                  cursor: "pointer",
                  opacity: channels[key] ? 1 : 0.35,
                  transition: "opacity 0.2s",
                }}
              >
                {channels[key] ? `● ${label}` : label}
              </button>
            ))}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 4,
                background: "rgba(168,85,247,0.1)",
                border: "1px solid #a855f7",
                color: "#a855f7",
                padding: "4px 10px",
                borderRadius: 4,
                fontFamily: "'Space Mono', monospace",
                fontSize: 9,
              }}
            >
              {aiConnected ? <Wifi size={9} /> : <WifiOff size={9} />}
              IA {aiConnected ? "LIVE" : "OFF"}
            </div>
          </div>
        </div>
      )}

      {/* ── Phase 13: Event Timeline ── */}
      <EventTimeline
        events={impactMarkers}
        onEventClick={(ev) => {
          if (globeEl.current) {
            globeEl.current.pointOfView(
              { lat: ev.lat, lng: ev.lng, altitude: 1.2 },
              1500,
            );
            setEvidenceEvent(ev);
          }
        }}
        onReplayAll={handleReplayAll}
        onSaveSimulation={handleSaveSimulation}
      />

      {/* ── Phase 12: Evidence Viewer Modal ── */}
      {evidenceEvent && (
        <EvidenceViewer
          event={evidenceEvent}
          onClose={() => setEvidenceEvent(null)}
          relatedEvents={impactMarkers.filter(
            (m) =>
              m.country === evidenceEvent.country && m.id !== evidenceEvent.id,
          )}
        />
      )}
    </div>
  );
};

export default OmniGlobe;
