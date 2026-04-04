import { Youtube, MessageCircle, Radio } from 'lucide-react'

export default function Footer() {
  return (
    <footer style={{
      marginTop: 120,
      borderTop: '1px solid rgba(200,169,110,0.1)',
      padding: '60px 60px 40px',
    }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 48 }}>

        {/* Brand */}
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '.2em', color: '#c8a96e', marginBottom: 12 }}>
            NEXO SOBERANO
          </div>
          <p style={{ fontSize: 13, color: '#5a5248', lineHeight: 1.7, maxWidth: 220 }}>
            Inteligencia geopolítica sin intermediarios. Datos en tiempo real. Análisis sin filtros.
          </p>
        </div>

        {/* Nav */}
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '.2em', color: '#3a3530', marginBottom: 16 }}>
            NAVEGACIÓN
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[['/', 'Inicio'], ['/analisis', 'Análisis'], ['/comunidad', 'Comunidad']].map(([href, label]) => (
              <a key={href} href={href} style={{ fontSize: 13, color: '#6a6058', textDecoration: 'none', transition: 'color .2s' }}
                onMouseEnter={e => e.currentTarget.style.color = '#c8a96e'}
                onMouseLeave={e => e.currentTarget.style.color = '#6a6058'}
              >{label}</a>
            ))}
          </div>
        </div>

        {/* Social */}
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '.2em', color: '#3a3530', marginBottom: 16 }}>
            CANALES
          </div>
          <div style={{ display: 'flex', gap: 16 }}>
            {[
              { icon: Youtube, color: '#ff4444', href: '#' },
              { icon: MessageCircle, color: '#5865F2', href: '#' },
              { icon: Radio, color: '#00d4ff', href: '#' },
            ].map(({ icon: Icon, color, href }, i) => (
              <a key={i} href={href} style={{
                width: 36, height: 36, borderRadius: 8,
                background: `${color}11`, border: `1px solid ${color}22`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all .2s', textDecoration: 'none',
              }}
                onMouseEnter={e => { e.currentTarget.style.background = `${color}22`; e.currentTarget.style.border = `1px solid ${color}55` }}
                onMouseLeave={e => { e.currentTarget.style.background = `${color}11`; e.currentTarget.style.border = `1px solid ${color}22` }}
              >
                <Icon size={14} color={color} />
              </a>
            ))}
          </div>
        </div>

      </div>

      {/* Bottom bar */}
      <div style={{
        maxWidth: 1200, margin: '48px auto 0',
        paddingTop: 24, borderTop: '1px solid rgba(255,255,255,0.04)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexWrap: 'wrap', gap: 12,
      }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '.12em', color: '#2a2520' }}>
          © 2026 NEXO SOBERANO — TODOS LOS DERECHOS RESERVADOS
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '.12em', color: '#2a2520' }}>
          POWERED BY NEXO IA
        </span>
      </div>
    </footer>
  )
}
