import { useState } from "react";
import Selector from "./components/Selector";
import Chat from "./components/Chat";

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [strategy, setStrategy] = useState<string>("");

  if (!sessionId) {
    return (
      <Selector
        onSelect={(id, strat) => {
          setSessionId(id);
          setStrategy(strat);
        }}
      />
    );
  }

  return (
    <Chat
      sessionId={sessionId}
      strategy={strategy}
      onBack={() => setSessionId(null)}
    />
  );
}
