import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useEffect } from 'react'
import Lenis from 'lenis'
import Navbar from './components/Navbar.jsx'
import AIChat from './components/AIChat.jsx'
import Home from './pages/Home.jsx'
import Analisis from './pages/Analisis.jsx'
import Comunidad from './pages/Comunidad.jsx'

export default function App() {
  // Lenis smooth scroll
  useEffect(() => {
    const lenis = new Lenis({ lerp: 0.08, smoothWheel: true })
    const raf = (time) => { lenis.raf(time); requestAnimationFrame(raf) }
    requestAnimationFrame(raf)
    return () => lenis.destroy()
  }, [])

  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/"          element={<Home />} />
        <Route path="/analisis"  element={<Analisis />} />
        <Route path="/comunidad" element={<Comunidad />} />
        <Route path="*"          element={<Home />} />
      </Routes>
      <AIChat />
    </BrowserRouter>
  )
}
