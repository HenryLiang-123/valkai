import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Chat from "./components/Chat";
import Evals from "./components/Evals";
import type { SessionSummary } from "./api";

export default function App() {
  const [activeSession, setActiveSession] = useState<{
    id: string;
    strategy: string;
  } | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [showEvals, setShowEvals] = useState(false);

  const handleSelectSession = (session: SessionSummary) => {
    setActiveSession({ id: session.id, strategy: session.strategy });
    setShowEvals(false);
  };

  const handleNewSession = (id: string, strategy: string) => {
    setActiveSession({ id, strategy });
    setRefreshKey((k) => k + 1);
    setShowEvals(false);
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar
        activeSessionId={activeSession?.id ?? null}
        onSelectSession={handleSelectSession}
        onNewSession={handleNewSession}
        onOpenEvals={() => { setShowEvals(true); setActiveSession(null); }}
        refreshKey={refreshKey}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        {showEvals ? (
          <Evals onBack={() => setShowEvals(false)} />
        ) : activeSession ? (
          <Chat
            key={activeSession.id}
            sessionId={activeSession.id}
            strategy={activeSession.strategy}
          />
        ) : (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100vh",
              gap: 12,
              padding: 40,
            }}
          >
            <p
              style={{
                fontFamily: "var(--font-display)",
                fontSize: 28,
                fontWeight: 400,
                color: "var(--text-primary)",
                letterSpacing: "-0.01em",
              }}
            >
              Memory Agent
            </p>
            <p
              style={{
                fontSize: 13,
                color: "var(--text-muted)",
                fontWeight: 300,
                letterSpacing: "0.02em",
              }}
            >
              Select a session or start a new conversation
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
