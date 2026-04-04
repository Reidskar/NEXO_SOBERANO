/**
 * NEXO SOBERANO — Critical Infrastructure Database
 * Sources: WRI Global Power Plant Database, OpenGridWorks, OSINT
 * Used for: real-time confrontation simulation & structural loss modeling
 */

// ── FUEL TYPE CONFIG ──────────────────────────────────────────────────────────
export const FUEL_CONFIG = {
  Nuclear:     { color: '#f0abfc', icon: '☢',  threat: 'CATASTROPHIC', baseRadius: 50  },
  Hydro:       { color: '#60a5fa', icon: '💧', threat: 'HIGH',         baseRadius: 20  },
  Gas:         { color: '#fbbf24', icon: '🔥', threat: 'HIGH',         baseRadius: 10  },
  Coal:        { color: '#94a3b8', icon: '⬛', threat: 'MODERATE',     baseRadius: 8   },
  Oil:         { color: '#f97316', icon: '🛢',  threat: 'MODERATE',     baseRadius: 8   },
  Wind:        { color: '#34d399', icon: '💨', threat: 'LOW',          baseRadius: 5   },
  Solar:       { color: '#fde68a', icon: '☀',  threat: 'LOW',          baseRadius: 3   },
  Biomass:     { color: '#86efac', icon: '🌿', threat: 'LOW',          baseRadius: 4   },
  Storage:     { color: '#c084fc', icon: '⚡', threat: 'MODERATE',     baseRadius: 6   },
  Other:       { color: '#e2e8f0', icon: '⚙',  threat: 'LOW',          baseRadius: 5   },
};

export const STATUS_CONFIG = {
  active:      { color: '#10b981', label: 'OPERATIONAL' },
  damaged:     { color: '#f59e0b', label: 'DAMAGED'     },
  destroyed:   { color: '#ef4444', label: 'DESTROYED'   },
  offline:     { color: '#6b7280', label: 'OFFLINE'     },
};

// ── GLOBAL STRATEGIC POWER PLANTS ─────────────────────────────────────────────
// Curated from WRI Global Power Plant Database (CC BY 4.0)
// Focus: conflict zones, chokepoints, high-value targets
export const POWER_PLANTS = [

  // ── UKRAINE (active conflict zone) ───────────────────────────────────────
  { id: 'ua_zaporizhzhia', name: 'Zaporizhzhia NPP',   country: 'UA', lat: 47.51, lng: 34.58, fuel: 'Nuclear', capacity_mw: 5700,  status: 'damaged',  damage_pct: 100, notes: 'Under Russian control since Mar 2022. All 6 reactors in cold shutdown. IAEA monitoring.' },
  { id: 'ua_khmelnytska', name: 'Khmelnytska NPP',     country: 'UA', lat: 50.30, lng: 26.65, fuel: 'Nuclear', capacity_mw: 2000,  status: 'active',   damage_pct: 0,   notes: 'Operational. 2 reactors active.' },
  { id: 'ua_rivnenska',   name: 'Rivnenska NPP',       country: 'UA', lat: 51.33, lng: 25.89, fuel: 'Nuclear', capacity_mw: 2835,  status: 'active',   damage_pct: 0,   notes: 'Operational. 4 reactors.' },
  { id: 'ua_pivdenno',    name: 'Pivdennoukrainska NPP',country: 'UA', lat: 47.83, lng: 31.22, fuel: 'Nuclear', capacity_mw: 3000,  status: 'active',   damage_pct: 0,   notes: '3 VVER-1000 reactors operational.' },
  { id: 'ua_burshtyn',    name: 'Burshtyn TPP',         country: 'UA', lat: 49.23, lng: 24.65, fuel: 'Coal',    capacity_mw: 2300,  status: 'damaged',  damage_pct: 60,  notes: 'Partially damaged by missile strikes.' },
  { id: 'ua_trypilska',   name: 'Trypilska TPP',        country: 'UA', lat: 50.11, lng: 30.73, fuel: 'Coal',    capacity_mw: 1800,  status: 'destroyed',damage_pct: 100, notes: 'Destroyed by Russian air strike Apr 2024.' },
  { id: 'ua_kryvorizka',  name: 'Kryvorizka TPP',       country: 'UA', lat: 47.88, lng: 33.38, fuel: 'Coal',    capacity_mw: 3000,  status: 'damaged',  damage_pct: 70,  notes: 'Major damage from repeated strikes.' },
  { id: 'ua_kakhovka',    name: 'Kakhovka HPP',          country: 'UA', lat: 46.77, lng: 33.37, fuel: 'Hydro',   capacity_mw: 351,   status: 'destroyed',damage_pct: 100, notes: 'Dam destroyed Jun 2023. 35,000 acres flooded downstream.' },

  // ── MIDDLE EAST / IRAN-US CONFLICT ZONE ─────────────────────────────────
  { id: 'ir_bushehr',     name: 'Bushehr NPP',           country: 'IR', lat: 28.83, lng: 50.89, fuel: 'Nuclear', capacity_mw: 1000,  status: 'active',   damage_pct: 0,   notes: 'Only Iranian NPP. Russian-built VVER-1000. Primary HVT.' },
  { id: 'ir_fordow',      name: 'Fordow FEP (enrichment)',country: 'IR', lat: 34.88, lng: 50.59, fuel: 'Nuclear', capacity_mw: 0,     status: 'active',   damage_pct: 0,   notes: 'Underground uranium enrichment facility. Key strategic target.' },
  { id: 'ir_natanz',      name: 'Natanz Enrichment',     country: 'IR', lat: 33.72, lng: 51.73, fuel: 'Nuclear', capacity_mw: 0,     status: 'active',   damage_pct: 0,   notes: 'Main enrichment complex. Sabotaged 2021 (Stuxnet2). Partially rebuilt.' },
  { id: 'ir_bandarabbas', name: 'Bandar Abbas CCPP',     country: 'IR', lat: 27.20, lng: 56.28, fuel: 'Gas',     capacity_mw: 1100,  status: 'active',   damage_pct: 0,   notes: 'Combined cycle. Powers Strait of Hormuz corridor.' },
  { id: 'ir_isfahan',     name: 'Isfahan Gas PP',         country: 'IR', lat: 32.65, lng: 51.67, fuel: 'Gas',     capacity_mw: 1800,  status: 'active',   damage_pct: 0,   notes: 'Critical to central Iran grid.' },
  { id: 'sa_jubail',      name: 'Jubail PP (Saudi)',      country: 'SA', lat: 27.01, lng: 49.66, fuel: 'Oil',     capacity_mw: 2784,  status: 'active',   damage_pct: 0,   notes: 'Key Gulf grid node. Aramco adjacent.' },
  { id: 'sa_abqaiq',      name: 'Abqaiq Processing',     country: 'SA', lat: 25.93, lng: 49.68, fuel: 'Oil',     capacity_mw: 500,   status: 'active',   damage_pct: 0,   notes: 'Largest crude oil stabilization facility globally. Struck by drones 2019.' },
  { id: 'il_hadera',      name: 'Hadera CCPP (Israel)',   country: 'IL', lat: 32.44, lng: 34.91, fuel: 'Gas',     capacity_mw: 1176,  status: 'active',   damage_pct: 0,   notes: 'Main coastal gas plant powering Tel Aviv grid.' },

  // ── TAIWAN STRAIT ────────────────────────────────────────────────────────
  { id: 'tw_chinshan',    name: 'Chinshan NPP',           country: 'TW', lat: 25.29, lng: 121.59, fuel: 'Nuclear', capacity_mw: 1208, status: 'offline',  damage_pct: 0,   notes: 'Decommissioned 2018-2023. Waste storage active.' },
  { id: 'tw_kuosheng',    name: 'Kuosheng NPP',           country: 'TW', lat: 25.21, lng: 121.66, fuel: 'Nuclear', capacity_mw: 1970, status: 'active',   damage_pct: 0,   notes: '2 BWR reactors. Shutdown vote pending. Key HVT in strait scenario.' },
  { id: 'tw_maanshan',    name: "Ma-anshan NPP",          country: 'TW', lat: 22.00, lng: 120.61, fuel: 'Nuclear', capacity_mw: 1902, status: 'active',   damage_pct: 0,   notes: 'Southern Taiwan. 2 PWR reactors. Critical for southern grid.' },
  { id: 'tw_taichung',    name: 'Taichung Coal PP',       country: 'TW', lat: 24.30, lng: 120.52, fuel: 'Coal',    capacity_mw: 5500, status: 'active',   damage_pct: 0,   notes: 'Largest coal plant in Asia. 10 units. Critical infrastructure.' },
  { id: 'cn_fuqing',      name: 'Fuqing NPP (China)',     country: 'CN', lat: 25.43, lng: 119.39, fuel: 'Nuclear', capacity_mw: 3348, status: 'active',   damage_pct: 0,   notes: '5 operational CPR-1000 + 1 Hualong-1. Directly facing Taiwan strait.' },
  { id: 'cn_ningde',      name: 'Ningde NPP',             country: 'CN', lat: 27.10, lng: 120.22, fuel: 'Nuclear', capacity_mw: 4000, status: 'active',   damage_pct: 0,   notes: '4 CPR-1000 reactors. Key PLA power supply node.' },

  // ── EUROPE (NATO grid) ────────────────────────────────────────────────────
  { id: 'fr_cattenom',    name: 'Cattenom NPP',           country: 'FR', lat: 49.40, lng: 6.22,   fuel: 'Nuclear', capacity_mw: 5200, status: 'active',   damage_pct: 0,   notes: '4 PWR reactors. Powers Luxembourg, Germany border region.' },
  { id: 'fr_paluel',      name: 'Paluel NPP',             country: 'FR', lat: 49.86, lng: 0.63,   fuel: 'Nuclear', capacity_mw: 5320, status: 'active',   damage_pct: 0,   notes: 'Normandy coast. 4 PWR reactors. Key French Atlantic grid.' },
  { id: 'de_boxberg',     name: 'Boxberg Power Station',  country: 'DE', lat: 51.40, lng: 14.61,  fuel: 'Coal',    capacity_mw: 1900, status: 'active',   damage_pct: 0,   notes: 'Largest lignite plant in Germany. Eastern grid anchor.' },
  { id: 'pl_belchatow',   name: 'Bełchatów PP',           country: 'PL', lat: 51.26, lng: 19.33,  fuel: 'Coal',    capacity_mw: 5354, status: 'active',   damage_pct: 0,   notes: 'Largest coal plant in Europe. 12 units. Poland baseload.' },
  { id: 'uk_drax',        name: 'Drax Power Station',     country: 'GB', lat: 53.73, lng: -1.07,  fuel: 'Biomass', capacity_mw: 3960, status: 'active',   damage_pct: 0,   notes: 'Largest power plant UK. Converted from coal to biomass.' },
  { id: 'no_tonstad',     name: 'Tonstad Hydro',          country: 'NO', lat: 58.68, lng: 6.73,   fuel: 'Hydro',   capacity_mw: 960,  status: 'active',   damage_pct: 0,   notes: 'Norway hydro exports to UK via North Sea Link cable.' },

  // ── RUSSIA ────────────────────────────────────────────────────────────────
  { id: 'ru_leningrad',   name: 'Leningrad NPP-2',        country: 'RU', lat: 59.84, lng: 29.08,  fuel: 'Nuclear', capacity_mw: 4800, status: 'active',   damage_pct: 0,   notes: '4 RBMK + 2 VVER-1200 reactors. Powers St. Petersburg.' },
  { id: 'ru_smolensk',    name: 'Smolensk NPP',            country: 'RU', lat: 54.15, lng: 33.23,  fuel: 'Nuclear', capacity_mw: 3000, status: 'active',   damage_pct: 0,   notes: '3 RBMK-1000. Near Ukrainian border. NATO monitoring.' },
  { id: 'ru_kursk',       name: 'Kursk NPP',               country: 'RU', lat: 51.67, lng: 35.60,  fuel: 'Nuclear', capacity_mw: 4000, status: 'active',   damage_pct: 0,   notes: '4 RBMK-1000. 60km from Ukrainian border. Periodically targeted.' },
  { id: 'ru_sayano',      name: 'Sayano-Shushenskaya HPP', country: 'RU', lat: 52.83, lng: 91.37,  fuel: 'Hydro',   capacity_mw: 6400, status: 'active',   damage_pct: 0,   notes: 'Largest hydro in Russia. Previously damaged 2009 accident.' },

  // ── NORTH KOREA / KOREAN PENINSULA ──────────────────────────────────────
  { id: 'kp_yongbyon',    name: 'Yongbyon Nuclear Complex',country: 'KP', lat: 39.80, lng: 125.75, fuel: 'Nuclear', capacity_mw: 0,    status: 'active',   damage_pct: 0,   notes: 'Primary DPRK nuclear weapons complex. 5MW reactor + enrichment.' },

  // ── INDIA-PAKISTAN BORDER ────────────────────────────────────────────────
  { id: 'pk_chashma',     name: 'Chashma NPP',             country: 'PK', lat: 32.39, lng: 71.46,  fuel: 'Nuclear', capacity_mw: 1330, status: 'active',   damage_pct: 0,   notes: '4 Chinese CNP-300/ACPR-1000. On Indus River.' },
  { id: 'in_tarapur',     name: 'Tarapur NPP',             country: 'IN', lat: 19.83, lng: 72.66,  fuel: 'Nuclear', capacity_mw: 1400, status: 'active',   damage_pct: 0,   notes: 'Oldest Indian NPP. 4 BWR/PHWR reactors. Mumbai region grid.' },

  // ── US INFRASTRUCTURE ────────────────────────────────────────────────────
  { id: 'us_diablo',      name: 'Diablo Canyon NPP',       country: 'US', lat: 35.21, lng: -120.85,fuel: 'Nuclear', capacity_mw: 2240, status: 'active',   damage_pct: 0,   notes: 'California only remaining NPP. 2 PWR reactors. Critical CA grid.' },
  { id: 'us_palo_verde',  name: 'Palo Verde NPP',          country: 'US', lat: 33.39, lng: -112.86,fuel: 'Nuclear', capacity_mw: 3942, status: 'active',   damage_pct: 0,   notes: 'Largest US NPP. 3 PWR. Powers AZ-CA-NM grids.' },
  { id: 'us_grand_coulee', name: 'Grand Coulee Dam',       country: 'US', lat: 47.96, lng: -118.98,fuel: 'Hydro',   capacity_mw: 6765, status: 'active',   damage_pct: 0,   notes: 'Largest US power plant. Columbia River. NW grid anchor.' },

  // ── CHINA ─────────────────────────────────────────────────────────────────
  { id: 'cn_three_gorges',name: 'Three Gorges Dam',        country: 'CN', lat: 30.82, lng: 111.00, fuel: 'Hydro',   capacity_mw: 22500,status: 'active',   damage_pct: 0,   notes: 'Largest power plant in the world. 32 generators. Yangtze River.' },
  { id: 'cn_hongyanhe',   name: 'Hongyanhe NPP',           country: 'CN', lat: 39.79, lng: 121.50, fuel: 'Nuclear', capacity_mw: 4400, status: 'active',   damage_pct: 0,   notes: '4 CPR-1000. Northeast China grid. Near North Korean border.' },
];

// ── STRUCTURAL LOSS SIMULATION ────────────────────────────────────────────────
/**
 * Calculates estimated affected population from a plant going offline
 * Based on capacity and regional grid load factor
 */
export function calcOutageImpact(plant) {
  const hoursPerYear = 8760;
  const loadFactor = 0.65;
  const peoplePerMW = 500; // rough: 1 MW ~ 500 households
  const affectedPeople = plant.capacity_mw * peoplePerMW * (1 - (plant.damage_pct || 0) / 100);
  const lostGWh = plant.capacity_mw * loadFactor * (plant.damage_pct || 0) / 100;
  return {
    affected_people: Math.round(affectedPeople),
    lost_gwh_annual: Math.round(lostGWh * hoursPerYear / 1000),
    outage_radius_km: Math.sqrt(plant.capacity_mw / 100) * 8,
  };
}

/**
 * Total losses from destroyed/damaged plants
 */
export function calcTotalLosses() {
  return POWER_PLANTS.reduce((acc, p) => {
    if (p.status === 'destroyed' || p.status === 'damaged') {
      const impact = calcOutageImpact(p);
      acc.lost_mw += p.capacity_mw * (p.damage_pct || 100) / 100;
      acc.affected_people += impact.affected_people;
      acc.plants_down += 1;
    }
    return acc;
  }, { lost_mw: 0, affected_people: 0, plants_down: 0 });
}

// Country name map
export const COUNTRY_NAMES = {
  UA: 'Ukraine', IR: 'Iran', SA: 'Saudi Arabia', IL: 'Israel',
  TW: 'Taiwan', CN: 'China', FR: 'France', DE: 'Germany',
  PL: 'Poland', GB: 'United Kingdom', NO: 'Norway', RU: 'Russia',
  KP: 'North Korea', PK: 'Pakistan', IN: 'India', US: 'United States',
};
