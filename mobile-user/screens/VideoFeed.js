import React, { useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, StatusBar } from 'react-native';

const CATS = ['TODOS','ANÁLISIS','OSINT','GEOPOLÍTICO','ECONÓMICO'];

const VIDEOS = [
  { id:1, cat:'GEOPOLÍTICO', title:'Maniobras navales China — análisis estratégico APAC', src:'NEXO IA', dur:'12:34', date:'Hoy', hot:true },
  { id:2, cat:'ANÁLISIS', title:'Impacto aranceles Trump — 90 días después', src:'NEXO IA', dur:'18:22', date:'Ayer', hot:false },
  { id:3, cat:'OSINT', title:'Imágenes satelitales Darfur — seguimiento semanal', src:'Planet Labs / NEXO', dur:'7:45', date:'Hace 2 días', hot:true },
  { id:4, cat:'ECONÓMICO', title:'Fed pausa subidas de tipos — qué significa para EM', src:'NEXO IA', dur:'15:10', date:'Hace 3 días', hot:false },
  { id:5, cat:'GEOPOLÍTICO', title:'Crisis OTAN — flancos sur y este en tensión simultánea', src:'NEXO IA', dur:'22:05', date:'Hace 4 días', hot:false },
  { id:6, cat:'ANÁLISIS', title:'Sudán: actualización humanitaria + mapa de control territorial', src:'NEXO OSINT', dur:'9:18', date:'Hace 5 días', hot:false },
];

function catColor(c) {
  return { ANÁLISIS:'#a5b4fc', OSINT:'#00e5ff', GEOPOLÍTICO:'#f59e0b', ECONÓMICO:'#10b981' }[c] ?? '#94a3b8';
}

export default function VideoFeed({ navigation }) {
  const [cat, setCat] = useState('TODOS');
  const filtered = cat === 'TODOS' ? VIDEOS : VIDEOS.filter(v => v.cat === cat);

  return (
    <View style={s.root}>
      <StatusBar barStyle="light-content" backgroundColor="#030712" />
      <View style={s.header}>
        <TouchableOpacity onPress={() => navigation?.goBack()} style={s.back}>
          <Text style={s.backTxt}>← Volver</Text>
        </TouchableOpacity>
        <Text style={s.title}>VIDEO NEXO</Text>
        <View style={s.badge}><Text style={s.badgeTxt}>{VIDEOS.length}</Text></View>
      </View>

      {/* Category filter */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.catBar}>
        {CATS.map(c => (
          <TouchableOpacity key={c} onPress={() => setCat(c)} style={[s.catBtn, cat === c && s.catBtnActive]}>
            <Text style={[s.catTxt, cat === c && s.catTxtActive]}>{c}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <ScrollView contentContainerStyle={{ paddingBottom: 32 }}>
        {filtered.map(v => {
          const cc = catColor(v.cat);
          return (
            <TouchableOpacity key={v.id} style={s.card} activeOpacity={0.7}>
              {/* Thumbnail placeholder */}
              <View style={[s.thumb, { borderLeftColor: cc }]}>
                <View style={s.playBtn}>
                  <Text style={s.playIcon}>▶</Text>
                </View>
                <View style={s.durBadge}><Text style={s.durTxt}>{v.dur}</Text></View>
                {v.hot && <View style={s.hotBadge}><Text style={s.hotTxt}>● HOT</Text></View>}
              </View>
              {/* Info */}
              <View style={s.info}>
                <View style={s.row}>
                  <View style={[s.typeBadge, { borderColor: cc + '40' }]}>
                    <Text style={[s.typeTxt, { color: cc }]}>{v.cat}</Text>
                  </View>
                  <Text style={s.date}>{v.date}</Text>
                </View>
                <Text style={s.videoTitle}>{v.title}</Text>
                <Text style={s.srcTxt}>{v.src}</Text>
              </View>
            </TouchableOpacity>
          );
        })}
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
  badge: { borderWidth: 1, borderColor: 'rgba(0,229,255,0.3)', paddingHorizontal: 8, paddingVertical: 3 },
  badgeTxt: { fontFamily: 'monospace', fontSize: 10, color: '#00e5ff' },
  catBar: { flexGrow: 0, borderBottomWidth: 1, borderBottomColor: 'rgba(0,229,255,0.08)', paddingHorizontal: 12, paddingVertical: 8 },
  catBtn: { paddingHorizontal: 12, paddingVertical: 5, borderWidth: 1, borderColor: '#1e293b', marginRight: 6 },
  catBtnActive: { borderColor: '#00e5ff', backgroundColor: 'rgba(0,229,255,0.08)' },
  catTxt: { fontFamily: 'monospace', fontSize: 9, color: '#475569', letterSpacing: 1 },
  catTxtActive: { color: '#00e5ff' },
  card: { borderBottomWidth: 1, borderBottomColor: '#0f172a', backgroundColor: '#030712' },
  thumb: { height: 140, backgroundColor: '#070f1a', justifyContent: 'center', alignItems: 'center', borderLeftWidth: 3, position: 'relative' },
  playBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(0,229,255,0.15)', borderWidth: 1, borderColor: 'rgba(0,229,255,0.4)', justifyContent: 'center', alignItems: 'center' },
  playIcon: { color: '#00e5ff', fontSize: 16, marginLeft: 3 },
  durBadge: { position: 'absolute', bottom: 8, right: 10, backgroundColor: 'rgba(3,7,18,0.85)', paddingHorizontal: 6, paddingVertical: 2 },
  durTxt: { fontFamily: 'monospace', fontSize: 9, color: '#94a3b8' },
  hotBadge: { position: 'absolute', top: 8, left: 8, backgroundColor: 'rgba(239,68,68,0.15)', borderWidth: 1, borderColor: '#ef444440', paddingHorizontal: 6, paddingVertical: 2 },
  hotTxt: { fontFamily: 'monospace', fontSize: 8, color: '#ef4444' },
  info: { padding: 12 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  typeBadge: { borderWidth: 1, paddingHorizontal: 6, paddingVertical: 2 },
  typeTxt: { fontFamily: 'monospace', fontSize: 8, letterSpacing: 1 },
  date: { fontFamily: 'monospace', fontSize: 9, color: '#334155' },
  videoTitle: { fontFamily: 'monospace', fontSize: 12, color: '#cbd5e1', lineHeight: 18, marginBottom: 4 },
  srcTxt: { fontFamily: 'monospace', fontSize: 9, color: '#00e5ff' },
});
