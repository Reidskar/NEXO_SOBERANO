import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getTimeline } from '../api/client';
import { Network, Activity } from 'lucide-react';

const Timeline = () => {
  const { country } = useParams();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await getTimeline(country === 'Global' ? '' : country);
        setEvents(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [country]);

  return (
    <div className="space-y-10 max-w-4xl">
      <header className="border-b border-gray-800/60 pb-6">
        <h2 className="text-3xl font-light text-white tracking-wide flex items-center gap-3">
          <Network size={28} className="text-indigo-500 opacity-80" /> 
          Línea Temporal: {country}
        </h2>
        <p className="text-sm text-gray-500 mt-2">Sucesión cronológica de eventos geolocalizados confirmados por IA y ordenados por impacto e interrelación.</p>
      </header>

      {loading ? (
        <div className="flex h-32 items-center justify-center text-gray-500 animate-pulse text-sm">
           <Activity size={16} className="mr-2" /> Analizando trazas temporales y dependencias...
        </div>
      ) : (
        <div className="relative pl-8 md:pl-0 space-y-12">
          {/* Timeline Center Line for Destktop */}
          <div className="hidden md:block absolute left-1/2 top-0 bottom-0 w-px bg-gray-800/80 -translate-x-1/2" />
          {/* Timeline Left Line for Mobile */}
          <div className="md:hidden absolute left-0 top-0 bottom-0 w-px bg-gray-800/80" />

          {events.length === 0 && (
            <div className="text-center p-8 bg-[#111820] border border-gray-800 rounded-lg text-sm text-gray-500">
              La IA no ha detectado eventos confirmados para esta línea temporal.
            </div>
          )}
          
          {events.map((ev, i) => {
            const isEven = i % 2 === 0;
            return (
              <div key={ev.id || i} className={`relative flex items-center justify-between md:justify-normal md:w-full ${isEven ? 'md:flex-row-reverse' : 'md:flex-row'}`}>
                
                {/* Marker */}
                <div className="absolute left-[-37px] md:left-1/2 md:-translate-x-1/2 flex items-center justify-center w-5 h-5 rounded-full bg-[#0a0f16] border-2 border-indigo-900/50 z-10 p-0.5">
                  <div className="w-full h-full bg-indigo-500/80 rounded-full animate-pulse" />
                </div>

                {/* Content Box */}
                <div className={`w-full md:w-[45%] ${isEven ? 'md:pl-10 text-left' : 'md:pr-10 md:text-right'}`}>
                  <div className="bg-[#111820] border border-gray-800/60 rounded-lg p-5 hover:border-gray-700 hover:bg-gray-800/10 transition-colors shadow-xl group">
                    <div className={`flex flex-col md:flex-row ${isEven ? 'md:justify-between' : 'md:justify-between md:flex-row-reverse'} items-start md:items-center mb-4 gap-2`}>
                      <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-widest bg-gray-900 text-gray-400 border border-gray-800">
                        {ev.type || 'SUCESO REGISTRADO'}
                      </span>
                      <span className="text-[10px] font-mono tracking-widest text-indigo-400/80">
                        {new Date(ev.created_at).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })}
                      </span>
                    </div>
                    
                    <h4 className="text-sm font-semibold tracking-wide text-gray-200 mb-2">{ev.country}</h4>
                    <p className="text-xs text-gray-400 leading-relaxed mb-5 font-light">
                      {ev.description}
                    </p>

                    <div className={`flex items-center gap-4 text-[10px] uppercase font-semibold tracking-widest text-gray-600 ${isEven ? 'justify-start' : 'md:justify-end'}`}>
                      <span className="flex flex-col gap-1">
                        Impacto Ec. 
                        <b className="text-indigo-400">{ev.economic_impact_score}</b>
                      </span>
                      <span className="flex flex-col gap-1">
                        Impacto Mil. 
                        <b className="text-indigo-400">{ev.military_impact_score}</b>
                      </span>
                    </div>

                    {ev.document_id && (
                      <div className={`mt-4 pt-4 border-t border-gray-800/50 ${isEven ? 'text-left' : 'md:text-right'} group-hover:border-gray-700`}>
                        <Link to={`/documents/${ev.document_id}`} className="inline-flex items-center text-[10px] font-bold tracking-widest uppercase text-indigo-500 hover:text-indigo-300 transition-colors">
                          Analizar Evidencia →
                        </Link>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Timeline;
