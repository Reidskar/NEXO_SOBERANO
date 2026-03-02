import { useEffect, useState } from "react";
import ChatBox from "../components/ChatBox";

function Dashboard() {
  const [estado, setEstado] = useState(null);
  const [documentos, setDocumentos] = useState([]);
  const [historial, setHistorial] = useState([]);
  const [costos, setCostos] = useState(null);

  useEffect(() => {
    const cargar = async () => {
      try {
        const [st, docs, hist, cos] = await Promise.all([
          fetch("/api/estado").then(r => r.json()),
          fetch("/api/documentos").then(r => r.json()),
          fetch("/api/historial").then(r => r.json()),
          fetch("/api/costos").then(r => r.json())
        ]);
        setEstado(st);
        setDocumentos(docs);
        setHistorial(hist);
        setCostos(cos);
      } catch (e) {
        console.error("Error cargando datos del dashboard", e);
      }
    };
    cargar();
  }, []);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 p-6">
      {/* Panel principal */}
      <div className="lg:col-span-2 bg-gray-800 rounded-lg border border-gray-700 p-6">
        <h2 className="text-2xl font-bold mb-4">Dashboard Principal</h2>
        <div className="space-y-4">
          {estado && (
            <div className="bg-gray-700 p-4 rounded">
              <h3 className="font-semibold mb-2">📊 Estadísticas</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-600 p-3 rounded">
                  <p className="text-sm text-gray-300">Documentos indexados</p>
                  <p className="text-2xl font-bold">{estado.docs_indexados}</p>
                </div>
                <div className="bg-gray-600 p-3 rounded">
                  <p className="text-sm text-gray-300">Chunks totales</p>
                  <p className="text-2xl font-bold">{estado.chunks_total}</p>
                </div>
                <div className="bg-gray-600 p-3 rounded col-span-2">
                  <p className="text-sm text-gray-300">Costos hoy</p>
                  <p className="text-2xl font-bold">{estado.costos_hoy}</p>
                </div>
              </div>
            </div>
          )}

          <div className="bg-gray-700 p-4 rounded">
            <h3 className="font-semibold mb-2">◆ Documentos recientes</h3>
            {documentos.length === 0 ? (
              <p className="text-gray-400">Sin documentos indexados</p>
            ) : (
              <ul className="text-sm space-y-1">
                {documentos.slice(0, 5).map((d,i) => (
                  <li key={i}>[{d.cat}] {d.nombre} <span className="text-gray-500">{d.fecha}</span></li>
                ))}
              </ul>
            )}
          </div>

          <div className="bg-gray-700 p-4 rounded">
            <h3 className="font-semibold mb-2">🕘 Historial de consultas</h3>
            {historial.length === 0 ? (
              <p className="text-gray-400">Aún no hay consultas</p>
            ) : (
              <ul className="text-sm space-y-1">
                {historial.map((h,i) => (
                  <li key={i}>{h.fecha} – {h.pregunta} ({h.chunks} chunks, {h.ms}ms)</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* Chat panel */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden flex flex-col">
        <ChatBox />
      </div>
    </div>
  );
}

export default Dashboard;
