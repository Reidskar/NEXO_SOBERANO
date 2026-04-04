/**
 * AISearchPanel — Panel flotante de IA para OmniGlobe.
 *
 * Permite al usuario:
 * 1. Hacer preguntas / búsquedas a la IA de NEXO.
 * 2. Ver la respuesta en streaming.
 * 3. Empujar el resultado como alerta al globo (ticker + animación).
 * 4. Guardar el resultado en Drive (vía backend).
 *
 * Se activa con el botón "IA SEARCH" del HUD o pulsando la tecla `/`.
 */
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, X, Send, Save, Globe2, Loader2, ChevronDown, ChevronUp } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY  = import.meta.env.VITE_NEXO_API_KEY || '';

const premiumEase = [0.23, 1, 0.32, 1];

// Quick-action prompts
const QUICK_PROMPTS = [
  { label: '🌍 Resumen global hoy',    text: 'Dame un resumen ejecutivo de los eventos geopolíticos más importantes de las últimas 24 horas.' },
  { label: '⚡ Alertas críticas',       text: 'Lista las 5 alertas tácticas más críticas del momento con ubicación y nivel de amenaza.' },
  { label: '📂 Drive: nuevo análisis', text: 'Analiza los documentos más recientes en Drive y extrae los puntos clave de inteligencia.' },
  { label: '🔍 Buscar en OSINT',       text: 'Busca y recopila información OSINT reciente sobre conflictos activos y compila un reporte.' },
  { label: '📊 Mercados de riesgo',    text: 'Analiza los mercados de predicción actuales y dame los escenarios con mayor probabilidad de riesgo.' },
  { label: '💾 Guardar sesión',        text: 'Genera un reporte completo de esta sesión y guárdalo en Drive como documento de inteligencia.' },
];

const AISearchPanel = ({ onPushAlert, onClose, isOpen }) => {
  const [query, setQuery]       = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading]   = useState(false);
  const [saving, setSaving]     = useState(false);
  const [minimized, setMinimized] = useState(false);
  const inputRef  = useRef(null);
  const scrollRef = useRef(null);

  // Auto-focus when opened
  useEffect(() => {
    if (isOpen && !minimized) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen, minimized]);

  // Auto-scroll to bottom on new message
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // The `/` key shortcut is handled in OmniGlobe.jsx which owns the open/close state.
  // This effect is kept intentionally empty (no-op) to document that contract.
  // Global `/` key toggle — note: panel is only rendered when isOpen=true (parent controls visibility)

  const sendQuery = useCallback(async (text) => {
    const q = (text || query).trim();
    if (!q || loading) return;

    const userMsg = { id: Date.now(), role: 'user', text: q, ts: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setQuery('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/ai/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
        },
        body: JSON.stringify({
          question: q,
          category: 'omniglobe_search',
          include_drive: true,
        }),
        signal: AbortSignal.timeout(30000),
      });

      const data = await res.json();
      const answer = data.answer || data.response || data.detail || 'Sin respuesta del servidor.';
      const sources = data.sources || [];

      const aiMsg = {
        id: Date.now() + 1,
        role: 'ai',
        text: answer,
        sources,
        ts: new Date(),
        raw: data,
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'error',
        text: err.name === 'TimeoutError'
          ? 'Timeout — el backend tardó demasiado. Intenta de nuevo.'
          : 'No se pudo conectar con el backend NEXO.',
        ts: new Date(),
      }]);
    } finally {
      setLoading(false);
    }
  }, [query, loading]);

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuery(); }
  };

  // Push last AI response as globe alert
  const pushToGlobe = useCallback(() => {
    const lastAI = [...messages].reverse().find(m => m.role === 'ai');
    if (!lastAI || !onPushAlert) return;
    onPushAlert(lastAI.text, { prefix: '[IA SEARCH]', color: '#a855f7', severity: 'medium' });
  }, [messages, onPushAlert]);

  // Save last AI response to Drive via backend
  const saveToDataSource = useCallback(async () => {
    const lastAI = [...messages].reverse().find(m => m.role === 'ai');
    if (!lastAI) return;
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/drive/guardar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
        },
        body: JSON.stringify({
          titulo: `IA Search — ${new Date().toLocaleString('es-CL')}`,
          contenido: lastAI.text,
          categoria: 'omniglobe_intel',
          fuente: 'AISearchPanel',
        }),
        signal: AbortSignal.timeout(15000),
      });
      const data = await res.json();
      if (res.ok) {
        setMessages(prev => [...prev, {
          id: Date.now(),
          role: 'system',
          text: `✅ Guardado en Drive: ${data.nombre || data.name || 'documento creado'}`,
          ts: new Date(),
        }]);
      } else {
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'system',
        text: `⚠️ No se pudo guardar: ${err.message}`,
        ts: new Date(),
      }]);
    } finally {
      setSaving(false);
    }
  }, [messages]);

  const hasAIResponse = messages.some(m => m.role === 'ai');

  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.92, y: 20 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9, y: 20 }}
      transition={{ duration: 0.35, ease: premiumEase }}
      style={{
        position: 'absolute',
        bottom: minimized ? 'auto' : 120,
        top: minimized ? 'auto' : undefined,
        left: '50%',
        transform: 'translateX(-50%)',
        width: 680,
        maxWidth: 'calc(100vw - 48px)',
        zIndex: 50,
        background: 'rgba(4, 6, 12, 0.96)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '1px solid rgba(168, 85, 247, 0.25)',
        boxShadow: '0 0 60px rgba(168,85,247,0.12), 0 24px 60px rgba(0,0,0,0.7)',
        borderRadius: 12,
        overflow: 'hidden',
        fontFamily: "'Inter', sans-serif",
      }}
    >
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 16px',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        background: 'rgba(168,85,247,0.06)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Search size={14} color="#a855f7" />
          <span style={{ color: '#e2e8f0', fontSize: 12, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase' }}>IA Search & Compile</span>
          <span style={{ background: 'rgba(168,85,247,0.2)', border: '1px solid rgba(168,85,247,0.3)', color: '#c084fc', fontSize: 9, padding: '1px 6px', borderRadius: 4, fontFamily: 'monospace' }}>NEXO</span>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            onClick={() => setMinimized(m => !m)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', padding: 4 }}
            title={minimized ? 'Expandir' : 'Minimizar'}
          >
            {minimized ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', padding: 4 }}
            title="Cerrar"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      <AnimatePresence>
        {!minimized && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            {/* Quick prompts */}
            <div style={{ padding: '10px 14px 8px', display: 'flex', gap: 6, flexWrap: 'wrap', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
              {QUICK_PROMPTS.map(p => (
                <button
                  key={p.label}
                  onClick={() => sendQuery(p.text)}
                  disabled={loading}
                  style={{
                    background: 'rgba(168,85,247,0.07)', border: '1px solid rgba(168,85,247,0.18)',
                    color: '#c084fc', fontSize: 9, padding: '4px 10px', borderRadius: 20,
                    cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.5 : 1,
                    fontFamily: 'monospace', transition: 'all 0.15s',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {p.label}
                </button>
              ))}
            </div>

            {/* Messages */}
            <div
              ref={scrollRef}
              style={{ maxHeight: 280, overflowY: 'auto', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 10 }}
            >
              {messages.length === 0 && (
                <div style={{ color: '#334155', fontSize: 11, textAlign: 'center', padding: '20px 0', fontFamily: 'monospace' }}>
                  Pregunta a la IA, busca información OSINT, o guarda análisis en Drive.
                  <br/>
                  <span style={{ color: '#475569', fontSize: 10 }}>Atajo: tecla <kbd style={{ background: 'rgba(255,255,255,0.07)', padding: '1px 5px', borderRadius: 3, border: '1px solid rgba(255,255,255,0.1)' }}>/</kbd></span>
                </div>
              )}
              <AnimatePresence initial={false}>
                {messages.map(msg => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.25 }}
                    style={{
                      alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      maxWidth: '90%',
                    }}
                  >
                    <div style={{
                      background: msg.role === 'user'
                        ? 'rgba(168,85,247,0.15)'
                        : msg.role === 'error'
                          ? 'rgba(239,68,68,0.1)'
                          : msg.role === 'system'
                            ? 'rgba(34,197,94,0.08)'
                            : 'rgba(255,255,255,0.04)',
                      border: `1px solid ${
                        msg.role === 'user' ? 'rgba(168,85,247,0.25)' :
                        msg.role === 'error' ? 'rgba(239,68,68,0.2)' :
                        msg.role === 'system' ? 'rgba(34,197,94,0.2)' :
                        'rgba(255,255,255,0.06)'}`,
                      borderRadius: msg.role === 'user' ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
                      padding: '8px 12px',
                      fontSize: 11,
                      color: msg.role === 'error' ? '#fca5a5' : msg.role === 'system' ? '#86efac' : '#e2e8f0',
                      lineHeight: 1.55,
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}>
                      {msg.text}
                      {msg.sources?.length > 0 && (
                        <div style={{ marginTop: 6, fontSize: 9, color: '#475569', fontFamily: 'monospace' }}>
                          Fuentes: {msg.sources.join(', ')}
                        </div>
                      )}
                    </div>
                    <div style={{ fontSize: 9, color: '#334155', marginTop: 3, textAlign: msg.role === 'user' ? 'right' : 'left', fontFamily: 'monospace' }}>
                      {msg.ts.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {loading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: 8, color: '#a855f7', fontSize: 10, fontFamily: 'monospace' }}
                >
                  <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
                    <Loader2 size={12} />
                  </motion.div>
                  IA procesando consulta...
                </motion.div>
              )}
            </div>

            {/* Input area */}
            <div style={{ padding: '10px 14px 14px', borderTop: '1px solid rgba(255,255,255,0.04)' }}>
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <input
                  ref={inputRef}
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={handleKey}
                  placeholder="Pregunta a la IA, busca info OSINT, pide análisis de Drive..."
                  disabled={loading}
                  style={{
                    flex: 1,
                    background: 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(168,85,247,0.2)',
                    borderRadius: 8,
                    padding: '8px 12px',
                    color: '#e2e8f0',
                    fontSize: 11,
                    outline: 'none',
                    fontFamily: "'Inter', sans-serif",
                    transition: 'border-color 0.2s',
                  }}
                  onFocus={e => { e.target.style.borderColor = 'rgba(168,85,247,0.5)'; }}
                  onBlur={e => { e.target.style.borderColor = 'rgba(168,85,247,0.2)'; }}
                />
                <motion.button
                  whileTap={{ scale: 0.93 }}
                  onClick={() => sendQuery()}
                  disabled={loading || !query.trim()}
                  style={{
                    background: query.trim() && !loading ? 'rgba(168,85,247,0.25)' : 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(168,85,247,0.3)',
                    borderRadius: 8,
                    padding: '8px 14px',
                    color: '#c084fc',
                    cursor: loading || !query.trim() ? 'not-allowed' : 'pointer',
                    opacity: loading || !query.trim() ? 0.5 : 1,
                    transition: 'all 0.2s',
                  }}
                >
                  <Send size={13} />
                </motion.button>
              </div>

              {/* Action buttons */}
              {hasAIResponse && (
                <div style={{ display: 'flex', gap: 6 }}>
                  <motion.button
                    whileTap={{ scale: 0.94 }}
                    onClick={pushToGlobe}
                    style={{
                      flex: 1,
                      background: 'rgba(0,229,255,0.08)', border: '1px solid rgba(0,229,255,0.2)',
                      borderRadius: 6, padding: '6px 12px', cursor: 'pointer',
                      color: '#00e5ff', fontSize: 10, fontFamily: 'monospace',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                    }}
                  >
                    <Globe2 size={11} /> ENVIAR AL GLOBO
                  </motion.button>
                  <motion.button
                    whileTap={{ scale: 0.94 }}
                    onClick={saveToDataSource}
                    disabled={saving}
                    style={{
                      flex: 1,
                      background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)',
                      borderRadius: 6, padding: '6px 12px', cursor: saving ? 'not-allowed' : 'pointer',
                      color: '#22c55e', fontSize: 10, fontFamily: 'monospace', opacity: saving ? 0.6 : 1,
                      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                    }}
                  >
                    {saving ? <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}><Loader2 size={11}/></motion.div> : <Save size={11} />}
                    {saving ? 'GUARDANDO...' : 'GUARDAR EN DRIVE'}
                  </motion.button>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default AISearchPanel;
