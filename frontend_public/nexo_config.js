/**
 * NEXO SOBERANO — Configuración dinámica de URLs
 * Se adapta automáticamente: localhost (dev) ↔ elanarcocapital.com (prod)
 *
 * Reglas:
 *  - Siempre usar el mismo host que sirve la página (relativo)
 *  - WS protocol: ws:// en HTTP, wss:// en HTTPS
 *  - API calls: siempre relativas (/api/...) — funciona en cualquier host
 *  - Si hay NEXO_BACKEND_URL en meta tag, usarlo explícitamente
 */

(function() {
  const _protocol  = location.protocol === 'https:' ? 'https' : 'http';
  const _wsProto   = location.protocol === 'https:' ? 'wss'   : 'ws';
  const _host      = location.host;   // hostname:port o solo hostname en prod
  const _isDev     = _host.includes('localhost') || _host.includes('127.0.0.1');
  const _isProd    = _host.includes('elanarcocapital.com');

  // Leer override explícito desde meta tag:
  // <meta name="nexo-backend" content="https://api.elanarcocapital.com">
  const _metaBackend = document.querySelector('meta[name="nexo-backend"]')?.content || '';

  const _backendBase = _metaBackend || `${_protocol}://${_host}`;
  const _wsBase      = _metaBackend
    ? _metaBackend.replace('https://', 'wss://').replace('http://', 'ws://')
    : `${_wsProto}://${_host}`;

  window.NEXO = {
    // URLs base
    API:    _backendBase,
    WS:     _wsBase,
    ORIGIN: _backendBase,

    // Constructores
    api:    (path)  => `${_backendBase}${path}`,
    ws:     (path)  => `${_wsBase}${path}`,
    // Relative (preferido cuando la page es servida por el mismo backend)
    relApi: (path)  => path,

    // Entorno
    isDev:  _isDev,
    isProd: _isProd,
    host:   _host,

    // URLs de las páginas del dominio
    pages: {
      home:          '/',
      omniglobe:     '/omniglobe',
      flowmap:       '/flowmap',
      controlCenter: '/control-center',
      dashboard:     '/dashboard',
      docs:          '/api/docs',
      health:        '/health',
    },

    // WebSocket channels
    ws_globe:  `${_wsBase}/ws/alerts/globe`,
    ws_alerts: `${_wsBase}/ws/alerts`,

    // API endpoints clave
    ep: {
      health:        '/health',
      intel_live:    '/api/platform/intel/live',
      intel_fetch:   '/api/platform/intel/fetch',
      globe_command: '/api/globe/command',
      globe_poll:    '/api/globe/poll',
      osint_status:  '/api/osint/status',
      obs_status:    '/api/platform/obs/status',
      narrativa:     '/api/platform/marketing/narrativa-globo',
      routing_stats: '/api/ai/routing-stats',
    },
  };

  if (_isDev) console.log('[NEXO] Dev mode — backend:', _backendBase);
  if (_isProd) console.log('[NEXO] Prod mode — domain:', _host);
})();
