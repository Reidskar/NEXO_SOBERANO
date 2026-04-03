import React, { useState } from 'react';
import { Users, MessageSquare, Upload, ExternalLink, CheckCircle, Clock, Shield } from 'lucide-react';

const mono = "'Space Mono', monospace";

const card = {
  background: 'var(--bg2)',
  border: '1px solid var(--border)',
  padding: '20px 24px',
};

const lbl = (color = 'var(--dim)') => ({
  fontFamily: mono, fontSize: 10, color, letterSpacing: '.12em', textTransform: 'uppercase',
});

const badge = (color = 'var(--cyan)') => ({
  fontFamily: mono, fontSize: 9, letterSpacing: '.08em', textTransform: 'uppercase',
  background: `${color}14`, color, border: `1px solid ${color}30`,
  padding: '3px 10px', borderRadius: 2,
});

const PIPELINE_STEPS = [
  { icon: MessageSquare, label: 'Discord',    color: '#5865F2',       desc: 'Canal #aportes o DM al bot'           },
  { icon: Shield,        label: 'API',        color: 'var(--cyan)',   desc: 'Ingesta vía REST endpoint'            },
  { icon: Clock,         label: 'Cuarentena', color: 'var(--amber)',  desc: 'Filtro anti-spam + anti-doxxing'      },
  { icon: CheckCircle,   label: 'Revisión',   color: 'var(--indigo)', desc: 'Validación de contenido'              },
  { icon: Upload,        label: 'Bóveda RAG', color: '#10b981',       desc: 'Indexado en Qdrant + Drive'           },
];

const CHANNELS = [
  { name: '#aportes-osint',    desc: 'Documentos e inteligencia',   badge: 'OSINT',    color: 'var(--cyan)'   },
  { name: '#análisis-geo',     desc: 'Análisis geopolítico',         badge: 'GEO',      color: '#10b981'       },
  { name: '#economia-austria', desc: 'Escuela austriaca y mercados', badge: 'ECO',      color: 'var(--amber)'  },
  { name: '#fuentes-libres',   desc: 'Links y referencias externas', badge: 'SOURCES',  color: 'var(--indigo)' },
  { name: '#alertas-nexo',     desc: 'Updates del sistema',          badge: 'SYSTEM',   color: 'var(--dim)'    },
];

export default function Comunidad() {
  const [copied, setCopied] = useState(false);

  const copyEndpoint = () => {
    navigator.clipboard.writeText('POST /api/agente/drive/upload-aporte');
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div style={{ padding: '28px 32px', maxWidth: 960, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <Users size={16} style={{ color: 'var(--cyan)' }} />
          <h1 style={{ fontFamily: mono, fontSize: 13, fontWeight: 700, color: 'var(--text)', letterSpacing: '.06em', textTransform: 'uppercase' }}>
            Terminal Omnicanal
          </h1>
          <span style={badge('var(--cyan)')}>Discord</span>
        </div>
        <p style={{ fontFamily: mono, fontSize: 10, color: 'var(--dim)', letterSpacing: '.06em' }}>
          Gestión de aportes comunitarios · Colaboración abierta
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 20 }}>

        {/* Left */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Pipeline */}
          <div style={card}>
            <div style={{ ...lbl(), marginBottom: 18, display: 'block' }}>Flujo de aportes</div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 0, overflowX: 'auto' }}>
              {PIPELINE_STEPS.map(({ icon: Icon, label: l, color, desc }, i) => (
                <React.Fragment key={l}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, minWidth: 90 }}>
                    <div style={{
                      width: 40, height: 40, borderRadius: 4,
                      background: `${color}14`, border: `1px solid ${color}30`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <Icon size={16} style={{ color }} />
                    </div>
                    <div style={{ fontFamily: mono, fontSize: 10, color: 'var(--text)', fontWeight: 600, textAlign: 'center' }}>{l}</div>
                    <div style={{ fontFamily: mono, fontSize: 8, color: 'var(--dim)', textAlign: 'center', lineHeight: 1.4 }}>{desc}</div>
                  </div>
                  {i < PIPELINE_STEPS.length - 1 && (
                    <div style={{ flex: 1, height: 1, background: 'var(--border)', minWidth: 16, marginTop: 20 }} />
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Channels */}
          <div style={card}>
            <div style={{ ...lbl(), marginBottom: 14, display: 'block' }}>Canales Discord</div>
            {CHANNELS.map(({ name, desc, badge: b, color }) => (
              <div key={name} style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0',
                borderBottom: '1px solid rgba(0,229,255,0.06)',
              }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: color, boxShadow: `0 0 5px ${color}`, flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontFamily: mono, fontSize: 11, color: 'var(--text)', marginBottom: 2 }}>{name}</div>
                  <div style={{ fontFamily: mono, fontSize: 9, color: 'var(--dim)' }}>{desc}</div>
                </div>
                <span style={badge(color)}>{b}</span>
              </div>
            ))}
          </div>

          {/* Reglas */}
          <div style={{ ...card, background: 'rgba(239,68,68,0.03)', border: '1px solid rgba(239,68,68,0.12)' }}>
            <div style={{ ...lbl('#ef4444'), marginBottom: 12, display: 'block' }}>Normas de contribución</div>
            {[
              'No doxxing — información personal protegida automáticamente',
              'Fuentes verificables — incluir origen o URL cuando sea posible',
              'Sin desinformación deliberada — los aportes pasan por cuarentena',
              'Idioma: español o inglés preferiblemente',
              'Adjuntar contexto geopolítico o económico relevante',
            ].map((rule, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 8, alignItems: 'flex-start' }}>
                <span style={{ fontFamily: mono, fontSize: 10, color: 'var(--dim)', flexShrink: 0, marginTop: 1 }}>{(i + 1).toString().padStart(2, '0')}.</span>
                <span style={{ fontFamily: mono, fontSize: 10, color: 'var(--muted)', lineHeight: 1.5 }}>{rule}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Discord CTA */}
          <div style={{ ...card, background: 'rgba(88,101,242,0.06)', border: '1px solid rgba(88,101,242,0.2)', textAlign: 'center' }}>
            <div style={{ width: 48, height: 48, borderRadius: 8, background: 'rgba(88,101,242,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 12px' }}>
              <MessageSquare size={22} style={{ color: '#5865F2' }} />
            </div>
            <div style={{ fontFamily: mono, fontSize: 11, color: 'var(--text)', fontWeight: 600, marginBottom: 4 }}>Servidor Discord</div>
            <div style={{ fontFamily: mono, fontSize: 9, color: 'var(--dim)', marginBottom: 14, lineHeight: 1.5 }}>
              Comunidad de analistas e investigadores independientes
            </div>
            <a
              href="https://discord.gg/QDUkfVA5"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                fontFamily: mono, fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase',
                padding: '10px 16px', background: '#5865F2', color: '#fff',
                textDecoration: 'none', cursor: 'pointer', transition: 'opacity .15s',
              }}
            >
              <ExternalLink size={12} />
              Unirse al servidor
            </a>
          </div>

          {/* Bot status */}
          <div style={card}>
            <div style={{ ...lbl(), marginBottom: 14, display: 'block' }}>Bot IA — Nexo Agent</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981', boxShadow: '0 0 8px #10b981', animation: 'blink-dot 1.8s infinite' }} />
              <span style={{ fontFamily: mono, fontSize: 11, color: 'var(--text)' }}>Activo en servidor</span>
            </div>
            {[
              { cmd: '/analizar', desc: 'Análisis geopolítico' },
              { cmd: '/fuentes',  desc: 'Consultar RAG'         },
              { cmd: '/aporte',   desc: 'Enviar documento'      },
              { cmd: '/mercados', desc: 'Snapshot de activos'   },
            ].map(({ cmd, desc }) => (
              <div key={cmd} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: '1px solid rgba(0,229,255,0.05)' }}>
                <code style={{ fontFamily: mono, fontSize: 10, color: 'var(--cyan)' }}>{cmd}</code>
                <span style={{ fontFamily: mono, fontSize: 9, color: 'var(--dim)' }}>{desc}</span>
              </div>
            ))}
          </div>

          {/* API endpoint */}
          <div style={{ ...card, background: 'rgba(0,229,255,0.03)', border: '1px solid rgba(0,229,255,0.12)' }}>
            <div style={{ ...lbl('var(--cyan)'), marginBottom: 10, display: 'block' }}>Endpoint REST</div>
            <div
              onClick={copyEndpoint}
              style={{
                fontFamily: mono, fontSize: 10,
                color: copied ? '#10b981' : 'var(--cyan)',
                padding: '8px 12px', background: 'var(--bg3)',
                border: `1px solid ${copied ? 'rgba(16,185,129,0.4)' : 'rgba(0,229,255,0.15)'}`,
                cursor: 'pointer', marginBottom: 8, transition: 'all .15s',
              }}
              title="Copiar"
            >
              {copied ? '✓ Copiado' : 'POST /api/agente/drive/upload-aporte'}
            </div>
            <div style={{ fontFamily: mono, fontSize: 9, color: 'var(--dim)', lineHeight: 1.5 }}>
              Acepta <code style={{ color: 'var(--cyan)' }}>multipart/form-data</code> con campo <code style={{ color: 'var(--cyan)' }}>file</code>.
              Los archivos pasan a cuarentena automáticamente.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
