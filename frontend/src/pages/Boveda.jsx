import React, { useState, useEffect, useRef } from 'react';
import { Search, Upload, FileText, Tag, Clock, Database, Filter, X, Eye } from 'lucide-react';

const API = import.meta.env.VITE_API_BASE_URL || '';
const mono = "'Space Mono', monospace";

// ── Shared style helpers ───────────────────────────────────────────────────────
const card = {
  background: 'var(--bg2)',
  border: '1px solid var(--border)',
  padding: '20px 24px',
};
const label = (color = 'var(--dim)') => ({
  fontFamily: mono, fontSize: 10, color, letterSpacing: '.12em', textTransform: 'uppercase',
});
const badge = (color = 'var(--cyan)') => ({
  fontFamily: mono, fontSize: 9, letterSpacing: '.08em', textTransform: 'uppercase',
  background: `${color}14`, color, border: `1px solid ${color}30`,
  padding: '2px 8px', borderRadius: 2,
});

// ── Mock documents ─────────────────────────────────────────────────────────────
const MOCK_DOCS = [
  { id: 1, title: 'Análisis OSINT: Movimientos militares frontera bielorrusa', tags: ['geo', 'military'], source: 'Telegram', date: '2026-04-02', status: 'indexed', relevance: 92 },
  { id: 2, title: 'Reporte: Flujos de capital Rusia-China Q1 2026', tags: ['economy', 'geopolitics'], source: 'Drive', date: '2026-04-01', status: 'indexed', relevance: 87 },
  { id: 3, title: 'Transcripción: Discurso APEC Lima — señales ocultas', tags: ['poder', 'masas'], source: 'Manual', date: '2026-03-30', status: 'indexed', relevance: 79 },
  { id: 4, title: 'Dataset: Actividad AIS — Estrecho de Ormuz', tags: ['maritime', 'geo'], source: 'AIS Feed', date: '2026-03-29', status: 'quarantine', relevance: 65 },
  { id: 5, title: 'PDF: Informe BIS sobre derivatives exposure', tags: ['economy', 'risk'], source: 'Drive', date: '2026-03-28', status: 'indexed', relevance: 83 },
  { id: 6, title: 'Análisis: Patrones de lenguaje — líderes G7', tags: ['conducta', 'poder'], source: 'Manual', date: '2026-03-27', status: 'indexed', relevance: 71 },
  { id: 7, title: 'Feed OSINT: Actividad RF elevada — Mar de China', tags: ['sigint', 'geo'], source: 'Telegram', date: '2026-03-26', status: 'quarantine', relevance: 58 },
];

const FILTER_TAGS = ['geo', 'economy', 'military', 'poder', 'conducta', 'masas', 'sigint', 'maritime', 'risk'];

// ── Upload zone ────────────────────────────────────────────────────────────────
function UploadZone({ onUpload }) {
  const [drag, setDrag] = useState(false);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef();

  const handle = async (files) => {
    if (!files?.length) return;
    setUploading(true);
    if (API) {
      try {
        const fd = new FormData();
        for (const f of files) fd.append('file', f);
        await fetch(`${API}/api/agente/drive/upload-aporte`, { method: 'POST', body: fd });
      } catch {}
    }
    await new Promise(r => setTimeout(r, 800));
    setUploading(false);
    onUpload?.();
  };

  return (
    <div
      onDragOver={e => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={e => { e.preventDefault(); setDrag(false); handle(e.dataTransfer.files); }}
      onClick={() => inputRef.current?.click()}
      style={{
        ...card,
        border: `1px dashed ${drag ? 'var(--cyan)' : 'rgba(0,229,255,0.18)'}`,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        gap: 10, cursor: 'pointer', minHeight: 110,
        background: drag ? 'rgba(0,229,255,0.04)' : 'var(--bg2)',
        transition: 'all .2s',
      }}
    >
      <input ref={inputRef} type="file" multiple style={{ display: 'none' }} onChange={e => handle(e.target.files)} />
      <Upload size={20} style={{ color: drag ? 'var(--cyan)' : 'var(--dim)' }} />
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontFamily: mono, fontSize: 11, color: uploading ? 'var(--cyan)' : 'var(--muted)', letterSpacing: '.05em' }}>
          {uploading ? 'Enviando a cuarentena…' : 'Soltar archivos aquí o hacer clic'}
        </div>
        <div style={{ fontFamily: mono, fontSize: 9, color: 'var(--dim)', marginTop: 4, letterSpacing: '.06em' }}>
          PDF · TXT · DOCX · JSON · MP4
        </div>
      </div>
    </div>
  );
}

// ── Document row ───────────────────────────────────────────────────────────────
function DocRow({ doc, onView }) {
  const isQ = doc.status === 'quarantine';
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12, padding: '12px 0',
      borderBottom: '1px solid rgba(0,229,255,0.06)', transition: 'all .15s',
    }}
      onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,229,255,0.02)'}
      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
    >
      <FileText size={14} style={{ color: isQ ? 'var(--amber)' : 'var(--cyan)', flexShrink: 0 }} />

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, color: 'var(--text)', fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginBottom: 4 }}>
          {doc.title}
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {doc.tags.map(t => <span key={t} style={badge('var(--cyan)')}>{t}</span>)}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, flexShrink: 0 }}>
        <span style={badge(isQ ? 'var(--amber)' : '#10b981')}>{isQ ? 'cuarentena' : 'indexado'}</span>
        <span style={{ fontFamily: mono, fontSize: 9, color: 'var(--dim)' }}>{doc.source} · {doc.date}</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
        <div style={{ fontFamily: mono, fontSize: 11, color: doc.relevance > 80 ? 'var(--green)' : 'var(--muted)', width: 30, textAlign: 'right' }}>
          {doc.relevance}%
        </div>
        <button onClick={() => onView?.(doc)} style={{
          background: 'none', border: '1px solid var(--border)', borderRadius: 2, cursor: 'pointer',
          color: 'var(--dim)', padding: '4px 6px', display: 'flex', alignItems: 'center', transition: 'all .15s',
        }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--cyan)'; e.currentTarget.style.borderColor = 'rgba(0,229,255,0.3)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--dim)'; e.currentTarget.style.borderColor = 'var(--border)'; }}
        >
          <Eye size={12} />
        </button>
      </div>
    </div>
  );
}

// ── Detail modal ───────────────────────────────────────────────────────────────
function DocModal({ doc, onClose }) {
  if (!doc) return null;
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}
      onClick={onClose}>
      <div style={{ ...card, width: '100%', maxWidth: 560, position: 'relative' }} onClick={e => e.stopPropagation()}>
        <button onClick={onClose} style={{ position: 'absolute', top: 16, right: 16, background: 'none', border: 'none', color: 'var(--dim)', cursor: 'pointer' }}>
          <X size={16} />
        </button>
        <div style={{ display: 'flex', gap: 10, marginBottom: 16, alignItems: 'center' }}>
          <Database size={16} style={{ color: 'var(--cyan)' }} />
          <span style={label('var(--cyan)')}>Documento OSINT</span>
        </div>
        <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)', marginBottom: 12, lineHeight: 1.5 }}>{doc.title}</div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          {doc.tags.map(t => <span key={t} style={badge('var(--cyan)')}>{t}</span>)}
          <span style={badge(doc.status === 'quarantine' ? 'var(--amber)' : '#10b981')}>{doc.status}</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {[
            { label: 'Fuente', value: doc.source },
            { label: 'Ingresado', value: doc.date },
            { label: 'Relevancia', value: `${doc.relevance}%` },
            { label: 'ID', value: `#${doc.id.toString().padStart(6, '0')}` },
          ].map(({ label: l, value }) => (
            <div key={l} style={{ background: 'var(--bg3)', padding: '10px 14px', border: '1px solid rgba(0,229,255,0.08)' }}>
              <div style={label()}>{l}</div>
              <div style={{ fontFamily: mono, fontSize: 12, color: 'var(--text)', marginTop: 4 }}>{value}</div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 16, padding: '10px 14px', background: 'rgba(0,229,255,0.04)', border: '1px solid rgba(0,229,255,0.12)', borderRadius: 2 }}>
          <div style={label()}>Ruta en bóveda</div>
          <code style={{ fontFamily: mono, fontSize: 10, color: 'var(--cyan)', marginTop: 4, display: 'block' }}>
            /boveda/osint/{doc.source.toLowerCase()}/{doc.id.toString().padStart(6, '0')}.json
          </code>
        </div>
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function Boveda() {
  const [docs, setDocs] = useState(MOCK_DOCS);
  const [query, setQuery] = useState('');
  const [activeTags, setActiveTags] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (API) {
      fetch(`${API}/api/rag/stats`).then(r => r.json()).then(setStats).catch(() => {});
    }
  }, []);

  const filtered = docs.filter(d => {
    const matchQ = !query || d.title.toLowerCase().includes(query.toLowerCase());
    const matchT = !activeTags.length || activeTags.every(t => d.tags.includes(t));
    const matchS = statusFilter === 'all' || d.status === statusFilter;
    return matchQ && matchT && matchS;
  });

  const toggleTag = (t) => setActiveTags(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]);

  const indexed = docs.filter(d => d.status === 'indexed').length;
  const quarantine = docs.filter(d => d.status === 'quarantine').length;

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1100, margin: '0 auto' }}>

      {/* ── Header ── */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <Database size={16} style={{ color: 'var(--cyan)' }} />
          <h1 style={{ fontFamily: mono, fontSize: 13, fontWeight: 700, color: 'var(--text)', letterSpacing: '.06em', textTransform: 'uppercase' }}>
            Bóveda OSINT
          </h1>
          <span style={badge('var(--cyan)')}>RAG</span>
        </div>
        <p style={{ fontFamily: mono, fontSize: 10, color: 'var(--dim)', letterSpacing: '.06em' }}>
          Repositorio vectorial de inteligencia · Qdrant + ChromaDB
        </p>
      </div>

      {/* ── Stats ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>
        {[
          { icon: Database, label: 'Total docs',   value: stats?.total_docs ?? docs.length, color: 'var(--cyan)' },
          { icon: FileText, label: 'Indexados',     value: stats?.indexed ?? indexed,        color: '#10b981'     },
          { icon: Clock,    label: 'Cuarentena',    value: stats?.quarantine ?? quarantine,  color: 'var(--amber)'},
          { icon: Tag,      label: 'Vectores',      value: stats?.vectors ?? '2.4k',         color: 'var(--indigo)'},
        ].map(({ icon: Icon, label: l, value, color }) => (
          <div key={l} style={{ ...card, display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ width: 36, height: 36, borderRadius: 4, background: `${color}14`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <Icon size={16} style={{ color }} />
            </div>
            <div>
              <div style={label(color)}>{l}</div>
              <div style={{ fontFamily: mono, fontSize: 20, fontWeight: 700, color: 'var(--text)', marginTop: 2 }}>{value}</div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 20 }}>

        {/* ── Left col ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Search + filter */}
          <div style={{ ...card, display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', gap: 10 }}>
              <div style={{ flex: 1, position: 'relative' }}>
                <Search size={13} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--dim)' }} />
                <input
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder="Buscar en la bóveda…"
                  style={{
                    width: '100%', background: 'var(--bg3)', border: '1px solid var(--border)',
                    color: 'var(--text)', fontFamily: mono, fontSize: 12, padding: '9px 12px 9px 34px',
                    outline: 'none', transition: 'border .15s',
                  }}
                  onFocus={e => e.target.style.borderColor = 'rgba(0,229,255,0.4)'}
                  onBlur={e => e.target.style.borderColor = 'var(--border)'}
                />
              </div>
              {['all', 'indexed', 'quarantine'].map(s => (
                <button key={s} onClick={() => setStatusFilter(s)} style={{
                  fontFamily: mono, fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase',
                  padding: '8px 14px', border: `1px solid ${statusFilter === s ? 'rgba(0,229,255,0.4)' : 'var(--border)'}`,
                  background: statusFilter === s ? 'rgba(0,229,255,0.06)' : 'var(--bg3)',
                  color: statusFilter === s ? 'var(--cyan)' : 'var(--dim)', cursor: 'pointer', transition: 'all .15s',
                }}>{s}</button>
              ))}
            </div>

            {/* Tag filters */}
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
              <Filter size={11} style={{ color: 'var(--dim)' }} />
              {FILTER_TAGS.map(t => {
                const active = activeTags.includes(t);
                return (
                  <button key={t} onClick={() => toggleTag(t)} style={{
                    fontFamily: mono, fontSize: 9, letterSpacing: '.08em', textTransform: 'uppercase',
                    padding: '3px 10px', border: `1px solid ${active ? 'rgba(0,229,255,0.5)' : 'rgba(0,229,255,0.12)'}`,
                    background: active ? 'rgba(0,229,255,0.1)' : 'transparent',
                    color: active ? 'var(--cyan)' : 'var(--dim)', cursor: 'pointer', borderRadius: 2, transition: 'all .15s',
                  }}>{t}</button>
                );
              })}
              {activeTags.length > 0 && (
                <button onClick={() => setActiveTags([])} style={{ background: 'none', border: 'none', color: 'var(--dim)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <X size={10} /><span style={{ fontFamily: mono, fontSize: 9 }}>limpiar</span>
                </button>
              )}
            </div>
          </div>

          {/* Doc list */}
          <div style={card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <span style={label()}>Documentos · {filtered.length} resultados</span>
              <span style={{ fontFamily: mono, fontSize: 9, color: 'var(--dim)' }}>RELEVANCIA ↓</span>
            </div>
            {filtered.length ? filtered.map(d => (
              <DocRow key={d.id} doc={d} onView={setSelectedDoc} />
            )) : (
              <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--dim)', fontFamily: mono, fontSize: 11 }}>
                Sin resultados para los filtros activos
              </div>
            )}
          </div>
        </div>

        {/* ── Right col ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Upload */}
          <div>
            <div style={{ ...label(), marginBottom: 8, display: 'block' }}>Ingresar documento</div>
            <UploadZone onUpload={() => {}} />
          </div>

          {/* RAG pipeline */}
          <div style={card}>
            <div style={{ ...label(), marginBottom: 14, display: 'block' }}>Pipeline RAG</div>
            {[
              { step: 'Ingreso',     desc: 'Discord / Drive / Manual', color: 'var(--cyan)'   },
              { step: 'Cuarentena', desc: 'Anti-spam + anti-doxxing',  color: 'var(--amber)'  },
              { step: 'Chunking',   desc: 'Segmentación semántica',    color: 'var(--indigo)' },
              { step: 'Embeddings', desc: 'text-embedding-004',        color: '#7c3aed'       },
              { step: 'Indexado',   desc: 'Qdrant · colección OSINT',  color: '#10b981'       },
            ].map(({ step, desc, color }, i, arr) => (
              <div key={step} style={{ display: 'flex', gap: 10, marginBottom: i < arr.length - 1 ? 2 : 0 }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 20 }}>
                  <div style={{ width: 7, height: 7, borderRadius: '50%', background: color, boxShadow: `0 0 6px ${color}`, flexShrink: 0, marginTop: 4 }} />
                  {i < arr.length - 1 && <div style={{ width: 1, flex: 1, background: 'var(--border)', margin: '2px 0' }} />}
                </div>
                <div style={{ paddingBottom: i < arr.length - 1 ? 10 : 0 }}>
                  <div style={{ fontFamily: mono, fontSize: 10, color: 'var(--text)', fontWeight: 600 }}>{step}</div>
                  <div style={{ fontFamily: mono, fontSize: 9, color: 'var(--dim)', marginTop: 1 }}>{desc}</div>
                </div>
              </div>
            ))}
          </div>

          {/* API endpoint */}
          <div style={{ ...card, background: 'rgba(0,229,255,0.03)', border: '1px solid rgba(0,229,255,0.12)' }}>
            <div style={{ ...label('var(--cyan)'), marginBottom: 10, display: 'block' }}>Endpoint contribución</div>
            <code style={{ fontFamily: mono, fontSize: 10, color: 'var(--cyan)', display: 'block', marginBottom: 6 }}>
              POST /api/agente/drive/upload-aporte
            </code>
            <div style={{ fontFamily: mono, fontSize: 9, color: 'var(--dim)' }}>
              Acepta multipart/form-data · file field
            </div>
            <div style={{ marginTop: 12 }}>
              <a href="https://discord.gg/QDUkfVA5" target="_blank" rel="noopener noreferrer"
                style={{ fontFamily: mono, fontSize: 9, color: '#10b981', textDecoration: 'none', letterSpacing: '.06em' }}>
                ↗ DISCORD OSINT CHANNEL
              </a>
            </div>
          </div>
        </div>
      </div>

      {selectedDoc && <DocModal doc={selectedDoc} onClose={() => setSelectedDoc(null)} />}
    </div>
  );
}
