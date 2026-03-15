function Mapa() {
  return (
    <div className="p-4 space-y-4">
      <div>
        <h2 className="text-lg font-bold text-nexo-text">Mapa Geopolítico</h2>
        <p className="text-xs text-nexo-dim">Visualización de infraestructura y zonas de interés</p>
      </div>

      <div className="nexo-card p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-nexo-green/15 flex items-center justify-center">
            <span className="text-nexo-green-l text-lg">◎</span>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-nexo-text">Módulo en desarrollo</h3>
            <p className="text-xs text-nexo-dim">Integración con API Overpass para datos geoespaciales</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="bg-nexo-dark rounded-lg p-4 border border-nexo-border/50">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs text-[#00d4ff]">◈</span>
              <h4 className="text-sm font-semibold text-nexo-text">Zonas activas</h4>
            </div>
            <p className="text-xs text-nexo-muted leading-relaxed">
              Datos en tiempo real de infraestructura geopolítica disponibles vía
              <code className="text-nexo-green-l bg-nexo-surface px-1 py-0.5 rounded text-[10px] ml-1">/eventos/infraestructura</code>
            </p>
          </div>
          <div className="bg-nexo-dark rounded-lg p-4 border border-nexo-border/50">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs text-amber-400">◎</span>
              <h4 className="text-sm font-semibold text-nexo-text">Overpass API</h4>
            </div>
            <p className="text-xs text-nexo-muted leading-relaxed">
              Motor de consultas OpenStreetMap para puntos de interés, fronteras, bases militares y rutas estratégicas.
            </p>
          </div>
        </div>
      </div>

      {/* Placeholder visual del mapa */}
      <div className="nexo-card overflow-hidden">
        <div className="relative h-64 bg-gradient-to-br from-nexo-dark via-nexo-panel to-nexo-surface flex items-center justify-center">
          <div className="absolute inset-0 opacity-5">
            {/* Grid visual */}
            <div className="w-full h-full" style={{
              backgroundImage: "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
              backgroundSize: "40px 40px"
            }} />
          </div>
          <div className="text-center z-10">
            <div className="w-16 h-16 rounded-full border-2 border-nexo-border flex items-center justify-center mx-auto mb-3">
              <span className="text-2xl text-nexo-dim">◎</span>
            </div>
            <p className="text-sm text-nexo-muted">Vista de mapa próximamente</p>
            <p className="text-[10px] text-nexo-dim mt-1">Integración Leaflet + datos Overpass</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Mapa;
