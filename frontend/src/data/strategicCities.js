/**
 * strategicCities.js — Ciudades estratégicas para el OmniGlobe NEXO
 * Tier: critical > high > medium > low
 */

// Mapping ISO-2 → nombre corto de país para labels del mapa
export const COUNTRY_NAMES = {
  IR: 'Irán',     IQ: 'Irak',      PS: 'Palestina', LB: 'Líbano',   YE: 'Yemen',
  SY: 'Siria',    SA: 'Arabia S',  IL: 'Israel',    TR: 'Turquía',   AE: 'Emiratos',
  QA: 'Qatar',    UA: 'Ucrania',   RU: 'Rusia',     BY: 'Belarrús',  MD: 'Moldavia',
  PL: 'Polonia',  LV: 'Letonia',   LT: 'Lituania',  RO: 'Rumania',   RS: 'Serbia',
  KP: 'Corea N',  TW: 'Taiwán',   CN: 'China',     HK: 'Hong Kong', KR: 'Corea S',
  JP: 'Japón',   SG: 'Singapur',  AF: 'Afganistán',PK: 'Pakistán', IN: 'India',
  UZ: 'Uzbekist',MM: 'Myanmar',   PH: 'Filipinas', SD: 'Sudán',     LY: 'Libia',
  SO: 'Somalia',  ML: 'Mali',      NE: 'Niger',     TD: 'Chad',      ET: 'Etiopía',
  EG: 'Egipto',   KE: 'Kenya',     NG: 'Nigeria',   CD: 'Congo',     SN: 'Senegal',
  VE: 'Venezuela',CU: 'Cuba',     CO: 'Colombia',  US: 'EE.UU.',    PA: 'Panamá',
  MX: 'México',  PE: 'Perú',     AR: 'Argentina', BR: 'Brasil',    GB: 'Reino U.',
  FR: 'Francia',  DE: 'Alemania',  BE: 'Bélgica',
};

export const STRATEGIC_CITIES = [
  // ── MEDIO ORIENTE ────────────────────────────────────────────────────
  { id: 'tehran',       name: 'Teherán',      country: 'IR', lat: 35.6892,  lng: 51.3890,  tier: 'critical', region: 'middleeast' },
  { id: 'baghdad',      name: 'Bagdad',        country: 'IQ', lat: 33.3152,  lng: 44.3661,  tier: 'critical', region: 'middleeast' },
  { id: 'gaza',         name: 'Gaza',          country: 'PS', lat: 31.5017,  lng: 34.4668,  tier: 'critical', region: 'middleeast' },
  { id: 'beirut',       name: 'Beirut',        country: 'LB', lat: 33.8938,  lng: 35.5018,  tier: 'critical', region: 'middleeast' },
  { id: 'sanaa',        name: "Sana'a",        country: 'YE', lat: 15.3694,  lng: 44.1910,  tier: 'critical', region: 'middleeast' },
  { id: 'aden',         name: 'Adén',          country: 'YE', lat: 12.7855,  lng: 45.0187,  tier: 'critical', region: 'middleeast' },
  { id: 'mosul',        name: 'Mosul',         country: 'IQ', lat: 36.3350,  lng: 43.1189,  tier: 'high',     region: 'middleeast' },
  { id: 'aleppo',       name: 'Alepo',         country: 'SY', lat: 36.2021,  lng: 37.1343,  tier: 'high',     region: 'middleeast' },
  { id: 'damascus',     name: 'Damasco',       country: 'SY', lat: 33.5102,  lng: 36.2912,  tier: 'high',     region: 'middleeast' },
  { id: 'riyadh',       name: 'Riad',          country: 'SA', lat: 24.6877,  lng: 46.7219,  tier: 'high',     region: 'middleeast' },
  { id: 'telaviv',      name: 'Tel Aviv',      country: 'IL', lat: 32.0853,  lng: 34.7818,  tier: 'critical', region: 'middleeast' },
  { id: 'jerusalem',    name: 'Jerusalén',     country: 'IL', lat: 31.7683,  lng: 35.2137,  tier: 'critical', region: 'middleeast' },
  { id: 'istanbul',     name: 'Estambul',      country: 'TR', lat: 41.0082,  lng: 28.9784,  tier: 'medium',   region: 'middleeast' },
  { id: 'ankara',       name: 'Ankara',        country: 'TR', lat: 39.9334,  lng: 32.8597,  tier: 'medium',   region: 'middleeast' },
  { id: 'abu_dhabi',    name: 'Abu Dabi',      country: 'AE', lat: 24.4539,  lng: 54.3773,  tier: 'medium',   region: 'middleeast' },
  { id: 'doha',         name: 'Doha',          country: 'QA', lat: 25.2854,  lng: 51.5310,  tier: 'medium',   region: 'middleeast' },
  { id: 'hormuz',       name: 'Estrecho Ormuz',country: 'IR', lat: 26.5667,  lng: 56.2500,  tier: 'high',     region: 'middleeast' },

  // ── EUROPA DEL ESTE ──────────────────────────────────────────────────
  { id: 'kyiv',         name: 'Kyiv',          country: 'UA', lat: 50.4501,  lng: 30.5234,  tier: 'critical', region: 'europe' },
  { id: 'kharkiv',      name: 'Járkov',        country: 'UA', lat: 49.9935,  lng: 36.2304,  tier: 'critical', region: 'europe' },
  { id: 'donetsk',      name: 'Donetsk',       country: 'UA', lat: 48.0159,  lng: 37.8029,  tier: 'critical', region: 'europe' },
  { id: 'odesa',        name: 'Odesa',         country: 'UA', lat: 46.4825,  lng: 30.7233,  tier: 'critical', region: 'europe' },
  { id: 'zaporizhzhia', name: 'Zaporizhzhia',  country: 'UA', lat: 47.8388,  lng: 35.1396,  tier: 'critical', region: 'europe' },
  { id: 'moscow',       name: 'Moscú',         country: 'RU', lat: 55.7558,  lng: 37.6173,  tier: 'high',     region: 'europe' },
  { id: 'stpetersburg', name: 'S. Petersburgo',country: 'RU', lat: 59.9343,  lng: 30.3351,  tier: 'medium',   region: 'europe' },
  { id: 'minsk',        name: 'Minsk',         country: 'BY', lat: 53.9045,  lng: 27.5615,  tier: 'high',     region: 'europe' },
  { id: 'chisinau',     name: 'Chișinău',      country: 'MD', lat: 47.0105,  lng: 28.8638,  tier: 'high',     region: 'europe' },
  { id: 'warsaw',       name: 'Varsovia',      country: 'PL', lat: 52.2297,  lng: 21.0122,  tier: 'medium',   region: 'europe' },
  { id: 'riga',         name: 'Riga',          country: 'LV', lat: 56.9460,  lng: 24.1059,  tier: 'medium',   region: 'europe' },
  { id: 'vilnius',      name: 'Vilna',         country: 'LT', lat: 54.6872,  lng: 25.2797,  tier: 'medium',   region: 'europe' },
  { id: 'bucharest',    name: 'Bucarest',      country: 'RO', lat: 44.4268,  lng: 26.1025,  tier: 'low',      region: 'europe' },
  { id: 'belgrade',     name: 'Belgrado',      country: 'RS', lat: 44.7866,  lng: 20.4489,  tier: 'medium',   region: 'europe' },

  // ── ASIA-PACÍFICO ────────────────────────────────────────────────────
  { id: 'pyongyang',    name: 'Pyongyang',     country: 'KP', lat: 39.0392,  lng: 125.7625, tier: 'critical', region: 'asia' },
  { id: 'taipei',       name: 'Taipéi',        country: 'TW', lat: 25.0320,  lng: 121.5654, tier: 'critical', region: 'asia' },
  { id: 'beijing',      name: 'Pekín',         country: 'CN', lat: 39.9042,  lng: 116.4074, tier: 'high',     region: 'asia' },
  { id: 'shanghai',     name: 'Shanghái',      country: 'CN', lat: 31.2304,  lng: 121.4737, tier: 'medium',   region: 'asia' },
  { id: 'hongkong',     name: 'Hong Kong',     country: 'HK', lat: 22.3193,  lng: 114.1694, tier: 'high',     region: 'asia' },
  { id: 'seoul',        name: 'Seúl',          country: 'KR', lat: 37.5665,  lng: 126.9780, tier: 'high',     region: 'asia' },
  { id: 'tokyo',        name: 'Tokio',         country: 'JP', lat: 35.6762,  lng: 139.6503, tier: 'medium',   region: 'asia' },
  { id: 'singapore',    name: 'Singapur',      country: 'SG', lat: 1.3521,   lng: 103.8198, tier: 'low',      region: 'asia' },
  { id: 'kabul',        name: 'Kabul',         country: 'AF', lat: 34.5553,  lng: 69.2075,  tier: 'critical', region: 'asia' },
  { id: 'islamabad',    name: 'Islamabad',     country: 'PK', lat: 33.6844,  lng: 73.0479,  tier: 'high',     region: 'asia' },
  { id: 'karachi',      name: 'Karachi',       country: 'PK', lat: 24.8607,  lng: 67.0011,  tier: 'high',     region: 'asia' },
  { id: 'delhi',        name: 'Nueva Delhi',   country: 'IN', lat: 28.6139,  lng: 77.2090,  tier: 'medium',   region: 'asia' },
  { id: 'mumbai',       name: 'Bombay',        country: 'IN', lat: 19.0760,  lng: 72.8777,  tier: 'medium',   region: 'asia' },
  { id: 'tashkent',     name: 'Taskent',       country: 'UZ', lat: 41.2995,  lng: 69.2401,  tier: 'medium',   region: 'asia' },
  { id: 'yangon',       name: 'Rangún',        country: 'MM', lat: 16.8661,  lng: 96.1951,  tier: 'high',     region: 'asia' },
  { id: 'manila',       name: 'Manila',        country: 'PH', lat: 14.5995,  lng: 120.9842, tier: 'medium',   region: 'asia' },

  // ── ÁFRICA ──────────────────────────────────────────────────────────
  { id: 'khartoum',     name: 'Jartum',        country: 'SD', lat: 15.5007,  lng: 32.5599,  tier: 'critical', region: 'africa' },
  { id: 'tripoli',      name: 'Trípoli',       country: 'LY', lat: 32.9040,  lng: 13.1850,  tier: 'critical', region: 'africa' },
  { id: 'mogadishu',    name: 'Mogadiscio',    country: 'SO', lat: 2.0469,   lng: 45.3182,  tier: 'critical', region: 'africa' },
  { id: 'bamako',       name: 'Bamako',        country: 'ML', lat: 12.6392,  lng: -8.0029,  tier: 'critical', region: 'africa' },
  { id: 'niamey',       name: 'Niamey',        country: 'NE', lat: 13.5137,  lng: 2.1098,   tier: 'critical', region: 'africa' },
  { id: 'ndjamena',     name: "N'Djamena",     country: 'TD', lat: 12.1048,  lng: 15.0441,  tier: 'critical', region: 'africa' },
  { id: 'addisababa',   name: 'Adís Abeba',    country: 'ET', lat: 9.0320,   lng: 38.7469,  tier: 'high',     region: 'africa' },
  { id: 'cairo',        name: 'El Cairo',      country: 'EG', lat: 30.0444,  lng: 31.2357,  tier: 'high',     region: 'africa' },
  { id: 'nairobi',      name: 'Nairobi',       country: 'KE', lat: -1.2921,  lng: 36.8219,  tier: 'medium',   region: 'africa' },
  { id: 'lagos',        name: 'Lagos',         country: 'NG', lat: 6.5244,   lng: 3.3792,   tier: 'medium',   region: 'africa' },
  { id: 'kinshasa',     name: 'Kinsasa',       country: 'CD', lat: -4.3276,  lng: 15.3214,  tier: 'high',     region: 'africa' },
  { id: 'dakar',        name: 'Dakar',         country: 'SN', lat: 14.7167,  lng: -17.4677, tier: 'medium',   region: 'africa' },

  // ── AMÉRICAS ─────────────────────────────────────────────────────────
  { id: 'caracas',      name: 'Caracas',       country: 'VE', lat: 10.4806,  lng: -66.9036, tier: 'critical', region: 'americas' },
  { id: 'havana',       name: 'La Habana',     country: 'CU', lat: 23.1136,  lng: -82.3666, tier: 'high',     region: 'americas' },
  { id: 'bogota',       name: 'Bogotá',        country: 'CO', lat: 4.7110,   lng: -74.0721, tier: 'high',     region: 'americas' },
  { id: 'dc',           name: 'Washington DC', country: 'US', lat: 38.9072,  lng: -77.0369, tier: 'high',     region: 'americas' },
  { id: 'miami',        name: 'Miami',         country: 'US', lat: 25.7617,  lng: -80.1918, tier: 'medium',   region: 'americas' },
  { id: 'panama',       name: 'Panamá',        country: 'PA', lat: 8.9936,   lng: -79.5197, tier: 'medium',   region: 'americas' },
  { id: 'mexico',       name: 'Cd. México',    country: 'MX', lat: 19.4326,  lng: -99.1332, tier: 'medium',   region: 'americas' },
  { id: 'lima',         name: 'Lima',          country: 'PE', lat: -12.0464, lng: -77.0428, tier: 'medium',   region: 'americas' },
  { id: 'buenos_aires', name: 'Bs. Aires',     country: 'AR', lat: -34.6037, lng: -58.3816, tier: 'low',      region: 'americas' },
  { id: 'saopaulo',     name: 'São Paulo',     country: 'BR', lat: -23.5505, lng: -46.6333, tier: 'low',      region: 'americas' },

  // ── OCCIDENTE ────────────────────────────────────────────────────────
  { id: 'london',       name: 'Londres',       country: 'GB', lat: 51.5074,  lng: -0.1278,  tier: 'medium',   region: 'europe' },
  { id: 'paris',        name: 'París',         country: 'FR', lat: 48.8566,  lng: 2.3522,   tier: 'medium',   region: 'europe' },
  { id: 'berlin',       name: 'Berlín',        country: 'DE', lat: 52.5200,  lng: 13.4050,  tier: 'medium',   region: 'europe' },
  { id: 'brussels',     name: 'Bruselas',      country: 'BE', lat: 50.8503,  lng: 4.3517,   tier: 'low',      region: 'europe' },
];

// Color por tier de riesgo — saturación reducida para monitoreo prolongado
export const CITY_COLORS = {
  critical: '#f87171',  // rojo suave (era #ef4444)
  high:     '#fb923c',  // naranja suave
  medium:   '#fcd34d',  // ámbar tenue
  low:      'rgba(148,163,184,0.35)', // gris-slate muy dim
};

// Config de anillos por tier — mínimo 4s, nivel ciudad (no country)
export const CITY_RING_CONFIG = {
  critical: { maxR: 0.18, propagationSpeed: 0.2, repeatPeriod: 4000 },
  high:     { maxR: 0.14, propagationSpeed: 0.12, repeatPeriod: 6000 },
  medium:   { maxR: 0.10, propagationSpeed: 0.08, repeatPeriod: 9000 },
  low:      null,
};

// Obtener ciudad más cercana a un punto lat/lng
export const getNearestCity = (lat, lng, maxDistDeg = 8) => {
  let best = null, bestDist = Infinity;
  for (const city of STRATEGIC_CITIES) {
    const d = Math.sqrt((city.lat - lat) ** 2 + (city.lng - lng) ** 2);
    if (d < bestDist) { bestDist = d; best = city; }
  }
  return bestDist <= maxDistDeg ? best : null;
};
