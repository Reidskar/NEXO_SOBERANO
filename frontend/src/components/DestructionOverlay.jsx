/**
 * DestructionOverlay — Animación de destrucción de estructura
 * Se activa sobre el mapa cuando llega un evento TACTICAL_SIMULATION crítico
 * o un GDELT critical. Simula visualmente el colapso de una estructura
 * sin cargar WebGL pesado. Pura CSS + Canvas 2D ligero.
 *
 * Props:
 *   event     — objeto con { lat, lng, target, country, text, driveLink, ... }
 *   mapRef    — ref al maplibregl.Map para proyectar coordenadas a pantalla
 *   onClose   — callback cuando el usuario cierra el overlay
 *   driveMarkers — todos los docs Drive para buscar evidencia relacionada
 */
import { useEffect, useRef, useState, useCallback } from 'react';

// ── Fases de la animación ──────────────────────────────────────────────────
// 1. Shockwave ring (0–1.2s)
// 2. Debris particles (0.3–2.5s)
// 3. Smoke column (0.8–4s)
// 4. Evidence panel fade-in (2s+)
const PHASE_DURATION = 4200; // ms total animation

// ── Generador de partículas de escombros ─────────────────────────────────────
const randomBetween = (a, b) => a + Math.random() * (b - a);

const createDebris = () => Array.from({ length: 22 }, (_, i) => ({
  id: i,
  angle: randomBetween(0, Math.PI * 2),
  speed: randomBetween(30, 120),
  size:  randomBetween(2, 6),
  color: ['#ef4444', '#f97316', '#fcd34d', '#94a3b8', '#374151'][Math.floor(Math.random() * 5)],
  delay: randomBetween(0, 400),
  gravity: randomBetween(40, 90),
}));

export default function DestructionOverlay({ event, mapRef, onClose, driveMarkers = [] }) {
  const canvasRef   = useRef(null);
  const animRef     = useRef(null);
  const startRef    = useRef(null);
  const debrisRef   = useRef(createDebris());
  const [phase, setPhase]   = useState('animating'); // 'animating' | 'evidence'
  const [screenPos, setScreenPos] = useState(null); // {x, y} pixel position on screen

  // ── Project lat/lng to screen pixels via Maplibre ─────────────────────────
  useEffect(() => {
    if (!mapRef?.current || !event) return;
    const map = mapRef.current;
    const project = () => {
      const pt = map.project([event.lng, event.lat]);
      setScreenPos({ x: pt.x, y: pt.y });
    };
    project();
    map.on('move', project);
    map.on('zoom', project);
    return () => { map.off('move', project); map.off('zoom', project); };
  }, [event, mapRef]);

  // ── Canvas animation loop ──────────────────────────────────────────────────
  useEffect(() => {
    if (!canvasRef.current || !screenPos) return;
    const canvas = canvasRef.current;
    const ctx    = canvas.getContext('2d');
    const debris = debrisRef.current;

    const draw = (ts) => {
      if (!startRef.current) startRef.current = ts;
      const elapsed = ts - startRef.current;
      const t = Math.min(elapsed / PHASE_DURATION, 1);

      // Resize canvas to window
      canvas.width  = window.innerWidth;
      canvas.height = window.innerHeight;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const cx = screenPos.x;
      const cy = screenPos.y;

      // ── 1. Shockwave rings ───────────────────────────────────────────────
      if (elapsed < 2000) {
        const rings = [0, 300, 700, 1200];
        rings.forEach(delay => {
          const rt = Math.max(0, elapsed - delay);
          if (rt <= 0) return;
          const progress = Math.min(rt / 1000, 1);
          const r = progress * 90;
          const opacity = (1 - progress) * 0.85;
          ctx.beginPath();
          ctx.arc(cx, cy, r, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(239, 68, 68, ${opacity})`;
          ctx.lineWidth   = 2 + (1 - progress) * 3;
          ctx.stroke();
        });
      }

      // ── 2. Core flash ─────────────────────────────────────────────────────
      if (elapsed < 600) {
        const flashT = elapsed / 600;
        const flashR = flashT < 0.3 ? flashT / 0.3 * 24 : (1 - flashT) * 24;
        const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, flashR);
        grad.addColorStop(0, `rgba(255,220,100,${0.9 * (1 - flashT)})`);
        grad.addColorStop(1, 'rgba(239,68,68,0)');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(cx, cy, flashR, 0, Math.PI * 2);
        ctx.fill();
      }

      // ── 3. Debris particles ───────────────────────────────────────────────
      debris.forEach(p => {
        const pt = Math.max(0, elapsed - p.delay);
        if (pt <= 0) return;
        const progress = Math.min(pt / 2000, 1);
        const x = cx + Math.cos(p.angle) * p.speed * progress;
        const y = cy + Math.sin(p.angle) * p.speed * progress + p.gravity * progress * progress;
        const opacity = Math.max(0, 1 - (progress - 0.5) / 0.5);
        ctx.beginPath();
        ctx.arc(x, y, p.size * (1 - progress * 0.5), 0, Math.PI * 2);
        ctx.fillStyle = p.color.replace(')', `,${opacity})`).replace('rgb', 'rgba').replace('rgba(rgba', 'rgba');
        // simple: just set globalAlpha
        ctx.globalAlpha = opacity;
        ctx.fillStyle   = p.color;
        ctx.fill();
        ctx.globalAlpha = 1;
      });

      // ── 4. Smoke column ───────────────────────────────────────────────────
      if (elapsed > 600) {
        const smokeT  = Math.min((elapsed - 600) / 3000, 1);
        const smokeH  = smokeT * 80;
        const smokeOpacity = smokeT < 0.3 ? smokeT / 0.3 * 0.45 : 0.45 * (1 - (smokeT - 0.3) / 0.7);
        const grad = ctx.createLinearGradient(cx, cy, cx + 20 * smokeT, cy - smokeH);
        grad.addColorStop(0, `rgba(60,40,30,${smokeOpacity})`);
        grad.addColorStop(1, `rgba(80,70,60,0)`);
        ctx.beginPath();
        ctx.ellipse(cx + 10 * smokeT, cy - smokeH / 2, 18 * smokeT + 6, smokeH / 2, 0.3, 0, Math.PI * 2);
        ctx.fillStyle = grad;
        ctx.fill();
      }

      if (elapsed < PHASE_DURATION) {
        animRef.current = requestAnimationFrame(draw);
      } else {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        setPhase('evidence');
      }
    };

    animRef.current = requestAnimationFrame(draw);
    return () => { if (animRef.current) cancelAnimationFrame(animRef.current); };
  }, [screenPos]);

  // ── Drive evidence relacionada al evento ──────────────────────────────────
  const relatedDrive = driveMarkers.filter(d => {
    if (!event) return false;
    const label = (d.label || '').toLowerCase();
    const country = (event.country || '').toLowerCase();
    const target  = (event.target  || '').toLowerCase();
    return label.includes(country) || label.includes(target) || label.includes('osint');
  }).slice(0, 4);

  if (!event || !screenPos) return null;

  return (
    <>
      {/* Canvas overlay for the destruction animation */}
      <canvas
        ref={canvasRef}
        style={{
          position: 'fixed', inset: 0, zIndex: 50,
          pointerEvents: 'none',
          width: '100vw', height: '100vh',
        }}
      />

      {/* Evidence panel — fades in after animation completes */}
      {phase === 'evidence' && (
        <div style={{
          position: 'fixed',
          left: Math.min(Math.max(screenPos.x - 180, 12), window.innerWidth - 380),
          top:  Math.min(Math.max(screenPos.y - 260, 12), window.innerHeight - 320),
          width: 360,
          zIndex: 60,
          background: 'rgba(4, 8, 16, 0.97)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(239,68,68,0.35)',
          borderRadius: 8,
          padding: 18,
          fontFamily: "'Space Mono', monospace",
          animation: 'fadeUp 0.5s ease both',
          boxShadow: '0 0 40px rgba(239,68,68,0.12), 0 20px 60px rgba(0,0,0,0.6)',
        }}>
          <style>{`@keyframes fadeUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:none; } }`}</style>

          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
            <div>
              <div style={{ fontSize: 9, color: '#ef4444', letterSpacing: '0.2em', marginBottom: 4 }}>
                ▲ EVENTO TÁCTICO DETECTADO
              </div>
              <div style={{ fontSize: 13, color: '#f8fafc', fontWeight: 600, lineHeight: 1.3 }}>
                {event.target || event.label || 'EVENTO SIN NOMBRE'}
              </div>
              {event.country && (
                <div style={{ fontSize: 9, color: '#64748b', marginTop: 3 }}>
                  {event.country} · {event.lat?.toFixed(3)}, {event.lng?.toFixed(3)}
                </div>
              )}
            </div>
            <button
              onClick={onClose}
              style={{ background: 'none', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 4, color: '#64748b', cursor: 'pointer', padding: '2px 8px', fontSize: 10 }}
            >
              ✕
            </button>
          </div>

          {/* Descripción */}
          {event.text && (
            <div style={{ fontSize: 10, color: '#94a3b8', lineHeight: 1.6, marginBottom: 14, padding: '8px 10px', background: 'rgba(255,255,255,0.03)', borderRadius: 4, borderLeft: '2px solid #ef444455' }}>
              {event.text}
            </div>
          )}

          {/* Timestamp */}
          {event.timestamp && (
            <div style={{ fontSize: 9, color: '#475569', marginBottom: 12 }}>
              REGISTRADO: {new Date(event.timestamp).toLocaleString('es-CL')}
            </div>
          )}

          {/* Drive evidence */}
          {relatedDrive.length > 0 && (
            <div>
              <div style={{ fontSize: 9, color: '#a855f7', letterSpacing: '0.15em', marginBottom: 8 }}>
                ◆ EVIDENCIA DRIVE ({relatedDrive.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {relatedDrive.map((d, i) => (
                  <a
                    key={i}
                    href={d.webViewLink || '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      padding: '6px 10px',
                      background: 'rgba(168,85,247,0.07)',
                      border: '1px solid rgba(168,85,247,0.2)',
                      borderRadius: 4,
                      textDecoration: 'none',
                      color: '#ddd6fe',
                      fontSize: 10,
                      transition: 'background 0.2s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(168,85,247,0.15)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'rgba(168,85,247,0.07)'}
                  >
                    <span style={{ color: '#a855f7', fontSize: 11 }}>📄</span>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {d.label || d.name || 'Documento OSINT'}
                    </span>
                  </a>
                ))}
              </div>
            </div>
          )}

          {relatedDrive.length === 0 && (
            <div style={{ fontSize: 9, color: '#334155', padding: '8px', textAlign: 'center', borderTop: '1px solid rgba(255,255,255,0.04)', marginTop: 8 }}>
              Sin documentos Drive relacionados aún
            </div>
          )}
        </div>
      )}

      {/* Pulse marker at event location */}
      <div style={{
        position: 'fixed',
        left: screenPos.x - 6,
        top:  screenPos.y - 6,
        width: 12, height: 12,
        borderRadius: '50%',
        background: '#ef4444',
        boxShadow: '0 0 0 3px rgba(239,68,68,0.3)',
        zIndex: 55,
        pointerEvents: 'none',
      }} />
    </>
  );
}
