import React, { useEffect, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, RefreshControl, StyleSheet, StatusBar } from 'react-native';
import axios from 'axios';

const API = 'http://192.168.100.22:8000'; // LAN. Fuera de casa: IP Tailscale de la Torre

const FEEDS = [
  { icon: '🔴', title: 'Tensión elevada — Mar de China', src: 'OSINT', time: 'hace 4 min', cat: 'Militar' },
  { icon: '📊', title: 'S&P 500 cae 1.4% tras datos de empleo', src: 'Mercados', time: 'hace 8 min', cat: 'Económico' },
  { icon: '🌐', title: 'Cumbre G20: acuerdo energético en curso', src: 'Reuters', time: 'hace 12 min', cat: 'Político' },
  { icon: '💬', title: 'Nuevo análisis IA disponible — Sudán', src: 'NEXO IA', time: 'hace 25 min', cat: 'IA' },
];

export default function Home({ navigation }) {
  const [health, setHealth] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const check = async () => {
    try {
      const r = await axios.get(`${API}/api/health`, { timeout: 4000 });
      setHealth(r.data?.status === 'ok' ? 'online' : 'degradado');
    } catch { setHealth('offline'); }
  };

  useEffect(() => { check(); }, []);
  const onRefresh = async () => { setRefreshing(true); await check(); setRefreshing(false); };

  return (
    <View style={s.root}>
      <StatusBar barStyle="light-content" backgroundColor="#030712" />
      <View style={s.header}>
        <View style={s.row}>
          <View style={[s.dot, { backgroundColor: health==='online'?'#10b981':health==='offline'?'#ef4444':'#f59e0b' }]} />
          <Text style={s.brand}>EL ANARCOCAPITAL</Text>
        </View>
        <TouchableOpacity onPress={() => navigation?.navigate('AIChat')} style={s.aiBtn}>
          <Text style={s.aiBtnTxt}>IA →</Text>
        </TouchableOpacity>
      </View>
      <ScrollView refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#00e5ff"/>}>
        <View style={s.liveBar}>
          <Text style={s.liveLabel}>SEÑALES EN VIVO</Text>
          <Text style={s.liveDot}>● LIVE</Text>
        </View>
        <View style={s.sec}>
          <Text style={s.secLabel}>FEED DE INTELIGENCIA</Text>
          {FEEDS.map((f,i) => (
            <TouchableOpacity key={i} style={s.card} onPress={() => navigation?.navigate('AIChat')}>
              <View style={[s.row,{justifyContent:'space-between',marginBottom:6}]}>
                <Text style={{fontSize:18}}>{f.icon}</Text>
                <View style={s.badge}><Text style={s.badgeTxt}>{f.cat}</Text></View>
              </View>
              <Text style={s.cardTitle}>{f.title}</Text>
              <View style={[s.row,{justifyContent:'space-between'}]}>
                <Text style={s.src}>{f.src}</Text>
                <Text style={s.time}>{f.time}</Text>
              </View>
            </TouchableOpacity>
          ))}
        </View>
        <View style={s.sec}>
          <Text style={s.secLabel}>ACCESO RÁPIDO</Text>
          <View style={s.grid}>
            {[['🧠','IA','AIChat'],['🗓','Timeline','Timeline'],['📹','Video','VideoFeed'],['📁','Bóveda','AIChat']].map(([icon,label,screen],i) => (
              <TouchableOpacity key={i} style={s.quick} onPress={() => navigation?.navigate(screen)}>
                <Text style={{fontSize:22}}>{icon}</Text>
                <Text style={s.quickLabel}>{label}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
        <View style={{height:40}}/>
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root:{flex:1,backgroundColor:'#030712'},
  row:{flexDirection:'row',alignItems:'center',gap:8},
  header:{flexDirection:'row',alignItems:'center',justifyContent:'space-between',padding:16,paddingTop:52,borderBottomWidth:1,borderBottomColor:'rgba(0,229,255,0.12)'},
  dot:{width:7,height:7,borderRadius:4},
  brand:{fontFamily:'monospace',fontSize:13,fontWeight:'700',color:'#00e5ff',letterSpacing:2},
  aiBtn:{borderWidth:1,borderColor:'#00e5ff',paddingHorizontal:12,paddingVertical:5},
  aiBtnTxt:{fontFamily:'monospace',fontSize:11,color:'#00e5ff'},
  liveBar:{flexDirection:'row',alignItems:'center',justifyContent:'space-between',paddingHorizontal:16,paddingVertical:8,backgroundColor:'#070f1a',borderBottomWidth:1,borderBottomColor:'rgba(0,229,255,0.1)'},
  liveLabel:{fontFamily:'monospace',fontSize:9,color:'#475569',letterSpacing:1.5},
  liveDot:{fontFamily:'monospace',fontSize:9,color:'#10b981'},
  sec:{padding:16,paddingBottom:0},
  secLabel:{fontFamily:'monospace',fontSize:9,color:'#475569',letterSpacing:1.5,marginBottom:10},
  card:{backgroundColor:'#070f1a',borderWidth:1,borderColor:'rgba(0,229,255,0.12)',padding:14,marginBottom:8},
  badge:{borderWidth:1,borderColor:'rgba(0,229,255,0.3)',paddingHorizontal:6,paddingVertical:2},
  badgeTxt:{fontFamily:'monospace',fontSize:8,color:'#00e5ff',letterSpacing:1},
  cardTitle:{fontFamily:'monospace',fontSize:12,color:'#e2e8f0',lineHeight:18,marginVertical:6},
  src:{fontFamily:'monospace',fontSize:9,color:'#00e5ff'},
  time:{fontFamily:'monospace',fontSize:9,color:'#475569'},
  grid:{flexDirection:'row',flexWrap:'wrap',gap:8},
  quick:{width:'47%',backgroundColor:'#070f1a',borderWidth:1,borderColor:'rgba(0,229,255,0.12)',padding:16,alignItems:'center',gap:6},
  quickLabel:{fontFamily:'monospace',fontSize:10,color:'#94a3b8',letterSpacing:1},
});
