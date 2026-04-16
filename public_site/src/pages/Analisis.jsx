import { useRef } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import FeaturedAnalysis from '../sections/FeaturedAnalysis.jsx'
import Footer from '../sections/Footer.jsx'

gsap.registerPlugin(ScrollTrigger)

export default function Analisis() {
  const headerRef = useRef()
  useGSAP(() => {
    gsap.fromTo(headerRef.current,
      { opacity: 0, y: 30 },
      { opacity: 1, y: 0, duration: 0.7, ease: 'power3.out', delay: 0.2 }
    )
  }, { scope: headerRef })

  return (
    <main style={{ paddingTop: 64 }}>
      <div ref={headerRef} className="page-pad page-pad-v" style={{ maxWidth: 700, paddingBottom: 0 }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '.2em', color: '#c8a96e', marginBottom: 16 }}>
          — ARCHIVO DE ANÁLISIS
        </div>
        <h1 style={{ fontSize: 'clamp(32px, 5vw, 64px)', fontWeight: 800, color: '#f0ece4', letterSpacing: '-0.02em', lineHeight: 1.1, marginBottom: 20 }}>
          Todo el análisis.<br />Sin filtros.
        </h1>
        <p style={{ fontSize: 15, color: '#8a8070', lineHeight: 1.7, maxWidth: 480 }}>
          Geopolítica, mercados, inteligencia abierta y escenarios estratégicos.
          Actualizado continuamente con datos en tiempo real.
        </p>
      </div>
      <FeaturedAnalysis />
      <Footer />
    </main>
  )
}
