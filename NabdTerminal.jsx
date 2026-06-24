import { useState, useRef, useEffect } from "react";

// Neon styling palette and Bento Box system tokens
const CYAN = "#00f5d4";
const GREEN = "#39ff14";
const AMBER = "#ffb703";
const RED = "#ff4d6d";
const PURPLE = "#b48ead";
const BLUE = "#38bdf8";
const DIM = "#6272a4";
const BG = "#080c10";
const SURFACE = "rgba(22, 27, 34, 0.7)";
const BORDER = "#21262d";
const GLOW_SHADOW = "0 0 20px rgba(0, 245, 212, 0.15)";

const BADGE_STYLES = {
  LIST:   { bg: "rgba(57, 255, 20, 0.1)", color: GREEN,  border: "rgba(57, 255, 20, 0.3)" },
  SEARCH: { bg: "rgba(0, 245, 212, 0.1)", color: CYAN,   border: "rgba(0, 245, 212, 0.3)" },
  READ:   { bg: "rgba(180, 142, 173, 0.1)", color: PURPLE, border: "rgba(180, 142, 173, 0.3)" },
  EDIT:   { bg: "rgba(255, 183, 3, 0.1)", color: AMBER,  border: "rgba(255, 183, 3, 0.3)" },
  EXECUTE:{ bg: "rgba(161, 85, 255, 0.1)", color: "#a155ff", border: "rgba(161, 85, 255, 0.3)" },
  ERROR:  { bg: "rgba(255, 77, 109, 0.1)", color: RED,    border: "rgba(255, 77, 109, 0.3)" },
  INFO:   { bg: "rgba(56, 189, 248, 0.1)", color: BLUE,   border: "rgba(56, 189, 248, 0.3)" },
};

const initialLog = [
  {
    type: "system",
    text: "NabdCode CLI Agent v2.0.0 Beta — نبض",
    sub: "platform: openmodel  |  model: deepseek-v4-flash  |  workspace: active",
  },
  {
    type: "entry",
    badge: "LIST",
    label: "[nabdcode-cli]",
    result: "Found 7 items (6 dirs, 1 file)",
    expandable: true,
    expanded: false,
    detail: [
      "📁 core/",
      "📁 agents/",
      "📁 tools/",
      "📁 ui/",
      "📁 utils/",
      "📁 tests/",
      "📄 main.py",
    ],
  },
];

// Helper to parse markdown code blocks
function parseMarkdown(text) {
  if (!text) return [];
  const parts = [];
  const regex = /```(\w*)\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "text", content: text.substring(lastIndex, match.index) });
    }
    parts.push({ type: "code", language: match[1] || "txt", content: match[2].trim() });
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push({ type: "text", content: text.substring(lastIndex) });
  }

  return parts.length > 0 ? parts : [{ type: "text", content: text }];
}

function Badge({ type }) {
  const s = BADGE_STYLES[type] || BADGE_STYLES.INFO;
  return (
    <span
      style={{
        background: s.bg,
        color: s.color,
        border: `1px solid ${s.border}`,
        borderRadius: "4px",
        fontSize: "10px",
        fontWeight: 700,
        letterSpacing: "0.08em",
        padding: "2px 8px",
        fontFamily: "'JetBrains Mono', monospace",
        userSelect: "none",
        flexShrink: 0,
      }}
    >
      {type}
    </span>
  );
}

function Cursor() {
  const [v, setV] = useState(true);
  useEffect(() => {
    const t = setInterval(() => setV(x => !x), 530);
    return () => clearInterval(t);
  }, []);
  return (
    <span
      style={{
        display: "inline-block",
        width: "8px",
        height: "14px",
        background: CYAN,
        opacity: v ? 1 : 0,
        marginLeft: "4px",
        verticalAlign: "middle",
        transition: "opacity 0.1s",
      }}
    />
  );
}

function CodeBlock({ language, content }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      style={{
        background: "#080c10",
        border: `1px solid ${BORDER}`,
        borderRadius: "6px",
        margin: "12px 0",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          background: "#0d1117",
          borderBottom: `1px solid ${BORDER}`,
          padding: "6px 12px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ color: DIM, fontSize: "11px", fontFamily: "monospace" }}>
          {language || "source"}
        </span>
        <button
          onClick={handleCopy}
          style={{
            background: "transparent",
            border: "none",
            color: copied ? GREEN : CYAN,
            fontSize: "11px",
            cursor: "pointer",
            fontFamily: "monospace",
          }}
        >
          {copied ? "✓ Copied" : "[ Copy ]"}
        </button>
      </div>
      <pre
        style={{
          margin: 0,
          padding: "12px",
          overflowX: "auto",
          color: "#e6edf3",
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: "12px",
          lineHeight: "1.5",
        }}
      >
        <code>{content}</code>
      </pre>
    </div>
  );
}

function LogEntry({ entry, onToggle }) {
  return (
    <div
      style={{
        marginBottom: "14px",
        animation: "fadeIn 0.2s ease-out",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "10px",
          cursor: entry.expandable ? "pointer" : "default",
        }}
        onClick={entry.expandable ? onToggle : undefined}
      >
        <Badge type={entry.badge} />
        <span style={{ color: "#8b949e", fontFamily: "monospace", fontSize: "13px" }}>
          {entry.label}
        </span>
        {entry.expandable && (
          <span style={{ color: DIM, fontSize: "11px", marginLeft: "auto", userSelect: "none" }}>
            {entry.expanded ? "▼ collapse" : "▶ expand"}
          </span>
        )}
      </div>
      <div
        style={{
          marginTop: "6px",
          paddingLeft: "4px",
          color: "#c9d1d9",
          fontFamily: "monospace",
          fontSize: "12px",
        }}
      >
        <span style={{ color: DIM }}>└ </span>
        {entry.result}
      </div>
      {entry.expandable && entry.expanded && (
        <div
          style={{
            marginTop: "6px",
            marginLeft: "20px",
            borderLeft: `2px solid ${BORDER}`,
            paddingLeft: "12px",
          }}
        >
          {entry.detail.map((line, i) => (
            <div
              key={i}
              style={{
                color: "#768390",
                fontFamily: "monospace",
                fontSize: "12px",
                lineHeight: "1.7",
              }}
            >
              {line}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SystemEntry({ entry }) {
  return (
    <div
      style={{
        marginBottom: "18px",
        paddingBottom: "14px",
        borderBottom: `1px solid ${BORDER}`,
      }}
    >
      <div style={{ color: CYAN, fontFamily: "'JetBrains Mono', monospace", fontSize: "13px", fontWeight: 700, letterSpacing: "0.05em" }}>
        ◆ {entry.text}
      </div>
      <div style={{ color: DIM, fontFamily: "monospace", fontSize: "11px", marginTop: "6px" }}>
        {entry.sub}
      </div>
    </div>
  );
}

function AssistantEntry({ entry }) {
  const parts = parseMarkdown(entry.text);
  return (
    <div
      style={{
        marginBottom: "14px",
        background: "#0c0f13",
        border: `1px solid ${BORDER}`,
        borderRadius: "6px",
        padding: "12px 16px",
        animation: "fadeIn 0.25s ease-out",
      }}
    >
      <div style={{ color: CYAN, fontSize: "10px", fontFamily: "monospace", marginBottom: "6px", opacity: 0.7, letterSpacing: "0.05em" }}>
        ◈ agent
      </div>
      <div style={{ color: "#c9d1d9", fontFamily: "monospace", fontSize: "13px", lineHeight: "1.6" }}>
        {parts.map((part, index) => {
          if (part.type === "code") {
            return <CodeBlock key={index} language={part.language} content={part.content} />;
          }
          return (
            <div key={index} style={{ whiteSpace: "pre-wrap" }}>
              {part.content}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function UserEntry({ entry }) {
  return (
    <div style={{ marginBottom: "14px", display: "flex", gap: "10px", alignItems: "flex-start", animation: "fadeIn 0.15s ease-out" }}>
      <span style={{ color: CYAN, fontFamily: "monospace", fontSize: "14px", flexShrink: 0, marginTop: "1px", userSelect: "none" }}>›</span>
      <span style={{ color: "#e6edf3", fontFamily: "monospace", fontSize: "13px", whiteSpace: "pre-wrap" }}>{entry.text}</span>
    </div>
  );
}

const MOCK_RESPONSES = {
  "/help": `الأوامر المحلية المتاحة داخل مساحة عمل نبض:
  /list [path]    — عرض محتويات المجلد الحالي
  /search <term>  — البحث الدلالي في ملفات الكود
  /read <file>    — قراءة محتويات ملف معين
  /clear          — تنظيف شاشة الطرفية الحالية`,
  "/list": `LIST [.]
Found 7 items (6 dirs, 1 file)
📁 core/  📁 agents/  📁 tools/
📁 ui/  📁 utils/  📁 tests/
📄 main.py`,
};

export default function NabdTerminal() {
  const [log, setLog] = useState(initialLog);
  const [input, setInput] = useState("");
  const [history, setHistory] = useState([]);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const [loading, setLoading] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Check backend server connection health
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/health", { method: "GET" }).catch(() => null);
        if (res && res.ok) {
          setBackendOnline(true);
        } else {
          setBackendOnline(false);
        }
      } catch {
        setBackendOnline(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [log, loading]);

  const toggleExpand = (idx) => {
    setLog(l => l.map((e, i) => i === idx ? { ...e, expanded: !e.expanded } : e));
  };

  const handleSubmit = async () => {
    const q = input.trim();
    if (!q) return;

    setHistory(h => [q, ...h]);
    setHistoryIdx(-1);
    setInput("");

    if (q === "/clear") {
      setLog([initialLog[0]]);
      return;
    }

    const userEntry = { type: "user", text: q };
    setLog(l => [...l, userEntry]);
    setLoading(true);

    // Fast local slash commands
    const mockKey = Object.keys(MOCK_RESPONSES).find(k => q.startsWith(k));
    if (mockKey) {
      await new Promise(r => setTimeout(r, 200));
      setLog(l => [...l, { type: "assistant", text: MOCK_RESPONSES[mockKey] }]);
      setLoading(false);
      return;
    }

    // Connect to python backend api
    try {
      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: q }),
      });
      const data = await res.json();
      setLog(l => [...l, { type: "assistant", text: data.response || "لم يتم إرجاع استجابة من النواة." }]);
    } catch (e) {
      setLog(l => [
        ...l,
        {
          type: "entry",
          badge: "ERROR",
          label: "Nabd Core Error",
          result: `Failed to connect: ${e.message}. Is nabdcode_server.py running on port 8000?`,
          expandable: false
        }
      ]);
    }
    setLoading(false);
  };

  const handleKey = (e) => {
    if (e.key === "Enter") {
      handleSubmit();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const next = Math.min(historyIdx + 1, history.length - 1);
      setHistoryIdx(next);
      setInput(history[next] ?? "");
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      const next = Math.max(historyIdx - 1, -1);
      setHistoryIdx(next);
      setInput(next === -1 ? "" : history[next]);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: BG,
        backgroundImage: "radial-gradient(circle at 50% 50%, #0d1624 0%, #080c10 100%)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        padding: "24px 16px",
      }}
      onClick={() => inputRef.current?.focus()}
    >
      {/* Global CSS Inject for Animations & Custom Scrollbars */}
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        ::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        ::-webkit-scrollbar-track {
          background: transparent;
        }
        ::-webkit-scrollbar-thumb {
          background: #21262d;
          border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
          background: #30363d;
        }
      `}} />

      <div
        style={{
          width: "100%",
          maxWidth: "760px",
          background: SURFACE,
          backdropFilter: "blur(12px)",
          border: `1px solid ${BORDER}`,
          borderRadius: "12px",
          overflow: "hidden",
          boxShadow: `0 24px 64px rgba(0,0,0,0.65), ${GLOW_SHADOW}`,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Upper title bar / Mac-style window controls */}
        <div
          style={{
            background: "rgba(13, 17, 23, 0.9)",
            borderBottom: `1px solid ${BORDER}`,
            padding: "12px 18px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            userSelect: "none",
          }}
        >
          <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#ff5f57", display: "inline-block" }} />
          <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#febc2e", display: "inline-block" }} />
          <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#28c840", display: "inline-block" }} />
          
          <span style={{ color: DIM, fontSize: "11px", marginLeft: "12px", letterSpacing: "0.05em" }}>
            nabdcode-agent — terminal
          </span>

          {/* Connection Health Indicator */}
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "6px" }}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: backendOnline ? GREEN : RED,
                boxShadow: backendOnline ? "0 0 8px #39ff14" : "0 0 8px #ff4d6d",
                display: "inline-block",
                transition: "all 0.3s ease",
              }}
            />
            <span style={{ color: backendOnline ? GREEN : RED, fontSize: "10px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              {backendOnline ? "online" : "offline"}
            </span>
          </div>
        </div>

        {/* Scrollable chat log viewport */}
        <div
          style={{
            padding: "20px 24px",
            height: "440px",
            overflowY: "auto",
            scrollBehavior: "smooth",
          }}
        >
          {log.map((entry, i) => {
            if (entry.type === "system") return <SystemEntry key={i} entry={entry} />;
            if (entry.type === "user") return <UserEntry key={i} entry={entry} />;
            if (entry.type === "assistant") return <AssistantEntry key={i} entry={entry} />;
            return <LogEntry key={i} entry={entry} onToggle={() => toggleExpand(i)} />;
          })}
          {loading && (
            <div
              style={{
                color: DIM,
                fontFamily: "monospace",
                fontSize: "12px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                marginTop: "12px",
                animation: "fadeIn 0.15s ease-out",
              }}
            >
              <span style={{ color: CYAN, animation: "pulse 1s infinite alternate" }}>◈</span>
              <span>جاري المعالجة عبر المحرك الدلالي</span>
              <Cursor />
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Smart interactive bottom input line */}
        <div
          style={{
            borderTop: `1px solid ${BORDER}`,
            padding: "14px 24px",
            display: "flex",
            alignItems: "center",
            gap: "12px",
            background: "rgba(13, 17, 23, 0.95)",
          }}
        >
          <span style={{ color: CYAN, fontSize: "16px", flexShrink: 0, userSelect: "none" }}>›</span>
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="اسأل نبض عن الكود، أو اكتب /help..."
            autoFocus
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              color: "#e6edf3",
              fontFamily: "inherit",
              fontSize: "13px",
              caretColor: CYAN,
            }}
          />
          {input && (
            <span style={{ color: DIM, fontSize: "10px", userSelect: "none", opacity: 0.7 }}>↵ enter</span>
          )}
        </div>

        {/* Shortcut Quick-action menu bar */}
        <div
          style={{
            padding: "0px 24px 14px",
            background: "rgba(13, 17, 23, 0.95)",
            display: "flex",
            gap: "12px",
            flexWrap: "wrap",
          }}
        >
          {["/list", "/search", "/help", "/clear"].map(cmd => (
            <button
              key={cmd}
              onClick={(e) => {
                e.stopPropagation();
                if (cmd === "/clear") {
                  setLog([initialLog[0]]);
                } else {
                  setInput(cmd + " ");
                }
                inputRef.current?.focus();
              }}
              style={{
                background: "rgba(33, 38, 45, 0.5)",
                border: `1px solid ${BORDER}`,
                borderRadius: "4px",
                cursor: "pointer",
                color: DIM,
                fontFamily: "monospace",
                fontSize: "11px",
                padding: "3px 8px",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={e => {
                e.target.style.color = CYAN;
                e.target.style.borderColor = CYAN;
                e.target.style.background = "rgba(0, 245, 212, 0.05)";
              }}
              onMouseLeave={e => {
                e.target.style.color = DIM;
                e.target.style.borderColor = BORDER;
                e.target.style.background = "rgba(33, 38, 45, 0.5)";
              }}
            >
              {cmd}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
