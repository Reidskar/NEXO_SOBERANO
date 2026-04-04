/**
 * LiveData — Ticker de datos OSINT en vivo desde el backend NEXO
 * GSAP horizontal scroll infinito (gsap-skills: quickTo + loop)
 */
import { useRef, useState, useEffect } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import axios from 'axios'
import { TrendingUp, TrendingDown, Flame, Satellite, Wifi, Shield } from 'lucide-react'

const API = import.meta.env.VITE_NEXO_API || 'http://localhost:8000'
const KEY = import.meta.env.VITE_NEXO_KEY || 'NEXO_LOCAL_2026_OK'

const STATIC_TICKERS = [
  { icon: Flame,     label: 'INCENDIOS ACTIVOS', value: '—', color: '#ff4444' },
  { icon: Satellite, label: 'SATÉLITES TRACKED', value: '—', color: '#00d4ff' },
  { icon: TrendingUp,label: 'BITCOIN',            value: '—', color: '#f7931a' },
  { icon: Shield,    label: 'VULNS CISA-KEV',     value: '—', color: '#c8a96e' },
  { icon: Wifi,      label: 'VUELOS OSCUROS',     value: '—', color: '#00ff9d' },
]

export default function LiveData() {
  const tickerRef = useRef()
  const sectionRef = useRef()
  const [tickers, setTickers] = useState(STATIC_TICKERS)

  // Fetch live data
  useEffect(() => {
    const load = async () => {
      try {
        const r = await axios.get(`${API}/api/osint/sweep`, { headers: { 'x-api-key': KEY }, timeout: 10000 })
        const d = r.data?.data || {}
        setTickers([
          { icon: Flame,     label: 'INCENDIOS ACTIVOS', value: d.fires?.total_detections || '—', color: '#ff4444' },
          { icon: Satellite, label: 'SATÉLITES TRACKED', value: d.satellites?.total_tracked || '—', color: '#00d4ff' },
          { icon: TrendingUp,label: 'BITCOIN',            value: `$${Math.round(d.markets?.quotes?.Bitcoin?.price || 0).toLocaleString() || '—'}`, color: '#f7931a' },
          { icon: Shield,    label: 'VULNS CISA-KEV',     value: d.cyber?.total_kev || '—', color: '#c8a96e' },
          { icon: Wifi,      label: 'VUELOS OSCUROS',     value: d.aviation?.total_dark_aircraft || '—', color: '#00ff9d' },
          { icon: TrendingDown,label:'VIX',               value: d.markets?.quotes?.VIX?.price?.toFixed(1) || '—', color: '#ff6b6b' },
          { icon: Flame,     label: 'GDELT EVENTOS',      value: d.gdelt?.count || '—', color: '#c8a96e' },
        ])
      } catch { /* keep static */ }
    }
    load()
    const t = setInterval(load, 60000)
    return () => clearInterval(t)
  }, [])

  // Infinite horizontal scroll (GSAP quickTo pattern)
  useGSAP(() => {
    const el = tickerRef.current
    if (!el) return
    const total = el.scrollWidth / 2
    gsap.to(el, {
      x: -total,
      duration: 30,
      ease: 'none',
      repeat: -1,
      modifiers: { x: gsap.utils.unitize(x => parseFloat(x) % total) },
    })
  }, { scope: sectionRef, dependencies: [tickers] })

  const items = [...tickers, ...tickers] // duplicate for seamless loop

  return (
    <section ref={sectionRef} style={{
      padding: '0', overflow: 'hidden',
      borderTop: '1px solid rgba(200,169,110,0.1)',
      borderBottom: '1px solid rgba(200,169,110,0.1)',
      background: 'rgba(200,169,110,0.03)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', overflow: 'hidden', height: 52 }}>
        {/* Live label */}
        <div style={{
          flexShrink: 0, padding: '0 20px', height: '100%',
          display: 'flex', alignItems: 'center', gap: 8,
          background: 'rgba(200,169,110,0.08)',
          borderRight: '1px solid rgba(200,169,110,0.15)',
          zIndex: 2,
        }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#00ff9d', boxShadow: '0 0 8px #00ff9d', animation: 'pulse 1.5s infinite' }} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '.15em', color: '#c8a96e', whiteSpace: 'nowrap' }}>EN VIVO</span>
        </div>

        {/* Scrolling tickers */}
        <div ref={tickerRef} style={{ display: 'flex', gap: 0, whiteSpace: 'nowrap' }}>
          {items.map((t, i) => {
            const Icon = t.icon
            return (
              <div key={i} style={{
                display: 'inline-flex', alignItems: 'center', gap: 8,
                padding: '0 28px', borderRight: '1px solid rgba(255,255,255,0.05)',
                height: 52,
              }}>
                <Icon size={12} color={t.color} />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '.12em', color: '#3a3530' }}>{t.label}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color: t.color }}>{t.value}</span>
              </div>
            )
          })}
        </div>
      </div>
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }`}</style>
    </section>
  )
}
