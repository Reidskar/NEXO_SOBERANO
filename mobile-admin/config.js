// Configuración NEXO Mobile Admin
// Cambia MODO para alternar entre producción y acceso local por Tailscale

const MODO = 'produccion'; // 'produccion' | 'tailscale' | 'local'

const URLS = {
  produccion: 'https://api.elanarcocapital.com',
  tailscale:  'http://100.112.238.97:8000',   // IP Tailscale de la Torre
  local:      'http://192.168.100.22:8000',    // IP WiFi local de la Torre
};

export const API_URL = URLS[MODO];
export const ADMIN_KEY = 'NEXO_LOCAL_2026_OK';
