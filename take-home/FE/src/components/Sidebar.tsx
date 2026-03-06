import { useEffect, useState } from "react";
import {
  fetchSessions,
  fetchStrategies,
  createSession,
  type SessionSummary,
  type Strategy,
} from "../api";
import styles from "./Sidebar.module.css";

interface Props {
  activeSessionId: string | null;
  onSelectSession: (session: SessionSummary) => void;
  onNewSession: (id: string, strategy: string) => void;
  onOpenEvals: () => void;
  refreshKey: number;
}

export default function Sidebar({
  activeSessionId,
  onSelectSession,
  onNewSession,
  onOpenEvals,
  refreshKey,
}: Props) {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [showPicker, setShowPicker] = useState(false);
  const [creating, setCreating] = useState<string | null>(null);

  useEffect(() => {
    fetchStrategies().then(setStrategies);
  }, []);

  useEffect(() => {
    fetchSessions().then(setSessions);
  }, [refreshKey]);

  const handlePickStrategy = async (key: string) => {
    if (creating) return;
    setCreating(key);
    try {
      const { id } = await createSession(key);
      onNewSession(id, key);
      setShowPicker(false);
      fetchSessions().then(setSessions);
    } finally {
      setCreating(null);
    }
  };

  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>Memory Agent</div>
      <div className={styles.newChat}>
        <button
          className={styles.newBtn}
          onClick={() => setShowPicker(!showPicker)}
        >
          + New chat
        </button>
      </div>

      {showPicker && (
        <div className={styles.picker}>
          <p className={styles.pickerLabel}>Select memory strategy</p>
          {strategies.map((s) => (
            <button
              key={s.key}
              className={styles.pickerItem}
              onClick={() => handlePickStrategy(s.key)}
              disabled={creating !== null}
            >
              <span className={styles.pickerName}>{s.name}</span>
              <span className={styles.pickerDesc}>{s.description}</span>
              {creating === s.key && (
                <span className={styles.pickerLoading}>...</span>
              )}
            </button>
          ))}
        </div>
      )}

      <div className={styles.sessionList}>
        {sessions.map((s) => (
          <button
            key={s.id}
            className={`${styles.sessionItem} ${
              s.id === activeSessionId ? styles.active : ""
            }`}
            onClick={() => onSelectSession(s)}
          >
            <span className={styles.sessionStrategy}>{s.strategy}</span>
            <span className={styles.sessionId}>{s.id.slice(0, 8)}...</span>
            <span className={styles.sessionDate}>
              {new Date(s.created_at).toLocaleDateString()}
            </span>
          </button>
        ))}
        {sessions.length === 0 && (
          <p className={styles.empty}>No sessions yet</p>
        )}
      </div>

      <div className={styles.footer}>
        <button className={styles.evalsBtn} onClick={onOpenEvals}>
          Evals & Harness
        </button>
      </div>
    </aside>
  );
}
