import { useEffect, useRef, useState } from "react";
import { fetchMessages, sendMessage, type ChatEvent, type Message } from "../api";
import styles from "./Chat.module.css";

interface Props {
  sessionId: string;
  strategy: string;
  onBack: () => void;
}

interface DisplayMessage {
  role: "user" | "assistant";
  type: "chat_message" | "saved_memory";
  content: string;
}

export default function Chat({ sessionId, strategy, onBack }: Props) {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchMessages(sessionId).then((data) => {
      setMessages(
        data.messages.map((m: Message) => ({
          role: m.role,
          type: m.message_type,
          content: m.content,
        }))
      );
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
      { role: "user", type: "chat_message", content: text },
    ]);

    try {
      const data = await sendMessage(sessionId, text);
      const newMessages: DisplayMessage[] = data.events.map((e: ChatEvent) => ({
        role: "assistant" as const,
        type: e.type,
        content: e.content,
      }));
      setMessages((prev) => [...prev, ...newMessages]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          type: "chat_message",
          content: `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
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
              msg.role === "user"
                ? styles.user
                : msg.type === "saved_memory"
                ? styles.savedMemory
                : styles.assistant
            }`}
          >
            {msg.type === "saved_memory" && (
              <span className={styles.memoryLabel}>Memory saved</span>
            )}
            {msg.content}
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
