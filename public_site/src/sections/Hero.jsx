/**
 * Hero — Sección principal con globo 3D y GSAP
 * Patrón: fromTo + stagger + ScrollTrigger (gsap-skills)
 */
import { useRef, Suspense } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { lazy } from 'react'
import { ArrowDown } from 'lucide-react'

gsap.registerPlugin(ScrollTrigger)

const Globe3D = lazy(() => import('../components/Globe3D.jsx'))

export default function Hero() {
  const sectionRef = useRef()
  const headRef    = useRef()
  const subRef     = useRef()
  const ctaRef     = useRef()
  const globeRef   = useRef()
  const tagsRef    = useRef()

  useGSAP(() => {
    // Tag line stagger
    gsap.fromTo('.hero-tag',
      { opacity: 0, y: 10 },
      { opacity: 1, y: 0, duration: 0.5, ease: 'power2.out', stagger: 0.1, delay: 0.4 }
    )
    // Headline letters
    gsap.fromTo(headRef.current,
      { opacity: 0, y: 50, skewY: 4 },
      { opacity: 1, y: 0, skewY: 0, duration: 1, ease: 'power4.out', delay: 0.6 }
    )
    // Sub
    gsap.fromTo(subRef.current,
      { opacity: 0, y: 20 },
      { opacity: 1, y: 0, duration: 0.8, ease: 'power3.out', delay: 0.9 }
    )
    // CTA buttons
    gsap.fromTo('.hero-cta-btn',
      { opacity: 0, y: 16, scale: 0.96 },
      { opacity: 1, y: 0, scale: 1, duration: 0.6, ease: 'back.out(1.4)', stagger: 0.12, delay: 1.1 }
    )
    // Globe parallax on scroll
    ScrollTrigger.create({
      trigger: sectionRef.current,
      start: 'top top',
      end: 'bottom top',
      scrub: 1.5,
      onUpdate: self => {
        if (globeRef.current) {
          gsap.set(globeRef.current, { y: self.progress * 120, opacity: 1 - self.progress * 0.6 })
        }
      }
    })
    // Section fade out on scroll
    gsap.to(sectionRef.current, {
      scrollTrigger: { trigger: sectionRef.current, start: 'center top', end: 'bottom top', scrub: true },
      opacity: 0.4,
    })
  }, { scope: sectionRef })

  return (
    <section ref={sectionRef} style={{
      position: 'relative', minHeight: '100vh',
      display: 'flex', alignItems: 'center', overflow: 'hidden',
    }}>
      {/* Globe — right side */}
      <div ref={globeRef} style={{
        position: 'absolute', right: '-5%', top: '50%',
        transform: 'translateY(-50%)',
        width: '55vw', height: '55vw', maxWidth: 700, maxHeight: 700,
        pointerEvents: 'none',
      }}>
        <Suspense fallback={null}>
          <Globe3D style={{ width: '100%', height: '100%' }} />
        </Suspense>
      </div>

      {/* Radial gradient overlay */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'radial-gradient(ellipse 60% 80% at 20% 50%, rgba(200,169,110,0.06) 0%, transparent 70%), radial-gradient(ellipse at 100% 50%, rgba(0,212,255,0.04) 0%, transparent 60%)',
        pointerEvents: 'none',
      }} />

      {/* Content */}
      <div style={{ position: 'relative', zIndex: 10, padding: '0 60px', maxWidth: 700 }}>
        {/* Tags */}
        <div ref={tagsRef} style={{ display: 'flex', gap: 10, marginBottom: 28 }}>
          {['INTELIGENCIA SOBERANA', 'ANÁLISIS GEOPOLÍTICO', 'DATOS EN TIEMPO REAL'].map(t => (
            <span key={t} className="hero-tag" style={{
              fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '.15em',
              color: '#c8a96e', padding: '4px 10px',
              border: '1px solid rgba(200,169,110,0.25)', borderRadius: 2,
              background: 'rgba(200,169,110,0.07)',
            }}>{t}</span>
          ))}
        </div>

        {/* Headline */}
        <h1 ref={headRef} style={{
          fontSize: 'clamp(42px, 6vw, 80px)', fontWeight: 800, lineHeight: 1.05,
          color: '#f0ece4', letterSpacing: '-0.03em', marginBottom: 28,
        }}>
          El mundo no<br />
          espera.<br />
          <span style={{ color: '#c8a96e' }}>Tú tampoco.</span>
        </h1>

        {/* Subheadline */}
        <p ref={subRef} style={{
          fontSize: 17, lineHeight: 1.7, color: '#8a8070',
          maxWidth: 500, marginBottom: 40,
        }}>
          Análisis geopolítico independiente, datos de inteligencia en tiempo real
          y una IA que no filtra la realidad. Para quienes necesitan entender el mundo
          antes de que los medios lo simplifiquen.
        </p>

        {/* CTA */}
        <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
          <a href="/analisis" className="hero-cta-btn" style={{
            padding: '14px 32px', borderRadius: 4,
            background: 'linear-gradient(135deg, #c8a96e 0%, #8b6914 100%)',
            color: '#03070f', fontWeight: 700, fontSize: 13,
            fontFamily: 'var(--font-mono)', letterSpacing: '.08em',
            transition: 'all .2s', boxShadow: '0 8px 32px rgba(200,169,110,0.3)',
          }}
            onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 12px 40px rgba(200,169,110,0.45)' }}
            onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 8px 32px rgba(200,169,110,0.3)' }}
          >
            LEER ANÁLISIS
          </a>
          <a href="#ia" className="hero-cta-btn" style={{
            padding: '14px 32px', borderRadius: 4,
            background: 'transparent', border: '1px solid rgba(200,169,110,0.3)',
            color: '#c8a96e', fontSize: 13,
            fontFamily: 'var(--font-mono)', letterSpacing: '.08em',
            transition: 'all .2s',
          }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(200,169,110,0.08)'; e.currentTarget.style.boxShadow = '0 0 20px rgba(200,169,110,0.15)' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.boxShadow = 'none' }}
          >
            HABLAR CON LA IA →
          </a>
        </div>

        {/* Scroll indicator */}
        <div style={{ position: 'absolute', bottom: 40, left: 60, display: 'flex', alignItems: 'center', gap: 10 }}>
          <ArrowDown size={14} color="#3a3530" style={{ animation: 'scrollBounce 2s infinite' }} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#3a3530', letterSpacing: '.12em' }}>SCROLL</span>
        </div>
      </div>

      {/* Bottom gradient */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0, height: 200,
        background: 'linear-gradient(to bottom, transparent, var(--bg))',
        pointerEvents: 'none',
      }} />

      <style>{`
        @keyframes scrollBounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(8px)} }
      `}</style>
    </section>
  )
}
