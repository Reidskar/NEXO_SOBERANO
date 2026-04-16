import {
    BookOpen,
    Brain,
    ChevronRight,
    FileText,
    RefreshCw,
    Trash2
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8080";

// ── DriveFilePicker ────────────────────────────────────────────────────────────
function DriveFilePicker({ selected, onToggle, onRefresh }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`${API}/api/drive/files?limit=40`, {
        signal: AbortSignal.timeout(4000),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      setFiles(d.files || d || []);
    } catch (e) {
      // Backend offline (Torre local) — silently degrade, no red error
      setError("drive_offline");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div style={styles.drivePanel}>
      <div style={styles.drivePanelHeader}>
        <span
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            color: "#00e5ff",
            fontWeight: 600,
          }}
        >
          <BookOpen size={14} /> Drive — Contexto
        </span>
        <button onClick={load} style={styles.iconBtn} title="Recargar">
          <RefreshCw
            size={13}
            style={{ animation: loading ? "spin 1s linear infinite" : "none" }}
          />
        </button>
      </div>

      {error === "drive_offline" && (
        <p
          style={{
            color: "rgba(0,229,255,0.35)",
            fontSize: 11,
            padding: "6px 12px",
            fontFamily: "'Space Mono', monospace",
            letterSpacing: ".04em",
          }}
        >
          Drive · backend local inactivo
        </p>
      )}
      {!error && files.length === 0 && !loading && (
        <p
          style={{
            color: "rgba(255,255,255,0.35)",
            fontSize: 12,
            padding: "8px 12px",
          }}
        >
          Sin archivos — autoriza Google Drive en el backend.
        </p>
      )}

      <div style={styles.fileList}>
        {files.map((f) => {
          const isSelected = selected.some((s) => s.id === (f.id || f.fileId));
          return (
            <button
              key={f.id || f.fileId}
              onClick={() => onToggle(f)}
              style={{
                ...styles.fileItem,
                background: isSelected ? "rgba(0,229,255,0.1)" : "transparent",
                borderColor: isSelected
                  ? "rgba(0,229,255,0.4)"
                  : "rgba(255,255,255,0.07)",
              }}
            >
              <FileText
                size={12}
                style={{
                  color: isSelected ? "#00e5ff" : "rgba(255,255,255,0.4)",
                  flexShrink: 0,
                }}
              />
              <span
                style={{
                  color: isSelected ? "#e0f7fa" : "rgba(255,255,255,0.6)",
                  fontSize: 12,
                  textAlign: "left",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {f.name || f.title || f.id}
              </span>
              {isSelected && (
                <span
                  style={{
                    marginLeft: "auto",
                    color: "#00e5ff",
                    fontSize: 10,
                    flexShrink: 0,
                  }}
                >
                  ✓
                </span>
              )}
            </button>
          );
        })}
      </div>

      {selected.length > 0 && (
        <div
          style={{
            padding: "6px 12px",
            borderTop: "1px solid rgba(255,255,255,0.06)",
            fontSize: 11,
            color: "#00e5ff",
          }}
        >
          {selected.length} archivo{selected.length > 1 ? "s" : ""} seleccionado
          {selected.length > 1 ? "s" : ""}
        </div>
      )}
    </div>
  );
}

// ── ChatBubble ────────────────────────────────────────────────────────────────
function ChatBubble({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        marginBottom: 14,
      }}
    >
      {!isUser && <div style={styles.avatar}>N</div>}
      <div
        style={{
          ...styles.bubble,
          background: isUser
            ? "rgba(0,229,255,0.12)"
            : "rgba(255,255,255,0.05)",
          borderColor: isUser
            ? "rgba(0,229,255,0.3)"
            : "rgba(255,255,255,0.08)",
          alignSelf: isUser ? "flex-end" : "flex-start",
          maxWidth: "78%",
        }}
      >
        {msg.thinking && (
          <div style={{ display: "flex", gap: 4, marginBottom: 6 }}>
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: "#00e5ff",
                  opacity: 0.7,
                  animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
                }}
              />
            ))}
          </div>
        )}
        {msg.content && (
          <p
            style={{
              margin: 0,
              fontSize: 14,
              lineHeight: 1.65,
              color: "rgba(255,255,255,0.88)",
              whiteSpace: "pre-wrap",
            }}
          >
            {msg.content}
          </p>
        )}
        {msg.sources && msg.sources.length > 0 && (
          <div
            style={{
              marginTop: 8,
              paddingTop: 8,
              borderTop: "1px solid rgba(255,255,255,0.07)",
            }}
          >
            <span style={{ fontSize: 11, color: "rgba(0,229,255,0.6)" }}>
              Contexto: {msg.sources.join(", ")}
            </span>
          </div>
        )}
      </div>
      {isUser && (
        <div style={{ ...styles.avatar, background: "rgba(0,229,255,0.15)" }}>
          C
        </div>
      )}
    </div>
  );
}

// ── ScenarioStarter ───────────────────────────────────────────────────────────
const TEMPLATES = [
  {
    label: "Expansión de negocio",
    prompt:
      "Analiza los escenarios de expansión para NEXO SOBERANO en los próximos 12 meses. ¿Cuáles son los 3 caminos más viables y sus riesgos?",
  },
  {
    label: "Crisis financiera",
    prompt:
      "Si las APIs de IA incrementan un 300% su costo, ¿qué estrategias de contingencia debería activar NEXO? Debate los trade-offs.",
  },
  {
    label: "Competencia IA",
    prompt:
      "En 2027 aparece un competidor con mejor LLM. ¿Cómo posiciona NEXO SOBERANO su diferenciación? Identifica ventajas defensivas.",
  },
  {
    label: "Autonomía total",
    prompt:
      "¿Qué requiere NEXO para operar 30 días sin intervención humana? Lista las capacidades faltantes y priorízalas.",
  },
];

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function Escenarios() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Soy NEXO en modo Debate Estratégico. Selecciona archivos de tu Drive como contexto y plantea cualquier escenario futuro. Puedo analizar datos reales de tu sistema para las proyecciones.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [showDrive, setShowDrive] = useState(true);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const toggleFile = (f) => {
    const id = f.id || f.fileId;
    setSelectedFiles((prev) =>
      prev.some((s) => (s.id || s.fileId) === id)
        ? prev.filter((s) => (s.id || s.fileId) !== id)
        : [...prev, f],
    );
  };

  const send = async (text) => {
    const q = text || input.trim();
    if (!q || loading) return;
    setInput("");
    const userMsg = { role: "user", content: q };
    const thinkMsg = { role: "assistant", thinking: true, content: "" };
    setMessages((prev) => [...prev, userMsg, thinkMsg]);
    setLoading(true);

    try {
      const fileNames = selectedFiles.map((f) => f.name || f.title || f.id);
      const contextNote =
        fileNames.length > 0
          ? `\n\n[Contexto Drive activo: ${fileNames.join(", ")}]`
          : "";

      const r = await fetch(`${API}/api/agente/consultar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mensaje: q + contextNote,
          modo: "escenarios",
          archivos_drive: fileNames,
          temperatura: 0.8,
        }),
      });
      const d = await r.json();
      const resp = d.respuesta || d.response || d.message || JSON.stringify(d);

      setMessages((prev) => [
        ...prev.slice(0, -1),
        {
          role: "assistant",
          content: resp,
          sources: fileNames.length > 0 ? fileNames : undefined,
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        {
          role: "assistant",
          content: `Error: ${e.message}. Verifica que el backend esté activo en ${API}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () =>
    setMessages([
      {
        role: "assistant",
        content: "Chat limpiado. Plantea un nuevo escenario.",
      },
    ]);

  return (
    <div style={styles.page}>
      <style>{`
        @keyframes bounce { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-6px)} }
        @keyframes spin { from{transform:rotate(0)} to{transform:rotate(360deg)} }
        .esc-input:focus { outline: none; border-color: rgba(0,229,255,0.5) !important; box-shadow: 0 0 0 2px rgba(0,229,255,0.1); }
        .tmpl-btn:hover { background: rgba(0,229,255,0.1) !important; border-color: rgba(0,229,255,0.3) !important; }
        .send-btn:hover:not(:disabled) { background: rgba(0,229,255,0.9) !important; }
      `}</style>

      {/* Header */}
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>
            <Brain size={20} style={{ color: "#00e5ff" }} /> Escenarios Futuros
          </h1>
          <p style={styles.subtitle}>
            Debate estratégico con contexto de tu Drive
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => setShowDrive((v) => !v)}
            style={styles.actionBtn}
          >
            <BookOpen size={14} /> {showDrive ? "Ocultar" : "Drive"}
          </button>
          <button
            onClick={clearChat}
            style={{ ...styles.actionBtn, color: "rgba(255,100,100,0.8)" }}
          >
            <Trash2 size={14} /> Limpiar
          </button>
        </div>
      </div>

      <div style={styles.body}>
        {/* Drive Panel */}
        {showDrive && (
          <DriveFilePicker selected={selectedFiles} onToggle={toggleFile} />
        )}

        {/* Chat area */}
        <div style={styles.chatArea}>
          {/* Templates */}
          <div style={styles.templates}>
            {TEMPLATES.map((t) => (
              <button
                key={t.label}
                className="tmpl-btn"
                onClick={() => send(t.prompt)}
                style={styles.templateBtn}
              >
                <ChevronRight
                  size={11}
                  style={{ color: "#00e5ff", flexShrink: 0 }}
                />
                {t.label}
              </button>
            ))}
          </div>

          {/* Messages */}
          <div style={styles.messages}>
            {messages.map((m, i) => (
              <ChatBubble key={i} msg={m} />
            ))}
            <div ref={chatEndRef} />
          </div>

          {/* Input */}
          <div style={styles.inputRow}>
            <textarea
              className="esc-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              placeholder="Plantea un escenario futuro... (Enter para enviar, Shift+Enter nueva línea)"
              style={styles.input}
              rows={2}
            />
            <button
              className="send-btn"
              onClick={() => send()}
              disabled={loading || !input.trim()}
              style={styles.sendBtn}
            >
              {loading ? (
                <RefreshCw
                  size={16}
                  style={{ animation: "spin 1s linear infinite" }}
                />
              ) : (
                "→"
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const styles = {
  page: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    background: "var(--bg1, #0a0e1a)",
    fontFamily: "'Inter', sans-serif",
    overflow: "hidden",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "16px 24px",
    borderBottom: "1px solid rgba(255,255,255,0.07)",
  },
  title: {
    margin: 0,
    fontSize: 18,
    fontWeight: 700,
    color: "#fff",
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  subtitle: { margin: "2px 0 0", fontSize: 12, color: "rgba(255,255,255,0.4)" },
  body: { display: "flex", flex: 1, overflow: "hidden" },
  actionBtn: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "6px 12px",
    background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: 6,
    color: "rgba(255,255,255,0.7)",
    cursor: "pointer",
    fontSize: 12,
  },
  drivePanel: {
    width: 240,
    flexShrink: 0,
    borderRight: "1px solid rgba(255,255,255,0.07)",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  drivePanelHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 12px 8px",
    fontSize: 13,
  },
  iconBtn: {
    background: "none",
    border: "none",
    cursor: "pointer",
    color: "rgba(255,255,255,0.4)",
    padding: 4,
  },
  fileList: { flex: 1, overflowY: "auto", padding: "0 6px 8px" },
  fileItem: {
    width: "100%",
    display: "flex",
    alignItems: "center",
    gap: 7,
    padding: "7px 8px",
    border: "1px solid",
    borderRadius: 6,
    cursor: "pointer",
    marginBottom: 4,
    transition: "all 0.15s",
  },
  chatArea: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  templates: {
    display: "flex",
    gap: 6,
    padding: "10px 16px",
    flexWrap: "wrap",
    borderBottom: "1px solid rgba(255,255,255,0.05)",
  },
  templateBtn: {
    display: "flex",
    alignItems: "center",
    gap: 5,
    padding: "5px 10px",
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 20,
    color: "rgba(255,255,255,0.6)",
    cursor: "pointer",
    fontSize: 11,
    transition: "all 0.15s",
  },
  messages: { flex: 1, overflowY: "auto", padding: "20px 20px 8px" },
  avatar: {
    width: 28,
    height: 28,
    borderRadius: "50%",
    background: "rgba(0,229,255,0.2)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 12,
    fontWeight: 700,
    color: "#00e5ff",
    flexShrink: 0,
    margin: "0 8px",
  },
  bubble: { padding: "12px 16px", borderRadius: 12, border: "1px solid" },
  inputRow: {
    display: "flex",
    gap: 8,
    padding: "12px 16px",
    borderTop: "1px solid rgba(255,255,255,0.07)",
  },
  input: {
    flex: 1,
    background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(255,255,255,0.12)",
    borderRadius: 8,
    padding: "10px 14px",
    color: "#fff",
    fontSize: 14,
    resize: "none",
    fontFamily: "inherit",
    lineHeight: 1.5,
  },
  sendBtn: {
    width: 44,
    background: "#00e5ff",
    border: "none",
    borderRadius: 8,
    color: "#000",
    fontSize: 18,
    fontWeight: 700,
    cursor: "pointer",
    transition: "all 0.15s",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
};
