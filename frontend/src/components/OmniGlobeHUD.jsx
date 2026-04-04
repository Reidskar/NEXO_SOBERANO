import React, { useState, useEffect, useRef } from 'react';
import { Activity, TrendingUp, MonitorPlay, Crosshair, Radar, FolderOpen, MessageSquare, Search, Wifi, WifiOff } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Emil Kowalski Framework - Premium Easings
const springHover = { type: 'spring', stiffness: 300, damping: 20 };
const premiumEase = [0.23, 1, 0.32, 1];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.05 } },
};

const itemVariants = {
  hidden: { opacity: 0, scale: 0.96, y: 12 },
  visible: { opacity: 1, scale: 1, y: 0, transition: { duration: 0.55, ease: premiumEase } },
};

const flashVariants = {
  idle:    { borderColor: 'rgba(255,255,255,0.05)', boxShadow: '0 20px 40px rgba(0,0,0,0.5)' },
  active:  { borderColor: 'rgba(168,85,247,0.6)',   boxShadow: '0 0 30px rgba(168,85,247,0.25), 0 20px 40px rgba(0,0,0,0.5)' },
};

// Reusable glassmorphism panel
const HudPanel = ({ children, style, icon: Icon, title, titleColor = '#00e5ff', flash = false }) => (
  <motion.div
    variants={itemVariants}
    animate={flash ? 'active' : 'idle'}
    transition={{ duration: 0.4 }}
    style={{
      ...style,
      background: 'rgba(5, 5, 10, 0.62)',
      backdropFilter: 'blur(14px)',
      WebkitBackdropFilter: 'blur(14px)',
      border: '1px solid rgba(255,255,255,0.05)',
      boxShadow: '0 20px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04)',
      borderRadius: 8,
      padding: 18,
      overflow: 'hidden',
    }}
  >
    {title && (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 12, marginBottom: 16 }}>
        {Icon && <Icon size={14} color={titleColor} />}
        <h2 style={{ margin: 0, color: '#f8fafc', fontSize: 12, fontFamily: "'Inter', sans-serif", fontWeight: 500, letterSpacing: '0.06em', textTransform: 'uppercase' }}>{title}</h2>
      </div>
    )}
    {children}
  </motion.div>
);

// Scrolling live log list
const LiveLog = ({ items, color, emptyMsg }) => {
  const listRef = useRef(null);
  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = 0;
  }, [items.length]);

  if (!items.length) {
    return (
      <div style={{ color: '#475569', fontSize: 10, fontFamily: 'monospace', padding: '8px 0', textAlign: 'center' }}>
        {emptyMsg || 'Esperando datos...'}
      </div>
    );
  }
  return (
    <div ref={listRef} style={{ maxHeight: 120, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
      <AnimatePresence initial={false}>
        {items.map((item, idx) => (
          <motion.div
            key={item.id || idx}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            style={{ fontSize: 10, fontFamily: 'monospace', color: '#cbd5e1', lineHeight: 1.4,
              borderLeft: `2px solid ${color}`, paddingLeft: 8, paddingTop: 2, paddingBottom: 2 }}
          >
            {item.ts && (
              <span style={{ color: '#475569', marginRight: 6 }}>
                {new Date(item.ts).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
            )}
            <span style={{ color }}>{item.prefix ? `${item.prefix} ` : ''}</span>
            {item.text || item.label || item.name || ''}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const OmniGlobeHUD = ({ currentAlert, driveActivity = [], discordActivity = [], aiAlerts = [] }) => {
  const [feed, setFeed] = useState('https://www.youtube.com/embed/live_stream?channel=UCNye-wNBqNL5ZzHSJj3l8Bg&autoplay=1&controls=1');

  // Live metrics fetched from backend (with static fallback)
  const [metrics, setMetrics] = useState({ brent: 89.50, ormuz: 40, tension: 72 });
  const [driveFlash, setDriveFlash] = useState(false);
  const [discordFlash, setDiscordFlash] = useState(false);
  const prevDriveLen    = useRef(driveActivity.length);
  const prevDiscordLen  = useRef(discordActivity.length);

  // AI Media Hijack
  useEffect(() => {
    if (currentAlert?.media_url) setFeed(currentAlert.media_url);
  }, [currentAlert]);

  // Flash Drive panel when new documents arrive
  useEffect(() => {
    if (driveActivity.length > prevDriveLen.current) {
      setDriveFlash(true);
      const t = setTimeout(() => setDriveFlash(false), 2200);
      return () => clearTimeout(t);
    }
    prevDriveLen.current = driveActivity.length;
  }, [driveActivity.length]);

  // Flash Discord panel when new messages arrive
  useEffect(() => {
    if (discordActivity.length > prevDiscordLen.current) {
      setDiscordFlash(true);
      const t = setTimeout(() => setDiscordFlash(false), 2200);
      return () => clearTimeout(t);
    }
    prevDiscordLen.current = discordActivity.length;
  }, [discordActivity.length]);

  // Periodically refresh metrics from backend (single batched setState)
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(5000) });
        if (res.ok) {
          const data = await res.json();
          // Backend may expose economic indicators; if not, keep defaults
          setMetrics(m => ({
            ...m,
            ...(data.brent   != null ? { brent:   data.brent   } : {}),
            ...(data.ormuz   != null ? { ormuz:   data.ormuz   } : {}),
            ...(data.tension != null ? { tension: data.tension } : {}),
          }));
        }
      } catch (_) {}
    };
    fetchMetrics();
    const iv = setInterval(fetchMetrics, 60000);
    return () => clearInterval(iv);
  }, []);

  const brentPct  = Math.min(100, (metrics.brent / 120) * 100);
  const ormuzPct  = metrics.ormuz;
  const tensionPct = metrics.tension;

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      style={{ pointerEvents: 'none', position: 'absolute', inset: 0, zIndex: 10, fontFamily: "'Inter', sans-serif" }}
    >
      {/* Title */}
      <motion.div variants={itemVariants} style={{ position: 'absolute', top: 28, left: '50%', transform: 'translateX(-50%)', display: 'flex', flexDirection: 'column', alignItems: 'center', pointerEvents: 'auto' }}>
        <h1 style={{ margin: 0, fontSize: 15, letterSpacing: '0.32em', color: '#f8fafc', fontWeight: 600, textTransform: 'uppercase' }}>O m n i g l o b e</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 5 }}>
          <motion.div
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            style={{ width: 4, height: 4, borderRadius: '50%', background: currentAlert?.color || '#00e5ff', boxShadow: `0 0 8px ${currentAlert?.color || '#00e5ff'}` }}
          />
          <span style={{ fontSize: 9, color: '#64748b', letterSpacing: '0.2em', textTransform: 'uppercase' }}>Live Tactical System</span>
        </div>
      </motion.div>

      {/* ── LEFT COLUMN ───────────────────────────────────────────────────── */}

      {/* Global Metrics */}
      <HudPanel title="MÉTRICAS GLOBALES" icon={Activity} style={{ position: 'absolute', top: 90, left: 28, width: 295, pointerEvents: 'auto' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {[
            { label: 'PETRÓLEO BRENT', value: `$${metrics.brent.toFixed(2)}`, pct: brentPct, color: '#ef4444', icon: <Activity size={11}/> },
            { label: 'FLUJO ORMUZ',    value: `-${metrics.ormuz}%`,           pct: ormuzPct,  color: '#f59e0b', icon: <Radar size={11}/> },
            { label: 'TENSIÓN GLOBAL', value: `${metrics.tension}%`,          pct: tensionPct, color: '#a855f7', icon: <Crosshair size={11}/> },
          ].map(({ label, value, pct, color, icon }) => (
            <div key={label}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#94a3b8', marginBottom: 6, fontWeight: 500 }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>{icon} {label}</span>
                <motion.span
                  key={value}
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  style={{ color, fontFamily: "'Space Mono', monospace", fontSize: 11 }}
                >
                  {value}
                </motion.span>
              </div>
              <div style={{ width: '100%', height: 3, background: 'rgba(255,255,255,0.05)', borderRadius: 2, overflow: 'hidden' }}>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 1.4, ease: premiumEase }}
                  style={{ height: '100%', background: color, borderRadius: 2 }}
                />
              </div>
            </div>
          ))}
        </div>
      </HudPanel>

      {/* Drive Intelligence Feed */}
      <HudPanel
        title="DRIVE INTEL FEED"
        icon={FolderOpen}
        titleColor="#a855f7"
        flash={driveFlash}
        style={{ position: 'absolute', top: 310, left: 28, width: 295, pointerEvents: 'auto' }}
      >
        <LiveLog
          items={driveActivity.slice(0, 8)}
          color="#a855f7"
          emptyMsg="Sin documentos recientes en Drive…"
        />
        <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 9, color: '#475569', fontFamily: 'monospace' }}>
          <span>DOCS: {driveActivity.length}</span>
          {driveFlash && <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ color: '#a855f7' }}>◉ NUEVO</motion.span>}
        </div>
      </HudPanel>

      {/* Discord Activity Feed */}
      <HudPanel
        title="DISCORD ACTIVITY"
        icon={MessageSquare}
        titleColor="#5865f2"
        flash={discordFlash}
        style={{ position: 'absolute', top: 490, left: 28, width: 295, pointerEvents: 'auto' }}
      >
        <LiveLog
          items={discordActivity.slice(0, 8)}
          color="#5865f2"
          emptyMsg="Sin actividad de Discord reciente…"
        />
        <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 9, color: '#475569', fontFamily: 'monospace' }}>
          <span>MSG: {discordActivity.length}</span>
          {discordFlash && <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ color: '#5865f2' }}>◉ NUEVO</motion.span>}
        </div>
      </HudPanel>

      {/* ── RIGHT COLUMN ──────────────────────────────────────────────────── */}

      {/* Polymarket Predictions */}
      <HudPanel title="MERCADOS PREDICTIVOS" icon={TrendingUp} titleColor="#22c55e" style={{ position: 'absolute', top: 90, right: 28, width: 315, pointerEvents: 'auto' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[
            { q: 'Resolution Middle East Conflict 2026?', yes: 28, vol: '$4.2M' },
            { q: 'Taiwan Strait Military Action (Q3)',    yes: 65, vol: '$12M'  },
            { q: 'Ukraine ceasefire before 2027?',       yes: 41, vol: '$8.1M' },
          ].map(({ q, yes, vol }) => (
            <div key={q} style={{ padding: '10px 12px', background: 'rgba(255,255,255,0.02)', borderRadius: 6, border: '1px solid rgba(255,255,255,0.04)' }}>
              <div style={{ fontSize: 10, color: '#e2e8f0', marginBottom: 6, fontWeight: 500, lineHeight: 1.4 }}>{q}</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ flex: 1, height: 2, background: 'rgba(255,255,255,0.05)', borderRadius: 1, marginRight: 10, overflow: 'hidden' }}>
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${yes}%` }}
                    transition={{ duration: 1.2, ease: premiumEase }}
                    style={{ height: '100%', background: yes > 50 ? '#ef4444' : '#22c55e' }}
                  />
                </div>
                <span style={{ color: yes > 50 ? '#ef4444' : '#22c55e', fontSize: 12, fontFamily: "'Space Mono', monospace", minWidth: 60 }}>
                  {yes}% YES
                </span>
                <span style={{ fontSize: 9, color: '#475569', marginLeft: 8 }}>{vol}</span>
              </div>
            </div>
          ))}
        </div>
      </HudPanel>

      {/* Live News Feeds */}
      <HudPanel title="SAT-LINK & FEEDS" icon={MonitorPlay} titleColor="#8b5cf6" style={{ position: 'absolute', top: 370, right: 28, width: 315, pointerEvents: 'auto' }}>
        <div style={{ width: '100%', height: 155, background: '#000', borderRadius: 6, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.05)', position: 'relative' }}>
          <iframe
            width="100%"
            height="100%"
            src={feed.startsWith('http') ? feed : `https://www.youtube.com/embed/${feed}?autoplay=1&controls=1`}
            title="Live Feed"
            frameBorder="0"
            allowFullScreen
            allow="autoplay; encrypted-media"
          />
          <div style={{ position: 'absolute', inset: 0, boxShadow: 'inset 0 0 18px rgba(0,0,0,0.85)', pointerEvents: 'none' }} />
        </div>

        <div style={{ display: 'flex', gap: 5, marginTop: 10, flexWrap: 'wrap' }}>
          {[
            { id: 'UCNye-wNBqNL5ZzHSJj3l8Bg', label: 'AJ ENG' },
            { id: 'UCoMdktPbSTixAyNGWB-PUiA', label: 'SKY UK' },
            { id: 'UCknLrEdhRCp1aegoMqRaCZg', label: 'DW EU'  },
            { id: 'UCQfwfsi5VrQ8yKZ-UWmAEFg', label: 'FRA 24' },
            { id: 'UCTeLqJqXmXXyEXWbYpI0k7g', label: 'ABC US' },
            { id: 'UChLtXXcb4uMD67reUmx_B6g', label: 'GLO CA' },
          ].map(ch => {
            const dest = `https://www.youtube.com/embed/live_stream?channel=${ch.id}&autoplay=1&controls=1`;
            const active = feed === dest;
            return (
              <motion.button
                whileHover={springHover}
                whileTap={{ scale: 0.94 }}
                key={ch.id}
                onClick={() => setFeed(dest)}
                style={{
                  flex: '1 1 calc(33% - 5px)', padding: '5px 6px',
                  background: active ? 'rgba(139,92,246,0.18)' : 'rgba(255,255,255,0.02)',
                  border: `1px solid ${active ? 'rgba(139,92,246,0.5)' : 'rgba(255,255,255,0.05)'}`,
                  color: active ? '#ddd6fe' : '#64748b',
                  fontSize: 9, fontWeight: 600, borderRadius: 4, cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                {ch.label}
              </motion.button>
            );
          })}
        </div>

        <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 9, color: '#475569', fontFamily: 'monospace' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}><Crosshair size={9} color="#8b5cf6"/> IA MEDIA SYNC</span>
          <motion.span
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 2.5, repeat: Infinity }}
            style={{ color: '#00e5ff' }}
          >
            LIVE
          </motion.span>
        </div>
      </HudPanel>

    </motion.div>
  );
};

export default OmniGlobeHUD;
