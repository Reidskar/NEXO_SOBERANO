import React, { useEffect, useState } from 'react';
import { useParams, Link, useOutletContext } from 'react-router-dom';
import { getDocument } from '../api/client';
import { ChevronLeft, ExternalLink, ShieldCheck, FileText, Globe, Activity, BrainCircuit } from 'lucide-react';

const DocumentDetail = () => {
  const { id } = useParams();
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const { openAI } = useOutletContext(); // Hook Contextual

  useEffect(() => {
    async function fetchDoc() {
      try {
        const data = await getDocument(id);
        setDoc(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    fetchDoc();
  }, [id]);

  if (loading) return (
    <div className="flex h-64 items-center justify-center text-gray-500 animate-pulse text-sm">
      <Activity size={16} className="mr-2" /> Recuperando traza del documento...
    </div>
  );
  if (!doc) return <div className="text-gray-500 text-sm mt-8">Documento no encontrado o acceso denegado.</div>;

  return (
    <div className="max-w-4xl space-y-8 animate-fade-in">
      <div className="flex justify-between">
        <Link to="/documents" className="inline-flex items-center gap-2 text-xs font-semibold tracking-wider text-gray-500 hover:text-indigo-400 transition-colors uppercase">
          <ChevronLeft size={16} /> Volver a Base Documental
        </Link>
        <button 
          onClick={() => openAI(`Analiza este documento en detalle. Título: ${doc.title}. País: ${doc.country}. Categoría: ${doc.category}. Resumen original: ${doc.summary}. ¿Qué implicaciones invisibles hay aquí?`)}
          className="flex items-center gap-2 px-3 py-1.5 text-xs font-bold tracking-widest uppercase text-indigo-400 hover:bg-indigo-900/20 border border-indigo-900/40 rounded transition-colors"
        >
          <BrainCircuit size={14} /> Analizar con Copilot
        </button>
      </div>

      <div className="bg-[#111820] border border-gray-800 rounded-lg p-8 shadow-2xl">
        <div className="flex flex-col md:flex-row md:justify-between md:items-start mb-8 gap-6">
          <h1 className="text-2xl font-light text-white tracking-wide leading-relaxed">{doc.title}</h1>
          <a 
            href={doc.drive_url || '#'} 
            target="_blank" 
            rel="noreferrer"
            className="shrink-0 flex items-center justify-center gap-2 px-4 py-2 bg-indigo-900/20 text-indigo-400 border border-indigo-900/50 rounded-md hover:bg-indigo-900/40 hover:border-indigo-500/50 transition-all text-sm font-medium tracking-wide"
          >
            <ExternalLink size={16} /> Ver Fuente Original
          </a>
        </div>

        <div className="grid grid-cols-3 gap-6 mb-8 border-y border-gray-800/60 py-6">
          <div className="flex flex-col gap-1">
            <span className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-gray-500 font-semibold mb-1"><Globe size={12} /> Región Contextual</span>
            <span className="text-sm font-medium text-gray-200">{doc.country}</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-gray-500 font-semibold mb-1"><FileText size={12} /> Vector Dominio</span>
            <span className="text-sm font-medium text-gray-200 uppercase">{doc.category}</span>
          </div>
          <div className="flex flex-col gap-1 lg:items-end">
            <span className="text-[10px] uppercase tracking-widest text-gray-500 font-semibold mb-1">Score de Impacto</span>
            <span className="px-3 py-1 rounded text-xs font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 inline-block w-fit">
              {doc.impact_level} / 10
            </span>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-2 text-gray-400 mb-4">
            <ShieldCheck size={18} className="text-indigo-400" />
            <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-300">Síntesis Táctica IA</h3>
          </div>
          <div className="p-6 bg-[#0a0f16] border border-gray-800/50 rounded-md shadow-inner relative">
            <div className="absolute top-0 left-0 w-1 h-full bg-indigo-900/50 rounded-l-md" />
            <p className="leading-relaxed text-sm text-gray-300 font-light whitespace-pre-line">
              {doc.summary || "No se ha generado la síntesis de inteligencia para esta evidencia."}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentDetail;
