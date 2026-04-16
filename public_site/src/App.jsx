import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useEffect, lazy, Suspense } from 'react'
import Lenis from 'lenis'
import Navbar from './components/Navbar.jsx'
import AIChat from './components/AIChat.jsx'
import Home from './pages/Home.jsx'

const Analisis     = lazy(() => import('./pages/Analisis.jsx'))
const Inteligencia = lazy(() => import('./pages/Inteligencia.jsx'))
const Mercados     = lazy(() => import('./pages/Mercados.jsx'))
const Comunidad    = lazy(() => import('./pages/Comunidad.jsx'))

export default function App() {
  useEffect(() => {
    const lenis = new Lenis({ lerp: 0.08, smoothWheel: true })
    const raf = (time) => { lenis.raf(time); requestAnimationFrame(raf) }
    requestAnimationFrame(raf)
    return () => lenis.destroy()
  }, [])

  return (
    <BrowserRouter>
      <Navbar />
      <Suspense fallback={null}>
        <Routes>
          <Route path="/"             element={<Home />} />
          <Route path="/analisis"     element={<Analisis />} />
          <Route path="/inteligencia" element={<Inteligencia />} />
          <Route path="/mercados"     element={<Mercados />} />
          <Route path="/comunidad"    element={<Comunidad />} />
          <Route path="*"             element={<Home />} />
        </Routes>
      </Suspense>
      <AIChat />
    </BrowserRouter>
  )
}
