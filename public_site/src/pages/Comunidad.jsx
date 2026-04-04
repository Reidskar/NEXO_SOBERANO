import { useRef } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import Footer from '../sections/Footer.jsx'
import { MessageCircle, Youtube, Radio } from 'lucide-react'

const CHANNELS = [
  { icon: Youtube, label: 'YouTube', desc: 'Análisis en vivo y grabados. Streams cuando algo importante sucede.', color: '#ff4444', href: '#' },
  { icon: MessageCircle, label: 'Discord', desc: 'Comunidad de inteligencia. Acceso a NEXO IA directamente.', color: '#5865F2', href: '#' },
  { icon: Radio, label: 'Telegram', desc: 'Alertas en tiempo real. Fuentes directas sin intermediarios.', color: '#00d4ff', href: '#' },
]

export default function Comunidad() {
  const ref = useRef()
  useGSAP(() => {
    gsap.fromTo('.channel-card',
      { opacity: 0, y: 40 },
      { opacity: 1, y: 0, duration: 0.6, ease: 'power3.out', stagger: 0.15, delay: 0.3 }
    )
  }, { scope: ref })

  return (
    <main ref={ref} style={{ paddingTop: 140, minHeight: '100vh' }}>
      <div style={{ padding: '0 60px', maxWidth: 800, margin: '0 auto', textAlign: 'center' }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '.2em', color: '#c8a96e', marginBottom: 16 }}>
          — COMUNIDAD
        </div>
        <h1 style={{ fontSize: 'clamp(32px, 5vw, 56px)', fontWeight: 800, color: '#f0ece4', letterSpacing: '-0.02em', marginBottom: 20 }}>
          Únete a la red.
        </h1>
        <p style={{ fontSize: 15, color: '#8a8070', lineHeight: 1.7, maxWidth: 500, margin: '0 auto 60px' }}>
          Accede a análisis exclusivos, alertas en tiempo real y la comunidad de
          personas que entienden el mundo sin simplificaciones.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 20 }}>
          {CHANNELS.map(c => {
            const Icon = c.icon
            return (
              <a key={c.label} href={c.href} className="channel-card" style={{
                padding: 32, borderRadius: 8,
                background: 'rgba(11,20,36,0.7)',
                border: `1px solid ${c.color}22`,
                transition: 'all .25s', textDecoration: 'none',
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16,
              }}
                onMouseEnter={e => { e.currentTarget.style.background = `${c.color}11`; e.currentTarget.style.border = `1px solid ${c.color}44`; e.currentTarget.style.transform = 'translateY(-6px)' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'rgba(11,20,36,0.7)'; e.currentTarget.style.border = `1px solid ${c.color}22`; e.currentTarget.style.transform = 'translateY(0)' }}
              >
                <Icon size={32} color={c.color} />
                <div style={{ fontWeight: 700, fontSize: 16, color: '#f0ece4' }}>{c.label}</div>
                <div style={{ fontSize: 13, color: '#8a8070', lineHeight: 1.6, textAlign: 'center' }}>{c.desc}</div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: c.color, letterSpacing: '.1em' }}>ENTRAR →</span>
              </a>
            )
          })}
        </div>
      </div>
      <Footer />
    </main>
  )
}
