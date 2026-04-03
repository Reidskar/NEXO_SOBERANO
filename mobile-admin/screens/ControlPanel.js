/**
 * ControlPanel.js
 * Panel de control bidireccional: muestra el estado del dispositivo
 * y ejecuta comandos enviados por la IA NEXO.
 */
import React, { useEffect, useState, useRef } from 'react';
import {
  View, Text, StyleSheet, ScrollView,
  TouchableOpacity, Alert, TextInput
} from 'react-native';
import axios from 'axios';
import { API_URL, ADMIN_KEY } from '../config';

const HEADERS = { 'x-api-key': ADMIN_KEY };
const POLL_MS = 5000; // chequear comandos de la IA cada 5s

export default function ControlPanel() {
  const [status, setStatus]     = useState('');
  const [log, setLog]           = useState([]);
  const [manualCmd, setManualCmd] = useState('');
  const timer = useRef(null);

  const addLog = (msg) => setLog(prev => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev.slice(0, 49)]);

  // ── Heartbeat con métricas del dispositivo ─────────────────────────
  const sendHeartbeat = async () => {
    try {
      await axios.post(`${API_URL}/api/mobile/heartbeat`, {
        agent_id: 'xiaomi-14t-pro',
        platform: 'android',
        app_version: '1.0.0',
      }, { headers: HEADERS });
    } catch (_) {}
  };

  // ── Polling de comandos push desde la IA ──────────────────────────
  const pollCommands = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/device/queue/pop`, { headers: HEADERS });
      const cmds = res.data?.commands || [];
      for (const cmd of cmds) {
        addLog(`Comando IA recibido: ${JSON.stringify(cmd)}`);
        // Notificar al usuario
        Alert.alert('Comando de NEXO IA', JSON.stringify(cmd, null, 2));
      }
    } catch (e) {
      // silencioso
    }
  };

  // ── Enviar estado del sistema al backend ──────────────────────────
  const fetchStatus = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/device/status`, { headers: HEADERS });
      setStatus(JSON.stringify(res.data, null, 2));
    } catch (e) {
      setStatus('Sin conexión con NEXO backend');
    }
  };

  // ── Ejecutar acción manual ────────────────────────────────────────
  const runAction = async (action, params = {}) => {
    try {
      const res = await axios.post(
        `${API_URL}/api/device/action`,
        { action, params },
        { headers: HEADERS }
      );
      addLog(`${action}: ${JSON.stringify(res.data)}`);
    } catch (e) {
      addLog(`Error en ${action}: ${e.message}`);
    }
  };

  const sendShell = async () => {
    if (!manualCmd.trim()) return;
    await runAction('shell', { command: manualCmd });
    setManualCmd('');
  };

  useEffect(() => {
    fetchStatus();
    sendHeartbeat();
    timer.current = setInterval(() => {
      pollCommands();
      sendHeartbeat();
    }, POLL_MS);
    return () => clearInterval(timer.current);
  }, []);

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.header}>Control Panel NEXO</Text>

      {/* Acciones rápidas */}
      <View style={styles.row}>
        {[
          { label: 'Screenshot', action: 'screenshot' },
          { label: 'Inicio', action: 'home' },
          { label: 'Atrás', action: 'back' },
          { label: 'Despertar', action: 'wake' },
        ].map(btn => (
          <TouchableOpacity key={btn.action} style={styles.btn} onPress={() => runAction(btn.action)}>
            <Text style={styles.btnText}>{btn.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Shell manual */}
      <View style={styles.shellRow}>
        <TextInput
          style={styles.input}
          placeholder="Comando shell..."
          placeholderTextColor="#555"
          value={manualCmd}
          onChangeText={setManualCmd}
        />
        <TouchableOpacity style={styles.sendBtn} onPress={sendShell}>
          <Text style={styles.btnText}>Enviar</Text>
        </TouchableOpacity>
      </View>

      {/* Estado */}
      <TouchableOpacity onPress={fetchStatus} style={styles.refreshBtn}>
        <Text style={styles.btnText}>Actualizar estado</Text>
      </TouchableOpacity>
      <Text style={styles.statusText}>{status}</Text>

      {/* Log */}
      <Text style={styles.logHeader}>Log de actividad</Text>
      {log.map((l, i) => <Text key={i} style={styles.logLine}>{l}</Text>)}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:   { flex: 1, backgroundColor: '#0a0f16', padding: 12 },
  header:      { color: '#00ffcc', fontSize: 18, fontWeight: 'bold', marginBottom: 12 },
  row:         { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 12 },
  btn:         { backgroundColor: '#1a2a3a', padding: 10, borderRadius: 8, minWidth: 80, alignItems: 'center' },
  sendBtn:     { backgroundColor: '#005544', padding: 10, borderRadius: 8, minWidth: 60, alignItems: 'center' },
  refreshBtn:  { backgroundColor: '#1a2a3a', padding: 10, borderRadius: 8, marginBottom: 8, alignItems: 'center' },
  btnText:     { color: '#00ffcc', fontWeight: 'bold', fontSize: 13 },
  shellRow:    { flexDirection: 'row', gap: 8, marginBottom: 12 },
  input:       { flex: 1, backgroundColor: '#111', color: '#fff', borderRadius: 8, padding: 8, borderWidth: 1, borderColor: '#333' },
  statusText:  { color: '#aaa', fontSize: 11, fontFamily: 'monospace', marginBottom: 12 },
  logHeader:   { color: '#00ffcc', fontWeight: 'bold', marginBottom: 4 },
  logLine:     { color: '#666', fontSize: 10, fontFamily: 'monospace' },
});
