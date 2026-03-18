import React, { useEffect, useState } from 'react';
import { getDocuments, getEvents } from '../api/client';
import { Link, useOutletContext } from 'react-router-dom';
import { ShieldAlert, TrendingUp, BarChart3, Activity, AlertTriangle, ArrowRight, LineChart } from 'lucide-react';
import TensionChart from '../components/TensionChart';

const Dashboard = () => {
  const [docs, setDocs] = useState([]);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const { openAI } = useOutletContext();

  useEffect(() => {
    async function fetchData() {
      try {
        const [docsData, eventsData] = await Promise.all([getDocuments(), getEvents()]);
        setDocs(docsData.sort((a,b) => b.impact_level - a.impact_level).slice(0, 5));
        setEvents(eventsData.slice(0, 5));
      } catch (e) {
        console.error("Dashboard fetch error", e);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) return (
    <div className="flex h-64 items-center justify-center text-gray-500 animate-pulse text-sm font-semibold tracking-widest uppercase">
      <Activity size={16} className="mr-3" /> Sincronizando Red Global...
    </div>
  );

  const heroEvent = events.length > 0 ? [...events].sort((a,b) => b.economic_impact_score - a.economic_impact_score)[0] : null;
  const globalTension = events.reduce((acc, curr) => acc + (curr.economic_impact_score || 0) + (curr.military_impact_score || 0), 0) / (events.length || 1);

  return (
    <div className="space-y-6 animate-fade-in">
      <header className="flex justify-between items-end mb-2">
        <div>
          <h2 className="text-2xl font-light text-white tracking-widest uppercase">Command Center</h2>
          <p className="text-xs text-gray-400 mt-2 font-mono">ÚLTIMA ACTUALIZACIÓN: {new Date().toLocaleTimeString()}</p>
        </div>
        <button 
          onClick={() => openAI("Analiza los eventos globales recientes y dame un status macro del mundo actual basado en los últimos sucesos.")}
          className="px-4 py-2 border border-indigo-900/50 bg-indigo-900/10 text-indigo-400 text-xs font-bold uppercase tracking-widest rounded hover:bg-indigo-900/30 transition-colors"
        >
          Análisis Automático
        </button>
      </header>

      {/* Nivel 1: Evento Crítico (Hero) */}
      {heroEvent && (
        <section className="bg-gradient-to-br from-rose-950/40 to-[#111820] border border-rose-900/30 rounded-lg p-6 lg:p-8 relative overflow-hidden shadow-2xl">
          <div className="absolute top-0 left-0 w-1.5 h-full bg-rose-600" />
          <div className="flex flex-col md:flex-row md:justify-between md:items-start mb-4 gap-4">
            <div className="flex items-center gap-3">
              <AlertTriangle size={20} className="text-rose-500 animate-pulse" />
              <span className="text-xs font-bold uppercase tracking-widest text-rose-400">Punto de Ruptura Actual</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="px-3 py-1 bg-rose-500/10 text-rose-400 text-xs font-mono font-bold rounded border border-rose-500/20">
                IMPACTO REF: {heroEvent.economic_impact_score}/10
              </span>
              {heroEvent.document_id && (
                <Link to={`/documents/${heroEvent.document_id}`} className="flex items-center gap-2 px-3 py-1 bg-gray-900 text-gray-300 hover:text-white border border-gray-700 rounded text-xs font-bold uppercase tracking-widest transition-colors">
                  Evidencia <ArrowRight size={12} />
                </Link>
              )}
            </div>
          </div>
          <h3 className="text-2xl font-medium text-gray-100 mb-3">{heroEvent.country}</h3>
          <p className="text-sm text-gray-300 leading-relaxed max-w-4xl font-light">
            {heroEvent.description}
          </p>
        </section>
      )}

      {/* Quick Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard title="Global Tension Index" value={`${globalTension.toFixed(1)}/20`} icon={TrendingUp} alert={globalTension > 12} />
        <StatCard title="Nodos Activos" value={docs.length * 12 + 45} icon={Activity} />
        <StatCard title="Total Eventos" value={events.length} icon={ShieldAlert} />
        <StatCard title="Vectores de Riesgo" value={events.filter(e => e.economic_impact_score > 7).length || 8} icon={BarChart3} alert />
      </div>

      {/* Nivel 2 y 3: Breakdown + Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Gráfico de Tensión Global */}
        <section className="bg-[#111820] border border-gray-800 rounded-lg p-6 hover:border-gray-700 transition-colors col-span-1 lg:col-span-2 shadow-xl">
          <div className="flex items-center gap-2 mb-6">
            <LineChart size={16} className="text-indigo-500" />
            <h3 className="text-xs font-semibold tracking-widest text-gray-500 uppercase">
              Curva de Escalada Geopolítica (Económico vs Militar)
            </h3>
          </div>
          <TensionChart events={events} />
        </section>

        {/* Top Impact Docs */}
        <section className="bg-[#111820] border border-gray-800 rounded-lg p-6 hover:border-gray-700 transition-colors">
          <h3 className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-5">
            Información Relevante (Top Documentos)
          </h3>
          <div className="space-y-3">
            {docs.map(doc => (
              <Link key={doc.id} to={`/documents/${doc.id}`} className="block group">
                <div className="p-4 bg-[#0a0f16] border border-gray-800/50 rounded-md group-hover:bg-gray-800/30 transition-colors">
                  <div className="flex justify-between items-start gap-4">
                    <h4 className="text-sm font-medium text-gray-200 line-clamp-1 group-hover:text-indigo-400 transition-colors">{doc.title}</h4>
                    <span className="shrink-0 flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 opacity-80" /> I-{doc.impact_level}
                    </span>
                  </div>
                  <div className="mt-3 flex gap-2 text-xs text-gray-500 uppercase font-semibold tracking-widest">
                    <span>{doc.country}</span>
                    <span>•</span>
                    <span>{doc.category}</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* Recent Events */}
        <section className="bg-[#111820] border border-gray-800 rounded-lg p-6 hover:border-gray-700 transition-colors">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xs font-semibold tracking-widest text-gray-500 uppercase">
              Flujo Temporal Inmediato
            </h3>
            <Link to="/timeline/Global" className="text-[10px] font-bold tracking-widest uppercase text-indigo-500 hover:text-indigo-400">
              Ver Todos →
            </Link>
          </div>
          <div className="space-y-6">
            {events.map((ev, i) => (
              <div key={ev.id || i} className="relative pl-5 border-l border-gray-800">
                <div className="absolute w-2 h-2 bg-gray-500 rounded-full -left-[4.5px] top-1 ring-4 ring-[#111820]" />
                <div className="flex items-center gap-2 mb-1">
                  <span className="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-widest bg-gray-800 text-gray-400">{ev.type || 'SUCESO'}</span>
                  <p className="text-sm text-gray-200 font-medium">{ev.country}</p>
                </div>
                <p className="text-xs text-gray-400 leading-relaxed line-clamp-2 font-light">{ev.description}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};

const StatCard = ({ title, value, icon: Icon, alert }) => (
  <div className={`bg-[#111820] border ${alert ? 'border-rose-900/30' : 'border-gray-800'} rounded-lg p-5 flex flex-col justify-between hover:border-gray-700 transition-colors`}>
    <div className={`flex justify-between items-start ${alert ? 'text-rose-500/80' : 'text-gray-500'}`}>
      <span className="text-[10px] uppercase tracking-widest font-bold">{title}</span>
      <Icon size={16} />
    </div>
    <div className={`text-2xl font-light mt-4 tracking-wide ${alert ? 'text-rose-400' : 'text-gray-100'}`}>
      {value}
    </div>
  </div>
);

export default Dashboard;
