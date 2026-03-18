import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Area,
  AreaChart
} from 'recharts';

const TensionChart = ({ events }) => {
  if (!events || events.length === 0) {
    return <div className="flex h-full items-center justify-center text-gray-600 text-xs">Sin telemetría suficiente para renderizar curva.</div>;
  }

  // Preparamos los datos invirtiendo para mostrar progreso temporal (más viejo al más nuevo)
  const data = [...events].reverse().map((ev) => ({
    pais: ev.country.split(' ')[0], // Nombre corto
    economía: ev.economic_impact_score || 0,
    militar: ev.military_impact_score || 0,
    fecha: new Date(ev.created_at).toLocaleDateString('es-ES', { month: 'short', day: 'numeric' })
  }));

  return (
    <div className="h-[280px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
          <defs>
            <linearGradient id="colorEcon" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="colorMil" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
          <XAxis 
            dataKey="pais" 
            stroke="#4b5563" 
            fontSize={10} 
            tickLine={false} 
            axisLine={false}
            dy={10}
          />
          <YAxis 
            stroke="#4b5563" 
            fontSize={10} 
            tickLine={false} 
            axisLine={false}
            tickCount={5}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#111820', border: '1px solid #1f2937', borderRadius: '8px', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)' }}
            itemStyle={{ fontSize: '11px', fontWeight: '600' }}
            labelStyle={{ color: '#9ca3af', marginBottom: '8px', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}
            cursor={{ stroke: '#374151', strokeWidth: 1, strokeDasharray: '4 4' }}
          />
          <Legend 
            wrapperStyle={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.05em', paddingTop: '20px' }}
            iconType="circle"
            iconSize={6}
          />
          <Area 
            type="monotone" 
            name="Impacto Económico"
            dataKey="economía" 
            stroke="#6366f1" 
            strokeWidth={2}
            fillOpacity={1} 
            fill="url(#colorEcon)" 
            activeDot={{ r: 4, fill: '#6366f1', strokeWidth: 0, stroke: '#fff' }}
          />
          <Area 
            type="monotone" 
            name="Escalada Militar"
            dataKey="militar" 
            stroke="#f43f5e" 
            strokeWidth={2}
            fillOpacity={1} 
            fill="url(#colorMil)" 
            activeDot={{ r: 4, fill: '#f43f5e', strokeWidth: 0, stroke: '#fff' }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default TensionChart;
