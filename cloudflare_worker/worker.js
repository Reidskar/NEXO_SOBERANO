/**
 * Cloudflare Worker — Proxy con fallback soberano
 * Si el túnel al backend local falla (502/504), sirve página estática.
 *
 * Deploy: wrangler deploy
 * Ruta: elanarcocapital.com/*
 */

const BACKEND_TUNNEL = "https://elanarcocapital.com"; // Cloudflare Tunnel URL real
const FALLBACK_HTML = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>El Anarcocapital — Modo Soberano</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: #0a0a0a; color: #e0e0e0;
      font-family: 'Courier New', monospace;
      display: flex; align-items: center; justify-content: center;
      min-height: 100vh; padding: 2rem;
    }
    .container { max-width: 600px; text-align: center; }
    .logo { font-size: 2rem; font-weight: bold; color: #f5a623; letter-spacing: 2px; }
    .status { margin: 1.5rem 0; padding: 1rem; border: 1px solid #333; border-radius: 8px; }
    .dot { display: inline-block; width: 10px; height: 10px; background: #f5a623;
           border-radius: 50%; animation: pulse 1.5s infinite; margin-right: 8px; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
    .msg { color: #aaa; font-size: 0.9rem; margin-top: 1rem; }
  </style>
</head>
<body>
  <div class="container">
    <div class="logo">EL ANARCOCAPITAL</div>
    <div class="status">
      <span class="dot"></span>
      <strong>Modo Soberano: Procesamiento en Segundo Plano</strong>
    </div>
    <p>La Torre está procesando inteligencia offline.<br>
    El sistema volverá en línea automáticamente.</p>
    <p class="msg">Si eres un agente: el backend estará disponible pronto.<br>
    Reintenta en 60 segundos.</p>
  </div>
</body>
</html>`;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    try {
      const response = await fetch(request, { cf: { cacheTtl: 0 } });

      // Si el tunnel está caído, Cloudflare devuelve 502/504/530
      if ([502, 504, 530, 522, 523, 524].includes(response.status)) {
        return fallbackPage(response.status);
      }

      return response;
    } catch (err) {
      return fallbackPage(502);
    }
  },
};

function fallbackPage(statusCode) {
  return new Response(FALLBACK_HTML, {
    status: 200,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Fallback-Reason": `tunnel-error-${statusCode}`,
    },
  });
}
