import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Landing from './pages/Landing';
import StatusDashboard from './components/StatusDashboard';
import Documents from './pages/Documents';
import DocumentDetail from './pages/DocumentDetail';
import Timeline from './pages/Timeline';
import SystemControl from './pages/SystemControl';
import Escenarios from './pages/Escenarios';
import SesionIA from './pages/SesionIA';
import Comunidad from './pages/Comunidad';
import Mapa from './pages/Mapa';
import Boveda from './pages/Boveda';
import Mercados from './pages/Mercados';
import Memoria from './pages/Memoria';
import VideoEstudio from './pages/VideoEstudio';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public landing */}
        <Route path="/" element={<Landing />} />
        <Route path="/mapa" element={<Mapa />} />

        {/* Internal warroom */}
        <Route path="/control" element={<MainLayout />}>
          <Route index element={<StatusDashboard />} />
          <Route path="sesion" element={<SesionIA />} />
          <Route path="comunidad" element={<Comunidad />} />
          <Route path="mapa" element={<Mapa />} />
          <Route path="documents" element={<Documents />} />
          <Route path="documents/:id" element={<DocumentDetail />} />
          <Route path="timeline/:country" element={<Timeline />} />
          <Route path="system" element={<SystemControl />} />
          <Route path="escenarios" element={<Escenarios />} />
          <Route path="boveda" element={<Boveda />} />
          <Route path="mercados" element={<Mercados />} />
          <Route path="memoria" element={<Memoria />} />
          <Route path="video-studio" element={<VideoEstudio />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
