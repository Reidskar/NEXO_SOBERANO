import React, { useState, useEffect, useRef, useCallback } from 'react';

const API = import.meta.env.VITE_API_BASE_URL?.replace('/api','') || '';

// ─── Domains of analysis ──────────────────────────────────────────────────────
const DOMAINS = [
  { id:'geo',       label:'Geopolítica',        icon:'🌐', hint:'Conflictos, alianzas, poder regional' },
  { id:'conducta',  label:'Conducta de Líderes', icon:'🧠', hint:'Lenguaje corporal, patrones, decisiones' },
  { id:'masas',     label:'Control de Masas',    icon:'📡', hint:'Narrativas, expectativa social, psicología' },
  { id:'eco_aus',   label:'Economía Austriaca',  icon:'📊', hint:'Ciclos, capital, anarcocapitalismo' },
  { id:'poder',     label:'Escenarios de Poder', icon:'♟', hint:'Tablero político, actores, vectores' },
  { id:'osint',     label:'OSINT',               icon:'🔍', hint:'Fuentes abiertas, señales, patrones' },
  { id:'libre',     label:'Libre',               icon:'∞',  hint:'Sin restricción de dominio' },
];

const WEB_MODES = [
  { id:'rag',    label:'Bóveda RAG',   icon:'📁', desc:'Documentos propios + memoria' },
  { id:'web',    label:'Web en vivo',  icon:'🌐', desc:'Búsqueda en tiempo real' },
  { id:'ambos',  label:'RAG + Web',    icon:'⚡', desc:'Máxima cobertura' },
];

const QUICK_PROMPTS = {
  conducta:  ['Analiza el lenguaje corporal de este líder', 'Patrones de mentira en declaraciones públicas', 'Mapa de relaciones de poder del sujeto'],
  masas:     ['Narrativa dominante esta semana en redes', 'Ingeniería del consentimiento en este evento', 'Expectativa social vs realidad económica'],
  eco_aus:   ['Ciclo de Mises: fase actual del mercado', 'Consecuencias del intervencionismo monetario', 'Análisis austriaco del dato macroeconómico'],
  poder:     ['Mapa de actores en este escenario', 'Quién gana con este conflicto', 'Vectores de poder en juego'],
  geo:       ['Situación APAC — balance de fuerzas', 'Alianzas ocultas detrás del conflicto', 'Próximo movimiento estratégico probable'],
  osint:     ['Contrastar fuentes sobre este evento', 'Señales débiles en los datos disponibles', 'Verificación cruzada de la narrativa oficial'],
  libre:     ['Compara con otras IAs esta perspectiva', 'Evalúa la consistencia de mi análisis', 'Qué no estoy viendo en este escenario'],
};

function useVoiceRecorder(onTranscript) {
  const [recording, setRecording] = useState(false);
  const mediaRecorder = useRef(null);
  const chunks = useRef([]);

  const start = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder.current = new MediaRecorder(stream);
      chunks.current = [];
      mediaRecorder.current.ondataavailable = e => chunks.current.push(e.data);
      mediaRecorder.current.onstop = async () => {
        const blob = new Blob(chunks.current, { type: 'audio/webm' });
        stream.getTracks().forEach(t => t.stop());
        // Send to backend for transcription
        if (API) {
          try {
            const fd = new FormData();
            fd.append('audio', blob, 'recording.webm');
            const r = await fetch(`${API}/api/media/transcribir`, { method:'POST', body:fd, signal:AbortSignal.timeout(20000) });
            if (r.ok) {
              const d = await r.json();
              onTranscript(d.texto || d.transcript || '');
            }
          } catch { onTranscript('[Audio grabado — backend no disponible para transcripción]'); }
        } else {
          onTranscript('[Audio grabado — conecta el backend para transcripción automática]');
        }
      };
      mediaRecorder.current.start();
      setRecording(true);
    } catch { alert('Micrófono no disponible'); }
  }, [onTranscript]);

  const stop = useCallback(() => {
    mediaRecorder.current?.stop();
    setRecording(false);
  }, []);

  return { recording, start, stop };
}

// ─── Session storage ──────────────────────────────────────────────────────────
function loadSessions() {
  try { return JSON.parse(localStorage.getItem('nexo_sessions') || '[]'); } catch { return []; }
}
function saveSessions(sessions) {
  localStorage.setItem('nexo_sessions', JSON.stringify(sessions));
}

// ─── Video Analysis Panel ─────────────────────────────────────────────────────
function VideoPanel({ domain, onAnalysisDone }) {
  const [mode, setMode]       = useState('file'); // 'file' | 'url'
  const [ytUrl, setYtUrl]     = useState('');
  const [file, setFile]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState(null);
  const [error, setError]     = useState('');
  const [progress, setProgress] = useState('');
  const fileRef = React.useRef(null);

  const analyze = async () => {
    if (mode === 'url' && !ytUrl.trim()) return;
    if (mode === 'file' && !file) return;
    setLoading(true); setError(''); setResult(null);
    setProgress(mode === 'url' ? 'Descargando audio de YouTube...' : 'Extrayendo audio...');

    try {
      const fd = new FormData();
      fd.append('dominio', domain);
      fd.append('idioma', 'es');
      if (mode === 'url') fd.append('youtube_url', ytUrl.trim());
      else fd.append('file', file);

      setProgress('Transcribiendo con Whisper...');
      const r = await fetch(`${API}/api/agente/analizar-video`, {
        method: 'POST', body: fd,
        signal: AbortSignal.timeout(300000), // 5 min
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: r.statusText }));
        throw new Error(err.detail || 'Error en servidor');
      }
      setProgress('Analizando con NEXO...');
      const data = await r.json();
      setResult(data);
      setProgress('');
      if (onAnalysisDone) onAnalysisDone(data);
    } catch (e) {
      setError(e.message || 'Error desconocido');
      setProgress('');
    } finally {
      setLoading(false);
    }
  };

  const downloadDocx = async () => {
    if (!result) return;
    try {
      const r = await fetch(`${API}/api/agente/exportar-docx`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(result),
        signal: AbortSignal.timeout(30000),
      });
      if (!r.ok) throw new Error('Error generando documento');
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const cd = r.headers.get('content-disposition') || '';
      const match = cd.match(/filename="(.+)"/);
      a.download = match ? match[1] : 'NEXO_analisis.docx';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      alert('Error descargando DOCX: ' + e.message);
    }
  };

  const formatDur = (s) => {
    const m = Math.floor(s / 60), sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  return (
    <div style={{ borderTop:'1px solid #161616', background:'#050505', flexShrink:0, maxHeight:480, overflowY:'auto' }}>
      {/* Header */}
      <div style={{ padding:'7px 16px', borderBottom:'1px solid #111', display:'flex', alignItems:'center', justifyContent:'space-between' }}>
        <span style={{ fontSize:8, color:'#d4a017', letterSpacing:'.12em' }}>📹 ANÁLISIS DE VIDEO</span>
        {result && (
          <button onClick={downloadDocx} style={{ fontSize:8, color:'#4ade80', background:'rgba(74,222,128,0.08)', border:'1px solid rgba(74,222,128,0.25)', padding:'3px 10px', cursor:'pointer', letterSpacing:'.06em' }}>
            ↓ DESCARGAR .DOCX
          </button>
        )}
      </div>

      {/* Input */}
      {!result && (
        <div style={{ padding:'10px 16px' }}>
          {/* Tabs */}
          <div style={{ display:'flex', gap:4, marginBottom:10 }}>
            {['file','url'].map(m => (
              <button key={m} onClick={()=>setMode(m)} style={{ fontSize:8, color: mode===m?'#d4a017':'#333', background:'none', border:`1px solid ${mode===m?'#d4a01730':'transparent'}`, padding:'3px 9px', cursor:'pointer' }}>
                {m === 'file' ? '📁 Archivo' : '▶ YouTube URL'}
              </button>
            ))}
          </div>

          {mode === 'url' ? (
            <input value={ytUrl} onChange={e=>setYtUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              style={{ width:'100%', background:'#0f0f0f', border:'1px solid #1c1c1c', color:'#e8e8e8', padding:'7px 10px', fontSize:10, outline:'none', boxSizing:'border-box', marginBottom:8 }}
              onFocus={e=>e.target.style.borderColor='#d4a01740'}
              onBlur={e=>e.target.style.borderColor='#1c1c1c'}
              onKeyDown={e=>e.key==='Enter'&&analyze()}/>
          ) : (
            <div style={{ marginBottom:8 }}>
              <input ref={fileRef} type="file" style={{ display:'none' }} accept="video/*,audio/*,.mp4,.mkv,.webm,.mov,.mp3,.wav,.m4a" onChange={e=>setFile(e.target.files?.[0]||null)}/>
              <button onClick={()=>fileRef.current?.click()} style={{ width:'100%', padding:'8px', background:'#0f0f0f', border:'1px dashed #2a2a2a', color: file?'#d4a017':'#444', cursor:'pointer', fontSize:9, letterSpacing:'.06em' }}>
                {file ? `📎 ${file.name}` : '+ Seleccionar video / audio'}
              </button>
            </div>
          )}

          {error && <div style={{ fontSize:9, color:'#c0392b', marginBottom:6 }}>⚠ {error}</div>}

          {loading ? (
            <div style={{ display:'flex', alignItems:'center', gap:8, padding:'6px 0' }}>
              {[0,1,2].map(i=><span key={i} style={{ width:5,height:5,borderRadius:'50%',background:'#d4a017',opacity:.3,animation:`blink-dot 1.2s ${i*0.4}s infinite`}}/>)}
              <span style={{ fontSize:9, color:'#555' }}>{progress}</span>
            </div>
          ) : (
            <button onClick={analyze} disabled={mode==='url'?!ytUrl.trim():!file}
              style={{ width:'100%', padding:'7px', background:'rgba(212,160,23,0.1)', border:'1px solid rgba(212,160,23,0.3)', color:'#d4a017', cursor:'pointer', fontSize:9, letterSpacing:'.1em', opacity:(mode==='url'?!ytUrl.trim():!file)?0.4:1 }}>
              ANALIZAR VIDEO →
            </button>
          )}
        </div>
      )}

      {/* Result */}
      {result && (
        <div style={{ padding:'10px 16px' }}>
          {/* Meta */}
          <div style={{ display:'flex', flexWrap:'wrap', gap:12, marginBottom:10, padding:'8px', background:'#0a0a0a', border:'1px solid #1a1a1a' }}>
            <div><span style={{ fontSize:7, color:'#333', display:'block', marginBottom:2 }}>TÍTULO</span><span style={{ fontSize:10, color:'#e8e8e8' }}>{result.titulo}</span></div>
            <div><span style={{ fontSize:7, color:'#333', display:'block', marginBottom:2 }}>CANAL</span><span style={{ fontSize:9, color:'#888' }}>{result.canal}</span></div>
            <div><span style={{ fontSize:7, color:'#333', display:'block', marginBottom:2 }}>DURACIÓN</span><span style={{ fontSize:9, color:'#d4a017' }}>{formatDur(result.duracion_seg)}</span></div>
            <div><span style={{ fontSize:7, color:'#333', display:'block', marginBottom:2 }}>PALABRAS</span><span style={{ fontSize:9, color:'#4ade80' }}>{result.palabras}</span></div>
          </div>

          {/* Análisis */}
          <div style={{ fontSize:7, color:'#4ade8050', letterSpacing:'.1em', marginBottom:6 }}>ANÁLISIS DE INTELIGENCIA — {result.dominio?.toUpperCase()}</div>
          <div style={{ fontSize:10, color:'#aaaaaa', lineHeight:1.75, whiteSpace:'pre-wrap', marginBottom:12 }}>{result.analisis}</div>

          {/* Transcripción colapsable */}
          <details style={{ cursor:'pointer' }}>
            <summary style={{ fontSize:8, color:'#333', letterSpacing:'.1em', marginBottom:6, listStyle:'none', userSelect:'none' }}>
              ▶ VER TRANSCRIPCIÓN COMPLETA ({result.palabras} palabras)
            </summary>
            <div style={{ marginTop:8, fontSize:9, color:'#555', lineHeight:1.7, whiteSpace:'pre-wrap', background:'#0a0a0a', padding:'8px', border:'1px solid #161616', maxHeight:200, overflowY:'auto' }}>
              {result.transcripcion}
            </div>
          </details>

          <button onClick={()=>setResult(null)} style={{ marginTop:10, fontSize:8, color:'#333', background:'none', border:'1px solid #1c1c1c', padding:'4px 12px', cursor:'pointer' }}>
            NUEVO ANÁLISIS
          </button>
        </div>
      )}
    </div>
  );
}

export default function SesionIA() {
  const [sessions, setSessions] = useState(loadSessions);
  const [activeSession, setActiveSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [domain, setDomain] = useState('libre');
  const [webMode, setWebMode] = useState('rag');
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState('');
  const [newTopic, setNewTopic] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [compareMode, setCompareMode] = useState(false);
  const [compareData, setCompareData] = useState(null); // {query, nexo, gpt, gemini, loading}
  const [videoMode, setVideoMode]     = useState(false);
  const msgEnd = useRef(null);
  const fileRef = useRef(null);

  useEffect(() => { msgEnd.current?.scrollIntoView({ behavior:'smooth' }); }, [messages]);

  // Persist sessions
  useEffect(() => { saveSessions(sessions); }, [sessions]);

  const startSession = async () => {
    if (!newName.trim()) return;
    const id = `s_${Date.now()}`;
    const session = { id, nombre: newName, tema: newTopic || domain, domain, created_at: new Date().toISOString(), estado: 'activa', messages: [] };
    // Backend
    if (API) {
      try {
        await fetch(`${API}/api/sesiones/iniciar`, {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ nombre: newName, tema: newTopic || domain }),
          signal: AbortSignal.timeout(5000)
        });
      } catch {}
    }
    setSessions(s => [session, ...s]);
    setActiveSession(session);
    setMessages([{ role:'system', text:`Sesión iniciada: ${newName} · Dominio: ${DOMAINS.find(d=>d.id===domain)?.label} · Modo: ${webMode}` }]);
    setShowNew(false);
    setNewName('');
    setNewTopic('');
  };

  const sendMessage = async (text = input) => {
    if (!text?.trim() || loading) return;
    const q = text.trim();
    setInput('');
    const userMsg = { role:'user', text: q, ts: new Date().toISOString() };
    setMessages(m => [...m, userMsg]);
    setLoading(true);

    // Save user message to backend
    if (API && activeSession) {
      fetch(`${API}/api/sesiones/guardar-mensaje`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ sesion_id: activeSession.id, rol:'usuario', contenido: q }),
      }).catch(() => {});
    }

    try {
      // Build context: domain + past messages (last 6)
      const domainCtx = DOMAINS.find(d => d.id === domain);
      const sessionHistory = messages.filter(m => m.role !== 'system').slice(-6)
        .map(m => `[${m.role === 'user' ? 'Analista' : 'NEXO'}]: ${m.text}`).join('\n');

      const enrichedPrompt = `
[DOMINIO: ${domainCtx?.label} — ${domainCtx?.hint}]
[SESIÓN: ${activeSession?.nombre || 'Libre'}]
[MODO: ${webMode === 'web' ? 'Búsqueda web en tiempo real' : webMode === 'ambos' ? 'RAG + Web' : 'Bóveda RAG + Memoria semántica'}]
${sessionHistory ? `\n[CONTEXTO SESIÓN]:\n${sessionHistory}` : ''}

CONSULTA: ${q}

Responde como sistema de inteligencia estratégica de alto nivel. Sé preciso, denso en información, sin relleno.
${webMode !== 'rag' ? 'Busca en fuentes actuales si es relevante.' : 'Usa la bóveda de conocimiento acumulado.'}`
        .trim();

      const endpoint = webMode === 'web' ? `/api/agente/` : `/api/agente/consultar-rag`;
      const body = webMode === 'web'
        ? { query: enrichedPrompt, user_id: activeSession?.id }
        : { pregunta: enrichedPrompt, modo: domain };

      const r = await fetch(`${API}${endpoint}`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(25000)
      });
      const data = await r.json();
      const reply = data?.answer || data?.respuesta || data?.response || data?.resultado || JSON.stringify(data).substring(0,400);
      const sources = data?.sources || data?.fuentes || [];

      const aiMsg = { role:'nexo', text: reply, sources, ts: new Date().toISOString() };
      setMessages(m => [...m, aiMsg]);

      // Save AI response to backend + Qdrant
      if (API && activeSession) {
        fetch(`${API}/api/sesiones/guardar-mensaje`, {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ sesion_id: activeSession.id, rol:'nexo', contenido: reply, fuentes: sources }),
        }).catch(() => {});
      }

      // Update session in state
      setSessions(s => s.map(sess => sess.id === activeSession?.id
        ? { ...sess, messages: [...(sess.messages || []), userMsg, aiMsg] }
        : sess));

    } catch {
      setMessages(m => [...m, { role:'nexo', text:'Backend desconectado. Reconecta el servidor para análisis con RAG y memoria semántica.', ts: new Date().toISOString() }]);
    } finally {
      setLoading(false);
    }
  };

  const sendCompare = async (text = input) => {
    if (!text?.trim() || loading) return;
    const q = text.trim();
    setInput('');
    setCompareData({ query: q, nexo: null, gpt: null, gemini: null, loading: true });
    const domainCtx = DOMAINS.find(d => d.id === domain);
    const prompt = `[DOMINIO: ${domainCtx?.label}]\nCONSULTA: ${q}\nResponde como sistema de inteligencia estratégica. Sé preciso y denso.`;

    const callModel = async (modelo) => {
      if (!API) return null;
      try {
        const r = await fetch(`${API}/api/agente/comparar`, {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ query: prompt, modelo }),
          signal: AbortSignal.timeout(30000)
        });
        if (!r.ok) return null;
        const d = await r.json();
        return d?.respuesta || d?.answer || d?.response || null;
      } catch { return null; }
    };

    const callNexo = async () => {
      if (!API) return null;
      try {
        const r = await fetch(`${API}/api/agente/consultar-rag`, {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ pregunta: prompt, modo: domain }),
          signal: AbortSignal.timeout(25000)
        });
        const d = await r.json();
        return d?.respuesta || d?.answer || d?.response || null;
      } catch { return null; }
    };

    const [nexo, gpt, gemini] = await Promise.all([
      callNexo(),
      callModel('gpt-4o'),
      callModel('gemini-1.5-pro'),
    ]);

    const fallback = (modelo) => `[${modelo} no disponible — configura la clave API en el backend para activar esta integración]`;
    setCompareData({
      query: q,
      nexo:   nexo   || fallback('NEXO/Claude'),
      gpt:    gpt    || fallback('GPT-4o'),
      gemini: gemini || fallback('Gemini 1.5 Pro'),
      loading: false,
    });
  };

  const closeSession = async () => {
    if (!activeSession) return;
    const summary = messages.filter(m => m.role !== 'system').slice(-4).map(m => m.text).join(' ').substring(0, 300);
    if (API) {
      try {
        await fetch(`${API}/api/sesiones/cerrar`, {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ sesion_id: activeSession.id }),
          signal: AbortSignal.timeout(15000)
        });
      } catch {}
    }
    setSessions(s => s.map(sess => sess.id === activeSession.id ? { ...sess, estado:'cerrada' } : sess));
    setActiveSession(null);
    setMessages([]);
  };

  const searchMemory = async () => {
    if (!searchQuery.trim()) return;
    try {
      const r = await fetch(`${API}/api/sesiones/buscar`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ query: searchQuery }),
        signal: AbortSignal.timeout(8000)
      });
      const d = await r.json();
      setSearchResults(d.resultados || []);
    } catch {
      // Fallback: local search
      const q = searchQuery.toLowerCase();
      const results = sessions.flatMap(s => (s.messages || []).filter(m => m.text?.toLowerCase().includes(q)).map(m => ({ ...m, sesion_nombre: s.nombre })));
      setSearchResults(results.slice(0, 10));
    }
  };

  const { recording, start: startRec, stop: stopRec } = useVoiceRecorder(text => setInput(p => p + (p ? ' ' : '') + text));

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !API) return;
    const fd = new FormData();
    fd.append('file', file);
    try {
      const r = await fetch(`${API}/api/agente/drive/upload-aporte`, { method:'POST', body:fd, signal:AbortSignal.timeout(30000) });
      const d = await r.json();
      setMessages(m => [...m, { role:'system', text:`Archivo indexado: ${file.name} → ${d.drive_id || 'OK'}` }]);
    } catch {
      setMessages(m => [...m, { role:'system', text:`Error indexando ${file.name}. Verifica backend.` }]);
    }
  };

  const quickPrompts = QUICK_PROMPTS[domain] || QUICK_PROMPTS.libre;

  // ─── Render ────────────────────────────────────────────────────────────────
  return (
    <div style={{ background:'#080808', minHeight:'100vh', color:'#e8e8e8', fontFamily:'monospace', display:'flex', flexDirection:'column' }}>
      <style>{`
        @keyframes blink-dot{0%,100%{opacity:1}50%{opacity:.3}}
        @keyframes pulse-red{0%,100%{box-shadow:0 0 0 0 rgba(192,57,43,.4)}70%{box-shadow:0 0 0 8px rgba(192,57,43,0)}}
        ::-webkit-scrollbar{width:3px} ::-webkit-scrollbar-track{background:#0a0a0a} ::-webkit-scrollbar-thumb{background:#1c1c1c}
      `}</style>

      {/* ── HEADER ── */}
      <div style={{ borderBottom:'1px solid #161616', padding:'10px 20px', display:'flex', alignItems:'center', justifyContent:'space-between', background:'#060606', flexShrink:0 }}>
        <div style={{ display:'flex', alignItems:'center', gap:12 }}>
          <span style={{ fontSize:10, color:'#4ade80', letterSpacing:'.18em', fontWeight:700 }}>SESIÓN DE ANÁLISIS</span>
          {activeSession && (
            <>
              <span style={{ color:'#1c1c1c' }}>·</span>
              <span style={{ fontSize:9, color:'#888888' }}>{activeSession.nombre}</span>
              <span style={{ fontSize:7, color:'#4ade80', border:'1px solid #4ade8030', padding:'1px 6px', letterSpacing:'.1em' }}>ACTIVA</span>
            </>
          )}
        </div>
        <div style={{ display:'flex', gap:8 }}>
          {activeSession && (
            <button onClick={closeSession} style={{ fontSize:8, color:'#c0392b', background:'none', border:'1px solid #c0392b30', padding:'4px 10px', cursor:'pointer', letterSpacing:'.08em' }}>CERRAR SESIÓN</button>
          )}
          <button onClick={() => setShowNew(true)} style={{ fontSize:8, color:'#4ade80', background:'none', border:'1px solid #4ade8030', padding:'4px 12px', cursor:'pointer', letterSpacing:'.1em', fontWeight:700 }}>+ NUEVA</button>
        </div>
      </div>

      {/* ── NEW SESSION MODAL ── */}
      {showNew && (
        <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,.85)', zIndex:100, display:'flex', alignItems:'center', justifyContent:'center' }}>
          <div style={{ background:'#0a0a0a', border:'1px solid #4ade8030', padding:'28px', width:460 }}>
            <div style={{ fontSize:11, color:'#4ade80', letterSpacing:'.15em', marginBottom:20 }}>INICIAR SESIÓN DE ANÁLISIS</div>

            <input value={newName} onChange={e=>setNewName(e.target.value)} placeholder="Nombre de la sesión..." style={{ width:'100%', background:'#0f0f0f', border:'1px solid #1c1c1c', color:'#e8e8e8', padding:'8px 12px', fontSize:12, outline:'none', marginBottom:10, boxSizing:'border-box' }} onKeyDown={e=>e.key==='Enter'&&startSession()} autoFocus/>
            <input value={newTopic} onChange={e=>setNewTopic(e.target.value)} placeholder="Tema o hipótesis inicial (opcional)..." style={{ width:'100%', background:'#0f0f0f', border:'1px solid #1c1c1c', color:'#e8e8e8', padding:'8px 12px', fontSize:11, outline:'none', marginBottom:16, boxSizing:'border-box' }}/>

            <div style={{ fontSize:8, color:'#333333', letterSpacing:'.15em', marginBottom:8 }}>DOMINIO DE ANÁLISIS</div>
            <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:4, marginBottom:16 }}>
              {DOMAINS.map(d => (
                <button key={d.id} onClick={()=>setDomain(d.id)} style={{ background: domain===d.id?'#0f1a0f':'#0a0a0a', border:`1px solid ${domain===d.id?'#4ade8040':'#1c1c1c'}`, padding:'7px 4px', cursor:'pointer', display:'flex', flexDirection:'column', alignItems:'center', gap:3 }}>
                  <span style={{ fontSize:14 }}>{d.icon}</span>
                  <span style={{ fontSize:7, color: domain===d.id?'#4ade80':'#444444', letterSpacing:'.05em', textAlign:'center', lineHeight:1.3 }}>{d.label}</span>
                </button>
              ))}
            </div>

            <div style={{ fontSize:8, color:'#333333', letterSpacing:'.15em', marginBottom:8 }}>FUENTE DE CONOCIMIENTO</div>
            <div style={{ display:'flex', gap:4, marginBottom:20 }}>
              {WEB_MODES.map(m => (
                <button key={m.id} onClick={()=>setWebMode(m.id)} style={{ flex:1, background: webMode===m.id?'#0f1a0f':'#0a0a0a', border:`1px solid ${webMode===m.id?'#4ade8040':'#1c1c1c'}`, padding:'8px 6px', cursor:'pointer' }}>
                  <div style={{ fontSize:11 }}>{m.icon}</div>
                  <div style={{ fontSize:8, color: webMode===m.id?'#4ade80':'#444444', marginTop:3 }}>{m.label}</div>
                </button>
              ))}
            </div>

            <div style={{ display:'flex', gap:8 }}>
              <button onClick={startSession} disabled={!newName.trim()} style={{ flex:1, background:'#4ade80', color:'#080808', border:'none', padding:'9px', fontSize:10, fontWeight:700, cursor:'pointer', letterSpacing:'.1em', opacity: newName.trim()?1:0.4 }}>INICIAR</button>
              <button onClick={()=>setShowNew(false)} style={{ background:'none', border:'1px solid #1c1c1c', color:'#444444', padding:'9px 16px', fontSize:10, cursor:'pointer' }}>CANCELAR</button>
            </div>
          </div>
        </div>
      )}

      {/* ── MAIN LAYOUT ── */}
      <div style={{ flex:1, display:'grid', gridTemplateColumns:'220px 1fr 220px', overflow:'hidden' }}>

        {/* ─── LEFT: Session history ─── */}
        <div style={{ borderRight:'1px solid #161616', overflowY:'auto', background:'#060606' }}>
          <div style={{ padding:'10px 12px', borderBottom:'1px solid #161616' }}>
            <div style={{ fontSize:7, color:'#333333', letterSpacing:'.15em', marginBottom:8 }}>SESIONES ({sessions.length})</div>
            {sessions.length === 0 && <div style={{ fontSize:9, color:'#222222' }}>Sin sesiones. Crea una.</div>}
            {sessions.map(s => (
              <div key={s.id} onClick={() => {
                setActiveSession(s);
                setMessages([{ role:'system', text:`Retomando: ${s.nombre}` }]);
              }} style={{ padding:'8px 10px', marginBottom:3, cursor:'pointer', background: activeSession?.id===s.id?'#0f1a0f':'transparent', border:`1px solid ${activeSession?.id===s.id?'#4ade8030':'#111111'}`, transition:'all .15s' }}
                onMouseEnter={e=>{ if(activeSession?.id!==s.id) e.currentTarget.style.background='#0a0a0a'; }}
                onMouseLeave={e=>{ if(activeSession?.id!==s.id) e.currentTarget.style.background='transparent'; }}
              >
                <div style={{ fontSize:9, color: s.estado==='activa'?'#e8e8e8':'#555555', marginBottom:2, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{s.nombre}</div>
                <div style={{ display:'flex', gap:6, alignItems:'center' }}>
                  <span style={{ fontSize:7, color: s.estado==='activa'?'#4ade80':'#333333' }}>{s.estado==='activa'?'●':'○'} {s.estado}</span>
                  <span style={{ fontSize:7, color:'#222222' }}>{s.domain}</span>
                </div>
                <div style={{ fontSize:7, color:'#222222', marginTop:1 }}>{new Date(s.created_at).toLocaleDateString('es-CL')}</div>
              </div>
            ))}
          </div>

          {/* Memory Search */}
          <div style={{ padding:'10px 12px' }}>
            <div style={{ fontSize:7, color:'#333333', letterSpacing:'.15em', marginBottom:8 }}>BUSCAR MEMORIA</div>
            <div style={{ display:'flex', flexDirection:'column', gap:5 }}>
              <input value={searchQuery} onChange={e=>setSearchQuery(e.target.value)} onKeyDown={e=>e.key==='Enter'&&searchMemory()} placeholder="buscar en sesiones..." style={{ background:'#0f0f0f', border:'1px solid #161616', color:'#888888', padding:'5px 8px', fontSize:9, outline:'none', width:'100%', boxSizing:'border-box' }}/>
              <button onClick={searchMemory} style={{ background:'none', border:'1px solid #1c1c1c', color:'#444444', padding:'4px', fontSize:8, cursor:'pointer', letterSpacing:'.08em' }}>BUSCAR →</button>
            </div>
            {searchResults.length > 0 && (
              <div style={{ marginTop:8 }}>
                {searchResults.map((r, i) => (
                  <div key={i} style={{ padding:'6px 0', borderBottom:'1px solid #111111' }}>
                    <div style={{ fontSize:7, color:'#4ade80', marginBottom:2 }}>{r.sesion_nombre || r.sesion_id}</div>
                    <div style={{ fontSize:8, color:'#555555', lineHeight:1.4 }}>{(r.contenido || r.text || '').substring(0,100)}...</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ─── CENTER: Chat ─── */}
        <div style={{ display:'flex', flexDirection:'column', overflow:'hidden' }}>

          {!activeSession ? (
            <div style={{ flex:1, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:20 }}>
              <div style={{ fontSize:28, marginBottom:4 }}>🧠</div>
              <div style={{ fontSize:13, color:'#4ade80', letterSpacing:'.1em' }}>NEXO ANÁLISIS ACUMULATIVO</div>
              <div style={{ fontSize:10, color:'#333333', textAlign:'center', maxWidth:360, lineHeight:1.7 }}>
                Cada sesión queda indexada en memoria semántica.<br/>
                La IA aprende de tu análisis y lo conecta con futuros contextos.
              </div>
              <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:8, width:'100%', maxWidth:480, padding:'0 20px' }}>
                {DOMAINS.slice(0,4).map(d => (
                  <button key={d.id} onClick={()=>{setDomain(d.id);setShowNew(true);}} style={{ background:'#0a0a0a', border:'1px solid #161616', padding:'14px 10px', cursor:'pointer', display:'flex', flexDirection:'column', alignItems:'center', gap:6, transition:'border-color .15s' }}
                    onMouseEnter={e=>e.currentTarget.style.borderColor='#4ade8030'}
                    onMouseLeave={e=>e.currentTarget.style.borderColor='#161616'}>
                    <span style={{ fontSize:20 }}>{d.icon}</span>
                    <span style={{ fontSize:8, color:'#555555', letterSpacing:'.06em', textAlign:'center' }}>{d.label}</span>
                  </button>
                ))}
              </div>
              <button onClick={()=>setShowNew(true)} style={{ background:'#4ade80', color:'#080808', border:'none', padding:'10px 32px', fontSize:10, fontWeight:700, cursor:'pointer', letterSpacing:'.12em' }}>INICIAR SESIÓN</button>
            </div>
          ) : (
            <>
              {/* Mode bar */}
              <div style={{ borderBottom:'1px solid #161616', padding:'6px 16px', display:'flex', gap:6, background:'#060606', flexShrink:0, overflowX:'auto' }}>
                {DOMAINS.map(d => (
                  <button key={d.id} onClick={()=>setDomain(d.id)} style={{ fontSize:8, color: domain===d.id?'#4ade80':'#333333', background:'none', border:`1px solid ${domain===d.id?'#4ade8030':'transparent'}`, padding:'3px 8px', cursor:'pointer', whiteSpace:'nowrap' }}>
                    {d.icon} {d.label}
                  </button>
                ))}
                <div style={{ marginLeft:'auto', display:'flex', gap:4, flexShrink:0 }}>
                  {WEB_MODES.map(m => (
                    <button key={m.id} onClick={()=>setWebMode(m.id)} style={{ fontSize:7, color: webMode===m.id?'#d4a017':'#333333', background:'none', border:`1px solid ${webMode===m.id?'#d4a01730':'transparent'}`, padding:'3px 7px', cursor:'pointer' }}>
                      {m.icon} {m.label}
                    </button>
                  ))}
                  <button onClick={()=>{setCompareMode(v=>!v);setCompareData(null);}} style={{ fontSize:7, color: compareMode?'#22d3ee':'#333333', background: compareMode?'rgba(34,211,238,0.06)':'none', border:`1px solid ${compareMode?'rgba(34,211,238,0.3)':'transparent'}`, padding:'3px 9px', cursor:'pointer', letterSpacing:'.06em' }}>
                    ⚡ COMPARAR IAs
                  </button>
                  <button onClick={()=>setVideoMode(v=>!v)} style={{ fontSize:7, color: videoMode?'#d4a017':'#333333', background: videoMode?'rgba(212,160,23,0.06)':'none', border:`1px solid ${videoMode?'rgba(212,160,23,0.3)':'transparent'}`, padding:'3px 9px', cursor:'pointer', letterSpacing:'.06em' }}>
                    📹 VIDEO
                  </button>
                </div>
              </div>

              {/* Messages */}
              <div style={{ flex:1, overflowY:'auto', padding:'16px' }}>
                {messages.map((m, i) => (
                  <div key={i} style={{ marginBottom:16 }}>
                    {m.role === 'system' && (
                      <div style={{ fontSize:8, color:'#2a4a2a', borderLeft:'2px solid #1a3a1a', paddingLeft:10, lineHeight:1.5 }}>⬡ {m.text}</div>
                    )}
                    {m.role === 'user' && (
                      <div style={{ display:'flex', gap:10 }}>
                        <span style={{ fontSize:9, color:'#4ade80', flexShrink:0, marginTop:2 }}>›</span>
                        <div>
                          <div style={{ fontSize:11, color:'#e8e8e8', lineHeight:1.6 }}>{m.text}</div>
                          <div style={{ fontSize:7, color:'#222222', marginTop:3 }}>{m.ts ? new Date(m.ts).toLocaleTimeString('es-CL') : ''}</div>
                        </div>
                      </div>
                    )}
                    {m.role === 'nexo' && (
                      <div style={{ background:'#0a0a0a', borderLeft:'2px solid #1c3a1c', padding:'12px 14px', marginLeft:18 }}>
                        <div style={{ fontSize:8, color:'#4ade8050', letterSpacing:'.1em', marginBottom:8 }}>NEXO · {DOMAINS.find(d=>d.id===domain)?.label}</div>
                        <div style={{ fontSize:11, color:'#aaaaaa', lineHeight:1.75, whiteSpace:'pre-wrap' }}>{m.text}</div>
                        {m.sources?.length > 0 && (
                          <div style={{ marginTop:10, display:'flex', flexWrap:'wrap', gap:4 }}>
                            {m.sources.map((s, si) => (
                              <span key={si} style={{ fontSize:7, color:'#4ade8060', border:'1px solid #4ade8015', padding:'1px 6px' }}>{s}</span>
                            ))}
                          </div>
                        )}
                        <div style={{ fontSize:7, color:'#222222', marginTop:6 }}>{m.ts ? new Date(m.ts).toLocaleTimeString('es-CL') : ''}</div>
                      </div>
                    )}
                  </div>
                ))}
                {loading && (
                  <div style={{ background:'#0a0a0a', borderLeft:'2px solid #1c3a1c', padding:'12px 14px', marginLeft:18 }}>
                    <div style={{ fontSize:8, color:'#4ade8030', letterSpacing:'.1em', marginBottom:6 }}>NEXO · procesando...</div>
                    <div style={{ display:'flex', gap:4 }}>
                      {[0,1,2].map(i => <span key={i} style={{ width:6, height:6, borderRadius:'50%', background:'#4ade80', opacity:.3, animation:`blink-dot 1.2s ${i*0.4}s infinite` }}/>)}
                    </div>
                  </div>
                )}
                <div ref={msgEnd}/>
              </div>

              {/* Quick prompts */}
              <div style={{ padding:'6px 16px', borderTop:'1px solid #111111', display:'flex', gap:4, flexWrap:'wrap', background:'#060606' }}>
                {quickPrompts.map(p => (
                  <button key={p} onClick={()=>sendMessage(p)} style={{ fontSize:8, color:'#333333', background:'none', border:'1px solid #161616', padding:'3px 8px', cursor:'pointer', transition:'all .15s' }}
                    onMouseEnter={e=>{e.currentTarget.style.borderColor='#4ade8030';e.currentTarget.style.color='#4ade80';}}
                    onMouseLeave={e=>{e.currentTarget.style.borderColor='#161616';e.currentTarget.style.color='#333333';}}>
                    {p}
                  </button>
                ))}
              </div>

              {/* ── Video Panel ── */}
              {videoMode && (
                <VideoPanel domain={domain} onAnalysisDone={(data) => {
                  const msg = { role:'nexo', text:`📹 VIDEO ANALIZADO: "${data.titulo}"\n\n${data.analisis}`, ts: new Date().toISOString(), sources: [`Transcripción: ${data.palabras} palabras`, `Duración: ${Math.floor(data.duracion_seg/60)}min`] };
                  setMessages(m => [...m, { role:'user', text:`Análisis de video: ${data.titulo}`, ts: new Date().toISOString() }, msg]);
                  if (API && activeSession) {
                    fetch(`${API}/api/sesiones/guardar-mensaje`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ sesion_id: activeSession.id, rol:'nexo', contenido: msg.text }) }).catch(()=>{});
                  }
                }}/>
              )}

              {/* ── Compare Panel ── */}
              {compareMode && (
                <div style={{ borderTop:'1px solid #161616', background:'#050505', flexShrink:0, maxHeight:340, overflowY:'auto' }}>
                  <div style={{ padding:'6px 16px', borderBottom:'1px solid #111', display:'flex', alignItems:'center', justifyContent:'space-between' }}>
                    <span style={{ fontSize:8, color:'#22d3ee', letterSpacing:'.12em' }}>⚡ COMPARACIÓN EN TIEMPO REAL</span>
                    {compareData && !compareData.loading && (
                      <button onClick={()=>setCompareData(null)} style={{ fontSize:7, color:'#333', background:'none', border:'1px solid #1c1c1c', padding:'2px 8px', cursor:'pointer' }}>LIMPIAR</button>
                    )}
                  </div>
                  {!compareData && (
                    <div style={{ padding:'16px', fontSize:9, color:'#333', textAlign:'center' }}>
                      Escribe una consulta y presiona <span style={{ color:'#22d3ee' }}>COMPARAR →</span> para ver respuestas paralelas de NEXO, GPT-4o y Gemini.
                    </div>
                  )}
                  {compareData?.loading && (
                    <div style={{ padding:'16px', display:'flex', gap:8, alignItems:'center' }}>
                      {[0,1,2].map(i=><span key={i} style={{ width:5,height:5,borderRadius:'50%',background:'#22d3ee',opacity:.3,animation:`blink-dot 1.2s ${i*0.4}s infinite`}}/>)}
                      <span style={{ fontSize:9, color:'#333' }}>Consultando 3 modelos en paralelo...</span>
                    </div>
                  )}
                  {compareData && !compareData.loading && (
                    <div style={{ padding:'8px 12px 12px' }}>
                      <div style={{ fontSize:8, color:'#444', marginBottom:8, fontStyle:'italic' }}>› {compareData.query}</div>
                      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:8 }}>
                        {[
                          { label:'NEXO / CLAUDE', color:'#4ade80', text: compareData.nexo },
                          { label:'GPT-4o',         color:'#22d3ee', text: compareData.gpt },
                          { label:'GEMINI 1.5 PRO', color:'#a78bfa', text: compareData.gemini },
                        ].map(col => (
                          <div key={col.label} style={{ background:'#0a0a0a', border:`1px solid ${col.color}18`, borderTop:`2px solid ${col.color}40` }}>
                            <div style={{ padding:'5px 8px', fontSize:7, color: col.color, letterSpacing:'.1em', borderBottom:`1px solid ${col.color}15` }}>{col.label}</div>
                            <div style={{ padding:'8px', fontSize:10, color:'#888', lineHeight:1.65, whiteSpace:'pre-wrap' }}>{col.text}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Input */}
              <div style={{ padding:'10px 16px', borderTop:'1px solid #161616', background:'#060606', flexShrink:0 }}>
                <div style={{ display:'flex', gap:6 }}>
                  <input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{ if(e.key==='Enter'&&!e.shiftKey){ compareMode?sendCompare():sendMessage(); } }} placeholder={`Consulta al sistema de inteligencia — dominio: ${DOMAINS.find(d=>d.id===domain)?.label}...`} disabled={loading} style={{ flex:1, background:'#0f0f0f', border:'1px solid #1c1c1c', color:'#e8e8e8', padding:'9px 12px', fontSize:11, outline:'none', transition:'border-color .15s' }}
                    onFocus={e=>e.target.style.borderColor='#4ade8040'}
                    onBlur={e=>e.target.style.borderColor='#1c1c1c'}/>
                  {/* Voice */}
                  <button onClick={recording ? stopRec : startRec} style={{ padding:'9px 12px', background: recording?'#c0392b12':'transparent', border:`1px solid ${recording?'#c0392b40':'#1c1c1c'}`, color: recording?'#c0392b':'#444444', cursor:'pointer', fontSize:14, animation: recording?'pulse-red 1.5s infinite':'' }} title={recording?'Detener':'Grabar voz'}>
                    {recording ? '⏹' : '🎤'}
                  </button>
                  {/* Upload */}
                  <button onClick={()=>fileRef.current?.click()} style={{ padding:'9px 12px', background:'transparent', border:'1px solid #1c1c1c', color:'#444444', cursor:'pointer', fontSize:14 }} title="Subir archivo">📎</button>
                  <input ref={fileRef} type="file" style={{ display:'none' }} onChange={handleUpload} accept=".pdf,.txt,.doc,.docx,.md,.csv"/>
                  {/* Send / Compare */}
                  {compareMode ? (
                    <button onClick={()=>sendCompare()} disabled={!input.trim()} style={{ padding:'9px 16px', background:'rgba(34,211,238,0.08)', border:'1px solid rgba(34,211,238,0.3)', color:'#22d3ee', cursor:'pointer', fontSize:9, letterSpacing:'.1em', opacity:input.trim()?1:0.4 }}>COMPARAR →</button>
                  ) : (
                    <button onClick={()=>sendMessage()} disabled={loading||!input.trim()} style={{ padding:'9px 16px', background:'#4ade8012', border:'1px solid #4ade8030', color:'#4ade80', cursor:'pointer', fontSize:9, letterSpacing:'.1em', opacity: loading||!input.trim()?0.4:1 }}>ENVIAR</button>
                  )}
                </div>
                <div style={{ fontSize:7, color:'#222222', marginTop:5, display:'flex', gap:16 }}>
                  <span>Enter → {compareMode?'comparar':'enviar'}</span>
                  <span>Qdrant: {API?'conectado':'offline'}</span>
                  <span>Modo: {compareMode?'⚡ COMPARACIÓN':WEB_MODES.find(m=>m.id===webMode)?.label}</span>
                  <span>{messages.filter(m=>m.role!=='system').length} intercambios guardados</span>
                </div>
              </div>
            </>
          )}
        </div>

        {/* ─── RIGHT: Domain intelligence ─── */}
        <div style={{ borderLeft:'1px solid #161616', overflowY:'auto', background:'#060606' }}>
          <div style={{ padding:'10px 12px', borderBottom:'1px solid #161616' }}>
            <div style={{ fontSize:7, color:'#333333', letterSpacing:'.15em', marginBottom:8 }}>DOMINIOS ACTIVOS</div>
            {DOMAINS.map(d => (
              <div key={d.id} onClick={()=>setDomain(d.id)} style={{ padding:'8px 10px', marginBottom:3, cursor:'pointer', background: domain===d.id?'#0f1a0f':'transparent', border:`1px solid ${domain===d.id?'#4ade8030':'#111111'}` }}>
                <div style={{ display:'flex', gap:7, alignItems:'center', marginBottom:2 }}>
                  <span style={{ fontSize:12 }}>{d.icon}</span>
                  <span style={{ fontSize:9, color: domain===d.id?'#4ade80':'#555555', fontWeight: domain===d.id?700:400 }}>{d.label}</span>
                </div>
                <div style={{ fontSize:7, color:'#333333', lineHeight:1.4 }}>{d.hint}</div>
              </div>
            ))}
          </div>

          {/* Session stats */}
          {activeSession && (
            <div style={{ padding:'10px 12px' }}>
              <div style={{ fontSize:7, color:'#333333', letterSpacing:'.15em', marginBottom:8 }}>SESIÓN ACTIVA</div>
              <div style={{ fontSize:8, color:'#555555', marginBottom:5 }}>{activeSession.nombre}</div>
              <div style={{ display:'flex', gap:4, flexDirection:'column' }}>
                <div style={{ display:'flex', justifyContent:'space-between' }}>
                  <span style={{ fontSize:7, color:'#333333' }}>Intercambios</span>
                  <span style={{ fontSize:7, color:'#4ade80' }}>{messages.filter(m=>m.role==='user').length}</span>
                </div>
                <div style={{ display:'flex', justifyContent:'space-between' }}>
                  <span style={{ fontSize:7, color:'#333333' }}>Memoria</span>
                  <span style={{ fontSize:7, color: API?'#4ade80':'#c0392b' }}>{API?'Qdrant':'Local'}</span>
                </div>
                <div style={{ display:'flex', justifyContent:'space-between' }}>
                  <span style={{ fontSize:7, color:'#333333' }}>Dominio</span>
                  <span style={{ fontSize:7, color:'#d4a017' }}>{DOMAINS.find(d=>d.id===domain)?.label}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
