import { lazy, Suspense, useState } from "react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";

const Dashboard    = lazy(() => import("./pages/Dashboard"));
const Mapa         = lazy(() => import("./pages/Mapa"));
const Inteligencia = lazy(() => import("./pages/Inteligencia"));
const Documentos   = lazy(() => import("./pages/Documentos"));
const Comunidad    = lazy(() => import("./pages/Comunidad"));
const Admin        = lazy(() => import("./pages/Admin"));

const PAGES = {
  dashboard:    <Dashboard />,
  mapa:         <Mapa />,
  inteligencia: <Inteligencia />,
  documentos:   <Documentos />,
  comunidad:    <Comunidad />,
  admin:        <Admin />,
};

function App() {
  const [currentPage, setCurrentPage] = useState("dashboard");

  return (
    <div className="flex h-screen bg-nexo-dark text-nexo-text font-sans">
      <Sidebar currentPage={currentPage} setCurrentPage={setCurrentPage} />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 overflow-auto">
          <Suspense
            fallback={
              <div className="flex items-center justify-center h-full">
                <div className="flex flex-col items-center gap-3">
                  <div className="w-8 h-8 border-2 border-nexo-green border-t-transparent rounded-full animate-spin" />
                  <span className="text-nexo-muted text-sm">Cargando módulo…</span>
                </div>
              </div>
            }
          >
            {PAGES[currentPage] ?? <Dashboard />}
          </Suspense>
        </main>
      </div>
    </div>
  );
}

export default App;
