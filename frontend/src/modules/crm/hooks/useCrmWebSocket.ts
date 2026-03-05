"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { CrmEvent } from "@/types/crm";

const WS_BASE =
  process.env.NEXT_PUBLIC_GATEWAY_WS_URL || "ws://localhost:8766";

export function useCrmWebSocket() {
  const [events, setEvents] = useState<CrmEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const retryCountRef = useRef(0);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_BASE}/api/v1/ws/crm-events`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      retryCountRef.current = 0;
    };

    ws.onmessage = (msg) => {
      try {
        const event: CrmEvent = JSON.parse(msg.data);
        setEvents((prev) => [event, ...prev].slice(0, 100));
      } catch {
        /* ignore malformed frames */
      }
    };

    ws.onclose = () => {
      setConnected(false);
      const backoff = Math.min(
        1000 * Math.pow(2, retryCountRef.current),
        30000,
      );
      retryCountRef.current += 1;
      reconnectTimer.current = setTimeout(connect, backoff);
    };

    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const clearEvents = useCallback(() => setEvents([]), []);

  return { events, connected, clearEvents };
}
