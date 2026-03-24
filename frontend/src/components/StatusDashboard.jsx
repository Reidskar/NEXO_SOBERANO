// ============================================================
// NEXO SOBERANO — Status Dashboard Component
// © 2026 elanarcocapital.com
// ============================================================
import { useState, useEffect } from 'react';
import { RefreshCw, Activity, Shield, Cpu, Globe } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

function MetricCard({ icon: Icon, label, value, sub, color = '#00e5ff' }) {
  return (
    <div style={{
      background: 'var(--bg2)', border: '1px solid var(--border)',
      padding: '20px 24px', transition: 'all 0.3s'
    }}
      onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(0,229,255,0.3)'}
      onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        {Icon && <Icon size={14} style={{ color }} />}
        <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: 'var(--dim)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>{label}</span>
      </div>
      <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em', marginBottom: 4 }}>{value}</div>
      {sub && <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: 'var(--muted)' }}>{sub}</div>}
    </div>
  );
}

function ServiceRow({ name, status }) {
  const color = status === 'ok' || status === 'online' ? '#10b981'
    : status === 'degraded' ? '#f59e0b' : '#ef4444';
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid rgba(0,229,255,0.06)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, boxShadow: `0 0 6px ${color}` }} />
        <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: 'var(--muted)' }}>{name}</span>
      </div>
      <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color }}>{status}</span>
    </div>
  );
}

export default function StatusDashboard() {
  const [health, setHealth] = useState(null);
  const [domain, setDomain] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  const fetchData = async () => {
    try {
      const [h, d] = await Promise.allSettled([
        fetch(`${API_BASE}/api/health`).then(r => r.json()),
        fetch(`${API_BASE}/api/tools/domain-scan`).then(r => r.json()),
      ]);
      if (h.status === 'fulfilled') setHealth(h.value);
      if (d.status === 'fulfilled') setDomain(d.value);
      setLastUpdate(new Date().toLocaleTimeString('es-CL'));
      setError(null);
    } catch (e) {
      setError('No se pudo conectar con la API');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 256 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontFamily: "'Space Mono', monospace", fontSize: 12, color: 'var(--muted)' }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--cyan)', animation: 'blink-dot 1s infinite' }} />
        Cargando estado del sistema...
      </div>
    </div>
  );

  const services = health?.services || {};
  const circuits = health?.circuit_breakers || {};
  const openCircuits = circuits?.open_circuits || [];

  return (
    <div style={{ maxWidth: 1100 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 32 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text)', marginBottom: 4 }}>Command Center</h1>
          <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: 'var(--muted)' }}>
            elanarcocapital.com · {lastUpdate ? `Actualizado ${lastUpdate}` : 'Cargando...'}
          </p>
        </div>
        <button onClick={fetchData} style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px',
          background: 'transparent', border: '1px solid var(--border)',
          color: 'var(--muted)', cursor: 'pointer', fontFamily: "'Space Mono', monospace",
          fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', transition: 'all 0.2s'
        }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--cyan)'; e.currentTarget.style.color = 'var(--cyan)'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--muted)'; }}
        >
          <RefreshCw size={12} />
          Actualizar
        </button>
      </div>

      {error && (
        <div style={{
          background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)',
          padding: '12px 20px', marginBottom: 24, fontFamily: "'Space Mono', monospace",
          fontSize: 12, color: '#ef4444'
        }}>
          ⚠ {error} — Mostrando datos en caché
        </div>
      )}

      {/* Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1, background: 'var(--border)', border: '1px solid var(--border)', marginBottom: 24 }}>
        <MetricCard icon={Activity} label="Agentes" value={health?.agents?.total_registered || 10} sub="activos 24/7" color="#10b981" />
        <MetricCard icon={Shield} label="SSL" value={domain?.ssl_days_left ? `${domain.ssl_days_left}d` : '—'} sub={domain?.ssl_valid ? 'Certificado válido' : 'Revisar certificado'} color="#00e5ff" />
        <MetricCard icon={Cpu} label="Circuit Breakers" value={openCircuits.length === 0 ? 'OK' : `${openCircuits.length} abiertos`} sub={openCircuits.length === 0 ? 'Sin alertas activas' : openCircuits.join(', ')} color={openCircuits.length === 0 ? '#10b981' : '#f59e0b'} />
        <MetricCard icon={Globe} label="API Status" value={health ? 'Online' : 'Offline'} sub={health?.version || 'NEXO v3.0.0'} color={health ? '#10b981' : '#ef4444'} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Services */}
        <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', padding: '24px 28px' }}>
          <h2 style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: 'var(--cyan)', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: 20 }}>
            Servicios del Sistema
          </h2>
          {Object.keys(services).length > 0 ? (
            Object.entries(services).map(([name, status]) => (
              <ServiceRow key={name} name={name} status={status} />
            ))
          ) : (
            <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: 'var(--dim)', padding: '20px 0' }}>
              Sin datos de servicios disponibles
            </div>
          )}
        </div>

        {/* Domain */}
        <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', padding: '24px 28px' }}>
          <h2 style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: 'var(--cyan)', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: 20 }}>
            Estado del Dominio
          </h2>
          {domain ? (
            <div>
              <ServiceRow name="elanarcocapital.com" status={domain.ssl_valid ? 'ok' : 'error'} />
              <ServiceRow name="DNS Resolution" status={domain.dns_resolved ? 'ok' : 'error'} />
              {domain.ips?.length > 0 && (
                <div style={{ padding: '10px 0', borderBottom: '1px solid rgba(0,229,255,0.06)' }}>
                  <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: 'var(--muted)' }}>
                    IP: {domain.ips[0]}
                  </span>
                </div>
              )}
              {domain.alerts?.map((a, i) => (
                <div key={i} style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: '#f59e0b', padding: '6px 0' }}>
                  ⚠ {a}
                </div>
              ))}
            </div>
          ) : (
            <div>
              <ServiceRow name="elanarcocapital.com" status="loading" />
              <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: 'var(--dim)', padding: '16px 0' }}>
                Verificando dominio...
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
