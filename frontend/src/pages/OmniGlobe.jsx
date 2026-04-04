import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import Globe from 'react-globe.gl';
import * as THREE from 'three';
import GlobeMaplibre from '../components/GlobeMaplibre';
import DestructionOverlay from '../components/DestructionOverlay';
import AISearchPanel from '../components/AISearchPanel';
import { AnimatePresence, motion } from 'framer-motion';
import { Plane, Ship, ShieldAlert, Flame, FileText, Wifi, WifiOff, RefreshCw, Globe2, Map, Search } from 'lucide-react';
import { renderToString } from 'react-dom/server';
import OmniGlobeHUD from '../components/OmniGlobeHUD';
import EvidenceViewer from '../components/EvidenceViewer';
import EventTimeline from '../components/EventTimeline';
import { usePolymarket } from '../hooks/usePolymarket';
import {
  TACTICAL_BASES, TACTICAL_SHIPS, TACTICAL_FLIGHTS, TACTICAL_AA_SYSTEMS, TACTICAL_STRIKES,
  TACTICAL_INFRASTRUCTURE, TACTICAL_MISSILES, TACTICAL_GOALS,
  TACTICAL_OIL_TANKERS, TACTICAL_MILITARY_AIRCRAFT, TACTICAL_EXECUTIVE_JETS,
  TACTICAL_DRONES_HELICOPTERS, TACTICAL_WARSHIPS,
  getInterpolatedPosition, create3DAssetNode, update3DAssetNode
} from '../data/tacticalAssets';
import { useAISStream, SHIP_COLORS } from '../hooks/useAISStream';
import { useOsintLive } from '../hooks/useOsintLive';
import { useGlobeAI } from '../hooks/useGlobeAI';
import { useSatellites } from '../hooks/useSatellites';
import { STRATEGIC_CITIES, CITY_COLORS, CITY_RING_CONFIG, getNearestCity, COUNTRY_NAMES } from '../data/strategicCities';
import * as satellite from 'satellite.js';

// ─── Minimalist Political Map Textures ─────────────────────────────────────────
// Using a black/transparent base to let the JSON borders shine
const GLOBE_IMG_URL   = null;
const GLOBE_BUMP_URL  = null;
const GLOBE_SKY_URL   = null;

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
  const globeEl     = useRef(); // kept for future use
  const maplibreRef = useRef();
  const [countries, setCountries] = useState({ features: [] });
  const [satTile, setSatTile]   = useState(false);
  const [timelineDay, setTimelineDay] = useState(-30);
  const [activeRings, setActiveRings]     = useState([]);
  const [activeObjects, setActiveObjects] = useState([]);
  const [activeArcs, setActiveArcs]       = useState([]);
  const [activePaths, setActivePaths]     = useState([]);
  const [activeLabels, setActiveLabels]   = useState([]);
  const [mapHtmlElements, setMapHtmlElements] = useState([]);
  const [globeSize, setGlobeSize] = useState({ w: window.innerWidth - 220, h: window.innerHeight });
  const [destructionEvent, setDestructionEvent] = useState(null);

  // AIS live data
  const [aisApiKey] = useState(import.meta.env.VITE_AIS_API_KEY || '');
  const { vessels: liveVessels, connected: aisConnected } = useAISStream(aisApiKey);

  // Live OSINT: GDELT conflicts + FIRMS thermal + OpenSky flights + Drive docs
  const { conflictMarkers, thermalMarkers, liveFlights, driveMarkers, lastSweep, loading: osintLoading, refetch } =
    useOsintLive(90000);

  // Contexto OSINT para la IA — ciudades más calientes + conteos
  const osintContext = useMemo(() => {
    const hotCities = conflictMarkers
      .filter(m => m.severity === 'critical')
      .map(m => {
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
  const { alerts: aiAlerts, connected: aiConnected, wsMode, pushAlert, discordActivity, driveActivity: aiDriveActivity } = useGlobeAI(true, osintContext);
  
  // Real-time Satellite TLE Propagation (CelesTrak)
  const { satellites } = useSatellites(true);

  // ── AISearchPanel visibility ────────────────────────────────────────────
  const [searchOpen, setSearchOpen] = useState(false);

  // `/` key toggles the search panel (only when not typing in an input)
  useEffect(() => {
    const handleKey = (e) => {
      const tag = document.activeElement?.tagName;
      if (e.key === '/' && tag !== 'INPUT' && tag !== 'TEXTAREA') {
        e.preventDefault();
        setSearchOpen(s => !s);
      }
      if (e.key === 'Escape' && searchOpen) {
        setSearchOpen(false);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [searchOpen]);

  // ── Merge Drive markers from OSINT hook + AI hook for HUD panel ────────
  const combinedDriveActivity = useMemo(() => {
    const osintDocs = driveMarkers.map(m => ({
      id: m.id || `osint-${m.lat}-${m.lng}`,
      text: m.label || m.name || 'Doc Drive',
      label: m.label || '',
      ts: m.ts || new Date().toISOString(),
      prefix: '[DRIVE]',
      color: '#a855f7',
      webViewLink: m.webViewLink,
    }));
    // Merge, deduplicate by id, most recent first
    const all = [...aiDriveActivity, ...osintDocs];
    const seen = new Set();
    return all.filter(d => { if (seen.has(d.id)) return false; seen.add(d.id); return true; }).slice(0, 20);
  }, [driveMarkers, aiDriveActivity]);

  // ── Auto-animate globe when NEW Drive docs arrive ───────────────────────
  // Initialize to 0 so any docs present at mount don't fire as "new"
  const prevDriveCountRef = useRef(0);
  const mountedRef = useRef(false);
  useEffect(() => {
    if (!mountedRef.current) {
      // Skip the first effect run (mounting): sync ref to current count without animating
      mountedRef.current = true;
      prevDriveCountRef.current = combinedDriveActivity.length;
      return;
    }
    const prev = prevDriveCountRef.current;
    const curr = combinedDriveActivity.length;
    prevDriveCountRef.current = curr;
    if (curr > prev) {
      const newCount = curr - prev;
      const newest   = combinedDriveActivity[0];
      // Fly to location if the newest doc has coordinates
      if (newest?.lat && newest?.lng && maplibreRef.current?.flyToEvent) {
        maplibreRef.current.flyToEvent(newest.lat, newest.lng, 5);
      }
      // Batch into a single ticker alert to avoid spam
      const alertText = newCount === 1
        ? `📂 Nuevo documento en Drive: ${newest.text || newest.label || 'Sin nombre'}`
        : `📂 ${newCount} nuevos documentos en Drive — análisis IA en proceso`;
      // eslint-disable-next-line react-hooks/exhaustive-deps -- pushAlert is stable, maplibreRef is a ref
      pushAlert(alertText, { color: '#a855f7', prefix: '[DRIVE INTEL]' });
    }
  }, [combinedDriveActivity.length]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Phase 12+13: OSINT Simulation State ────────────────────────────────
  const [activeSimulations, setActiveSimulations] = useState([]); // Descending missiles
  const [impactMarkers, setImpactMarkers]         = useState([]); // Persistent evidence pins
  const [evidenceEvent, setEvidenceEvent]         = useState(null);
  const simAltRef = useRef({});

  // Polymarket conflict odds
  const { markets: polyMarkets } = usePolymarket(true);

  // Intercept OSINT TACTICAL_SIMULATION events from WebSocket
  // → Trigger inteligente: vuela al punto + DestructionOverlay
  useEffect(() => {
    const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const WS_URL   = API_BASE.replace(/^http/, 'ws') + '/ws/alerts/demo';
    const ws = new WebSocket(WS_URL);
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.tipo === 'TACTICAL_SIMULATION' && data.lat != null && data.lng != null) {
          const id = `sim-${Date.now()}`;
          simAltRef.current[id] = 1.5;
          setActiveSimulations(prev => [...prev, { ...data, _simId: id }]);
          // Trigger inteligente: volar al evento y mostrar overal
          if (maplibreRef.current?.flyToEvent) {
            maplibreRef.current.flyToEvent(data.lat, data.lng, 15);
          }
          // DestructionOverlay con delay de 2.2s (tiempo del flyTo al nivel de calle)
          setTimeout(() => {
            setDestructionEvent({ ...data, id, timestamp: new Date().toISOString() });
          }, 2200);
        }
      } catch (_) {}
    };
    return () => ws.close();
  }, []);

  // Animate descending missiles — SLOW & CLEAN (0.02 per 100ms = ~7.5 seconds total descent)
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveSimulations(prev => {
        const remaining = [];
        const impacts = [];
        prev.forEach(sim => {
          const currentAlt = (simAltRef.current[sim._simId] ?? 1.5) - 0.02;
          simAltRef.current[sim._simId] = currentAlt;
          if (currentAlt <= 0) {
            impacts.push({ ...sim, alt: 0, timestamp: new Date().toISOString() });
          } else {
            remaining.push({ ...sim, alt: currentAlt });
          }
        });

        // ── Phase 13.2: RedAlert - Warning Zones for Incoming Missiles ────────
        const warningRings = remaining.map(sim => {
          const progress = 1.0 - (simAltRef.current[sim._simId] / 1.5); // 0 at start, 1 at impact
          return {
            lat: sim.lat, lng: sim.lng,
            maxR: 1.2,
            propagationSpeed: 0.5 + progress * 4.0, // Precess quicker
            repeatPeriod: 1000 - progress * 800,    // Pulse faster
            color: progress > 0.8 ? 'rgba(255, 0, 0, 0.95)' : 'rgba(255, 80, 0, 0.65)',
            _incoming: true,
            _simId: sim._simId
          };
        });

        if (impacts.length > 0) {
          // Final impact ring (Slow, clean, persistent)
          setActiveRings(prev => [
            ...prev.filter(r => !impacts.some(i => i._simId === r._simId)), // Remove active warnings for THIS impact
            ...impacts.map(e => ({
              lat: e.lat, lng: e.lng,
              maxR: 0.8, propagationSpeed: 0.4, repeatPeriod: 1500,
              color: 'rgba(239,68,68,0.7)',
            })),
          ]);
          // Ballistic arc...
          setActiveArcs(prev => [
            ...prev,
            ...impacts.map(e => ({
              startLat: e.lat + (Math.random() > 0.5 ? 8 : -8),
              startLng: e.lng + (Math.random() > 0.5 ? 12 : -12),
              endLat: e.lat, endLng: e.lng,
              color: 'rgba(239,68,68,0.9)',
              _type: 'missile_arc',
            })),
          ]);
          // Evidence pins
          setImpactMarkers(prev => [
            ...prev,
            ...impacts.map(e => ({ ...e, id: e._simId })),
          ]);
        }

        // Always update active warnings for the remaining missiles
        setActiveRings(prev => [
          ...prev.filter(r => !r._incoming || remaining.some(s => s._simId === r._simId)),
          ...warningRings
        ]);

        return remaining;
      });
    }, 100);
    return () => clearInterval(interval);
  }, []);


  // Responsive globe size
  useEffect(() => {
    const onResize = () => setGlobeSize({ w: window.innerWidth - 220, h: window.innerHeight });
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // ── Phase 13: Clean Dot Markers ──────────────────────────────────────────
  const impactHtmlElements = useMemo(() => {
    return (impactMarkers || []).map(m => ({
      ...m,
      html: `
        <div style="cursor: pointer; transform: translate(-50%, -50%);" title="${m.target || 'Impacto'}">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="6" fill="#ef4444" fill-opacity="0.2" />
            <circle cx="12" cy="12" r="3" fill="#ef4444" stroke="white" stroke-width="1.5" />
            <path d="M12 2V5M12 19V22M2 12H5M19 12H22" stroke="#ef4444" stroke-width="1" stroke-linecap="round" />
          </svg>
        </div>
      `
    }));
  }, [impactMarkers]);

  const handleSaveSimulation = () => {
    const session = {
      id: `sim-${Date.now()}`,
      name: `Simulación ${new Date().toLocaleString()}`,
      timestamp: new Date().toISOString(),
      events: impactMarkers,
    };
    const saved = JSON.parse(localStorage.getItem('nexo_simulations') || '[]');
    localStorage.setItem('nexo_simulations', JSON.stringify([...saved, session]));
    alert('Simulación guardada en panel local.');
  };

  const handleReplayAll = async () => {
    if (impactMarkers.length === 0) return;
    for (const m of impactMarkers) {
      if (globeEl.current) {
        globeEl.current.pointOfView({ lat: m.lat, lng: m.lng, altitude: 1.2 }, 1500);
        await new Promise(r => setTimeout(r, 2000));
      }
    }
  };

  // Layer channels
  const [channels, setChannels] = useState({
    bases: true, naval: true, flights: true, defense: true,
    tankers: true, milAir: true, execJets: true, dronesHelos: true, warships: true,
    aisLive: true,
    gdelt: true, firms: true, osintFlights: true, drive: true,
    satellites: true,
    cities: true,
  });

  // Scanner meridiano giratorio (efecto radar) — muy lento para no distraer
  const [scannerLng, setScannerLng] = useState(0);
  useEffect(() => {
    const iv = setInterval(() => setScannerLng(l => (l + 0.4) % 360), 120);
    return () => clearInterval(iv);
  }, []);

  // Render satelites dynamically using frame time instead of states to avoid heavy re-renders
  const [satData, setSatData] = useState([]);
  
  useEffect(() => {
    let animationFrameId;
    let current = -30; 
    let lastTimestamp = 0;
    
    const animate = (timestamp) => {
      if (!lastTimestamp) lastTimestamp = timestamp;
      const deltaTime = timestamp - lastTimestamp;
      
      current += (deltaTime / 1000) * 0.5; // Simulate 0.5 days per second
      
      if (current > 15) {
        current = -30; // Auto-loop
      }
      setTimelineDay(current);
      
      // Update satellite positions every ~30 frames (0.5s) to avoid React depth/performance issues
      if (channels.satellites && satellites.length > 0 && frame % 30 === 0) {
        const now = new Date();
        const activeSats = satellites.map(sat => {
          const positionAndVelocity = satellite.propagate(sat.satrec, now);
          const positionEci = positionAndVelocity.position;
          if (!positionEci || typeof positionEci === 'boolean') return null;
          
          const gmst = satellite.gstime(now);
          const positionGd = satellite.eciToGeodetic(positionEci, gmst);
          
          return {
            lat: satellite.degreesLat(positionGd.latitude),
            lng: satellite.degreesLong(positionGd.longitude),
            alt: positionGd.height / 6371 * 1.5,
            name: sat.name
          };
        }).filter(Boolean);
        setSatData(activeSats);
      }

      lastTimestamp = timestamp;
      animationFrameId = requestAnimationFrame(animate);
    };
    
    animationFrameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  useEffect(() => {
    fetch('https://raw.githubusercontent.com/vasturiano/react-globe.gl/master/example/datasets/ne_110m_admin_0_countries.geojson')
      .then(res => res.json())
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
      conflictMarkers.forEach(m => {
        rings.push({ lat: m.lat, lng: m.lng, maxR: 0.6, propagationSpeed: m.ringSpeed * 0.15, repeatPeriod: 4000, color: m.ringColor });
        elements.push({
          lat: m.lat, lng: m.lng,
          html: renderToString(
            <div style={{ transform: 'translate(-50%,-50%)', pointerEvents: 'auto', display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
              <div style={{ width: m.severity === 'critical' ? 5 : 3, height: m.severity === 'critical' ? 5 : 3, background: '#fff', borderRadius: '50%', border: `1.5px solid ${m.color}`, boxShadow: `0 0 5px 1px ${m.color}` }} />
              <span style={{ color: '#e2e8f0', fontSize: 7, fontFamily: 'monospace', fontWeight: 'bold', textShadow: '0 0 4px #000, 0 0 8px #000' }}>
                {m.label.split(' ').slice(0, 2).join(' ').toUpperCase()}
              </span>
            </div>
          )
        });
      });
    }

    // ── LIVE OSINT: FIRMS Thermal Anomalies (fires/explosions) ─────────────
    if (channels.firms) {
      thermalMarkers.forEach(m => {
        rings.push({ lat: m.lat, lng: m.lng, maxR: 0.5, propagationSpeed: m.ringSpeed * 0.15, repeatPeriod: 5000, color: m.ringColor });
        elements.push({
          lat: m.lat, lng: m.lng,
          html: renderToString(
            <div style={{ transform: 'translate(-50%,-50%)', pointerEvents: 'auto', display: 'flex', alignItems: 'center', gap: 3, cursor: 'pointer' }}>
              <div style={{ width: 3, height: 3, background: '#fff', borderRadius: '50%', border: '1.5px solid #fb923c', boxShadow: '0 0 4px 1px #fb923c' }} />
              <span style={{ color: '#fed7aa', fontSize: 7, fontFamily: 'monospace', fontWeight: 'bold', textShadow: '0 0 4px #000' }}>FIRE</span>
            </div>
          )
        });
      });
    }

    // ── LIVE OSINT: Drive docs as intelligence pins ─────────────────────────
    if (channels.drive) {
      driveMarkers.forEach(m => {
        rings.push({ lat: m.lat, lng: m.lng, maxR: 0.4, propagationSpeed: m.ringSpeed * 0.12, repeatPeriod: 7000, color: m.ringColor });
        elements.push({
          lat: m.lat, lng: m.lng,
          html: renderToString(
            <a href={m.webViewLink || '#'} target="_blank" rel="noopener noreferrer" style={{ transform: 'translate(-50%,-50%)', pointerEvents: 'auto', display: 'flex', alignItems: 'center', gap: 4, textDecoration: 'none', cursor: 'pointer' }}>
              <div style={{ width: 4, height: 4, background: '#fff', borderRadius: '50%', border: '1.5px solid #a855f7', boxShadow: '0 0 5px 1px #a855f7' }} />
              <span style={{ color: '#e9d5ff', fontSize: 7, fontFamily: 'monospace', fontWeight: 'bold', textShadow: '0 0 4px #000, 0 0 8px #000' }}>
                {m.label.split(' ')[0].toUpperCase()}
              </span>
            </a>
          )
        });
      });
    }


    // Only bases get HTML markers now
    if (channels.bases) {
      TACTICAL_BASES.forEach(base => {
        elements.push({
          lat: base.lat,
          lng: base.lng,
          size: 20,
          color: base.type === 'airbase' ? '#06b6d4' : '#3b82f6',
          html: renderToString(
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', transform: 'translate(-50%, -50%)', pointerEvents: 'none' }}>
              <div style={{ background: 'rgba(0,0,0,0.8)', border: `1px solid ${base.type === 'airbase' ? '#06b6d4' : '#3b82f6'}`, padding: 5, borderRadius: '50%' }}>
                {base.type === 'airbase' ? <Plane size={14} color="#06b6d4" /> : <ShieldAlert size={14} color="#3b82f6" />}
              </div>
              <div style={{ marginTop: 4, background: 'rgba(0,0,0,0.8)', padding: '2px 6px', borderRadius: 4, color: '#fff', fontSize: 10, border: '1px solid rgba(255,255,255,0.2)', whiteSpace: 'nowrap', fontFamily: 'monospace' }}>
                {base.id.toUpperCase()}
              </div>
            </div>
          )
        });
        // Add radar ping to active headquarters — slow pulse
        if (base.type === 'airbase') {
          rings.push({ lat: base.lat, lng: base.lng, maxR: 0.4, propagationSpeed: 0.15, repeatPeriod: 5000 });
        }
        
        // Agregar información de tropas (tamaño ciudad)
        labels.push({ lat: base.lat, lng: base.lng, text: `${base.troops} TROOPS`, color: 'rgba(16, 185, 129, 0.5)', size: 0.22 });
      });
    }

    // Añadir Infraestructura Crítica y Zonas de Conflicto
    TACTICAL_INFRASTRUCTURE.forEach(infra => {
      if (infra.type === 'conflict') {
        // Red heat map rings for high conflict areas
        rings.push({ lat: infra.lat, lng: infra.lng, maxR: 0.6, propagationSpeed: 0.05, repeatPeriod: 3500, color: 'rgba(239, 68, 68, 0.4)' });
        elements.push({
          lat: infra.lat, lng: infra.lng, size: 20,
          html: renderToString(<div style={{ color: '#ef4444', fontSize: 9, fontWeight: 'bold', fontFamily: 'monospace', textShadow: '0 0 5px red' }}>[ CONFLICT ZONE ]</div>)
        });
      } else {
        // Docks and Pipelines
        elements.push({
          lat: infra.lat, lng: infra.lng, size: 25,
          html: renderToString(
            <div style={{ display:'flex', alignItems:'center', gap:6, padding:'2px 6px', background:'rgba(5,5,10,0.7)', backdropFilter:'blur(4px)', border:'1px solid #eab308', borderRadius:4, pointerEvents:'none', boxShadow:'0 0 10px rgba(234,179,8,0.3)' }}>
              <ShieldAlert size={10} color="#eab308" />
              <span style={{ color:'#eab308', fontSize:9, fontFamily:"'Inter', monospace", fontWeight:600, letterSpacing:1, whiteSpace:'nowrap' }}>
                {infra.name.toUpperCase()}
              </span>
            </div>
          )
        });
      }
    });

    // --- WebGL 3D Markers (Replacing messy HTML tags for cleaner look) ---
    
    // Military Bases
    if (channels.bases) {
      TACTICAL_BASES.forEach(base => {
        objects.push({ ...base, heading: 0 }); // push to customLayerData eventually
        
        // Etiqueta legible a nivel ciudad
        const labelText = base.troops ? `${base.name.toUpperCase()} [${base.troops}]` : base.name.toUpperCase();
        labels.push({ lat: base.lat, lng: base.lng, text: labelText, color: base.type === 'airbase' ? '#06b6d4' : '#3b82f6', size: 0.28 });
        
        // Ping ring — slow
        if (base.type === 'airbase') rings.push({ lat: base.lat, lng: base.lng, maxR: 1.5, propagationSpeed: 0.18, repeatPeriod: 6000 });
      });
    }

    // Dynamic Fleet
    if (channels.naval) {
      TACTICAL_SHIPS.forEach(ship => {
        const position = getInterpolatedPosition(ship.trajectory, timelineDay);
        objects.push({ ...position, ...ship });
        labels.push({ lat: position.lat, lng: position.lng, text: ship.name, color: '#eab308', size: 0.28 });
        rings.push({ lat: position.lat, lng: position.lng, maxR: 0.5, propagationSpeed: 0.12, repeatPeriod: 6000, color: 'rgba(239, 68, 68, 0.4)' });
      });
    }

    // High-Value Maritime Assets (Oil Tankers)
    if (channels.tankers) {
      TACTICAL_OIL_TANKERS.forEach(t => {
        objects.push({ ...t, heading: 45 });
        labels.push({ lat: t.lat, lng: t.lng, text: `${t.flag} ${t.name.toUpperCase()}`, color: '#eab308', size: 0.28 });
        rings.push({ lat: t.lat, lng: t.lng, maxR: 0.5, propagationSpeed: 0.08, repeatPeriod: 8000, color: 'rgba(234,179,8,0.28)' });
      });
    }

    // Warships
    if (channels.warships) {
      TACTICAL_WARSHIPS.forEach(w => {
        objects.push({ ...w, heading: 90 });
        labels.push({ lat: w.lat, lng: w.lng, text: `${w.name.toUpperCase()} [${w.country}]`, color: '#3b82f6', size: 0.28 });
        rings.push({ lat: w.lat, lng: w.lng, maxR: 0.6, propagationSpeed: 0.12, repeatPeriod: 7000, color: 'rgba(59,130,246,0.3)' });
      });
    }

    // Military Aircraft
    if (channels.milAir) {
      TACTICAL_MILITARY_AIRCRAFT.forEach(a => {
        objects.push({ ...a, alt: 0.08, heading: 30 });
        labels.push({ lat: a.lat, lng: a.lng, text: `${a.name.toUpperCase()} · ${a.country}`, color: '#ef4444', size: 0.14 });
        rings.push({ lat: a.lat, lng: a.lng, maxR: 1.2, propagationSpeed: 0.25, repeatPeriod: 5000, color: 'rgba(239,68,68,0.45)' });
      });
    }

    // Executive Jets
    if (channels.execJets) {
      TACTICAL_EXECUTIVE_JETS.forEach(j => {
        objects.push({ ...j, alt: 0.1, heading: 60 });
        labels.push({ lat: j.lat, lng: j.lng, text: `${j.reg} — ${j.owner}`, color: '#a855f7', size: 0.24 });
      });
    }

    // Drones & Helicopters
    if (channels.dronesHelos) {
      TACTICAL_DRONES_HELICOPTERS.forEach(d => {
        const isDrone = d.type === 'drone';
        objects.push({ ...d, alt: isDrone ? 0.15 : 0.05, heading: isDrone ? 120 : 80 });
        labels.push({ lat: d.lat, lng: d.lng, text: d.callsign || d.name.toUpperCase(), color: isDrone ? '#06b6d4' : '#f59e0b', size: 0.26 });
        rings.push({ lat: d.lat, lng: d.lng, maxR: isDrone ? 1.2 : 0.8, propagationSpeed: isDrone ? 0.2 : 0.15, repeatPeriod: isDrone ? 5000 : 6000, color: isDrone ? 'rgba(6,182,212,0.4)' : 'rgba(245,158,11,0.35)' });
      });
    }
    // --- AIS Live Vessel Feed (Real-time) ---
    if (channels.aisLive && liveVessels.length > 0) {
      const TYPE_EMOJI = { oil_tanker: '🛢️', warship: '⚓', cargo: '📦', passenger: '🚢', tug: '⛽', sar: '🆘', highspeed: '⚡', unknown: '🚢' };
      liveVessels.forEach(v => {
        elements.push({
          lat: v.lat, lng: v.lng, size: 20,
          html: renderToString(
            <div style={{ display:'flex', alignItems:'center', gap:4, padding:'2px 6px', background:'rgba(5,5,10,0.6)', backdropFilter:'blur(4px)', border:`1px solid ${v.color || '#64748b'}`, borderRadius:4, pointerEvents:'none' }}>
              <div style={{ width:4, height:4, borderRadius:'50%', background:v.color || '#64748b', boxShadow:`0 0 6px ${v.color || '#64748b'}` }} />
              <span style={{ color:v.color || '#94a3b8', fontSize:8, fontFamily:"'Inter', monospace", fontWeight:500, letterSpacing:0.5, whiteSpace:'nowrap' }}>
                {v.name.slice(0, 16).toUpperCase()}
              </span>
            </div>
          )
        });
        // Speed-proportional ring: faster ships pulse quicker
        const speed = Math.max(v.sog || 0, 0.1);
        rings.push({ lat: v.lat, lng: v.lng, maxR: v.category === 'warship' ? 0.8 : 0.4, propagationSpeed: 0.1 + speed * 0.02, repeatPeriod: 4000 - Math.min(speed * 100, 3000), color: `${v.color || '#64748b'}55` });
      });
    }

    // Add 3D OSINT Flight Radar
    if (channels.flights) {
      TACTICAL_FLIGHTS.forEach(flight => {
        const position = getInterpolatedPosition(flight.trajectory, timelineDay);
        objects.push({ ...position, ...flight });
        labels.push({ lat: position.lat, lng: position.lng, text: flight.name, color: '#a855f7', size: 0.28, alt: (position.alt || 0) + 0.05 });
        rings.push({ lat: position.lat, lng: position.lng, maxR: 0.4, propagationSpeed: 0.15, repeatPeriod: 5000, color: 'rgba(6, 182, 212, 0.4)' });
        const trailPoints = flight.trajectory.filter(p => p.day <= timelineDay);
        if (trailPoints.length > 1) {
          const coords = trailPoints.map(p => [p.lat, p.lng, (p.alt || 0.1) + 0.01]);
          coords.push([position.lat, position.lng, (position.alt || 0.1) + 0.01]);
          paths.push({
            coords: coords,
            color: flight.type === 'vip' ? 'rgba(234, 179, 8, 0.5)' : 'rgba(6, 182, 212, 0.5)'
          });
        }
      });
    }

    // Sistemas Antiaéreos y Bombardeos
    if (channels.defense) {
      TACTICAL_AA_SYSTEMS.forEach(aa => {
        objects.push({ lat: aa.lat, lng: aa.lng, alt: 0.02, heading: 0, ...aa });
        // Scale down the SAM radar rings drastically to prevent graphic overlap on the globe surface
        const ringSize = Math.max(0.1, Math.min(aa.radius / 1200, 0.4)); 
        rings.push({ lat: aa.lat, lng: aa.lng, maxR: ringSize, propagationSpeed: 0.2, repeatPeriod: 4000, color: 'rgba(16, 185, 129, 0.2)' });
      });

      TACTICAL_STRIKES.forEach(strike => {
        // Solo mostrar la explosión si el timelineDay está cerca de la fecha de ataque (+/- 1.5 días)
        if (Math.abs(timelineDay - strike.day) < 1.5) {
          // Anillo de explosión — calmado
          rings.push({ lat: strike.lat, lng: strike.lng, maxR: 0.5, propagationSpeed: 0.3, repeatPeriod: 4000, color: 'rgba(239, 68, 68, 0.6)' });
          
          elements.push({
            lat: strike.lat,
            lng: strike.lng,
            size: 35,
            color: '#ef4444',
            html: renderToString(
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', transform: 'translate(-50%, -50%)', pointerEvents: 'none' }}>
                <style>{`@keyframes pinger { 0% { transform: scale(0.9); opacity: 0.8; } 100% { transform: scale(1.4); opacity: 0; } }`}</style>
                <div style={{ background: 'rgba(239, 68, 68, 0.8)', border: '2px solid #fff', padding: 8, borderRadius: '50%', boxShadow: '0 0 12px #ef444466' }}>
                  <ShieldAlert size={20} color="#fff" />
                  <div style={{position:'absolute', top:0, left:0, width:'100%', height:'100%', borderRadius:'50%', background:'rgba(239,68,68,0.3)', animation:'pinger 3s ease-out infinite'}}></div>
                </div>
                <div style={{ marginTop: 4, background: 'rgba(0,0,0,0.9)', padding: '2px 6px', borderRadius: 4, color: '#fca5a5', fontSize: 13, border: '1px solid rgba(239, 68, 68, 0.7)', whiteSpace: 'nowrap', fontFamily: 'monospace', fontWeight: 'bold' }}>
                  [ BOMBARDEO: {strike.target.toUpperCase()} ]
                </div>
              </div>
            )
          });
        }
      });
    }

    // Misiles Balísticos e intercepciones en tiempo real
    if (channels.defense) {
      TACTICAL_MISSILES.forEach(missile => {
        arcs.push(missile);
      });
    }
    // Añadir marcadores de objetivo estratégico
    if (channels.defense) {
      TACTICAL_GOALS.forEach(goal => {
        elements.push({
          lat: goal.lat,
          lng: goal.lng,
          size: 12,
          html: renderToString(
            <div style={{ color: '#ffd700', fontSize: 10, fontWeight: 'bold', textShadow: '0 0 8px #ffd700', fontFamily: "'Space Mono', monospace" }}>OBJETIVO</div>
          )
        });
      });
    }

    // --- Phase 11: Geopolitical Nomenclature & Boundaries (Country Names) ---
    if (countries && countries.features) {
      countries.features.forEach(f => {
        const p = f.properties;
        if (p.LABEL_Y && p.LABEL_X && p.ADMIN) {
          labels.push({
            lat: p.LABEL_Y,
            lng: p.LABEL_X,
            text: p.ADMIN.toUpperCase(),
            color: 'rgba(255, 255, 255, 0.07)',
            size: 0.2,
            alt: 0.005,
            dotRadius: 0
          });
        }
      });
    }

    // ── CAPA DE CIUDADES ESTRATÉGICAS ────────────────────────────────────
    if (channels.cities) {
      STRATEGIC_CITIES.forEach(city => {
        const cityColor = CITY_COLORS[city.tier];
        const countryLabel = COUNTRY_NAMES[city.country] || city.country;
        // Label formato: CIUDAD · PAÍS
        labels.push({
          lat: city.lat, lng: city.lng,
          text: `${city.name.toUpperCase()} · ${countryLabel.toUpperCase()}`,
          color: cityColor,
          size: city.tier === 'critical' ? 0.32 : city.tier === 'high' ? 0.24 : 0.18,
          alt: 0.018,
          dotRadius: city.tier === 'low' ? 0 : 0.12,
        });
        const ringCfg = CITY_RING_CONFIG[city.tier];
        if (ringCfg) rings.push({ lat: city.lat, lng: city.lng, ...ringCfg, color: `${cityColor}55` });
      });
    }

    setMapHtmlElements(elements);
    setActiveRings(rings);
    setActiveObjects(objects);
    setActiveArcs(arcs);
    setActivePaths(paths);
    setActiveLabels(labels);
  }, [timelineDay, channels, liveVessels, conflictMarkers, thermalMarkers, driveMarkers, countries]);

  // Globe: esfera semitransparente + glow atmosférico para el overlay
  const onGlobeReady = useCallback(() => {
    const globe = globeEl.current;
    if (!globe || !globe.scene) return;
    const scene = globe.scene();
    if (!scene) return;
    try { globe.renderer().setClearColor(0x000000, 0); } catch (_) {}
    const globeMaterial = globe.globeMaterial();
    globeMaterial.color = new THREE.Color(0x010308);
    globeMaterial.emissive = new THREE.Color(0x000000);
    globeMaterial.roughness = 1;
    globeMaterial.transparent = true;
    globeMaterial.opacity = 0.15;
    const geoAtm = new THREE.SphereGeometry(101.5, 64, 64);
    const glow   = new THREE.Mesh(geoAtm, buildAtmosphereMaterial());
    glow.name    = 'nexo-atmosphere';
    if (!scene.getObjectByName('nexo-atmosphere')) scene.add(glow);
    const ambient = new THREE.AmbientLight(0x334466, 0.4);
    ambient.name  = 'nexo-ambient';
    if (!scene.getObjectByName('nexo-ambient')) scene.add(ambient);
    globe.controls().autoRotate    = false;
    globe.controls().enableDamping = true;
    globe.controls().dampingFactor = 0.08;
  }, []);


  // Auto-cámara: volar a nuevo evento GDELT crítico (una vez cada 30s máximo)
  const lastAutoCamRef = useRef(0);
  useEffect(() => {
    if (!globeEl.current || conflictMarkers.length === 0) return;
    const now = Date.now();
    if (now - lastAutoCamRef.current < 30000) return;
    const critical = conflictMarkers.filter(m => m.severity === 'critical');
    if (critical.length === 0) return;
    const target = critical[Math.floor(Math.random() * critical.length)];
    lastAutoCamRef.current = now;
    globeEl.current.controls().autoRotate = false;
    globeEl.current.pointOfView({ lat: target.lat, lng: target.lng, altitude: 1.4 }, 2200);
    // Reanudar rotación después de 8 segundos
    setTimeout(() => {
      if (globeEl.current) globeEl.current.controls().autoRotate = true;
    }, 8000);
  }, [conflictMarkers]);

  // AI alert ticker — rotate through alerts with smooth transition
  const [tickerIdx, setTickerIdx] = useState(0);
  const [tickerVisible, setTickerVisible] = useState(true);
  useEffect(() => {
    const t = setInterval(() => {
      setTickerVisible(false);
      setTimeout(() => {
        setTickerIdx(i => (i + 1) % Math.max(1, aiAlerts.length));
        setTickerVisible(true);
      }, 300);
    }, 7000);
    return () => clearInterval(t);
  }, [aiAlerts.length]);

  // When new alert arrives, jump to it
  useEffect(() => {
    if (aiAlerts.length > 0) {
      setTickerVisible(false);
      setTimeout(() => { setTickerIdx(0); setTickerVisible(true); }, 200);
    }
  }, [aiAlerts.length]);

  const currentAlert = aiAlerts[tickerIdx] || null;
  // Globe3D alerting: pulse when there's a critical alert
  const isAlertingCritical = currentAlert?.severity === 'critical';

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: '100vh', background: 'radial-gradient(ellipse at 40% 60%, #071428 0%, #020810 100%)', overflow: 'hidden' }}>

      {/* Status bar — top right */}
      <div style={{ position: 'absolute', top: 16, right: 16, zIndex: 20, display: 'flex', gap: 8, alignItems: 'center', fontFamily: 'monospace', fontSize: 10 }}>
        {/* OSINT live indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, background: 'rgba(0,0,0,0.7)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 4, padding: '4px 8px', color: osintLoading ? '#f59e0b' : '#22c55e' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: osintLoading ? '#f59e0b' : '#22c55e', display: 'inline-block', boxShadow: `0 0 6px ${osintLoading ? '#f59e0b' : '#22c55e'}` }} />
          OSINT {osintLoading ? 'SWEEP' : `${conflictMarkers.length + thermalMarkers.length} EVT`}
        </div>
        {/* AI indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, background: 'rgba(0,0,0,0.7)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 4, padding: '4px 8px', color: aiConnected ? '#a855f7' : '#64748b' }}>
          {aiConnected ? <Wifi size={10} /> : <WifiOff size={10} />}
          AI {wsMode ? 'WS' : 'POLL'}
        </div>
        {/* Drive indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, background: 'rgba(0,0,0,0.7)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 4, padding: '4px 8px', color: driveMarkers.length > 0 ? '#a855f7' : '#64748b' }}>
          <FileText size={10} />
          DRIVE {driveMarkers.length}
        </div>
        <button onClick={refetch} style={{ background: 'rgba(0,0,0,0.7)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 4, padding: '4px 8px', color: '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
          <RefreshCw size={10} />
        </button>
      </div>

      {/* ── MODO UNIFICADO: Maplibre (globo + ciudad + edificios 3D) ────────── */}
      <div style={{ position: 'absolute', inset: 0, zIndex: 5 }}>
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
            if (ev.severity === 'critical' || ev.type === 'conflict') {
              maplibreRef.current?.flyToEvent(ev.lat, ev.lng, 15);
              setTimeout(() => setDestructionEvent({ ...ev, timestamp: new Date().toISOString() }), 2200);
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
      <div style={{
        position: 'absolute', inset: 0, zIndex: 10,
        pointerEvents: 'none',
        mixBlendMode: 'screen',
      }}>
        <Globe
          ref={globeEl}
          onGlobeReady={onGlobeReady}
          globeImageUrl=""
          showAtmosphere={false}
          showGraticules={false}
          backgroundColor="rgba(0,0,0,0)"

          objectsData={[
            ...activeObjects,
            ...(activeSimulations || []).map(s => ({ ...s, _simMissile: true }))
          ]}
          objectLat="lat"
          objectLng="lng"
          objectAltitude={d => d.alt !== undefined ? d.alt : 0.02}
          objectThreeObject={d => {
            if (d._simMissile) {
              const geo = new THREE.TetrahedronGeometry(0.18, 0);
              const mat = new THREE.MeshBasicMaterial({ color: 0xff4444, wireframe: true });
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
                new THREE.MeshBasicMaterial({ color: '#f59e0b' })
              );
              group.add(core);
              return group;
            }
            return create3DAssetNode(d);
          }}
          customThreeObjectUpdate={(obj, d) => {
            if (d.satrec) {
              Object.assign(obj.position, globeEl.current.getCoords(d.lat, d.lng, d.alt));
            } else {
              update3DAssetNode(obj, d, globeEl);
            }
          }}

          ringsData={activeRings}
          ringColor={t => t.color || 'rgba(6, 182, 212, 0.5)'}
          ringMaxRadius="maxR"
          ringAltitude={0.015}
          ringPropagationSpeed="propagationSpeed"
          ringRepeatPeriod="repeatPeriod"

          arcsData={activeArcs}
          arcStartLat={d => d.startLat}
          arcStartLng={d => d.startLng}
          arcEndLat={d => d.endLat}
          arcEndLng={d => d.endLng}
          arcColor={d => [d.color || 'rgba(239,68,68,0.2)', d.color || 'rgba(234,179,8,1)']}
          arcDashLength={0.15}
          arcDashGap={1.5}
          arcDashInitialGap={d => d._arcGap ?? 0.5}
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
              color: ['rgba(6,182,212,0)', 'rgba(6,182,212,0.3)', 'rgba(6,182,212,0.6)', 'rgba(6,182,212,0.3)', 'rgba(6,182,212,0)'],
            },
          ]}
          pathPoints="coords"
          pathPointLat={p => p[0]}
          pathPointLng={p => p[1]}
          pathPointAlt={p => p[2]}
          pathColor="color"
          pathStroke={1.5}
          pathResolution={2}

          htmlElementsData={[...mapHtmlElements, ...impactHtmlElements]}
          htmlAltitude={0.02}
          htmlElement={d => {
            const el = document.createElement('div');
            el.innerHTML = d.html;
            return el;
          }}

          animateIn={false}
          width={globeSize.w}
          height={globeSize.h}
          rendererConfig={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
        />
      </div>


      {/* Visual Overlay FX */}
      <div className="crt-vignette" />
      <div className="crt-overlay" />
      
      <OmniGlobeHUD
        currentAlert={currentAlert}
        driveActivity={combinedDriveActivity}
        discordActivity={discordActivity}
        aiAlerts={aiAlerts}
      />

      {/* AI Search Panel — floating, toggled with button or "/" key */}
      <AnimatePresence>
        {searchOpen && (
          <AISearchPanel
            isOpen={searchOpen}
            onClose={() => setSearchOpen(false)}
            onPushAlert={pushAlert}
          />
        )}
      </AnimatePresence>

      {/* Destruction Overlay — animación + evidencia Drive al detectar evento crítico */}
      {destructionEvent && (
        <DestructionOverlay
          event={destructionEvent}
          mapRef={{ current: maplibreRef.current?.getMap?.() }}
          driveMarkers={driveMarkers}
          onClose={() => setDestructionEvent(null)}
        />
      )}

      {/* AI Live Ticker — animated transitions between alerts */}
      <div style={{
        position: 'absolute', bottom: 0, left: '50%', transform: 'translateX(-50%)',
        width: '100%',
        borderTop: `1px solid ${currentAlert?.color ? currentAlert.color.replace(/[\d.]+\)$/, '0.35)') : 'rgba(239,68,68,0.35)'}`,
        padding: '7px 16px', zIndex: 30,
        display: 'flex', alignItems: 'center', gap: 12,
        background: 'rgba(4,8,14,0.96)', backdropFilter: 'blur(12px)',
        transition: 'border-color 0.5s ease',
        minHeight: 40,
      }}>
        {/* Severity indicator bar */}
        <motion.div
          animate={{ background: currentAlert?.color || '#ef4444', boxShadow: `0 0 12px ${currentAlert?.color || '#ef4444'}` }}
          transition={{ duration: 0.5 }}
          style={{ width: 3, height: 22, borderRadius: 2, flexShrink: 0 }}
        />

        {/* Alert text with fade transition */}
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <AnimatePresence mode="wait">
            <motion.div
              key={tickerIdx}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: tickerVisible ? 1 : 0, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.28 }}
              style={{ color: '#f1f5f9', fontFamily: "'Space Mono', monospace", fontSize: 11, letterSpacing: 0.3, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}
            >
              <span style={{ color: currentAlert?.color || '#ef4444', fontWeight: 700, textShadow: `0 0 10px ${currentAlert?.color || '#ef4444'}88`, flexShrink: 0 }}>
                {currentAlert?.prefix || '[NEXO INTEL]'}
              </span>
              <span>
                {currentAlert
                  ? currentAlert.text
                  : 'Sistema NEXO inicializando feeds de inteligencia en tiempo real...'}
              </span>
              {lastSweep && (
                <span style={{ color: '#334155', fontSize: 9, flexShrink: 0 }}>
                  SWEEP {lastSweep.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Right-side badges */}
        <div style={{ display: 'flex', gap: 6, flexShrink: 0, alignItems: 'center' }}>
          {discordActivity.length > 0 && (
            <div style={{ background: 'rgba(88,101,242,0.15)', border: '1px solid rgba(88,101,242,0.4)', borderRadius: 4, padding: '2px 7px', color: '#818cf8', fontSize: 9, fontFamily: 'monospace' }}>
              DISC {discordActivity.length}
            </div>
          )}
          {aiAlerts.length > 0 && (
            <div style={{ background: 'rgba(168,85,247,0.15)', border: '1px solid rgba(168,85,247,0.4)', borderRadius: 4, padding: '2px 7px', color: '#c084fc', fontSize: 9, fontFamily: 'monospace' }}>
              {aiAlerts.length} IA
            </div>
          )}
          {/* IA Search button */}
          <motion.button
            whileTap={{ scale: 0.93 }}
            onClick={() => setSearchOpen(s => !s)}
            style={{
              background: searchOpen ? 'rgba(168,85,247,0.25)' : 'rgba(168,85,247,0.08)',
              border: `1px solid rgba(168,85,247,${searchOpen ? 0.5 : 0.25})`,
              borderRadius: 5, padding: '3px 9px', cursor: 'pointer',
              color: '#c084fc', fontSize: 9, fontFamily: 'monospace',
              display: 'flex', alignItems: 'center', gap: 4, transition: 'all 0.2s',
            }}
            title="Abrir IA Search (tecla /)"
          >
            <Search size={10} /> IA SEARCH
          </motion.button>
        </div>
      </div>

      {/* Timeline Slider HUD & Simulation Control — Floating above the ticker */}
      <div style={{ position: 'absolute', bottom: 48, left: '50%', transform: 'translateX(-50%)', width: '70%', maxWidth: 900, background: 'rgba(5,10,15,0.85)', backdropFilter: 'blur(12px)', padding: '12px 24px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)', zIndex: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10, fontFamily: "'Space Mono', monospace", color: 'var(--text)', fontSize: 12 }}>
          <span>Pasado (-30d)</span>
          <span style={{ color: timelineDay > 0 ? '#f97316' : '#22c55e', fontWeight: 'bold' }}>
            {Math.abs(timelineDay) < 0.2 ? "HOY (LIVE)" : timelineDay > 0 ? `SIMULADOR: DÍA +${timelineDay.toFixed(1)}` : `DÍA ${timelineDay.toFixed(1)}`}
          </span>
          <span style={{ color: '#f97316' }}>Futuro (+15d)</span>
        </div>
        <input 
          type="range" 
          min="-30" 
          max="15" 
          step="0.01"
          value={timelineDay} 
          readOnly
          style={{ width: '100%', cursor: 'default', pointerEvents: 'none', accentColor: timelineDay > 0 ? '#f97316' : '#22c55e' }}
        />
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 15, gap: 8, flexWrap: 'wrap' }}>
          {[
            { key: 'naval',      label: 'NAVAL',        color: '#f97316' },
            { key: 'tankers',    label: 'TANKERS',      color: '#eab308' },
            { key: 'warships',   label: 'WARSHIPS',     color: '#3b82f6' },
            { key: 'milAir',     label: 'MIL AIR',      color: '#ef4444' },
            { key: 'execJets',   label: 'VIP JETS',     color: '#a855f7' },
            { key: 'dronesHelos',label: 'DRONES/HELOS', color: '#06b6d4' },
            { key: 'flights',    label: 'FLIGHT INTEL', color: '#06b6d4' },
            { key: 'defense',    label: 'SAM/STRIKE',   color: '#10b981' },
            { key: 'aisLive',    label: `AIS LIVE${liveVessels.length > 0 ? ` (${liveVessels.length})` : ''}`, color: aisConnected ? '#22c55e' : '#64748b' },
          ].map(({ key, label, color }) => (
            <button
              key={key}
              onClick={() => setChannels(c => ({ ...c, [key]: !c[key] }))}
              style={{
                background: channels[key] ? `rgba(${color.replace('#','').match(/../g).map(h=>parseInt(h,16)).join(',')}, 0.18)` : 'transparent',
                border: `1px solid ${color}`, color, padding: '5px 12px', borderRadius: 4,
                fontFamily: "'Space Mono', monospace", fontSize: 9, cursor: 'pointer',
                opacity: channels[key] ? 1 : 0.4, transition: 'opacity 0.2s'
              }}
            >
              {channels[key] ? `✔ ${label}` : label}
            </button>
          ))}
          <button
            onClick={() => { const g = TACTICAL_GOALS[0]; if (globeEl.current && g) globeEl.current.pointOfView({ lat: g.lat, lng: g.lng, altitude: 2 }, 2000); }}
            style={{ background: 'rgba(255,215,0,0.15)', border: '1px solid #ffd700', color: '#ffd700', padding: '5px 12px', borderRadius: 4, fontFamily: "'Space Mono', monospace", fontSize: 9, cursor: 'pointer' }}
          >
            🎯 OBJETIVO
          </button>
          <div style={{ display:'flex', alignItems:'center', background:'transparent', border:'1px solid #10b981', color:'#10b981', padding:'5px 12px', borderRadius:4, fontFamily:"'Space Mono', monospace", fontSize:9 }}>
            <span style={{ display:'inline-block', width:6, height:6, background:'#10b981', borderRadius:'50%', marginRight:6, animation:'blink-dot 4s ease-in-out infinite' }} />
            {timelineDay > 0 ? 'PREDICCIÓN IA' : 'HISTÓRICO LIVE'}
          </div>
        </div>

        {/* OSINT Live layer buttons — second row */}
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 8, gap: 6, flexWrap: 'wrap' }}>
          {[
            { key: 'cities',       label: `CIUDADES (${STRATEGIC_CITIES.length})`, color: '#f97316' },
            { key: 'gdelt',        label: `GDELT (${conflictMarkers.length})`,   color: '#ef4444' },
            { key: 'firms',        label: `THERMAL (${thermalMarkers.length})`,  color: '#fb923c' },
            { key: 'osintFlights', label: `OPENSKY (${liveFlights.length})`,     color: '#06b6d4' },
            { key: 'drive',        label: `DRIVE (${driveMarkers.length})`,      color: '#a855f7' },
          ].map(({ key, label, color }) => (
            <button
              key={key}
              onClick={() => setChannels(c => ({ ...c, [key]: !c[key] }))}
              style={{
                background: channels[key] ? `rgba(${color.replace('#','').match(/../g).map(h=>parseInt(h,16)).join(',')}, 0.15)` : 'transparent',
                border: `1px solid ${color}`, color, padding: '4px 10px', borderRadius: 4,
                fontFamily: "'Space Mono', monospace", fontSize: 9, cursor: 'pointer',
                opacity: channels[key] ? 1 : 0.35, transition: 'opacity 0.2s',
              }}
            >
              {channels[key] ? `● ${label}` : label}
            </button>
          ))}
          <div style={{ display:'flex', alignItems:'center', gap: 4, background:'rgba(168,85,247,0.1)', border:'1px solid #a855f7', color:'#a855f7', padding:'4px 10px', borderRadius:4, fontFamily:"'Space Mono', monospace", fontSize:9 }}>
            {aiConnected ? <Wifi size={9} /> : <WifiOff size={9} />}
            IA {aiConnected ? 'LIVE' : 'OFF'}
          </div>
        </div>
      </div>

      {/* ── Phase 13: Polymarket Ticker ── */}
      <div style={{
        position: 'absolute', top: 70, right: 20, width: 220, zIndex: 40,
        background: 'rgba(7,10,18,0.8)', backdropFilter: 'blur(10px)',
        border: '1px solid rgba(6,182,212,0.2)', borderRadius: 8, padding: 12,
        fontFamily: "'Space Mono', monospace"
      }}>
        <div style={{ fontSize: 9, color: '#06b6d4', letterSpacing: 1.5, marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
          <span>POLYMARKET ODDS</span>
          <span style={{ color: '#22c55e' }}>LIVE</span>
        </div>
        {(polyMarkets || []).slice(0, 3).map(m => (
          <div key={m.id} style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 10, color: '#e2e8f0', lineHeight: 1.3, marginBottom: 4 }} className="truncate-2">
              {m.question}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9 }}>
              <span style={{ color: '#22c55e' }}>YES: {Math.round((m.yesPrice || 0) * 100)}%</span>
              <span style={{ color: '#ef4444' }}>NO: {Math.round((m.noPrice || 0) * 100)}%</span>
            </div>
          </div>
        ))}
      </div>

      {/* ── Phase 13: Event Timeline ── */}
      <EventTimeline
        events={impactMarkers}
        onEventClick={(ev) => {
          if (globeEl.current) {
            globeEl.current.pointOfView({ lat: ev.lat, lng: ev.lng, altitude: 1.2 }, 1500);
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
          relatedEvents={impactMarkers.filter(m => m.country === evidenceEvent.country && m.id !== evidenceEvent.id)}
        />
      )}
    </div>
  );
};

export default OmniGlobe;
