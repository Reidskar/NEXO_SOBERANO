import React, { useState, useEffect } from 'react';
import { X, Mail, CheckCircle } from 'lucide-react';
import axios from 'axios';

const EmailCapture = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState('idle'); // idle, loading, success, error

  useEffect(() => {
    // 🧲 Growth Logic: Trigger after 10s or 50% scroll
    const timer = setTimeout(() => {
      if (!sessionStorage.getItem('email_captured')) {
        setIsVisible(true);
      }
    }, 10000);

    const handleScroll = () => {
      const scrolled = window.scrollY;
      const total = document.documentElement.scrollHeight - window.innerHeight;
      if (scrolled / total > 0.5 && !sessionStorage.getItem('email_captured')) {
        setIsVisible(true);
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email) return;
    setStatus('loading');
    try {
      await axios.post('https://api.elanarcocapital.com/api/email/subscribe', {
        email,
        source: 'scroll_timeout_popup'
      });
      setStatus('success');
      sessionStorage.setItem('email_captured', 'true');
      setTimeout(() => setIsVisible(false), 2000);
    } catch (err) {
      console.error(err);
      setStatus('error');
    }
  };

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 animate-in slide-in-from-bottom-5">
      <div className="bg-black/90 border border-red-900 shadow-2xl shadow-red-900/20 p-6 rounded-lg max-w-sm w-full relative backdrop-blur-sm">
        <button 
          onClick={() => setIsVisible(false)}
          className="absolute top-2 right-2 text-neutral-400 hover:text-white"
        >
          <X size={18} />
        </button>
        
        {status === 'success' ? (
          <div className="text-center py-4 text-green-500">
            <CheckCircle className="mx-auto mb-2" size={32} />
            <h3 className="text-lg font-bold">Autorización Concedida</h3>
            <p className="text-sm text-neutral-300">Recibirás alertas tempranas en tu canal seguro.</p>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-900/30 rounded text-red-500">
                <Mail size={24} />
              </div>
              <h3 className="font-bold text-white leading-tight">Acceso Nivel 2: Alertas Tempranas</h3>
            </div>
            <p className="text-sm text-neutral-400 mb-4">
              Suscríbete para recibir inteligencia táctica filtrada directo a tu dispositivo, antes que los medios tracionales.
            </p>
            <form onSubmit={handleSubmit} className="flex flex-col gap-2">
              <input 
                type="email" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Identificación: Correo Seguro" 
                className="w-full bg-neutral-900 border border-neutral-700 p-2 rounded text-white outline-none focus:border-red-500"
                required
              />
              <button 
                type="submit" 
                disabled={status === 'loading'}
                className="w-full bg-red-800 hover:bg-red-700 text-white font-bold p-2 rounded transition-colors"
              >
                {status === 'loading' ? 'Verificando...' : 'ACTIVAR CANAL SEGURI'}
              </button>
              {status === 'error' && <p className="text-xs text-red-500 mt-1">Fallo de enlace. Reintente.</p>}
            </form>
          </>
        )}
      </div>
    </div>
  );
};

export default EmailCapture;
