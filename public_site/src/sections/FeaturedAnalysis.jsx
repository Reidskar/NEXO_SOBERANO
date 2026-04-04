/**
 * FeaturedAnalysis — Grid de análisis con scroll reveal (GSAP ScrollTrigger)
 * El contenido se alimentará desde /api/content o estático hasta integrar CMS
 */
import { useRef } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { ArrowUpRight, Clock, Tag } from 'lucide-react'

gsap.registerPlugin(ScrollTrigger)

// Placeholder posts — se reemplazarán con API
const POSTS = [
  {
    id: 1, tag: 'GEOPOLÍTICA', readTime: '8 min',
    title: 'El Estrecho de Taiwán y el próximo reordenamiento del Pacífico',
    excerpt: 'China ha aumentado 340% sus ejercicios militares frente a Taiwán en los últimos 18 meses. Analizamos los escenarios posibles y las implicaciones para el comercio global.',
    accent: '#00d4ff',
  },
  {
    id: 2, tag: 'MERCADOS', readTime: '5 min',
    title: 'Por qué el oro romperá $3.000 antes de fin de año',
    excerpt: 'Los bancos centrales del bloque BRICS compraron más oro en 2024 que en los últimos 50 años combinados. Los datos on-chain cuentan otra historia.',
    accent: '#c8a96e',
  },
  {
    id: 3, tag: 'INTELIGENCIA', readTime: '12 min',
    title: 'OSINT: Lo que los satélites dicen sobre la movilización rusa',
    excerpt: 'Usando imágenes satelitales públicas de Planet Labs y patrones de tráfico ADS-B, reconstruimos el movimiento de fuerzas en los últimos 30 días.',
    accent: '#00ff9d',
  },
  {
    id: 4, tag: 'AMERICA LATINA', readTime: '7 min',
    title: 'Venezuela 2025: el colapso silencioso que los medios ignoran',
    excerpt: 'Mientras el petróleo venezolano vuelve al mercado con sanciones parcialmente levantadas, la realidad en el terreno es más compleja de lo que reportan.',
    accent: '#c8a96e',
  },
]

function AnalysisCard({ post, index }) {
  return (
    <a href={`/analisis/${post.id}`} className="analysis-card" style={{
      display: 'block', padding: 28, borderRadius: 6,
      background: 'rgba(11,20,36,0.7)', border: '1px solid rgba(255,255,255,0.07)',
      transition: 'all .3s', cursor: 'pointer', position: 'relative', overflow: 'hidden',
      textDecoration: 'none',
    }}
      onMouseEnter={e => {
        e.currentTarget.style.border = `1px solid ${post.accent}33`
        e.currentTarget.style.background = 'rgba(11,20,36,0.95)'
        e.currentTarget.style.transform = 'translateY(-4px)'
        e.currentTarget.style.boxShadow = `0 20px 60px rgba(0,0,0,0.4), 0 0 40px ${post.accent}11`
      }}
      onMouseLeave={e => {
        e.currentTarget.style.border = '1px solid rgba(255,255,255,0.07)'
        e.currentTarget.style.background = 'rgba(11,20,36,0.7)'
        e.currentTarget.style.transform = 'translateY(0)'
        e.currentTarget.style.boxShadow = 'none'
      }}
    >
      {/* Accent line */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg, ${post.accent}, transparent)` }} />

      {/* Meta */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '.15em', color: post.accent, padding: '3px 8px', background: `${post.accent}15`, borderRadius: 2 }}>
          {post.tag}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#3a3530' }}>
          <Clock size={10} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9 }}>{post.readTime}</span>
        </div>
      </div>

      <h3 style={{ fontSize: 17, fontWeight: 700, lineHeight: 1.3, color: '#f0ece4', marginBottom: 12, letterSpacing: '-0.01em' }}>
        {post.title}
      </h3>
      <p style={{ fontSize: 13, lineHeight: 1.65, color: '#8a8070', marginBottom: 20 }}>
        {post.excerpt}
      </p>

      <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: post.accent, fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '.08em' }}>
        LEER ANÁLISIS <ArrowUpRight size={12} />
      </div>
    </a>
  )
}

export default function FeaturedAnalysis() {
  const sectionRef = useRef()
  const titleRef = useRef()

  useGSAP(() => {
    // Title reveal on scroll
    gsap.fromTo(titleRef.current,
      { opacity: 0, y: 40 },
      {
        opacity: 1, y: 0, duration: 0.8, ease: 'power3.out',
        scrollTrigger: { trigger: titleRef.current, start: 'top 85%' }
      }
    )
    // Cards stagger reveal
    gsap.fromTo('.analysis-card',
      { opacity: 0, y: 50, scale: 0.97 },
      {
        opacity: 1, y: 0, scale: 1, duration: 0.7, ease: 'power3.out', stagger: 0.12,
        scrollTrigger: { trigger: '.analysis-card', start: 'top 88%' }
      }
    )
  }, { scope: sectionRef })

  return (
    <section ref={sectionRef} style={{ padding: '120px 60px', position: 'relative' }}>
      {/* Section header */}
      <div ref={titleRef} style={{ marginBottom: 60 }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '.2em', color: '#c8a96e', marginBottom: 16 }}>
          — ANÁLISIS RECIENTES
        </div>
        <h2 style={{ fontSize: 'clamp(28px, 4vw, 48px)', fontWeight: 800, color: '#f0ece4', letterSpacing: '-0.02em', lineHeight: 1.1 }}>
          Inteligencia sin<br />intermediarios.
        </h2>
      </div>

      {/* Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: 24,
      }}>
        {POSTS.map((p, i) => <AnalysisCard key={p.id} post={p} index={i} />)}
      </div>

      <div style={{ marginTop: 48, textAlign: 'center' }}>
        <a href="/analisis" style={{
          fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '.12em',
          color: '#8a8070', borderBottom: '1px solid rgba(200,169,110,0.3)', paddingBottom: 2,
          transition: 'color .15s',
        }}
          onMouseEnter={e => e.currentTarget.style.color = '#c8a96e'}
          onMouseLeave={e => e.currentTarget.style.color = '#8a8070'}
        >
          VER TODOS LOS ANÁLISIS →
        </a>
      </div>
    </section>
  )
}
