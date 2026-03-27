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

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public landing page */}
        <Route path="/" element={<Landing />} />

        {/* Scenario debate (Drive-powered) */}
        <Route path="/escenarios" element={<Escenarios />} />

        {/* Internal control panel */}
        <Route path="/control" element={<MainLayout />}>
          <Route index element={<StatusDashboard />} />
          <Route path="documents" element={<Documents />} />
          <Route path="documents/:id" element={<DocumentDetail />} />
          <Route path="timeline/:country" element={<Timeline />} />
          <Route path="system" element={<SystemControl />} />
          <Route path="escenarios" element={<Escenarios />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
