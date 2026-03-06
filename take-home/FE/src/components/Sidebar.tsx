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
  const [strategy, setStrategy] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchStrategies().then((list) => {
      setStrategies(list);
      if (list.length > 0) setStrategy(list[0].key);
    });
  }, []);

  useEffect(() => {
    fetchSessions().then(setSessions);
  }, [refreshKey]);

  const handleNew = async () => {
    if (!strategy || creating) return;
    setCreating(true);
    try {
      const { id } = await createSession(strategy);
      onNewSession(id, strategy);
      fetchSessions().then(setSessions);
    } finally {
      setCreating(false);
    }
  };

  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>Memory Agent</div>
      <div className={styles.newChat}>
        <select
          className={styles.strategySelect}
          value={strategy}
          onChange={(e) => setStrategy(e.target.value)}
          disabled={creating}
        >
          {strategies.map((s) => (
            <option key={s.key} value={s.key}>
              {s.name}
            </option>
          ))}
        </select>
        <button
          className={styles.newBtn}
          onClick={handleNew}
          disabled={creating}
        >
          + New chat
        </button>
      </div>

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
