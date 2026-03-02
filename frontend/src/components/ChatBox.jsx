import { useState } from "react";

function ChatBox() {
  const [pregunta, setPregunta] = useState("");
  const [categoria, setCategoria] = useState("");
  const [respuesta, setRespuesta] = useState("");
  const [fuentes, setFuentes] = useState([]);
  const [chunks, setChunks] = useState(null);
  const [ms, setMs] = useState(null);
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!message.trim()) return;

    setLoading(true);
    setRespuesta("");
    setFuentes([]);
    setChunks(null);
    setMs(null);

    try {
      const res = await fetch("http://localhost:8000/agente/consultar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pregunta: pregunta,
          categoria: categoria || undefined
        })
      });

      if (res.ok) {
        const data = await res.json();
        setRespuesta(data.respuesta || "Sin respuesta");
        setFuentes(data.fuentes || []);
        setChunks(data.chunks);
        setMs(data.ms);
      } else {
        const errorData = await res.json();
        setRespuesta(`⚠️ Error ${res.status}: ${errorData.detail || "Error procesando tu pregunta"}`);
      }
    } catch (error) {
      setResponse("❌ No se pudo conectar con el backend");
      console.error("Error:", error);
    } finally {
      setLoading(false);
      setPregunta("");
      setCategoria("");
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && e.ctrlKey && !loading) {
      sendMessage();
    }
  };

  return (
    <div className="p-6 space-y-4">
      <h2 className="text-xl font-bold">Chat IA - Nexo Soberano</h2>

      <div className="space-y-3">
        <textarea
          className="w-full p-3 bg-gray-700 rounded border border-gray-600 text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
          placeholder="Escribe tu pregunta aquí... (Ctrl+Enter para enviar)"
          value={pregunta}
          onChange={e => setPregunta(e.target.value)}
          onKeyPress={handleKeyPress}
          rows={3}
        />
      <div className="mt-2">
        <select
          className="w-full p-2 bg-gray-700 rounded border border-gray-600 text-white"
          value={categoria}
          onChange={e => setCategoria(e.target.value)}
        >
          <option value="">Todas las categorías</option>
          <option value="GEO">GEO</option>
          <option value="ECO">ECO</option>
          <option value="PSI">PSI</option>
          <option value="TEC">TEC</option>
          <option value="COM">COM</option>
          <option value="ADM">ADM</option>
        </select>
      </div>

        <button
          onClick={sendMessage}
          disabled={loading || !message.trim()}
          className="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded font-semibold transition-all"
        >
          {loading ? "Consultando bóveda..." : "Enviar"}
        </button>
      </div>

      {respuesta && (
        <div className="mt-6 space-y-4">
          <div className="p-4 bg-gray-700 rounded border border-gray-600">
            <h3 className="font-semibold mb-2 text-blue-200">Respuesta:</h3>
            <p className="text-gray-100 whitespace-pre-wrap">{respuesta}</p>
          </div>

          {fuentes && fuentes.length > 0 && (
            <div className="p-4 bg-gray-800 rounded border border-gray-700">
              <h3 className="font-semibold mb-2 text-green-200">Fuentes:</h3>
              <ul className="list-disc pl-5 text-gray-300 space-y-1">
                {fuentes.map((source, i) => (
                  <li key={i} className="text-sm">{source}</li>
                ))}
              </ul>
            </div>
          )}

          {(chunks !== null || ms !== null) && (
            <div className="p-3 bg-gray-800 rounded text-xs text-gray-400 space-y-1">
              {chunks !== null && <div>📄 Chunks consultados: {chunks}</div>}
              {ms !== null && <div>⏱️ Tiempo: {ms}ms</div>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ChatBox;
