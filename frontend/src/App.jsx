import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import Dashboard from "./pages/Dashboard";
import { useState } from "react";

function App() {
  const [currentPage, setCurrentPage] = useState("dashboard");

  return (
    <div className="flex h-screen bg-gray-900 text-white">
      <Sidebar currentPage={currentPage} setCurrentPage={setCurrentPage} />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 overflow-auto">
          {currentPage === "dashboard" && <Dashboard />}
        </main>
      </div>
    </div>
  );
}

export default App;
