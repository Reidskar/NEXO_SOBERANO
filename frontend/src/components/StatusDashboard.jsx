// ============================================================
// NEXO SOBERANO — Status Dashboard Component
// © 2026 elanarcocapital.com
// ============================================================
import { useState, useEffect } from "react"

const API_BASE = import.meta.env.VITE_API_URL || ""

function StatusBadge({ status }) {
  const color = status === "ok" || status === "online"
    ? "bg-green-500"
    : status === "degraded"
    ? "bg-yellow-500"
    : "bg-red-500"
  return (
    <span className={`inline-block w-2 h-2 rounded-full ${color} mr-2`} />
  )
}

function MetricCard({ label, value, sub }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">
        {label}
      </p>
      <p className="text-white text-2xl font-medium">{value}</p>
      {sub && <p className="text-gray-500 text-xs mt-1">{sub}</p>}
    </div>
  )
}

export default function StatusDashboard() {
  const [health, setHealth]   = useState(null)
  const [domain, setDomain]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)

  const fetchData = async () => {
    try {
      const [h, d] = await Promise.all([
        fetch(`${API_BASE}/api/health`).then(r => r.json()),
        fetch(`${API_BASE}/api/tools/domain-scan`).then(r => r.json())
      ])
      setHealth(h)
      setDomain(d)
      setLastUpdate(new Date().toLocaleTimeString("es-CL"))
      setError(null)
    } catch (e) {
      setError("No se pudo conectar con la API")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-gray-400">
      Cargando estado del sistema...
    </div>
  )

  if (error) return (
    <div className="flex items-center justify-center h-64 text-red-400">
      {error}
    </div>
  )

  const services = health?.services || {}
  const circuits = health?.circuit_breakers || {}
  const openCircuits = circuits?.open_circuits || []

  return (
    <div className="p-6 max-w-4xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-white text-xl font-medium">
            NEXO SOBERANO
          </h1>
          <p className="text-gray-400 text-sm">
            elanarcocapital.com
          </p>
        </div>
        <div className="text-right">
          <p className="text-gray-500 text-xs">
            Actualizado: {lastUpdate}
          </p>
          <button
            onClick={fetchData}
            className="text-indigo-400 text-xs hover:text-indigo-300 mt-1"
          >
            Actualizar
          </button>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <MetricCard
          label="Agentes"
          value={health?.agents?.total_registered || 10}
          sub="activos 24/7"
        />
        <MetricCard
          label="SSL"
          value={domain?.ssl_days_left ? `${domain.ssl_days_left}d` : "—"}
          sub={domain?.ssl_valid ? "válido" : "revisar"}
        />
        <MetricCard
          label="Circuit Breakers"
          value={openCircuits.length === 0 ? "OK" : `${openCircuits.length} abiertos`}
          sub={openCircuits.length === 0 ? "sin alertas" : openCircuits.join(", ")}
        />
        <MetricCard
          label="API"
          value={health ? "Online" : "Offline"}
          sub={health?.version || "NEXO v1.0"}
        />
      </div>

      {/* Services */}
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700 mb-4">
        <h2 className="text-gray-300 text-sm font-medium mb-3">
          Servicios
        </h2>
        <div className="space-y-2">
          {Object.entries(services).map(([name, status]) => (
            <div key={name} className="flex items-center justify-between">
              <span className="text-gray-400 text-sm flex items-center">
                <StatusBadge status={status} />
                {name}
              </span>
              <span className="text-gray-500 text-xs">{status}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Domain */}
      {domain && (
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <h2 className="text-gray-300 text-sm font-medium mb-3">
            Dominio
          </h2>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">elanarcocapital.com</span>
              <span className={domain.ssl_valid
                ? "text-green-400" : "text-red-400"}>
                {domain.ssl_valid ? "SSL OK" : "SSL Error"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">DNS</span>
              <span className={domain.dns_resolved
                ? "text-green-400" : "text-red-400"}>
                {domain.dns_resolved
                  ? domain.ips?.[0] : "No resuelve"}
              </span>
            </div>
            {domain.alerts?.length > 0 && domain.alerts.map((a, i) => (
              <div key={i} className="text-yellow-400 text-xs">
                ⚠ {a}
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  )
}
