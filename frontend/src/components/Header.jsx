import { useEffect, useState } from "react";

function Header() {
  const [status, setStatus] = useState("loading");
  const [info, setInfo] = useState({});

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/estado");
        if (response.ok) {
          const data = await response.json();
          setStatus(data.online ? "online" : "offline");
          setInfo(data);
        } else {
          setStatus("offline");
        }
      } catch (error) {
        setStatus("offline");
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  const statusColor = {
    online: "text-green-400 bg-green-900/30",
    offline: "text-red-400 bg-red-900/30",
    loading: "text-yellow-400 bg-yellow-900/30"
  };

  const statusIcon = {
    online: "🟢",
    offline: "🔴",
    loading: "🟡"
  };

  return (
    <div className="h-16 bg-gray-800 border-b border-gray-700 flex items-center justify-between px-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-blue-400">Nexo Soberano</h1>
      </div>
      
      <div className={`flex items-center gap-2 px-4 py-2 rounded ${statusColor[status]}`}>
        <span className="text-lg">{statusIcon[status]}</span>
        <span className="font-semibold capitalize">{status}</span>
        {status === "online" && info.version && (
          <span className="ml-4 text-xs text-gray-300">v{info.version}</span>
        )}
        {status === "online" && info.docs_indexados != null && (
          <span className="ml-4 text-xs text-gray-300">📁 {info.docs_indexados} docs</span>
        )}
        {status === "online" && info.chunks_total != null && (
          <span className="ml-4 text-xs text-gray-300">🔗 {info.chunks_total} chunks</span>
        )}
        {status === "online" && info.costos_hoy && (
          <span className="ml-4 text-xs text-gray-300">💰 {info.costos_hoy}</span>
        )}
      </div>
    </div>
  );
}

export default Header;
