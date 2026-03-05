"use client";

import { useState } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";

function getMessageText(m: { parts?: Array<{ type?: string; text?: string }> }) {
  if (!m.parts) return "";
  return m.parts
    .filter((p): p is { type: string; text: string } => p.type === "text")
    .map((p) => p.text)
    .join("");
}

export function OrchestratorChat() {
  const [input, setInput] = useState("");
  const { messages, sendMessage, status } = useChat({
    transport: new DefaultChatTransport({
      api: "/api/v1/orchestrator/chat",
    }),
  });

  const isLoading = status === "submitted" || status === "streaming";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    sendMessage({ text });
    setInput("");
  };

  return (
    <div className="flex flex-col h-full min-h-[400px] bg-[var(--color-surface)] rounded-lg border border-[var(--color-border)]">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`rounded-lg p-3 max-w-[80%] ${
              m.role === "user"
                ? "ml-auto bg-[var(--color-accent)]/20"
                : "bg-[var(--color-surface-alt)]"
            }`}
          >
            <p className="text-sm text-[var(--color-text)]">
              {getMessageText(m)}
            </p>
          </div>
        ))}
        {isLoading && (
          <div className="text-[var(--color-text-muted)] text-sm animate-pulse">
            Thinking...
          </div>
        )}
      </div>
      <form
        onSubmit={handleSubmit}
        className="p-3 border-t border-[var(--color-border)] flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the orchestrator..."
          className="flex-1 bg-[var(--color-bg)] text-[var(--color-text)] rounded px-3 py-2 text-sm border border-[var(--color-border)] focus:border-[var(--color-accent)] outline-none"
        />
        <button
          type="submit"
          className="px-4 py-2 bg-[var(--color-accent)] text-white rounded text-sm hover:opacity-90"
        >
          Send
        </button>
      </form>
    </div>
  );
}
