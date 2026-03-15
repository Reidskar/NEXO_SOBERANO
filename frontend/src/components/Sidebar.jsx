function Sidebar({ currentPage, setCurrentPage }) {
  const menuItems = [
    { id: "dashboard", label: "Dashboard", icon: "📊" },
    { id: "mapa", label: "Mapa", icon: "🗺️" },
    { id: "inteligencia", label: "Inteligencia", icon: "🧠" },
    { id: "documentos", label: "Documentos", icon: "📄" },
    { id: "comunidad", label: "Comunidad", icon: "👥" },
    { id: "admin", label: "Admin", icon: "⚙️" }
  ];

  return (
    <div className="w-64 bg-[#111118]/80 backdrop-blur-md border border-[#00d4ff]/10 border-r border-gray-700 flex flex-col">
      <div className="p-6 border-b border-gray-700">
        <h2 className="text-sm font-bold text-gray-400">MENÚ</h2>
      </div>
      
      <nav className="flex-1 p-4 space-y-2">
        {menuItems.map(item => (
          <button
            key={item.id}
            onClick={() => setCurrentPage(item.id)}
            className={`w-full text-left px-4 py-3 rounded transition-all ${
              currentPage === item.id
                ? "bg-blue-600 text-white"
                : "text-gray-300 hover:bg-gray-700"
            }`}
          >
            <span className="mr-3">{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>
      
      <div className="p-4 border-t border-gray-700 space-y-2">
        <div className="text-xs text-gray-500">
          <p>v1.0.0</p>
        </div>
      </div>
    </div>
  );
}

export default Sidebar;
