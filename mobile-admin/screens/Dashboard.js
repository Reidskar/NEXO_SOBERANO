import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator } from 'react-native';
import axios from 'axios';
import { API_URL, ADMIN_KEY } from '../config';

export default function Dashboard() {
  const [opsData, setOpsData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchOps = async () => {
    try {
      const res = await axios.get(`${API_URL}/system/ops`, {
        headers: { 'x-admin-key': ADMIN_KEY }
      });
      setOpsData(res.data);
    } catch (e) {
      console.error("Ops Fetch Error:", e.response?.data || e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOps();
    const interval = setInterval(fetchOps, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.header}>⚡ AIOps Control</Text>
      
      {loading && !opsData ? (
        <ActivityIndicator size="large" color="#00ffcc" style={{marginTop: 50}} />
      ) : opsData ? (
        <View style={styles.content}>
          <View style={styles.card}>
              <Text style={styles.cardTitle}>Real-time Telemetry</Text>
              <Text style={styles.text}>Risk Level: <Text style={{color: opsData.risk_level === 'LOW' ? '#00ffcc' : '#ff3333'}}>{opsData.risk_level}</Text></Text>
              <Text style={styles.text}>Queue Load: {opsData.queue_load} pending</Text>
              <Text style={styles.text}>Error Rate: {(opsData.error_rate * 100).toFixed(1)}%</Text>
          </View>
          
          <View style={styles.card}>
              <Text style={styles.cardTitle}>Subsystem Status</Text>
              {Object.keys(opsData.services || {}).map(k => (
                 <Text key={k} style={styles.text}>
                    • {k.toUpperCase()}: <Text style={{color: opsData.services[k].status === 'ok' ? '#00ffcc' : '#ffcc00'}}>{opsData.services[k].status}</Text> ({opsData.services[k].latency}ms)
                 </Text>
              ))}
          </View>

          <View style={styles.card}>
              <Text style={styles.cardTitle}>Recent Decisions</Text>
              {opsData.last_decisions?.length > 0 ? opsData.last_decisions.map((d, i) => (
                 <Text key={i} style={styles.text}>- {d}</Text>
              )) : <Text style={styles.text}>No recent mutations.</Text>}
          </View>

          <TouchableOpacity style={styles.buttonRed} onPress={() => alert('Safe Mode activated!')}>
            <Text style={styles.buttonText}>ENABLE SYSTEM SAFE-MODE</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <Text style={styles.text}>Failed to connect to Ops Center.</Text>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0f16', padding: 20, paddingTop: 60 },
  header: { color: '#fff', fontSize: 24, fontWeight: 'bold', marginBottom: 20 },
  content: { paddingBottom: 50 },
  card: { backgroundColor: '#111827', padding: 20, borderRadius: 10, marginBottom: 20, borderColor: '#1f2937', borderWidth: 1 },
  cardTitle: { color: '#00ffcc', fontSize: 18, fontWeight: 'bold', marginBottom: 15 },
  text: { color: '#fff', fontSize: 16, marginBottom: 8 },
  buttonRed: { backgroundColor: '#dc2626', padding: 15, borderRadius: 8, alignItems: 'center', marginTop: 10 },
  buttonText: { color: '#fff', fontWeight: 'bold' }
});
