function Sidebar({ currentPage, setCurrentPage }) {
  const menuItems = [
    { id: "dashboard",    label: "Dashboard",    icon: "◈" },
    { id: "inteligencia", label: "Inteligencia", icon: "◉" },
    { id: "documentos",   label: "Documentos",   icon: "◫" },
    { id: "mapa",         label: "Mapa",         icon: "◎" },
    { id: "comunidad",    label: "Comunidad",    icon: "◆" },
    { id: "admin",        label: "Admin",        icon: "⚙" },
  ];

  return (
    <div className="w-[220px] bg-nexo-panel border-r border-nexo-border flex flex-col shrink-0">
      {/* Branding */}
      <div className="px-5 py-5 border-b border-nexo-border">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded bg-nexo-green flex items-center justify-center text-white font-bold text-sm shadow-nexo">
            Nₛ
          </div>
          <div>
            <h1 className="text-sm font-bold text-nexo-text leading-tight tracking-wide">NEXO</h1>
            <p className="text-[10px] text-nexo-muted font-medium tracking-widest uppercase">Soberano</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-3 space-y-0.5">
        <p className="text-[10px] text-nexo-dim font-semibold tracking-widest uppercase px-3 pb-2 pt-1">Módulos</p>
        {menuItems.map(item => (
          <button
            key={item.id}
            onClick={() => setCurrentPage(item.id)}
            className={`w-full text-left px-3 py-2.5 rounded text-sm flex items-center gap-2.5 transition-nexo group ${
              currentPage === item.id
                ? "bg-nexo-green text-white shadow-nexo"
                : "text-nexo-muted hover:bg-nexo-surface hover:text-nexo-text"
            }`}
          >
            <span className={`text-xs w-5 text-center ${
              currentPage === item.id ? "text-nexo-accent" : "text-nexo-dim group-hover:text-nexo-muted"
            }`}>
              {item.icon}
            </span>
            <span className="font-medium">{item.label}</span>
          </button>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-nexo-border">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-nexo-dim font-medium">v2.0.0</span>
          <span className="nexo-badge bg-nexo-green/20 text-nexo-green-l">Activo</span>
        </div>
      </div>
    </div>
  );
}

export default Sidebar;
