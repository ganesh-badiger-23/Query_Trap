import { useState, useEffect, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { TelemetryEvent, TelemetryCounts } from '../types';
import { fetchTelemetryEvents, getBaseUrl, SOC_DEFAULT_TOKEN } from '../services/api';

export function useSocketTelemetry(authToken: string = SOC_DEFAULT_TOKEN) {
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [counts, setCounts] = useState<TelemetryCounts>({ safe: 0, suspicious: 0, honeypot: 0 });
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string>('Connecting to telemetry stream…');
  const socketRef = useRef<Socket | null>(null);

  // Load durable historical events from SQLite on mount
  useEffect(() => {
    let isMounted = true;
    fetchTelemetryEvents(getBaseUrl('sentinel'), authToken)
      .then((data) => {
        if (!isMounted) return;
        setEvents(data.events || []);
        if (data.counts) {
          setCounts(data.counts);
        }
      })
      .catch((err) => {
        console.warn('Initial event history fetch error:', err);
      });

    return () => {
      isMounted = false;
    };
  }, [authToken]);

  // Establish persistent authenticated Socket.IO connection
  useEffect(() => {
    const sentinelHost = getBaseUrl('sentinel') || 'http://127.0.0.1:5100';

    const socket = io(sentinelHost, {
      transports: ['websocket', 'polling'],
      auth: { token: authToken },
      query: { token: authToken },
      reconnectionAttempts: 10,
      reconnectionDelay: 1500,
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      setIsConnected(true);
      setStatusMessage('Listening for incoming telemetry events');
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
      setStatusMessage('Reconnecting to telemetry stream…');
    });

    socket.on('connect_error', (err) => {
      setIsConnected(false);
      setStatusMessage(`Telemetry stream auth error: ${err.message}`);
    });

    socket.on('telemetry', (payload: { event: TelemetryEvent; counts: TelemetryCounts }) => {
      if (payload && payload.event) {
        setEvents((prev) => {
          // Avoid duplicate event insertions
          if (prev.some((e) => e.id === payload.event.id)) {
            return prev;
          }
          return [payload.event, ...prev].slice(0, 1000); // Cap at 1000 in memory
        });
      }
      if (payload && payload.counts) {
        setCounts(payload.counts);
      }
    });

    return () => {
      socket.disconnect();
    };
  }, [authToken]);

  const clearEvents = useCallback(() => {
    setEvents([]);
    setCounts({ safe: 0, suspicious: 0, honeypot: 0 });
  }, []);

  return {
    events,
    counts,
    isConnected,
    statusMessage,
    clearEvents,
    setEvents,
  };
}
