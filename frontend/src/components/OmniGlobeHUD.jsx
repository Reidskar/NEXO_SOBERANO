import React, { useState, useEffect } from 'react';
import { Activity, TrendingUp, MonitorPlay, Zap, ChevronRight, Crosshair, Radar } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Emil Kowalski Framework - Premium Easings
const springHover = { type: "spring", stiffness: 300, damping: 20 };
const premiumEase = [0.23, 1, 0.32, 1]; // Strong ease-out

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { 
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.1 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, scale: 0.96, y: 15 },
  visible: { 
    opacity: 1, 
    scale: 1, 
    y: 0,
    transition: { duration: 0.6, ease: premiumEase }
  }
};

// Reusable Panel Component for consistent glassmorphism
const HudPanel = ({ children, style, icon: Icon, title, titleColor = "#00e5ff" }) => (
  <motion.div variants={itemVariants} style={{ 
    ...style, 
    background: 'rgba(5, 5, 10, 0.6)', 
    backdropFilter: 'blur(12px)',
    WebkitBackdropFilter: 'blur(12px)',
    border: '1px solid rgba(255, 255, 255, 0.05)', 
    boxShadow: '0 20px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05)',
    borderRadius: 8,
    padding: 20
  }}>
    {title && (
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 15, marginBottom: 20 }}>
        {Icon && <Icon size={16} color={titleColor} />}
        <h2 style={{ margin: 0, color: '#f8fafc', fontSize: 13, fontFamily: "'Inter', sans-serif", fontWeight: 500, letterSpacing: '0.05em' }}>{title}</h2>
      </div>
    )}
    {children}
  </motion.div>
);

const OmniGlobeHUD = ({ currentAlert }) => {
  // Inicializamos con el stream en vivo de Al Jazeera English usando su Channel ID para que nunca muera.
  const [feed, setFeed] = useState('https://www.youtube.com/embed/live_stream?channel=UCNye-wNBqNL5ZzHSJj3l8Bg&autoplay=1&controls=1');

  // AI Media Hijack: if the AI provides a specific video/clip URL, switch the player automatically
  useEffect(() => {
    if (currentAlert && currentAlert.media_url) {
      setFeed(currentAlert.media_url);
    }
  }, [currentAlert]);

  return (
    <motion.div 
      variants={containerVariants} 
      initial="hidden" 
      animate="visible" 
      style={{ pointerEvents: 'none', position: 'absolute', inset: 0, zIndex: 10, fontFamily: "'Inter', sans-serif" }}
    >
      {/* Title - Clean, minimal typography */}
      <motion.div variants={itemVariants} style={{ position: 'absolute', top: 30, left: '50%', transform: 'translateX(-50%)', display: 'flex', flexDirection: 'column', alignItems: 'center', pointerEvents: 'auto' }}>
        <h1 style={{ margin: 0, fontSize: 16, letterSpacing: '0.3em', color: '#f8fafc', fontWeight: 600, textTransform: 'uppercase' }}>O m n i g l o b e</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6 }}>
          <div style={{ width: 4, height: 4, borderRadius: '50%', background: '#00e5ff', boxShadow: '0 0 8px #00e5ff' }} />
          <span style={{ fontSize: 9, color: '#94a3b8', letterSpacing: '0.2em', textTransform: 'uppercase' }}>Live Tactical System</span>
        </div>
      </motion.div>

      {/* Global Metrics - Left */}
      <HudPanel 
        title="MÉTRICAS GLOBALES" 
        icon={Activity} 
        style={{ position: 'absolute', top: 100, left: 30, width: 300, pointerEvents: 'auto' }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#94a3b8', marginBottom: 8, fontWeight: 500 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><Activity size={12}/> PETRÓLEO BRENT</span>
              <span style={{ color: '#ef4444', fontFamily: "'Space Mono', monospace" }}>$89.50</span>
            </div>
            <div style={{ width: '100%', height: 4, background: 'rgba(255,255,255,0.05)', borderRadius: 2, overflow: 'hidden' }}>
              <motion.div initial={{ width: 0 }} animate={{ width: '85%' }} transition={{ duration: 1.5, ease: premiumEase }} style={{ height: '100%', background: '#ef4444' }} />
            </div>
          </div>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#94a3b8', marginBottom: 8, fontWeight: 500 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><Radar size={12}/> FLUJO ORMUZ</span>
              <span style={{ color: '#f59e0b', fontFamily: "'Space Mono', monospace" }}>-40%</span>
            </div>
            <div style={{ width: '100%', height: 4, background: 'rgba(255,255,255,0.05)', borderRadius: 2, overflow: 'hidden' }}>
              <motion.div initial={{ width: 0 }} animate={{ width: '40%' }} transition={{ duration: 1.5, delay: 0.2, ease: premiumEase }} style={{ height: '100%', background: '#f59e0b' }} />
            </div>
          </div>
        </div>
      </HudPanel>

      {/* Polymarket Predictions - Right */}
      <HudPanel 
        title="MERCADOS PREDICTIVOS" 
        icon={TrendingUp} 
        titleColor="#22c55e"
        style={{ position: 'absolute', top: 100, right: 30, width: 320, pointerEvents: 'auto' }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ padding: '12px 14px', background: 'rgba(255,255,255,0.02)', borderRadius: 6, border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ fontSize: 11, color: '#e2e8f0', marginBottom: 8, fontWeight: 500, lineHeight: 1.5 }}>Resolution Middle East Conflict 2026?</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: '#22c55e', fontSize: 14, fontFamily: "'Space Mono', monospace" }}>28% YES</span>
              <span style={{ fontSize: 10, color: '#64748b' }}>Vol: $4.2M</span>
            </div>
          </div>

          <div style={{ padding: '12px 14px', background: 'rgba(255,255,255,0.02)', borderRadius: 6, border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ fontSize: 11, color: '#e2e8f0', marginBottom: 8, fontWeight: 500, lineHeight: 1.5 }}>Taiwan Strait Military Action (Q3)</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: '#ef4444', fontSize: 14, fontFamily: "'Space Mono', monospace" }}>65% YES</span>
              <span style={{ fontSize: 10, color: '#64748b' }}>Vol: $12M</span>
            </div>
          </div>
        </div>
      </HudPanel>

      {/* Satellite Feeds */}
      <HudPanel 
        title="SAT-LINK & FEEDS" 
        icon={MonitorPlay} 
        titleColor="#8b5cf6"
        style={{ position: 'absolute', top: 380, right: 30, width: 320, pointerEvents: 'auto' }}
      >
        <div style={{ width: '100%', height: 160, background: '#000', borderRadius: 6, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.05)', position: 'relative' }}>
          <iframe 
            width="100%" 
            height="100%" 
            src={feed.startsWith('http') ? feed : `https://www.youtube.com/embed/${feed}?autoplay=1&controls=1`} 
            title="Live Feed" 
            frameBorder="0" 
            allowFullScreen 
            allow="autoplay; encrypted-media"
          />
          {/* Subtly darkened edges so it feels integrated, but pointers pass through */}
          <div style={{ position: 'absolute', inset: 0, boxShadow: 'inset 0 0 15px rgba(0,0,0,0.8)', pointerEvents: 'none' }} />
        </div>

        <div style={{ display: 'flex', gap: 6, marginTop: 12, flexWrap: 'wrap' }}>
          {[
            { id: 'UCNye-wNBqNL5ZzHSJj3l8Bg', label: 'AJ ENG', isChannel: true },    // Al Jazeera English
            { id: 'UCoMdktPbSTixAyNGWB-PUiA', label: 'SKY UK', isChannel: true },    // Sky News UK
            { id: 'UCknLrEdhRCp1aegoMqRaCZg', label: 'DW EU', isChannel: true },     // DW News
            { id: 'UCQfwfsi5VrQ8yKZ-UWmAEFg', label: 'FRA 24', isChannel: true },    // France 24 English
            { id: 'UCTeLqJqXmXXyEXWbYpI0k7g', label: 'ABC US', isChannel: true },    // ABC News Live
            { id: 'UChLtXXcb4uMD67reUmx_B6g', label: 'GLO CA', isChannel: true }     // Global News Canada
          ].map(ch => {
            const dest = ch.isChannel ? `https://www.youtube.com/embed/live_stream?channel=${ch.id}&autoplay=1&controls=1` : ch.id;
            const active = feed === dest;
            return (
              <motion.button 
                whileHover={springHover} whileTap={{ scale: 0.95 }}
                key={ch.id} onClick={() => setFeed(dest)}
                style={{ 
                  flex: '1 1 calc(33% - 6px)', padding: '6px 8px', 
                  background: active ? 'rgba(139, 92, 246, 0.15)' : 'rgba(255,255,255,0.02)', 
                  border: `1px solid ${active ? 'rgba(139, 92, 246, 0.4)' : 'rgba(255,255,255,0.05)'}`, 
                  color: active ? '#ddd6fe' : '#94a3b8', 
                  fontSize: 10, fontWeight: 500, borderRadius: 4, cursor: 'pointer', transition: 'background 0.2s, border 0.2s' 
                }}
              >
                {ch.label}
              </motion.button>
            );
          })}
        </div>

        <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#64748b' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><Crosshair size={10} color="#8b5cf6"/> IA TUNING</span>
          <span style={{ color: '#00e5ff', fontFamily: "'Space Mono', monospace" }}>SYNC_ON</span>
        </div>
      </HudPanel>



    </motion.div>
  );
};

export default OmniGlobeHUD;
