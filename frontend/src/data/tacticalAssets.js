import * as THREE from 'three';

// Datos de Inteligencia Táctica (OSINT / INSS Marzo 2026)

export const TACTICAL_BASES = [
  // Middle East
  { id: 'al-udeid', name: 'Al Udeid Air Base', type: 'airbase', country: 'Qatar', lat: 25.116, lng: 51.315, troops: '10,000', assets: 'F-35, C-17' },
  { id: 'nsa-bahrain', name: 'NSA Bahrain', type: 'naval', country: 'Bahrain', lat: 26.210, lng: 50.606, troops: '9,000', assets: '5th Fleet HQ' },
  { id: 'muwaffaq-salti', name: 'Muwaffaq Salti Base', type: 'airbase', country: 'Jordan', lat: 31.835, lng: 36.786, troops: '3,000', assets: 'F-15E Strike Eagles' },
  // Europe / Ukraine War
  { id: 'kyiv-hq', name: 'Kyiv Command', type: 'airbase', country: 'Ukraine', lat: 50.45, lng: 30.52, troops: 'HQ', assets: 'Patriot' },
  { id: 'rzeszow-hub', name: 'Rzeszów-Jasionka', type: 'airbase', country: 'Poland', lat: 50.11, lng: 22.01, troops: 'NATO', assets: 'Logistics Hub' },
  { id: 'moscow-hq', name: 'Moscow MoD', type: 'naval', country: 'Russia', lat: 55.75, lng: 37.61, troops: 'HQ', assets: 'Command' },
  { id: 'tehran-hq', name: 'Tehran IRGC', type: 'naval', country: 'Iran', lat: 35.68, lng: 51.38, troops: 'HQ', assets: 'Shahed Assembly' },
];

const generateTrajectory = (startLat, startLng, endLat, endLng, pastDays = 30, futureDays = 15, baseAlt = 0) => {
  const points = [];
  const totalDays = pastDays + futureDays;
  for (let i = 0; i <= totalDays; i++) {
    const progress = i / totalDays;
    const curve = Math.sin(progress * Math.PI) * 2; 
    
    // Calculate heading (yaw) towards the target
    const heading = Math.atan2(endLng - startLng, endLat - startLat) * (180 / Math.PI);
    
    // Altitude arcs for flights, 0 for ships
    const altitude = baseAlt > 0 ? baseAlt + (Math.sin(progress * Math.PI) * 0.05) : 0;

    points.push({
      day: i - pastDays,
      lat: startLat + (endLat - startLat) * progress + curve,
      lng: startLng + (endLng - startLng) * progress,
      alt: altitude,
      heading: heading
    });
  }
  return points;
};

export const TACTICAL_SHIPS = [
  // Flota Operativa Real de EE.UU. (Mar Rojo / Golfo de Omán)
  { id: 'cvn-69', name: 'USS Dwight Eisenhower (CVN-69)', type: 'carrier', trajectory: generateTrajectory(12.0, 45.0, 20.0, 38.0, 30, 15, 0) },
  // Black Sea Fleet
  { id: 'admiral-makarov', name: 'Admiral Makarov', type: 'warship', trajectory: generateTrajectory(44.6, 33.5, 43.5, 39.5, 30, 15, 0) }, // Sevastopol to Novorossiysk
  // Barcos Comerciales y Petroleros Importantes (Históricos Recientes)
  { id: 'marlin-l', name: 'Marlin Luanda (Oil Tanker)', type: 'commercial', trajectory: generateTrajectory(26.0, 56.0, 12.0, 43.0, 30, 15, 0) },
  { id: 'msc-aries', name: 'MSC Aries (Seized)', type: 'commercial', trajectory: generateTrajectory(25.0, 55.0, 25.0, 55.0, 30, 15, 0) }, // Estático / Incautado
];

export const TACTICAL_FLIGHTS = [
  // Llamadas (Callsigns) Históricos Verificables OSINT (y fotos de drones captadas)
  { id: 'forte11', name: 'FORTE11 (RQ-4 Global Hawk)', type: 'drone', trajectory: generateTrajectory(37.4, 14.9, 43.0, 34.0, 30, 15, 0.15) }, // Sigonella a Mar Negro
  { id: 'homer11', name: 'HOMER11 (RC-135W Rivet Joint)', type: 'military', trajectory: generateTrajectory(25.116, 51.315, 27.5, 51.0, 30, 15, 0.12) }, // Al Udeid a Golfo Pérsico
  { id: 'sam28000', name: 'SAM28000 (US Air Force One)', type: 'vip', trajectory: generateTrajectory(38.89, -77.0, 31.7, 35.2, 30, 15, 0.2) }, // Vuelo Presidencial
  // Logistics USA (Mapa INSS animado)
  { id: 'c17-logistics', name: 'C-17 Globemaster III', type: 'military', trajectory: generateTrajectory(25.11, 51.31, 31.83, 36.78, 30, 15, 0.1) }, // De Qatar a Jordania
  // Ukraine Logistics
  { id: 'nato-logistics', name: 'NATO Supply Route', type: 'military', trajectory: generateTrajectory(50.11, 22.01, 50.45, 30.52, 30, 15, 0.08) }, // Rzeszow to Kyiv
  { id: 'shahed-bridge', name: 'IL-76 Cargo', type: 'military', trajectory: generateTrajectory(35.68, 51.38, 55.75, 37.61, 30, 15, 0.12) }, // Tehran to Moscow
];

// Sistemas de Defensa Antiaérea (Radar Domes) extraídos de análisis satelital / Google Photos
export const TACTICAL_AA_SYSTEMS = [
  { id: 'patriot-erbil', name: 'Patriot PAC-3', type: 'aa_system', lat: 36.19, lng: 44.0, radius: 150 },
  { id: 'thaad-uae', name: 'THAAD Battery', type: 'aa_system', lat: 24.249, lng: 54.547, radius: 200 },
  { id: 'iron-dome-eilat', name: 'Iron Dome', type: 'aa_system', lat: 29.558, lng: 34.948, radius: 70 },
  { id: 's400-khm', name: 'S-400 (Khmeimim)', type: 'aa_system', lat: 35.41, lng: 35.94, radius: 400 },
  // Ukraine
  { id: 'patriot-kyiv', name: 'Patriot PAC-3', type: 'aa_system', lat: 50.45, lng: 30.52, radius: 150 },
  { id: 's400-crimea', name: 'S-400 (Dzhankoi)', type: 'aa_system', lat: 45.71, lng: 34.39, radius: 400 },
];

export const TACTICAL_STRIKES = [
  // Bombardeos y ataques pasados y simulados/predichos
  { id: 'strike-hodeidah', target: 'Houthi Radar', type: 'bombing', lat: 14.79, lng: 42.95, day: -5 },
  { id: 'strike-sanaa', target: 'Drone Assembly', type: 'bombing', lat: 15.36, lng: 44.19, day: -2 },
  { id: 'strike-mayadin', target: 'IRGC Depot', type: 'bombing', lat: 35.01, lng: 40.45, day: 3 }, // Predicción
];

// Infraestructura Crítica y Zonas de Conflicto (Etiquetado desde Drive Photos)
export const TACTICAL_INFRASTRUCTURE = [
  // Muelles y Oleoductos
  { id: 'port-hodeidah', name: 'Port of Hodeidah (Dock)', type: 'dock', lat: 14.83, lng: 42.93 },
  { id: 'ras-tanura', name: 'Ras Tanura (Pipeline)', type: 'pipeline', lat: 26.64, lng: 50.15 },
  // Zonas Rojas de Conflicto Constante
  { id: 'gaza-strip', name: 'Gaza / Rafah Zone', type: 'conflict', lat: 31.27, lng: 34.25 },
  { id: 'south-lebanon', name: 'Southern Lebanon', type: 'conflict', lat: 33.27, lng: 35.39 },
  // Nuevas Zonas de Conflicto añadidas
  { id: 'aleppo-syria', name: 'Aleppo (Syria)', type: 'conflict', lat: 36.20, lng: 37.16 },
  { id: 'mosul-iraq', name: 'Mosul (Iraq)', type: 'conflict', lat: 36.34, lng: 43.13 },
  { id: 'hodeidah-yemen', name: 'Hodeidah (Yemen)', type: 'conflict', lat: 14.80, lng: 42.95 },
  // Hotspots Globales (Importados de Mapa.jsx)
  { id: 'taiwan-strait', name: 'Taiwan Strait (PLA Drill)', type: 'conflict', lat: 24.0, lng: 121.0 },
  { id: 'ukraine-east', name: 'Ukraine (Eastern Front)', type: 'conflict', lat: 48.5, lng: 37.5 },
  { id: 'sudan-civil-war', name: 'Sudan (RSF vs SAF)', type: 'conflict', lat: 15.0, lng: 30.0 },
  { id: 'venezuela-crisis', name: 'Venezuela Crisis', type: 'conflict', lat: 8.0, lng: -66.0 },
  { id: 'south-china-sea', name: 'South China Sea (Scarborough)', type: 'conflict', lat: 12.0, lng: 114.0 },
  { id: 'dprk-icbm', name: 'North Korea (Punggye-ri)', type: 'conflict', lat: 41.28, lng: 129.08 }
];

// Meta / objetivo estratégico para animación de mapa
export const TACTICAL_GOALS = [
  { id: 'goal-1', name: 'Objetivo Estratégico', type: 'goal', lat: 30.0, lng: 45.0 }
];

// =====================================================================
// NUEVAS CATEGORÍAS DE ACTIVOS — Alta Fidelidad (RTX 3060 GPU Map)
// =====================================================================

export const TACTICAL_OIL_TANKERS = [
  { id: 'tanker-1', name: 'M/T Al‑Mansur', type: 'oil_tanker', lat: 22.5, lng: 44.0, flag: '🇸🇦', cargo: 'Crude Oil' },
  { id: 'tanker-2', name: 'M/T Kuwait Star', type: 'oil_tanker', lat: 25.0, lng: 51.5, flag: '🇰🇼', cargo: 'Crude Oil' },
  { id: 'tanker-3', name: 'Marlin Luanda', type: 'oil_tanker', lat: 13.5, lng: 43.5, flag: '🇦🇴', cargo: 'Crude Oil', note: 'Attacked Jan 2024' },
  { id: 'tanker-4', name: 'MSC Ruby', type: 'oil_tanker', lat: 14.0, lng: 42.5, flag: '🇱🇧', cargo: 'LPG' },
  { id: 'tanker-5', name: 'Sounion (Houthi Attack)', type: 'oil_tanker', lat: 15.2, lng: 42.8, flag: '🇬🇷', cargo: 'Crude Oil', note: 'Hit Aug 2024' },
];

export const TACTICAL_MILITARY_AIRCRAFT = [
  { id: 'f15-1', name: 'F‑15E Strike Eagle', type: 'military_aircraft', lat: 30.0, lng: 45.0, country: 'USA', unit: '494th FS' },
  { id: 'su57-1', name: 'Su‑57 Felon', type: 'military_aircraft', lat: 35.0, lng: 50.0, country: 'Russia', unit: 'VKS' },
  { id: 'f35-1', name: 'F‑35I Adir', type: 'military_aircraft', lat: 32.0, lng: 35.0, country: 'Israel', unit: 'IAF 140th Sqn' },
  { id: 'b52-1', name: 'B‑52H Stratofortress', type: 'military_aircraft', lat: 20.0, lng: 65.0, country: 'USA', unit: '5th BW Diego Garcia' },
  { id: 'rc135-1', name: 'RC‑135W Rivet Joint', type: 'military_aircraft', lat: 27.5, lng: 51.0, country: 'USA', callsign: 'HOMER11' },
];

export const TACTICAL_EXECUTIVE_JETS = [
  { id: 'g650-1', name: 'Gulfstream G650', type: 'executive_jet', lat: 28.0, lng: 48.0, reg: 'M-BFAM', owner: 'Gulf Royalty' },
  { id: 'fj7x-1', name: 'Dassault Falcon 7X', type: 'executive_jet', lat: 32.0, lng: 46.0, reg: 'HZ-MF1', owner: 'Saudi MoD' },
];

export const TACTICAL_DRONES_HELICOPTERS = [
  { id: 'rq4-1', name: 'RQ‑4 Global Hawk', type: 'drone', lat: 37.4, lng: 14.9, country: 'USA', callsign: 'FORTE11' },
  { id: 'mq9-1', name: 'MQ‑9 Reaper', type: 'drone', lat: 25.0, lng: 43.0, country: 'USA', callsign: 'JAKE21' },
  { id: 'shahed-1', name: 'Shahed‑136', type: 'drone', lat: 34.0, lng: 48.0, country: 'Iran', note: 'One‑way attack UAV' },
  { id: 'ah64-1', name: 'AH‑64E Apache', type: 'helicopter', lat: 29.5, lng: 47.0, country: 'Kuwait', unit: 'KAF' },
  { id: 'ch47-1', name: 'CH‑47F Chinook', type: 'helicopter', lat: 31.8, lng: 36.7, country: 'USA', unit: '101st' },
];

export const TACTICAL_WARSHIPS = [
  // INDOPACOM & CENTCOM active fleet OSINT (Approximate current coordinates)
  { id: 'cvn72', name: 'USS Abraham Lincoln (CVN‑72)', type: 'carrier', lat: 24.5, lng: 58.5, country: 'USA', class: 'Carrier' }, // Gulf of Oman
  { id: 'cvn71', name: 'USS Theodore Roosevelt (CVN‑71)', type: 'carrier', lat: 14.5, lng: 114.0, country: 'USA', class: 'Carrier' }, // South China Sea
  { id: 'cvn69', name: 'USS Dwight Eisenhower (CVN‑69)', type: 'carrier', lat: 36.8, lng: -76.3, country: 'USA', class: 'Carrier' }, // Norfolk (Maintenance Phase)
  { id: 'ddg109', name: 'USS Jason Dunham (DDG‑109)', type: 'warship', lat: 13.5, lng: 44.0, country: 'USA', class: 'Destroyer' },
  { id: 'hms-diamond', name: 'HMS Diamond (D34)', type: 'warship', lat: 14.0, lng: 43.5, country: 'UK', class: 'Destroyer' },
  { id: 'fr-alsace', name: 'FS Alsace (D656)', type: 'warship', lat: 15.0, lng: 44.5, country: 'France', class: 'Frigate' },
];

// Simulador de Misiles Balísticos e Intercepciones (Alerta Telegram)
export const TACTICAL_MISSILES = [
  // Yemen (Sanaa) a Eilat (Intercepción Iron Dome)
  { startLat: 15.36, startLng: 44.19, endLat: 29.55, endLng: 34.94, color: ['#ef4444', '#10b981'] },
  // Irán a Israel (Barrera)
  { startLat: 35.68, startLng: 51.38, endLat: 31.76, endLng: 35.21, color: ['#ef4444', '#f97316'] },
  // Líbano a Norte de Israel
  { startLat: 33.27, startLng: 35.39, endLat: 32.79, endLng: 34.98, color: ['#ef4444', '#ef4444'] }
];

export const getInterpolatedPosition = (trajectory, currentDayFloat) => {
  if (!trajectory || trajectory.length === 0) return {lat: 0, lng: 0, alt: 0, heading: 0};
  if (currentDayFloat <= trajectory[0].day) return trajectory[0];
  if (currentDayFloat >= trajectory[trajectory.length - 1].day) return trajectory[trajectory.length - 1];

  const p1 = trajectory.slice().reverse().find(p => p.day <= currentDayFloat);
  const p2 = trajectory.find(p => p.day > currentDayFloat);
  
  if (!p1) return p2 || trajectory[0];
  if (!p2) return p1;

  const ratio = (currentDayFloat - p1.day) / (p2.day - p1.day);
  return {
    lat: p1.lat + (p2.lat - p1.lat) * ratio,
    lng: p1.lng + (p2.lng - p1.lng) * ratio,
    alt: (p1.alt || 0) + ((p2.alt || 0) - (p1.alt || 0)) * ratio,
    heading: p1.heading // keep starting heading for simplicity
  };
};

// --- Fabricador de 3D Meshes (Hologramas Tácticos Volumétricos) para react-globe.gl ---
export const create3DAssetNode = (d) => {
  const group = new THREE.Group();
  
  // Asignación de colores
  let colorStr = '#ef4444'; // Red (Hostile/Default)
  let emissiveIntensity = 1.0;
  
  if (d.type === 'carrier' || d.type === 'warship') colorStr = '#3b82f6'; // Blue
  else if (d.type === 'commercial' || d.type === 'oil_tanker') colorStr = '#eab308'; // Yellow
  else if (d.type === 'vip' || d.type === 'executive_jet') colorStr = '#a855f7'; // Purple
  else if (d.type === 'aa_system') colorStr = '#10b981'; // Green
  else if (d.type === 'airbase' || d.type === 'naval') colorStr = '#06b6d4'; // Base Cyan
  else if (d.type === 'drone') colorStr = '#06b6d4'; // Cyan
  else if (d.type === 'military' || d.type === 'military_aircraft' || d.type === 'helicopter') colorStr = '#ef4444'; // Red

  // Material de wireframe "holográfico"
  const mat = new THREE.MeshBasicMaterial({ color: colorStr, transparent: true, opacity: 0.35, depthWrite: false, blending: THREE.AdditiveBlending });
  const edgeMat = new THREE.LineBasicMaterial({ color: colorStr, transparent: true, opacity: 0.9 });
  
  const createHoloShape = (geometry, scaleY = 1, offsetY = 0) => {
    const mesh = new THREE.Mesh(geometry, mat);
    const edges = new THREE.EdgesGeometry(geometry);
    const lines = new THREE.LineSegments(edges, edgeMat);
    mesh.add(lines);
    mesh.scale.set(1, scaleY, 1);
    mesh.position.y = offsetY;
    return mesh;
  };

  // 1. CARRIERS / WARSHIPS / TANKERS: Rombo naval alargado (Octahedron achatado)
  if (['carrier', 'warship', 'commercial', 'oil_tanker'].includes(d.type)) {
    const size = d.type === 'carrier' ? 1.5 : 1.0;
    const geom = new THREE.OctahedronGeometry(0.6 * size, 0);
    const shape = createHoloShape(geom, 0.4, 0.2); // flat like a ship
    const ringMat = new THREE.MeshBasicMaterial({ color: colorStr, side: THREE.DoubleSide, transparent: true, opacity: 0.6, blending: THREE.AdditiveBlending });
    const ring = new THREE.Mesh(new THREE.RingGeometry(0.7 * size, 0.8 * size, 32), ringMat);
    ring.rotation.x = Math.PI / 2;
    ring.position.y = 0.05;
    group.add(shape, ring);
    group.userData = { type: 'naval', spinPhase: Math.random() * Math.PI, ringPhase: 0 };
  } 
  
  // 2. AIRCRAFT / DRONES: Pirámide voladora apuntando al frente
  else if (['drone', 'military', 'military_aircraft', 'executive_jet', 'helicopter', 'vip'].includes(d.type)) {
    const isDrone = d.type === 'drone';
    const size = isDrone ? 0.7 : 1.0;
    const geom = new THREE.TetrahedronGeometry(0.8 * size, 0);
    const shape = createHoloShape(geom, 1, 0);
    shape.rotation.x = -Math.PI / 4;
    shape.rotation.y = Math.PI / 4;
    
    if (isDrone) {
      const shapeCore = createHoloShape(geom, 1, 0);
      shapeCore.scale.set(0.5, 0.5, 0.5);
      shapeCore.rotation.set(-Math.PI/4, Math.PI/4, Math.PI); 
      group.add(shapeCore);
    }
    
    group.add(shape);
    group.userData = { type: 'air', spinPhase: 0, floatPhase: Math.random() * Math.PI * 2 };
  }
  
  // 3. AA SYSTEMS : Domo Radar
  else if (d.type === 'aa_system') {
    const geom = new THREE.SphereGeometry(1.2, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2);
    const shape = createHoloShape(geom, 1, 0);
    const coneGeom = new THREE.ConeGeometry(0.4, 2, 4);
    const radarBeam = new THREE.Mesh(coneGeom, new THREE.MeshBasicMaterial({ color: colorStr, transparent: true, opacity: 0.15, blending: THREE.AdditiveBlending }));
    radarBeam.position.y = 1;
    radarBeam.rotation.x = Math.PI/2 - 0.5;
    group.add(shape, radarBeam);
    group.userData = { type: 'radar', spinPhase: 0, beamRef: radarBeam };
  }

  // 4. BASES / CITIES: Cilindro o Hexágono rotante
  else {
    const geom = new THREE.CylinderGeometry(0.6, 0.6, 1.5, 6);
    const shape = createHoloShape(geom, 1, 0.75);
    group.add(shape);
    group.userData = { type: 'structure', spinPhase: 0 };
  }

  // Orient trajectory
  if (d.heading !== undefined) group.rotation.y = (d.heading * Math.PI) / 180;
  
  // City-level scale — small enough not to clutter at globe zoom
  group.scale.set(0.65, 0.65, 0.65);
  return group;
};

// Continuous Animation Tick
export const update3DAssetNode = (obj, d, globeEl) => {
  if (globeEl && globeEl.current) {
    Object.assign(obj.position, globeEl.current.getCoords(d.lat, d.lng, d.alt !== undefined ? d.alt : 0.02));
  }

  if (obj.userData) {
    if (obj.userData.type === 'air') {
      obj.userData.floatPhase += 0.018; // was 0.05 — slower float
      obj.children.forEach(c => { c.rotation.y += 0.006; }); // was 0.02
      const pulse = 1 + Math.sin(obj.userData.floatPhase) * 0.06; // was 0.1
      obj.scale.set(0.65 * pulse, 0.65 * pulse, 0.65 * pulse); // was 1.4
    } 
    else if (obj.userData.type === 'naval') {
      obj.userData.ringPhase += 0.008; // was 0.03
      obj.userData.spinPhase += 0.003; // was 0.01
      const ring = obj.children[1];
      if (ring) {
        ring.scale.set(1 + Math.sin(obj.userData.ringPhase)*0.08, 1 + Math.sin(obj.userData.ringPhase)*0.08, 1); // was 0.15
        ring.material.opacity = 0.4 - (Math.sin(obj.userData.ringPhase)*0.15); // was 0.6/0.3
      }
      obj.children[0].position.y = 0.2 + Math.sin(obj.userData.spinPhase) * 0.03; // was 0.05
    }
    else if (obj.userData.type === 'radar') {
      if (obj.userData.beamRef) obj.userData.beamRef.rotation.y += 0.012; // was 0.04
    }
    else if (obj.userData.type === 'structure') {
      obj.children.forEach(c => { c.rotation.y -= 0.003; }); // was 0.01
    }
  }
};
