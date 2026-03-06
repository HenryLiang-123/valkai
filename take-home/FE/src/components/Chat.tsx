import { useEffect, useRef, useState } from "react";
import { fetchMessages, sendMessage, type ChatEvent } from "../api";
import styles from "./Chat.module.css";

interface Props {
  sessionId: string;
  strategy: string;
  onBack: () => void;
}

export default function Chat({ sessionId, strategy, onBack }: Props) {
  const [messages, setMessages] = useState<ChatEvent[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchMessages(sessionId).then((data) => {
      setMessages(data.messages);
    });
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setInput("");
    setSending(true);
    setMessages((prev) => [
      ...prev,
      { type: "chat_message", role: "user", text },
    ]);

    try {
      const data = await sendMessage(sessionId, text);
      setMessages((prev) => [...prev, ...data.events]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          type: "chat_message" as const,
          role: "assistant" as const,
          text: `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <button className={styles.back} onClick={onBack}>
          &larr; Back
        </button>
        <h1 className={styles.title}>Memory Agent</h1>
        <span className={styles.badge}>{strategy}</span>
      </header>

      <div className={styles.chatArea}>
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`${styles.msg} ${
              msg.type === "tool_use"
                ? styles.savedMemory
                : msg.role === "user"
                ? styles.user
                : styles.assistant
            }`}
          >
            {msg.type === "tool_use" ? (
              <span className={styles.memoryLabel}>Tool: {msg.tool_name}</span>
            ) : (
              msg.text
            )}
          </div>
        ))}
        {sending && (
          <div className={`${styles.msg} ${styles.loading}`}>Thinking...</div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className={styles.inputArea}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="Send a message..."
          disabled={sending}
          autoFocus
        />
        <button onClick={handleSend} disabled={sending || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
