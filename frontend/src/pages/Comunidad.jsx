function Comunidad() {
  return (
    <div className="p-4 space-y-4">
      <div>
        <h2 className="text-lg font-bold text-nexo-text">Comunidad</h2>
        <p className="text-xs text-nexo-dim">Gestión de aportes comunitarios y colaboración</p>
      </div>

      {/* Aportes */}
      <div className="nexo-card p-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-lg bg-nexo-green/15 flex items-center justify-center">
            <span className="text-nexo-green-l">◆</span>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-nexo-text">Aportes de la comunidad</h3>
            <p className="text-[10px] text-nexo-dim">Los aportes pasan por cuarentena antes de ser indexados</p>
          </div>
        </div>
        <div className="bg-nexo-dark rounded-lg p-3 border border-nexo-border/50">
          <p className="text-xs text-nexo-muted leading-relaxed">
            Los miembros pueden enviar documentos e información vía Discord. Cada aporte se almacena en cuarentena
            en Google Drive con un ID único para trazabilidad, luego pasa por revisión de contenido (anti-spam, anti-doxxing)
            antes de ser incorporado a la bóveda de inteligencia.
          </p>
        </div>
      </div>

      {/* Flujo */}
      <div className="nexo-card p-4">
        <h3 className="text-sm font-semibold text-nexo-text mb-3 flex items-center gap-2">
          <span className="text-nexo-dim">△</span> Flujo de aportes
        </h3>
        <div className="flex items-center gap-2 text-xs">
          {["Discord", "→", "API", "→", "Cuarentena", "→", "Revisión", "→", "Bóveda RAG"].map((step, i) => (
            step === "→"
              ? <span key={i} className="text-nexo-dim">→</span>
              : <span key={i} className="nexo-badge bg-nexo-surface text-nexo-muted border border-nexo-border px-2.5 py-1">{step}</span>
          ))}
        </div>
      </div>

      {/* Discord */}
      <div className="nexo-card p-4">
        <h3 className="text-sm font-semibold text-nexo-text mb-3 flex items-center gap-2">
          <span className="text-nexo-dim">◈</span> Servidor Discord
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-nexo-dark rounded-lg p-3 border border-nexo-border/50">
            <p className="text-[10px] text-nexo-dim font-semibold uppercase mb-1">Invitación</p>
            <a
              href="https://discord.gg/QDUkfVA5"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-nexo-green-l hover:text-nexo-accent transition-colors"
            >
              discord.gg/QDUkfVA5 ↗
            </a>
          </div>
          <div className="bg-nexo-dark rounded-lg p-3 border border-nexo-border/50">
            <p className="text-[10px] text-nexo-dim font-semibold uppercase mb-1">Bot IA</p>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 nexo-pulse" />
              <span className="text-xs text-nexo-muted">Nexo Agent activo</span>
            </div>
          </div>
        </div>
      </div>

      {/* Endpoint */}
      <div className="nexo-card p-4">
        <h3 className="text-sm font-semibold text-nexo-text mb-2 flex items-center gap-2">
          <span className="text-nexo-dim">◫</span> API de aportes
        </h3>
        <code className="text-xs text-nexo-green-l bg-nexo-dark px-2 py-1 rounded border border-nexo-border/50">
          POST /agente/drive/upload-aporte
        </code>
      </div>
    </div>
  );
}

export default Comunidad;
