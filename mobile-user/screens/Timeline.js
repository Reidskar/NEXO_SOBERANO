import React, { useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, StatusBar } from 'react-native';

const EVENTS = [
  { date:'2024-10-07', label:'Ataque Hamas — Gaza', type:'MILITAR', color:'#ef4444', detail:'Ofensiva terrestre posterior. 40,000+ bajas civiles.' },
  { date:'2024-11-05', label:'Elecciones EE.UU. — Victoria Trump', type:'POLÍTICO', color:'#60a5fa', detail:'47º presidente. Aranceles masivos anunciados semana 1.' },
  { date:'2025-01-20', label:'Toma de posesión Trump', type:'POLÍTICO', color:'#60a5fa', detail:'EO día 1: aranceles 25% México/Canadá, salida OMS.' },
  { date:'2025-03-12', label:'Crisis aranceles globales — mercados -8%', type:'ECONÓMICO', color:'#10b981', detail:'Retaliación China + UE. Recesión técnica en 3 economías.' },
  { date:'2025-06-01', label:'Maniobras navales APAC', type:'MILITAR', color:'#ef4444', detail:'3 portaaviones PLA frente a Taiwán. DEFCON 3 regional.' },
  { date:'2026-01-15', label:'Cumbre G20 — Acuerdo energético', type:'ECONÓMICO', color:'#10b981', detail:'Tregua arancelaria 90 días. Acuerdo transición energética.' },
  { date:'2026-03-28', label:'Tensión elevada — Estrecho de Taiwán', type:'MILITAR', color:'#ef4444', detail:'Incidente aéreo no confirmado. Fuentes OSINT + ADS-B.' },
];

const TYPE_COLORS = { MILITAR:'#ef4444', POLÍTICO:'#60a5fa', ECONÓMICO:'#10b981', OSINT:'#a5b4fc' };

export default function Timeline({ navigation }) {
  const [selected, setSelected] = useState(null);

  return (
    <View style={s.root}>
      <StatusBar barStyle="light-content" backgroundColor="#030712" />
      <View style={s.header}>
        <TouchableOpacity onPress={() => navigation?.goBack()} style={s.back}>
          <Text style={s.backTxt}>← Volver</Text>
        </TouchableOpacity>
        <Text style={s.title}>TIMELINES</Text>
        <View style={s.liveBadge}><Text style={s.liveTxt}>● IA</Text></View>
      </View>

      <View style={s.subheader}>
        <Text style={s.subTxt}>CRISIS GLOBALES · CRONOLOGÍA CON EVIDENCIA</Text>
      </View>

      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 32 }}>
        <View style={s.line} />
        {EVENTS.map((e, i) => (
          <TouchableOpacity key={i} onPress={() => setSelected(selected === i ? null : i)} style={s.eventRow} activeOpacity={0.7}>
            <View style={[s.dot, { backgroundColor: e.color, shadowColor: e.color }]} />
            <View style={s.eventContent}>
              <Text style={s.date}>{e.date}</Text>
              <Text style={[s.eventLabel, selected === i && { color: '#e2e8f0' }]}>{e.label}</Text>
              <View style={[s.typeBadge, { borderColor: e.color + '40' }]}>
                <Text style={[s.typeText, { color: e.color }]}>{e.type}</Text>
              </View>
              {selected === i && (
                <View style={s.detail}>
                  <Text style={s.detailTxt}>{e.detail}</Text>
                </View>
              )}
            </View>
          </TouchableOpacity>
        ))}
        <View style={s.aiRow}>
          <View style={[s.dot, { backgroundColor: '#00e5ff' }]} />
          <Text style={s.aiLabel}>IA indexando eventos...</Text>
        </View>
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#030712' },
  header: { flexDirection: 'row', alignItems: 'center', padding: 16, paddingTop: 52, borderBottomWidth: 1, borderBottomColor: 'rgba(0,229,255,0.12)' },
  back: { paddingRight: 12 },
  backTxt: { fontFamily: 'monospace', fontSize: 11, color: '#00e5ff' },
  title: { flex: 1, fontFamily: 'monospace', fontSize: 13, fontWeight: '700', color: '#00e5ff', letterSpacing: 2 },
  liveBadge: { borderWidth: 1, borderColor: 'rgba(0,229,255,0.3)', paddingHorizontal: 8, paddingVertical: 3 },
  liveTxt: { fontFamily: 'monospace', fontSize: 9, color: '#00e5ff' },
  subheader: { padding: '10px 16px', backgroundColor: '#070f1a', borderBottomWidth: 1, borderBottomColor: 'rgba(0,229,255,0.08)' },
  subTxt: { fontFamily: 'monospace', fontSize: 8, color: '#334155', letterSpacing: 1.5 },
  line: { position: 'absolute', left: 27, top: 0, bottom: 0, width: 1, backgroundColor: '#1e293b' },
  eventRow: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 20, paddingLeft: 8 },
  dot: { width: 10, height: 10, borderRadius: 5, marginTop: 4, marginRight: 14, shadowOpacity: 0.8, shadowRadius: 4, elevation: 4 },
  eventContent: { flex: 1 },
  date: { fontFamily: 'monospace', fontSize: 9, color: '#475569', marginBottom: 3 },
  eventLabel: { fontFamily: 'monospace', fontSize: 12, color: '#94a3b8', lineHeight: 18, marginBottom: 5 },
  typeBadge: { alignSelf: 'flex-start', borderWidth: 1, paddingHorizontal: 6, paddingVertical: 2, marginBottom: 2 },
  typeText: { fontFamily: 'monospace', fontSize: 8, letterSpacing: 1 },
  detail: { backgroundColor: '#070f1a', borderLeftWidth: 2, borderLeftColor: '#00e5ff30', paddingLeft: 10, paddingVertical: 6, marginTop: 6 },
  detailTxt: { fontFamily: 'monospace', fontSize: 10, color: '#64748b', lineHeight: 16 },
  aiRow: { flexDirection: 'row', alignItems: 'center', paddingLeft: 8, gap: 14 },
  aiLabel: { fontFamily: 'monospace', fontSize: 10, color: '#00e5ff' },
});
