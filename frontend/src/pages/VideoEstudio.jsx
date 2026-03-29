import React, { useState, useEffect, useRef } from 'react';
import { Film, Globe, Mic, Upload, Play, RefreshCw, Download, Youtube, ChevronDown, ChevronUp, AlertCircle, CheckCircle, Clock } from 'lucide-react';

const API = import.meta.env.VITE_API_BASE_URL?.replace('/api','') || '';

const C = {
  bg:'#080808', bg2:'#0f0f0f', bg3:'#141414',
  border:'#1a1a1a', green:'#4ade80', red:'#c0392b',
  amber:'#d4a017', cyan:'#22d3ee', purple:'#a78bfa',
  text:'#e5e5e5', muted:'#888', dim:'#444',
};
const mono = "'Space Mono', monospace";

const IDIOMAS = [
  { id:'es', label:'Español',    flag:'🇪🇸' },
  { id:'en', label:'English',    flag:'🇺🇸' },
  { id:'pt', label:'Português',  flag:'🇧🇷' },
];
const FORMATOS = [
  { id:'reel',    label:'REEL / SHORTS',  desc:'9:16 · 60s · TikTok, Instagram, YouTube Shorts', icon:'📱' },
  { id:'youtube', label:'YOUTUBE',         desc:'16:9 · 3-5 min · Canal principal', icon:'▶' },
];
const DOMINIOS = [
  { id:'geo',     label:'Geopolítica' },
  { id:'conducta',label:'Conducta' },
  { id:'masas',   label:'Control Masas' },
  { id:'eco_aus', label:'Economía Aus.' },
  { id:'poder',   label:'Poder' },
  { id:'libre',   label:'Libre' },
];

const STATUS_COLORS = {
  pendiente:        C.dim,
  generando_guion:  C.amber,
  traduciendo:      C.amber,
  sintetizando_voz: C.cyan,
  compilando:       C.purple,
  publicando:       C.green,
  completado:       C.green,
  error:            C.red,
};
const STATUS_ICONS = {
  pendiente:        <Clock size={10}/>,
  generando_guion:  <RefreshCw size={10}/>,
  traduciendo:      <Globe size={10}/>,
  sintetizando_voz: <Mic size={10}/>,
  compilando:       <Film size={10}/>,
  publicando:       <Youtube size={10}/>,
  completado:       <CheckCircle size={10}/>,
  error:            <AlertCircle size={10}/>,
};

// ── Sección header ────────────────────────────────────────────────────────────
const SectionHead = ({ label, icon: Icon, color = C.cyan }) => (
  <div style={{ padding:'6px 14px', borderBottom:`1px solid ${C.border}`, display:'flex', alignItems:'center', gap:7, background:C.bg3, flexShrink:0 }}>
    <Icon size={11} color={color}/>
    <span style={{ fontFamily:mono, fontSize:8, letterSpacing:'.12em', textTransform:'uppercase', color }}>{label}</span>
  </div>
);

// ── Job card ──────────────────────────────────────────────────────────────────
function JobCard({ job, onRefresh }) {
  const [expanded, setExpanded] = useState(false);
  const color = STATUS_COLORS[job.estado] || C.dim;

  const downloadVideo = async (idioma) => {
    const url = `${API}/api/video/jobs/${job.id}/descargar/${idioma}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = `NEXO_${job.id}_${idioma}.mp4`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const publicar = async (idioma) => {
    if (!window.confirm(`Publicar video en YouTube (${idioma})?`)) return;
    try {
      const r = await fetch(`${API}/api/video/publicar`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ job_id: job.id, idioma, privacy_status:'public' }),
      });
      const d = await r.json();
      if (d.ok) alert(`✅ Publicado en YouTube. ID: ${d.youtube_id}`);
      else alert('Error: ' + (d.detail || 'desconocido'));
      onRefresh();
    } catch(e) { alert('Error: ' + e.message); }
  };

  return (
    <div style={{ background:C.bg2, border:`1px solid ${C.border}`, borderLeft:`3px solid ${color}`, marginBottom:8 }}>
      {/* Header */}
      <div onClick={() => setExpanded(v => !v)}
        style={{ padding:'10px 14px', cursor:'pointer', display:'flex', alignItems:'center', justifyContent:'space-between' }}
        onMouseEnter={e => e.currentTarget.style.background = C.bg3}
        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
      >
        <div style={{ flex:1, minWidth:0 }}>
          <div style={{ fontFamily:mono, fontSize:10, color:C.text, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap', marginBottom:3 }}>{job.titulo}</div>
          <div style={{ display:'flex', gap:8, alignItems:'center', flexWrap:'wrap' }}>
            <span style={{ display:'flex', alignItems:'center', gap:3, fontFamily:mono, fontSize:7, color }}>
              {STATUS_ICONS[job.estado]} {job.estado.replace(/_/g,' ').toUpperCase()}
            </span>
            <span style={{ fontFamily:mono, fontSize:7, color:C.dim }}>{job.formato?.toUpperCase()}</span>
            <span style={{ fontFamily:mono, fontSize:7, color:C.dim }}>{(job.idiomas || []).join(' · ')}</span>
            <span style={{ fontFamily:mono, fontSize:7, color:C.dim }}>{job.id}</span>
          </div>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          {job.estado !== 'completado' && job.estado !== 'error' && (
            <button onClick={e => { e.stopPropagation(); onRefresh(); }}
              style={{ padding:'3px 6px', background:'none', border:`1px solid ${C.border}`, color:C.muted, cursor:'pointer', fontSize:8 }}>
              <RefreshCw size={9}/>
            </button>
          )}
          {expanded ? <ChevronUp size={12} color={C.dim}/> : <ChevronDown size={12} color={C.dim}/>}
        </div>
      </div>

      {/* Detalle */}
      {expanded && (
        <div style={{ borderTop:`1px solid ${C.border}` }}>
          {/* Guiones */}
          {job.guiones && Object.keys(job.guiones).length > 0 && (
            <div style={{ padding:'10px 14px', borderBottom:`1px solid ${C.border}` }}>
              <div style={{ fontFamily:mono, fontSize:7, color:C.dim, letterSpacing:'.1em', marginBottom:8 }}>GUIONES</div>
              <div style={{ display:'flex', gap:4, marginBottom:8, flexWrap:'wrap' }}>
                {Object.keys(job.guiones).map(lang => (
                  <span key={lang} style={{ fontFamily:mono, fontSize:7, color:C.green, border:`1px solid ${C.green}25`, padding:'2px 7px' }}>
                    {IDIOMAS.find(i=>i.id===lang)?.flag} {lang.toUpperCase()}
                  </span>
                ))}
              </div>
              {/* Preview del guión ES */}
              {job.guiones.es && (
                <div style={{ fontFamily:mono, fontSize:9, color:'#555', lineHeight:1.6, maxHeight:80, overflow:'hidden' }}>
                  {job.guiones.es.substring(0, 200)}...
                </div>
              )}
            </div>
          )}

          {/* Videos disponibles */}
          {job.videos && Object.keys(job.videos).length > 0 && (
            <div style={{ padding:'10px 14px', borderBottom:`1px solid ${C.border}` }}>
              <div style={{ fontFamily:mono, fontSize:7, color:C.dim, letterSpacing:'.1em', marginBottom:8 }}>VIDEOS COMPILADOS</div>
              <div style={{ display:'flex', gap:6, flexWrap:'wrap' }}>
                {Object.keys(job.videos).map(lang => (
                  <div key={lang} style={{ display:'flex', gap:4 }}>
                    <button onClick={() => downloadVideo(lang)}
                      style={{ display:'flex', alignItems:'center', gap:4, padding:'4px 10px', background:`rgba(74,222,128,0.06)`, border:`1px solid rgba(74,222,128,0.2)`, color:C.green, cursor:'pointer', fontFamily:mono, fontSize:8 }}>
                      <Download size={9}/> {lang.toUpperCase()}
                    </button>
                    {!job.youtube_ids?.[lang] && (
                      <button onClick={() => publicar(lang)}
                        style={{ display:'flex', alignItems:'center', gap:4, padding:'4px 10px', background:'rgba(255,0,0,0.06)', border:'1px solid rgba(255,0,0,0.2)', color:'#ff4444', cursor:'pointer', fontFamily:mono, fontSize:8 }}>
                        <Youtube size={9}/> YT
                      </button>
                    )}
                    {job.youtube_ids?.[lang] && (
                      <span style={{ fontFamily:mono, fontSize:7, color:C.green, display:'flex', alignItems:'center', gap:3 }}>
                        <CheckCircle size={8}/> Publicado
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Pasos */}
          {job.pasos?.length > 0 && (
            <div style={{ padding:'8px 14px', maxHeight:140, overflowY:'auto' }}>
              <div style={{ fontFamily:mono, fontSize:7, color:C.dim, letterSpacing:'.1em', marginBottom:6 }}>LOG</div>
              {job.pasos.map((p, i) => (
                <div key={i} style={{ display:'flex', gap:8, padding:'2px 0', borderBottom:`1px solid ${C.border}` }}>
                  <span style={{ fontFamily:mono, fontSize:7, color: p.estado==='ok'?C.green:p.estado==='warning'?C.amber:C.red, flexShrink:0, width:40 }}>{p.estado}</span>
                  <span style={{ fontFamily:mono, fontSize:7, color:C.muted }}>{p.paso}</span>
                  {p.detalle && <span style={{ fontFamily:mono, fontSize:7, color:C.dim, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{p.detalle}</span>}
                </div>
              ))}
            </div>
          )}

          {job.error && (
            <div style={{ padding:'8px 14px', fontFamily:mono, fontSize:9, color:C.red }}>⚠ {job.error}</div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Componente principal ──────────────────────────────────────────────────────
export default function VideoEstudio() {
  const [contenido, setContenido] = useState('');
  const [titulo, setTitulo]       = useState('');
  const [formato, setFormato]     = useState('reel');
  const [idiomas, setIdiomas]     = useState(['es']);
  const [dominio, setDominio]     = useState('libre');
  const [publicar, setPublicar]   = useState(false);
  const [launching, setLaunching] = useState(false);
  const [jobs, setJobs]           = useState([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [dailyContent, setDailyContent] = useState(null);
  const [guionPreview, setGuionPreview] = useState('');
  const [genGuion, setGenGuion]   = useState(false);
  const [tab, setTab]             = useState('nuevo'); // nuevo | jobs
  const pollRef = useRef(null);

  const fetchJobs = async () => {
    try {
      const r = await fetch(`${API}/api/video/jobs`);
      if (r.ok) { const d = await r.json(); setJobs(d.jobs || []); }
    } catch {}
  };

  const fetchDailyContent = async () => {
    try {
      const r = await fetch(`${API}/api/video/daily-content`);
      if (r.ok) { const d = await r.json(); setDailyContent(d); }
    } catch {}
  };

  const previewGuion = async () => {
    if (!contenido.trim()) return;
    setGenGuion(true);
    try {
      const r = await fetch(`${API}/api/video/generar-guion`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ contenido, formato, idioma_base:'es', dominio, titulo }),
        signal: AbortSignal.timeout(30000),
      });
      const d = await r.json();
      if (d.ok) setGuionPreview(d.guion);
    } catch(e) { console.error(e); }
    finally { setGenGuion(false); }
  };

  const toggleIdioma = (id) => {
    setIdiomas(prev => prev.includes(id) ? (prev.length > 1 ? prev.filter(i => i !== id) : prev) : [...prev, id]);
  };

  const lanzarPipeline = async () => {
    if (!contenido.trim()) return;
    setLaunching(true);
    try {
      const r = await fetch(`${API}/api/video/compilar`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ contenido, titulo: titulo || `NEXO — ${new Date().toLocaleDateString('es-CL')}`, formato, idiomas, dominio, publicar }),
        signal: AbortSignal.timeout(15000),
      });
      const d = await r.json();
      if (d.ok) {
        setTab('jobs');
        await fetchJobs();
        // Auto-polling cada 5s mientras haya jobs activos
        if (pollRef.current) clearInterval(pollRef.current);
        pollRef.current = setInterval(async () => {
          await fetchJobs();
          const activeJobs = jobs.filter(j => !['completado','error'].includes(j.estado));
          if (activeJobs.length === 0) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
        }, 5000);
      }
    } catch(e) { alert('Error: ' + e.message); }
    finally { setLaunching(false); }
  };

  useEffect(() => {
    fetchJobs();
    fetchDailyContent();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const activeJobs = jobs.filter(j => !['completado','error'].includes(j.estado)).length;

  return (
    <div style={{ height:'100vh', display:'flex', flexDirection:'column', background:C.bg, color:C.text, overflow:'hidden' }}>
      <style>{`
        ::-webkit-scrollbar{width:3px} ::-webkit-scrollbar-track{background:#0a0a0a} ::-webkit-scrollbar-thumb{background:#1c1c1c}
        @keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
      `}</style>

      {/* Header */}
      <div style={{ padding:'10px 20px', borderBottom:`1px solid ${C.border}`, display:'flex', alignItems:'center', justifyContent:'space-between', flexShrink:0 }}>
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          <Film size={15} color={C.amber}/>
          <span style={{ fontFamily:mono, fontSize:12, fontWeight:700, letterSpacing:'.1em' }}>VIDEO ESTUDIO</span>
          <span style={{ fontFamily:mono, fontSize:8, color:C.dim }}>COMPILACIÓN MULTI-IDIOMA</span>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          {activeJobs > 0 && (
            <span style={{ fontFamily:mono, fontSize:8, color:C.amber, border:`1px solid ${C.amber}30`, padding:'2px 8px', display:'flex', alignItems:'center', gap:4 }}>
              <RefreshCw size={8} style={{ animation:'spin 1.5s linear infinite' }}/> {activeJobs} EN PROCESO
            </span>
          )}
          <button onClick={() => { fetchJobs(); fetchDailyContent(); }}
            style={{ display:'flex', alignItems:'center', gap:4, padding:'4px 10px', background:'none', border:`1px solid ${C.border}`, color:C.muted, cursor:'pointer', fontFamily:mono, fontSize:8 }}>
            <RefreshCw size={10}/> ACTUALIZAR
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display:'flex', borderBottom:`1px solid ${C.border}`, flexShrink:0 }}>
        {[
          { id:'nuevo', label:'NUEVO VIDEO', icon:Film },
          { id:'jobs',  label:`JOBS (${jobs.length})`, icon:Play },
        ].map(t => {
          const Icon = t.icon;
          return (
            <button key={t.id} onClick={() => setTab(t.id)} style={{
              display:'flex', alignItems:'center', gap:6,
              padding:'8px 18px', cursor:'pointer', border:'none', background:'transparent',
              borderBottom: tab===t.id ? `2px solid ${C.amber}` : '2px solid transparent',
              color: tab===t.id ? C.amber : C.muted, fontFamily:mono, fontSize:9, letterSpacing:'.08em',
            }}>
              <Icon size={11}/> {t.label}
            </button>
          );
        })}
      </div>

      {/* ── Tab: Nuevo Video ── */}
      {tab === 'nuevo' && (
        <div style={{ flex:1, display:'flex', overflow:'hidden' }}>

          {/* Panel izquierdo: Config */}
          <div style={{ width:320, borderRight:`1px solid ${C.border}`, display:'flex', flexDirection:'column', overflow:'hidden', flexShrink:0 }}>
            <SectionHead label="Configuración" icon={Film} color={C.amber}/>
            <div style={{ flex:1, overflowY:'auto', padding:14 }}>

              {/* Título */}
              <div style={{ marginBottom:14 }}>
                <div style={{ fontFamily:mono, fontSize:7, color:C.dim, letterSpacing:'.1em', marginBottom:5 }}>TÍTULO DEL VIDEO</div>
                <input value={titulo} onChange={e=>setTitulo(e.target.value)}
                  placeholder={`NEXO — Análisis ${new Date().toLocaleDateString('es-CL')}`}
                  style={{ width:'100%', background:C.bg2, border:`1px solid ${C.border}`, color:C.text, padding:'7px 10px', fontSize:9, outline:'none', fontFamily:mono, boxSizing:'border-box' }}
                  onFocus={e=>e.target.style.borderColor=C.amber+'40'}
                  onBlur={e=>e.target.style.borderColor=C.border}/>
              </div>

              {/* Formato */}
              <div style={{ marginBottom:14 }}>
                <div style={{ fontFamily:mono, fontSize:7, color:C.dim, letterSpacing:'.1em', marginBottom:5 }}>FORMATO</div>
                {FORMATOS.map(f => (
                  <div key={f.id} onClick={() => setFormato(f.id)}
                    style={{ padding:'8px 10px', marginBottom:4, cursor:'pointer', background: formato===f.id ? `${C.amber}08` : C.bg2,
                      border:`1px solid ${formato===f.id ? C.amber+'40' : C.border}`, transition:'all .1s' }}>
                    <div style={{ display:'flex', gap:6, alignItems:'center', marginBottom:2 }}>
                      <span style={{ fontSize:12 }}>{f.icon}</span>
                      <span style={{ fontFamily:mono, fontSize:9, color: formato===f.id ? C.amber : C.text }}>{f.label}</span>
                    </div>
                    <div style={{ fontFamily:mono, fontSize:7, color:C.dim }}>{f.desc}</div>
                  </div>
                ))}
              </div>

              {/* Idiomas */}
              <div style={{ marginBottom:14 }}>
                <div style={{ fontFamily:mono, fontSize:7, color:C.dim, letterSpacing:'.1em', marginBottom:5 }}>IDIOMAS (multi-selección)</div>
                <div style={{ display:'flex', gap:4 }}>
                  {IDIOMAS.map(i => (
                    <button key={i.id} onClick={() => toggleIdioma(i.id)}
                      style={{ flex:1, padding:'6px 4px', cursor:'pointer',
                        background: idiomas.includes(i.id) ? `${C.green}08` : C.bg2,
                        border:`1px solid ${idiomas.includes(i.id) ? C.green+'40' : C.border}`,
                        color: idiomas.includes(i.id) ? C.green : C.muted, fontFamily:mono, fontSize:8 }}>
                      <div style={{ fontSize:14 }}>{i.flag}</div>
                      <div style={{ marginTop:3 }}>{i.label}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Dominio */}
              <div style={{ marginBottom:14 }}>
                <div style={{ fontFamily:mono, fontSize:7, color:C.dim, letterSpacing:'.1em', marginBottom:5 }}>DOMINIO</div>
                <div style={{ display:'flex', flexWrap:'wrap', gap:4 }}>
                  {DOMINIOS.map(d => (
                    <button key={d.id} onClick={() => setDominio(d.id)}
                      style={{ padding:'3px 8px', cursor:'pointer', fontFamily:mono, fontSize:7,
                        background: dominio===d.id ? `${C.cyan}08` : 'none',
                        border:`1px solid ${dominio===d.id ? C.cyan+'40' : C.border}`,
                        color: dominio===d.id ? C.cyan : C.muted }}>
                      {d.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Publicar auto */}
              <div style={{ marginBottom:14 }}>
                <label style={{ display:'flex', alignItems:'center', gap:8, cursor:'pointer' }}>
                  <input type="checkbox" checked={publicar} onChange={e=>setPublicar(e.target.checked)} style={{ accentColor:C.green }}/>
                  <span style={{ fontFamily:mono, fontSize:8, color:C.muted }}>Auto-publicar en YouTube al terminar</span>
                </label>
              </div>

              {/* Contenido Drive del día */}
              {dailyContent && dailyContent.drive_files?.length > 0 && (
                <div>
                  <div style={{ fontFamily:mono, fontSize:7, color:C.dim, letterSpacing:'.1em', marginBottom:5 }}>
                    CONTENIDO DRIVE HOY ({dailyContent.drive_files.length} archivos)
                  </div>
                  {dailyContent.drive_files.slice(0,5).map((f,i) => (
                    <div key={i} onClick={() => setContenido(p => p + (p?'\n\n':'') + f.nombre)}
                      style={{ padding:'4px 8px', marginBottom:2, cursor:'pointer', background:C.bg2, border:`1px solid ${C.border}`, fontFamily:mono, fontSize:8, color:C.muted, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}
                      title={`Click para incluir: ${f.nombre}`}>
                      + {f.nombre}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Panel centro: Contenido + Guión */}
          <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
            <SectionHead label="Contenido del día" icon={Upload} color={C.green}/>

            <div style={{ flex:1, display:'flex', overflow:'hidden' }}>
              {/* Textarea contenido */}
              <div style={{ flex:1, display:'flex', flexDirection:'column', borderRight:`1px solid ${C.border}`, overflow:'hidden' }}>
                <div style={{ padding:'6px 12px', borderBottom:`1px solid ${C.border}`, display:'flex', alignItems:'center', justifyContent:'space-between', flexShrink:0 }}>
                  <span style={{ fontFamily:mono, fontSize:7, color:C.dim, letterSpacing:'.08em' }}>PEGA EL CONTENIDO DEL DÍA AQUÍ</span>
                  <button onClick={previewGuion} disabled={!contenido.trim() || genGuion}
                    style={{ display:'flex', alignItems:'center', gap:4, padding:'3px 10px', background:`rgba(74,222,128,0.06)`, border:`1px solid rgba(74,222,128,0.2)`, color:C.green, cursor:'pointer', fontFamily:mono, fontSize:8, opacity:!contenido.trim()?0.4:1 }}>
                    {genGuion ? <RefreshCw size={9} style={{ animation:'spin 1s linear infinite' }}/> : <Film size={9}/>}
                    PREVISUALIZAR GUIÓN
                  </button>
                </div>
                <textarea value={contenido} onChange={e=>setContenido(e.target.value)}
                  placeholder="Pega aquí el contenido del día: análisis de sesiones, noticias, eventos geopolíticos, datos del Drive...

Puedes incluir:
- Resúmenes de sesiones NEXO
- Artículos o noticias
- Análisis propios
- Transcripciones

El sistema generará un guión de video a partir de este contenido."
                  style={{ flex:1, background:C.bg, border:'none', color:C.text, padding:'12px', fontSize:10, fontFamily:mono, lineHeight:1.7, resize:'none', outline:'none' }}/>
              </div>

              {/* Preview guión */}
              {guionPreview && (
                <div style={{ width:340, display:'flex', flexDirection:'column', overflow:'hidden' }}>
                  <div style={{ padding:'6px 12px', borderBottom:`1px solid ${C.border}`, display:'flex', alignItems:'center', justifyContent:'space-between', flexShrink:0 }}>
                    <span style={{ fontFamily:mono, fontSize:7, color:C.amber, letterSpacing:'.08em' }}>GUIÓN GENERADO (ES)</span>
                    <button onClick={() => setGuionPreview('')} style={{ fontFamily:mono, fontSize:7, color:C.dim, background:'none', border:'none', cursor:'pointer' }}>×</button>
                  </div>
                  <div style={{ flex:1, overflowY:'auto', padding:12 }}>
                    <div style={{ fontFamily:mono, fontSize:9, color:'#888', lineHeight:1.7, whiteSpace:'pre-wrap' }}>{guionPreview}</div>
                  </div>
                </div>
              )}
            </div>

            {/* Footer botón */}
            <div style={{ padding:'12px 16px', borderTop:`1px solid ${C.border}`, display:'flex', alignItems:'center', justifyContent:'space-between', flexShrink:0, background:C.bg3 }}>
              <div style={{ fontFamily:mono, fontSize:8, color:C.dim }}>
                Idiomas: {idiomas.join(', ')} · Formato: {formato} · {publicar ? 'Auto-publicar' : 'Solo compilar'}
              </div>
              <button onClick={lanzarPipeline} disabled={!contenido.trim() || launching}
                style={{ display:'flex', alignItems:'center', gap:8, padding:'9px 24px', background:`${C.amber}12`, border:`1px solid ${C.amber}40`, color:C.amber, cursor:'pointer', fontFamily:mono, fontSize:10, fontWeight:700, letterSpacing:'.1em', opacity:!contenido.trim()?0.4:1 }}>
                {launching ? <RefreshCw size={12} style={{ animation:'spin 1s linear infinite' }}/> : <Film size={12}/>}
                LANZAR PIPELINE
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Jobs ── */}
      {tab === 'jobs' && (
        <div style={{ flex:1, overflowY:'auto', padding:16 }}>
          {jobs.length === 0 && (
            <div style={{ textAlign:'center', padding:40, fontFamily:mono, fontSize:10, color:C.dim }}>
              Sin jobs aún. Crea un video en la pestaña "NUEVO VIDEO".
            </div>
          )}
          {jobs.map(job => (
            <JobCard key={job.id} job={job} onRefresh={fetchJobs}/>
          ))}
        </div>
      )}
    </div>
  );
}
