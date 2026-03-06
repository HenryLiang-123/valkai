import { useEffect, useState } from "react";
import { fetchStrategies, createSession, type Strategy } from "../api";
import styles from "./Selector.module.css";

interface Props {
  onSelect: (sessionId: string, strategy: string) => void;
}

export default function Selector({ onSelect }: Props) {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchStrategies().then(setStrategies);
  }, []);

  const handleClick = async (key: string) => {
    setLoading(key);
    const { id } = await createSession(key);
    onSelect(id, key);
  };

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Memory Agent</h1>
      <p className={styles.subtitle}>Choose a memory strategy to start chatting.</p>
      <div className={styles.grid}>
        {strategies.map((s) => (
          <button
            key={s.key}
            className={styles.card}
            onClick={() => handleClick(s.key)}
            disabled={loading !== null}
          >
            <h2>{s.name}</h2>
            <p>{s.description}</p>
            {loading === s.key && <span className={styles.spinner}>...</span>}
          </button>
        ))}
      </div>
    </div>
  );
}
