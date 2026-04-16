import { AnimatePresence, motion } from "framer-motion";
import {
    Activity,
    Crosshair,
    Minus,
    MonitorPlay,
    Plus,
    Radar,
    TrendingUp
} from "lucide-react";
import { useEffect, useState } from "react";

// Emil Kowalski Framework - Premium Easings
const springHover = { type: "spring", stiffness: 300, damping: 20 };
const premiumEase = [0.23, 1, 0.32, 1]; // Strong ease-out

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, scale: 0.96, y: 15 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: 0.6, ease: premiumEase },
  },
};

// Reusable Panel Component for consistent glassmorphism — with minimize support
const HudPanel = ({
  children,
  style,
  icon: Icon,
  title,
  titleColor = "#00e5ff",
  onMinimize,
}) => (
  <motion.div
    variants={itemVariants}
    style={{
      ...style,
      background: "rgba(5, 5, 10, 0.85)",
      border: "1px solid rgba(255, 255, 255, 0.05)",
      boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
      borderRadius: 8,
      padding: 16,
    }}
  >
    {title && (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          borderBottom: "1px solid rgba(255,255,255,0.05)",
          paddingBottom: 15,
          marginBottom: 20,
        }}
      >
        {Icon && <Icon size={16} color={titleColor} />}
        <h2
          style={{
            margin: 0,
            flex: 1,
            color: "#f8fafc",
            fontSize: 13,
            fontFamily: "'Inter', sans-serif",
            fontWeight: 500,
            letterSpacing: "0.05em",
          }}
        >
          {title}
        </h2>
        {onMinimize && (
          <button
            onClick={onMinimize}
            style={{
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 4,
              width: 22,
              height: 22,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              color: "#64748b",
              transition: "color 0.2s, background 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "#f8fafc";
              e.currentTarget.style.background = "rgba(255,255,255,0.1)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "#64748b";
              e.currentTarget.style.background = "rgba(255,255,255,0.05)";
            }}
          >
            <Minus size={12} />
          </button>
        )}
      </div>
    )}
    {children}
  </motion.div>
);

const PANEL_CONFIG = [
  { id: "metrics", label: "MÉTRICAS", icon: Activity, color: "#00e5ff" },
  { id: "polymarket", label: "MERCADOS", icon: TrendingUp, color: "#22c55e" },
  { id: "satlink", label: "SAT-LINK", icon: MonitorPlay, color: "#8b5cf6" },
];

const OmniGlobeHUD = ({ currentAlert }) => {
  // Inicializamos con el stream en vivo de Al Jazeera English usando su Channel ID para que nunca muera.
  const [feed, setFeed] = useState(
    "https://www.youtube.com/embed/live_stream?channel=UCNye-wNBqNL5ZzHSJj3l8Bg&autoplay=1&controls=1",
  );
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [hiddenPanels, setHiddenPanels] = useState(new Set());

  const hidePanel = (id) =>
    setHiddenPanels((prev) => {
      const n = new Set(prev);
      n.add(id);
      return n;
    });
  const showPanel = (id) =>
    setHiddenPanels((prev) => {
      const n = new Set(prev);
      n.delete(id);
      return n;
    });

  // AI Media Hijack: if the AI provides a specific video/clip URL, switch the player automatically
  useEffect(() => {
    if (currentAlert && currentAlert.media_url) {
      setFeed(currentAlert.media_url);
      setIframeLoaded(true);
    }
  }, [currentAlert]);

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      style={{
        pointerEvents: "none",
        position: "absolute",
        inset: 0,
        zIndex: 10,
        fontFamily: "'Inter', sans-serif",
      }}
    >
      {/* Title - Clean, minimal typography */}
      <motion.div
        variants={itemVariants}
        style={{
          position: "absolute",
          top: 30,
          left: "50%",
          transform: "translateX(-50%)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          pointerEvents: "auto",
        }}
      >
        <h1
          style={{
            margin: 0,
            fontSize: 16,
            letterSpacing: "0.3em",
            color: "#f8fafc",
            fontWeight: 600,
            textTransform: "uppercase",
          }}
        >
          O m n i g l o b e
        </h1>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            marginTop: 6,
          }}
        >
          <div
            style={{
              width: 4,
              height: 4,
              borderRadius: "50%",
              background: "#00e5ff",
              boxShadow: "0 0 8px #00e5ff",
            }}
          />
          <span
            style={{
              fontSize: 9,
              color: "#94a3b8",
              letterSpacing: "0.2em",
              textTransform: "uppercase",
            }}
          >
            Live Tactical System
          </span>
        </div>
      </motion.div>

      {/* Restore tabs for minimized panels */}
      <AnimatePresence>
        {hiddenPanels.size > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            style={{
              position: "absolute",
              top: 70,
              left: 16,
              zIndex: 25,
              display: "flex",
              flexDirection: "column",
              gap: 4,
              pointerEvents: "auto",
            }}
          >
            {PANEL_CONFIG.filter((p) => hiddenPanels.has(p.id)).map((p) => (
              <motion.button
                key={p.id}
                initial={{ opacity: 0, x: -15 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -15 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => showPanel(p.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  background: "rgba(5,5,10,0.9)",
                  border: `1px solid ${p.color}33`,
                  borderRadius: 6,
                  padding: "5px 10px",
                  cursor: "pointer",
                  color: p.color,
                  fontSize: 9,
                  fontFamily: "'Space Mono', monospace",
                  letterSpacing: "0.05em",
                }}
              >
                <Plus size={10} />
                {p.label}
              </motion.button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Global Metrics - Bottom left (below EventTimeline) */}
      {!hiddenPanels.has("metrics") && (
        <HudPanel
          title="MÉTRICAS GLOBALES"
          icon={Activity}
          onMinimize={() => hidePanel("metrics")}
          style={{
            position: "absolute",
            bottom: 240,
            left: 16,
            width: 240,
            pointerEvents: "auto",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 11,
                  color: "#94a3b8",
                  marginBottom: 8,
                  fontWeight: 500,
                }}
              >
                <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <Activity size={12} /> PETRÓLEO BRENT
                </span>
                <span
                  style={{
                    color: "#ef4444",
                    fontFamily: "'Space Mono', monospace",
                  }}
                >
                  $89.50
                </span>
              </div>
              <div
                style={{
                  width: "100%",
                  height: 4,
                  background: "rgba(255,255,255,0.05)",
                  borderRadius: 2,
                  overflow: "hidden",
                }}
              >
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: "85%" }}
                  transition={{ duration: 1.5, ease: premiumEase }}
                  style={{ height: "100%", background: "#ef4444" }}
                />
              </div>
            </div>
            <div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 11,
                  color: "#94a3b8",
                  marginBottom: 8,
                  fontWeight: 500,
                }}
              >
                <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <Radar size={12} /> FLUJO ORMUZ
                </span>
                <span
                  style={{
                    color: "#f59e0b",
                    fontFamily: "'Space Mono', monospace",
                  }}
                >
                  -40%
                </span>
              </div>
              <div
                style={{
                  width: "100%",
                  height: 4,
                  background: "rgba(255,255,255,0.05)",
                  borderRadius: 2,
                  overflow: "hidden",
                }}
              >
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: "40%" }}
                  transition={{ duration: 1.5, delay: 0.2, ease: premiumEase }}
                  style={{ height: "100%", background: "#f59e0b" }}
                />
              </div>
            </div>
          </div>
        </HudPanel>
      )}

      {/* Polymarket Predictions - Right */}
      {!hiddenPanels.has("polymarket") && (
        <HudPanel
          title="MERCADOS PREDICTIVOS"
          icon={TrendingUp}
          titleColor="#22c55e"
          onMinimize={() => hidePanel("polymarket")}
          style={{
            position: "absolute",
            top: 70,
            right: 16,
            width: 260,
            pointerEvents: "auto",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div
              style={{
                padding: "12px 14px",
                background: "rgba(255,255,255,0.02)",
                borderRadius: 6,
                border: "1px solid rgba(255,255,255,0.05)",
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  color: "#e2e8f0",
                  marginBottom: 8,
                  fontWeight: 500,
                  lineHeight: 1.5,
                }}
              >
                Resolution Middle East Conflict 2026?
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span
                  style={{
                    color: "#22c55e",
                    fontSize: 14,
                    fontFamily: "'Space Mono', monospace",
                  }}
                >
                  28% YES
                </span>
                <span style={{ fontSize: 10, color: "#64748b" }}>
                  Vol: $4.2M
                </span>
              </div>
            </div>

            <div
              style={{
                padding: "12px 14px",
                background: "rgba(255,255,255,0.02)",
                borderRadius: 6,
                border: "1px solid rgba(255,255,255,0.05)",
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  color: "#e2e8f0",
                  marginBottom: 8,
                  fontWeight: 500,
                  lineHeight: 1.5,
                }}
              >
                Taiwan Strait Military Action (Q3)
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span
                  style={{
                    color: "#ef4444",
                    fontSize: 14,
                    fontFamily: "'Space Mono', monospace",
                  }}
                >
                  65% YES
                </span>
                <span style={{ fontSize: 10, color: "#64748b" }}>
                  Vol: $12M
                </span>
              </div>
            </div>
          </div>
        </HudPanel>
      )}

      {/* Satellite Feeds */}
      {!hiddenPanels.has("satlink") && (
        <HudPanel
          title="SAT-LINK & FEEDS"
          icon={MonitorPlay}
          titleColor="#8b5cf6"
          onMinimize={() => hidePanel("satlink")}
          style={{
            position: "absolute",
            top: 350,
            right: 16,
            width: 260,
            pointerEvents: "auto",
          }}
        >
          <div
            style={{
              width: "100%",
              height: 140,
              background: "#000",
              borderRadius: 6,
              overflow: "hidden",
              border: "1px solid rgba(255,255,255,0.05)",
              position: "relative",
            }}
          >
            {iframeLoaded ? (
              <iframe
                width="100%"
                height="100%"
                src={
                  feed.startsWith("http")
                    ? feed
                    : `https://www.youtube.com/embed/${feed}?autoplay=1&controls=1`
                }
                title="Live Feed"
                frameBorder="0"
                allowFullScreen
                allow="autoplay; encrypted-media"
                loading="lazy"
              />
            ) : (
              <div
                onClick={() => setIframeLoaded(true)}
                style={{
                  width: "100%",
                  height: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                  color: "#8b5cf6",
                  fontSize: 11,
                  fontFamily: "'Space Mono', monospace",
                  letterSpacing: 1,
                }}
              >
                ▶ CARGAR FEED EN VIVO
              </div>
            )}
            {/* Subtly darkened edges so it feels integrated, but pointers pass through */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                boxShadow: "inset 0 0 15px rgba(0,0,0,0.8)",
                pointerEvents: "none",
              }}
            />
          </div>

          <div
            style={{ display: "flex", gap: 6, marginTop: 12, flexWrap: "wrap" }}
          >
            {[
              {
                id: "UCNye-wNBqNL5ZzHSJj3l8Bg",
                label: "AJ ENG",
                isChannel: true,
              }, // Al Jazeera English
              {
                id: "UCoMdktPbSTixAyNGWB-PUiA",
                label: "SKY UK",
                isChannel: true,
              }, // Sky News UK
              {
                id: "UCknLrEdhRCp1aegoMqRaCZg",
                label: "DW EU",
                isChannel: true,
              }, // DW News
              {
                id: "UCQfwfsi5VrQ8yKZ-UWmAEFg",
                label: "FRA 24",
                isChannel: true,
              }, // France 24 English
              {
                id: "UCTeLqJqXmXXyEXWbYpI0k7g",
                label: "ABC US",
                isChannel: true,
              }, // ABC News Live
              {
                id: "UChLtXXcb4uMD67reUmx_B6g",
                label: "GLO CA",
                isChannel: true,
              }, // Global News Canada
            ].map((ch) => {
              const dest = ch.isChannel
                ? `https://www.youtube.com/embed/live_stream?channel=${ch.id}&autoplay=1&controls=1`
                : ch.id;
              const active = feed === dest;
              return (
                <motion.button
                  whileHover={springHover}
                  whileTap={{ scale: 0.95 }}
                  key={ch.id}
                  onClick={() => {
                    setFeed(dest);
                    setIframeLoaded(true);
                  }}
                  style={{
                    flex: "1 1 calc(33% - 6px)",
                    padding: "6px 8px",
                    background: active
                      ? "rgba(139, 92, 246, 0.15)"
                      : "rgba(255,255,255,0.02)",
                    border: `1px solid ${active ? "rgba(139, 92, 246, 0.4)" : "rgba(255,255,255,0.05)"}`,
                    color: active ? "#ddd6fe" : "#94a3b8",
                    fontSize: 10,
                    fontWeight: 500,
                    borderRadius: 4,
                    cursor: "pointer",
                    transition: "background 0.2s, border 0.2s",
                  }}
                >
                  {ch.label}
                </motion.button>
              );
            })}
          </div>

          <div
            style={{
              marginTop: 16,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: 10,
              color: "#64748b",
            }}
          >
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <Crosshair size={10} color="#8b5cf6" /> IA TUNING
            </span>
            <span
              style={{
                color: "#00e5ff",
                fontFamily: "'Space Mono', monospace",
              }}
            >
              SYNC_ON
            </span>
          </div>
        </HudPanel>
      )}
    </motion.div>
  );
};

export default OmniGlobeHUD;
