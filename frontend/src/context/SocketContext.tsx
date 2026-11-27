import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { API_BASE, useAuth } from './AuthContext';

export interface TicketSocketEvent {
  type: 'ticket_created' | 'ticket_updated' | 'ticket_deleted' | string;
  ticket_id: number;
  status?: string;
}

type SocketListener = (event: TicketSocketEvent) => void;

interface SocketContextType {
  connected: boolean;
  lastEvent: TicketSocketEvent | null;
  subscribe: (listener: SocketListener) => () => void;
}

const SocketContext = createContext<SocketContextType | undefined>(undefined);

function buildWebSocketUrl(apiBase: string, token: string): string {
  const normalizedBase = apiBase.replace(/\/+$/, '');
  let wsBase: string;
  if (normalizedBase.startsWith('https://')) {
    wsBase = `wss://${normalizedBase.slice('https://'.length)}`;
  } else if (normalizedBase.startsWith('http://')) {
    wsBase = `ws://${normalizedBase.slice('http://'.length)}`;
  } else {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const prefix = normalizedBase.startsWith('/') ? normalizedBase : `/${normalizedBase}`;
    wsBase = `${protocol}//${window.location.host}${prefix}`;
  }
  return `${wsBase}/ws/tickets?token=${encodeURIComponent(token)}`;
}

export const SocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token } = useAuth();
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<TicketSocketEvent | null>(null);
  const listenersRef = useRef<Set<SocketListener>>(new Set());

  const subscribe = useCallback((listener: SocketListener) => {
    listenersRef.current.add(listener);
    return () => {
      listenersRef.current.delete(listener);
    };
  }, []);

  useEffect(() => {
    if (!token) {
      setConnected(false);
      return;
    }

    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let pingTimer: ReturnType<typeof setInterval> | null = null;
    let attempt = 0;
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;

      const wsUrl = buildWebSocketUrl(API_BASE, token);
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (cancelled) return;
        attempt = 0;
        setConnected(true);
        if (pingTimer) clearInterval(pingTimer);
        pingTimer = setInterval(() => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 25000);
      };

      ws.onmessage = (msgEvent) => {
        if (msgEvent.data === 'pong') return;
        try {
          const parsed: TicketSocketEvent = JSON.parse(msgEvent.data);
          setLastEvent(parsed);
          listenersRef.current.forEach((listener) => listener(parsed));
        } catch {
          // Ignore non-JSON frames
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (pingTimer) {
          clearInterval(pingTimer);
          pingTimer = null;
        }
        if (!cancelled) {
          const delayMs = Math.min(30000, 2000 * Math.pow(2, attempt));
          attempt += 1;
          reconnectTimer = setTimeout(connect, delayMs);
        }
      };

      ws.onerror = () => {
        ws?.close();
      };
    };

    connect();

    return () => {
      cancelled = true;
      setConnected(false);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (pingTimer) clearInterval(pingTimer);
      ws?.close();
    };
  }, [token]);

  return (
    <SocketContext.Provider value={{ connected, lastEvent, subscribe }}>
      {children}
    </SocketContext.Provider>
  );
};

export const useSocket = () => {
  const ctx = useContext(SocketContext);
  if (!ctx) {
    throw new Error('useSocket must be used within a SocketProvider');
  }
  return ctx;
};
