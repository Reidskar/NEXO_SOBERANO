import { useRef, useEffect, useState } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { Link, useLocation } from 'react-router-dom'
import { Menu, X } from 'lucide-react'

const NAV = [
  { label: 'Análisis', href: '/analisis' },
  { label: 'Inteligencia', href: '/inteligencia' },
  { label: 'Mercados', href: '/mercados' },
  { label: 'Comunidad', href: '/comunidad' },
]

export default function Navbar() {
  const ref = useRef()
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  useGSAP(() => {
    gsap.fromTo(ref.current,
      { y: -60, opacity: 0 },
      { y: 0, opacity: 1, duration: 0.8, ease: 'power3.out', delay: 0.2 }
    )
  }, { scope: ref })

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <nav ref={ref} style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 8000,
      padding: '0 40px', height: 64,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      transition: 'background .3s, border-color .3s',
      background: scrolled ? 'rgba(3,7,15,0.95)' : 'transparent',
      borderBottom: scrolled ? '1px solid rgba(200,169,110,0.12)' : '1px solid transparent',
      backdropFilter: scrolled ? 'blur(20px)' : 'none',
    }}>
      {/* Logo */}
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#c8a96e', boxShadow: '0 0 10px #c8a96e' }} />
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, letterSpacing: '.15em', color: '#f0ece4' }}>
          EL ANARCOCAPITAL
        </span>
      </Link>

      {/* Desktop nav */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 32 }} className="desktop-nav">
        {NAV.map(n => (
          <Link key={n.href} to={n.href} style={{
            fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '.08em',
            color: location.pathname.startsWith(n.href) ? '#c8a96e' : '#8a8070',
            transition: 'color .15s',
          }}
            onMouseEnter={e => e.currentTarget.style.color = '#c8a96e'}
            onMouseLeave={e => e.currentTarget.style.color = location.pathname.startsWith(n.href) ? '#c8a96e' : '#8a8070'}
          >
            {n.label}
          </Link>
        ))}

        {/* CTA */}
        <a href="https://nexo.elanarcocapital.com" target="_blank" rel="noopener" style={{
          padding: '7px 18px', borderRadius: 4,
          background: 'rgba(200,169,110,0.1)', border: '1px solid rgba(200,169,110,0.3)',
          fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '.1em',
          color: '#c8a96e', transition: 'all .15s',
        }}
          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(200,169,110,0.2)'; e.currentTarget.style.boxShadow = '0 0 20px rgba(200,169,110,0.2)' }}
          onMouseLeave={e => { e.currentTarget.style.background = 'rgba(200,169,110,0.1)'; e.currentTarget.style.boxShadow = 'none' }}
        >
          NEXO →
        </a>
      </div>

      {/* Mobile menu btn */}
      <button
        style={{ display: 'none', background: 'none', border: 'none', cursor: 'pointer', color: '#c8a96e' }}
        className="mobile-menu-btn"
        onClick={() => setMenuOpen(o => !o)}
      >
        {menuOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      <style>{`
        @media (max-width: 768px) {
          .desktop-nav { display: none !important; }
          .mobile-menu-btn { display: flex !important; }
        }
      `}</style>
    </nav>
  )
}
