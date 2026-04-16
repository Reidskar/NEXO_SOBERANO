/**
 * AIChat — Widget de chat público para visitantes
 * Llama al NEXO backend /api/agente/ para respuestas
 */
import { useState, useRef, useEffect } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import axios from 'axios'
import { MessageCircle, X, Send, Zap } from 'lucide-react'

const API = import.meta.env.VITE_NEXO_API || 'https://nexo.elanarcocapital.com'

const SUGGESTED = [
  '¿Qué es el anarcocapitalismo?',
  '¿Cuál es la situación en Taiwán?',
  '¿Cómo afecta la geopolítica a los mercados?',
  '¿Cómo funciona el ciclo austriaco?',
]

export default function AIChat() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([
    { role: 'ai', text: 'Hola. Soy NEXO — analista de inteligencia estratégica. ¿Qué quieres analizar hoy?' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const panelRef = useRef()
  const btnRef = useRef()
  const bottomRef = useRef()

  useGSAP(() => {
    // Botón FAB — entrada
    gsap.fromTo(btnRef.current,
      { scale: 0, rotation: -180 },
      { scale: 1, rotation: 0, duration: 0.6, ease: 'back.out(2)', delay: 2 }
    )
  }, { scope: btnRef })

  // Animar apertura/cierre del panel
  useEffect(() => {
    if (!panelRef.current) return
    if (open) {
      gsap.fromTo(panelRef.current,
        { opacity: 0, y: 20, scale: 0.95 },
        { opacity: 1, y: 0, scale: 1, duration: 0.35, ease: 'power3.out' }
      )
    }
  }, [open])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (text) => {
    const q = text || input.trim()
    if (!q) return
    setInput('')
    setMessages(m => [...m, { role: 'user', text: q }])
    setLoading(true)
    try {
      const r = await axios.post(
        `${API}/api/intel/chat`,
        { mensaje: q, modelo: 'fast', temperatura: 0.3 },
        { timeout: 25000 }
      )
      const resp = r.data?.respuesta || 'Sin respuesta.'
      setMessages(m => [...m, { role: 'ai', text: resp }])
    } catch {
      setMessages(m => [...m, { role: 'ai', text: 'Sistema procesando. Intenta nuevamente en un momento.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* FAB button */}
      <button
        ref={btnRef}
        onClick={() => setOpen(o => !o)}
        style={{
          position: 'fixed', bottom: 32, right: 32, zIndex: 9000,
          width: 56, height: 56, borderRadius: '50%',
          background: 'linear-gradient(135deg, #c8a96e, #8b6914)',
          border: 'none', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 0 24px rgba(200,169,110,0.4)',
          transition: 'transform .2s, box-shadow .2s',
        }}
        onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.1)'; e.currentTarget.style.boxShadow = '0 0 36px rgba(200,169,110,0.6)' }}
        onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)'; e.currentTarget.style.boxShadow = '0 0 24px rgba(200,169,110,0.4)' }}
      >
        {open ? <X size={22} color="#03070f" /> : <MessageCircle size={22} color="#03070f" />}
      </button>

      {/* Chat panel */}
      {open && (
        <div
          ref={panelRef}
          style={{
            position: 'fixed', bottom: 100, right: 32, zIndex: 8999,
            width: 360, height: 500,
            background: 'rgba(7, 13, 26, 0.97)',
            border: '1px solid rgba(200,169,110,0.25)',
            borderRadius: 12,
            display: 'flex', flexDirection: 'column',
            backdropFilter: 'blur(20px)',
            boxShadow: '0 24px 60px rgba(0,0,0,0.7), 0 0 40px rgba(200,169,110,0.08)',
            overflow: 'hidden',
          }}
        >
          {/* Header */}
          <div style={{ padding: '14px 18px', borderBottom: '1px solid rgba(200,169,110,0.15)', display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#00ff9d', boxShadow: '0 0 8px #00ff9d', animation: 'pulse 2s infinite' }} />
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, letterSpacing: '.1em', color: '#c8a96e' }}>NEXO — IA</div>
              <div style={{ fontSize: 9, color: '#3a3530', fontFamily: 'var(--font-mono)' }}>INTELIGENCIA EN LÍNEA</div>
            </div>
            <Zap size={14} color="#c8a96e" style={{ marginLeft: 'auto' }} />
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
            {messages.map((m, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
                <div style={{
                  maxWidth: '82%', padding: '10px 14px', borderRadius: m.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                  background: m.role === 'user' ? 'rgba(200,169,110,0.15)' : 'rgba(255,255,255,0.04)',
                  border: `1px solid ${m.role === 'user' ? 'rgba(200,169,110,0.3)' : 'rgba(255,255,255,0.07)'}`,
                  fontSize: 13, lineHeight: 1.5, color: m.role === 'user' ? '#c8a96e' : '#d4cfc6',
                }}>
                  {m.text}
                </div>
              </div>
            ))}
            {loading && (
              <div style={{ display: 'flex', gap: 5, padding: '8px 14px', alignItems: 'center' }}>
                {[0,1,2].map(i => (
                  <div key={i} style={{ width: 6, height: 6, borderRadius: '50%', background: '#c8a96e', animation: `bounce 1.2s ${i*0.2}s infinite` }} />
                ))}
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Suggested questions */}
          {messages.length === 1 && (
            <div style={{ padding: '8px 16px', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {SUGGESTED.map(s => (
                <button key={s} onClick={() => send(s)} style={{
                  padding: '4px 10px', borderRadius: 20, fontSize: 10,
                  background: 'rgba(200,169,110,0.08)', border: '1px solid rgba(200,169,110,0.2)',
                  color: '#8a8070', cursor: 'pointer', fontFamily: 'var(--font-sans)',
                  transition: 'all .15s',
                }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(200,169,110,0.15)'; e.currentTarget.style.color = '#c8a96e' }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'rgba(200,169,110,0.08)'; e.currentTarget.style.color = '#8a8070' }}
                >{s}</button>
              ))}
            </div>
          )}

          {/* Input */}
          <div style={{ padding: '12px 14px', borderTop: '1px solid rgba(200,169,110,0.1)', display: 'flex', gap: 8 }}>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
              placeholder="Pregunta algo..."
              style={{
                flex: 1, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(200,169,110,0.15)',
                borderRadius: 8, padding: '8px 12px', color: '#f0ece4',
                fontSize: 13, outline: 'none', fontFamily: 'var(--font-sans)',
              }}
            />
            <button
              onClick={() => send()}
              disabled={loading || !input.trim()}
              style={{
                width: 38, height: 38, borderRadius: 8, border: 'none',
                background: input.trim() ? 'linear-gradient(135deg, #c8a96e, #8b6914)' : 'rgba(255,255,255,0.05)',
                cursor: input.trim() ? 'pointer' : 'default',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all .15s', flexShrink: 0,
              }}
            >
              <Send size={15} color={input.trim() ? '#03070f' : '#3a3530'} />
            </button>
          </div>
        </div>
      )}

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
        @keyframes bounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)} }
      `}</style>
    </>
  )
}
