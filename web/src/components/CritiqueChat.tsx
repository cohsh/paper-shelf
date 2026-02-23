import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { sendChatMessage } from "../api/client";
import type { ChatMessage } from "../types/paper";

interface Props {
  paperId: string;
}

export default function CritiqueChat({ paperId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = { role: "user", content: text };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput("");
    setLoading(true);

    try {
      const { reply } = await sendChatMessage(paperId, text, messages);
      setMessages([...updatedMessages, { role: "assistant", content: reply }]);
    } catch (e) {
      setMessages([
        ...updatedMessages,
        { role: "assistant", content: `Error: ${e}` },
      ]);
    } finally {
      setLoading(false);
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-container">
      <h3 style={{ marginBottom: 12 }}>Dialogue</h3>

      {messages.length === 0 && (
        <p
          style={{
            color: "var(--color-text-secondary)",
            fontSize: 14,
            marginBottom: 12,
          }}
        >
          Ask questions about this paper to deepen your understanding.
        </p>
      )}

      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={
              msg.role === "user"
                ? "chat-message chat-message-user"
                : "chat-message chat-message-assistant"
            }
          >
            <div className="chat-message-role">
              {msg.role === "user" ? "You" : "Critique"}
            </div>
            <div className="chat-message-content">
              {msg.role === "assistant" ? (
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              ) : (
                msg.content
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="chat-message chat-message-assistant">
            <div className="chat-message-role">Critique</div>
            <div
              className="chat-message-content"
              style={{ color: "var(--color-text-secondary)" }}
            >
              Thinking...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-row">
        <textarea
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about this paper..."
          rows={2}
          disabled={loading}
        />
        <button
          className="btn btn-primary"
          onClick={handleSend}
          disabled={loading || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
}
