import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Landing from './pages/Landing';
import Timeline from './pages/Timeline';
import OmniGlobe from './pages/OmniGlobe';
import SesionIA from './pages/SesionIA';
import Comunidad from './pages/Comunidad';
import Mapa from './pages/Mapa';
import Escenarios from './pages/Escenarios';
import Mercados from './pages/Mercados';
import Memoria from './pages/Memoria';
import VideoEstudio from './pages/VideoEstudio';
import OSINT from './pages/OSINT';
import Wireless from './pages/Wireless';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public landing */}
        <Route path="/" element={<Landing />} />
        <Route path="/mapa" element={<Mapa />} />

        {/* Warroom — index redirects to Mapa */}
        <Route path="/control" element={<MainLayout />}>
          <Route index element={<Navigate to="/control/mapa" replace />} />
          <Route path="sesion" element={<SesionIA />} />
          <Route path="memoria" element={<Memoria />} />
          <Route path="mapa" element={<Mapa />} />
          <Route path="omniglobe" element={<OmniGlobe />} />
          <Route path="escenarios" element={<Escenarios />} />
          <Route path="osint" element={<OSINT />} />
          <Route path="wireless" element={<Wireless />} />
          <Route path="timeline/:country" element={<Timeline />} />
          <Route path="mercados" element={<Mercados />} />
          <Route path="video-studio" element={<VideoEstudio />} />
          <Route path="comunidad" element={<Comunidad />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
