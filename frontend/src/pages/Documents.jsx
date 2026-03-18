import React, { useEffect, useState } from 'react';
import { getDocuments } from '../api/client';
import { Link } from 'react-router-dom';
import { Search, Filter, Activity } from 'lucide-react';

const Documents = () => {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    async function fetchDocs() {
      try {
        const data = await getDocuments();
        setDocs(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    fetchDocs();
  }, []);

  const filtered = docs.filter(d => 
    d.title?.toLowerCase().includes(search.toLowerCase()) ||
    d.country?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-3xl font-light text-white tracking-wide">Base Documental</h2>
        <p className="text-sm text-gray-400 mt-2">Archivo crudo e inferencia de inteligencia sobre documentos ingresados.</p>
      </header>

      {/* Toolbar */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search size={16} className="absolute left-3 top-3 text-gray-600" />
          <input 
            type="text"
            placeholder="Buscar por título o país..."
            className="w-full bg-[#111820] border border-gray-800 rounded-md py-2.5 pl-10 pr-4 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-indigo-500/50 transition-colors"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <button className="flex items-center gap-2 px-4 py-2.5 bg-[#111820] border border-gray-800 rounded-md text-sm text-gray-400 hover:text-gray-200 transition-colors">
          <Filter size={16} /> Filtrar
        </button>
      </div>

      {/* List */}
      <div className="bg-[#111820] border border-gray-800 rounded-lg overflow-hidden shadow-2xl">
        {loading ? (
           <div className="p-8 text-center text-sm text-gray-500 animate-pulse flex items-center justify-center gap-2">
             <Activity size={16} /> Leyendo la bóveda...
           </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-800 text-[10px] uppercase tracking-widest font-semibold text-gray-500 bg-[#0d131a]">
                <th className="px-6 py-4">Evidencia / Documento</th>
                <th className="px-6 py-4">Región</th>
                <th className="px-6 py-4">Clasificación</th>
                <th className="px-6 py-4 text-right">Impacto</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {filtered.map(doc => (
                <tr key={doc.id} className="hover:bg-gray-800/30 transition-colors group cursor-pointer">
                  <td className="px-6 py-4">
                    <Link to={`/documents/${doc.id}`} className="block">
                      <span className="text-sm font-medium text-gray-300 group-hover:text-indigo-400 transition-colors">
                        {doc.title}
                      </span>
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-400">{doc.country}</td>
                  <td className="px-6 py-4 text-xs font-semibold tracking-wider text-gray-500 uppercase">{doc.category}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-3">
                      <div className="w-full bg-gray-900 rounded-full h-1 max-w-[60px] overflow-hidden">
                        <div className="bg-indigo-500 h-1 rounded-full" style={{ width: `${(doc.impact_level/10)*100}%` }}></div>
                      </div>
                      <span className="text-xs font-mono text-gray-400">{doc.impact_level}/10</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default Documents;
