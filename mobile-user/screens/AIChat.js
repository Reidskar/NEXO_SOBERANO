import React, { useState, useRef, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, ScrollView, KeyboardAvoidingView, Platform, ActivityIndicator, StyleSheet, StatusBar } from 'react-native';
import axios from 'axios';

const API = 'http://192.168.100.22:8000';

export default function AIChat({ navigation }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', text: 'Sistema NEXO listo. Puedes preguntarme sobre conflictos globales, analizar documentos de tu bóveda o pedir un timeline de cualquier evento.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scroll = useRef(null);

  useEffect(() => {
    scroll.current?.scrollToEnd({ animated: true });
  }, [messages]);

  const send = async () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput('');
    const next = [...messages, { role: 'user', text: q }];
    setMessages(next);
    setLoading(true);
    try {
      const r = await axios.post(`${API}/agente/chat`, { mensaje: q }, { timeout: 20000 });
      const reply = r.data?.respuesta ?? r.data?.reply ?? r.data?.message ?? 'Sin respuesta del servidor.';
      setMessages([...next, { role: 'assistant', text: reply }]);
    } catch {
      setMessages([...next, { role: 'assistant', text: '⚠️ No se pudo conectar con el servidor NEXO. Verifica que el backend esté activo.' }]);
    }
    setLoading(false);
  };

  const QUICK = ['¿Qué pasa en Taiwán?', 'Resumen OTAN semana', 'Análisis mercados hoy', '¿Qué hay en mi Drive?'];

  return (
    <KeyboardAvoidingView style={s.root} behavior={Platform.OS === 'ios' ? 'padding' : 'height'} keyboardVerticalOffset={90}>
      <StatusBar barStyle="light-content" backgroundColor="#030712" />

      {/* Header */}
      <View style={s.header}>
        <TouchableOpacity onPress={() => navigation?.goBack()} style={s.back}>
          <Text style={s.backTxt}>← Volver</Text>
        </TouchableOpacity>
        <View style={s.headerMid}>
          <View style={[s.dot, { backgroundColor: '#10b981' }]} />
          <Text style={s.title}>NEXO IA</Text>
        </View>
        <Text style={s.model}>RAG</Text>
      </View>

      {/* Messages */}
      <ScrollView ref={scroll} style={s.scroll} contentContainerStyle={{ padding: 16, paddingBottom: 8 }}>
        {messages.map((m, i) => (
          <View key={i} style={[s.bubble, m.role === 'user' ? s.userBubble : s.aiBubble]}>
            {m.role === 'assistant' && (
              <Text style={s.roleLabel}>NEXO IA</Text>
            )}
            <Text style={[s.bubbleTxt, m.role === 'user' && s.userTxt]}>{m.text}</Text>
          </View>
        ))}
        {loading && (
          <View style={[s.bubble, s.aiBubble]}>
            <Text style={s.roleLabel}>NEXO IA</Text>
            <View style={s.row}>
              <ActivityIndicator size="small" color="#00e5ff" />
              <Text style={[s.bubbleTxt, { marginLeft: 8 }]}>Procesando consulta...</Text>
            </View>
          </View>
        )}
      </ScrollView>

      {/* Quick prompts */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.quickBar} contentContainerStyle={{ padding: '0 12px', gap: 6 }}>
        {QUICK.map((q, i) => (
          <TouchableOpacity key={i} onPress={() => { setInput(q); }} style={s.quickChip}>
            <Text style={s.quickTxt}>{q}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Input */}
      <View style={s.inputRow}>
        <TextInput
          value={input}
          onChangeText={setInput}
          placeholder="Pregunta al sistema..."
          placeholderTextColor="#334155"
          style={s.input}
          multiline
          maxLength={1000}
          returnKeyType="send"
          onSubmitEditing={send}
        />
        <TouchableOpacity onPress={send} disabled={loading || !input.trim()} style={[s.sendBtn, (!input.trim() || loading) && s.sendBtnDisabled]}>
          <Text style={s.sendTxt}>→</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#030712' },
  header: { flexDirection: 'row', alignItems: 'center', padding: 16, paddingTop: 52, borderBottomWidth: 1, borderBottomColor: 'rgba(0,229,255,0.12)' },
  back: { paddingRight: 12 },
  backTxt: { fontFamily: 'monospace', fontSize: 11, color: '#00e5ff' },
  headerMid: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 6 },
  dot: { width: 7, height: 7, borderRadius: 4 },
  title: { fontFamily: 'monospace', fontSize: 13, fontWeight: '700', color: '#00e5ff', letterSpacing: 2 },
  model: { fontFamily: 'monospace', fontSize: 9, color: '#475569', letterSpacing: 1 },
  scroll: { flex: 1 },
  row: { flexDirection: 'row', alignItems: 'center' },
  bubble: { marginBottom: 12, maxWidth: '85%' },
  aiBubble: { alignSelf: 'flex-start', backgroundColor: '#070f1a', borderWidth: 1, borderColor: 'rgba(0,229,255,0.12)', padding: 12 },
  userBubble: { alignSelf: 'flex-end', backgroundColor: '#0a2040', borderWidth: 1, borderColor: 'rgba(0,229,255,0.25)', padding: 12 },
  roleLabel: { fontFamily: 'monospace', fontSize: 8, color: '#00e5ff', letterSpacing: 1.5, marginBottom: 4 },
  bubbleTxt: { fontFamily: 'monospace', fontSize: 12, color: '#cbd5e1', lineHeight: 18 },
  userTxt: { color: '#e2e8f0' },
  quickBar: { flexGrow: 0, borderTopWidth: 1, borderTopColor: 'rgba(0,229,255,0.08)', paddingVertical: 8, paddingHorizontal: 12 },
  quickChip: { borderWidth: 1, borderColor: 'rgba(0,229,255,0.2)', paddingHorizontal: 10, paddingVertical: 5, marginRight: 6 },
  quickTxt: { fontFamily: 'monospace', fontSize: 9, color: '#64748b' },
  inputRow: { flexDirection: 'row', alignItems: 'flex-end', padding: 12, borderTopWidth: 1, borderTopColor: 'rgba(0,229,255,0.12)', gap: 8 },
  input: { flex: 1, backgroundColor: '#070f1a', borderWidth: 1, borderColor: 'rgba(0,229,255,0.2)', padding: 10, fontFamily: 'monospace', fontSize: 12, color: '#e2e8f0', maxHeight: 100 },
  sendBtn: { backgroundColor: '#00e5ff', paddingHorizontal: 16, paddingVertical: 11 },
  sendBtnDisabled: { backgroundColor: '#0a2040', opacity: 0.5 },
  sendTxt: { fontFamily: 'monospace', fontSize: 16, color: '#030712', fontWeight: '700' },
});
