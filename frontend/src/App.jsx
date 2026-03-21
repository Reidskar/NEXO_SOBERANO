import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import StatusDashboard from './components/StatusDashboard';
import Documents from './pages/Documents';
import DocumentDetail from './pages/DocumentDetail';
import Timeline from './pages/Timeline';
import SystemControl from './pages/SystemControl';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<StatusDashboard />} />
          <Route path="documents" element={<Documents />} />
          <Route path="documents/:id" element={<DocumentDetail />} />
          <Route path="timeline/:country" element={<Timeline />} />
          <Route path="control" element={<SystemControl />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
