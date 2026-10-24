import { useEffect } from 'react';
import { useStore } from '../state/store';

const WS_URL = import.meta.env.VITE_WS_URL ?? `ws://${window.location.hostname || 'localhost'}:8000/ws`;
/** Same server over HTTP: the stop button uses it when the browser's WebSocket is down or half-open. */
export const API_URL = WS_URL.replace(/^ws/, 'http').replace(/\/ws$/, '');

/**
 * Only the newest frame is parsed: if the tab falls behind (background tab, heavy GPU
 * frame), stale frames are dropped instead of replayed, so the scene never lags.
 */
export function useSimSocket() {
  useEffect(() => {
    const { setSend, setConnected } = useStore.getState();
    let ws: WebSocket | null = null;
    let closed = false;
    let retry: number | undefined;
    let pending: string | null = null;
    let scheduled = false;
    let staticsAskedAt = 0;
    // MessageChannel tasks are not subject to background-tab timer throttling.
    const channel = new MessageChannel();
    channel.port1.onmessage = () => flush();
    const schedule = () => channel.port2.postMessage(0);

    const flush = () => {
      scheduled = false;
      const raw = pending;
      pending = null;
      if (!raw) return;
      try {
        useStore.getState().applyMessage(JSON.parse(raw));
      } catch {
        return;
      }
      const s = useStore.getState();
      const missing = s.mode === 'single' && s.state && (!s.heights || s.heights.length !== s.state.n_beds * s.state.n_plants);
      if (missing && performance.now() - staticsAskedAt > 1000) {
        staticsAskedAt = performance.now();
        s.send?.({ cmd: 'statics' });
      }
    };

    const connect = () => {
      if (closed) return;
      ws = new WebSocket(WS_URL);
      ws.onopen = () => {
        setConnected(true);
        const socket = ws;
        setSend((msg) => {
          if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(msg));
        });
      };
      ws.onmessage = (ev) => {
        const data = String(ev.data);
        if (data.includes('"mode": "export"') || data.includes('"mode":"export"') || data.includes('"heights"')) {
          if (pending) flush();
          pending = data;
          flush();
          return;
        }
        pending = data;
        if (!scheduled) {
          scheduled = true;
          schedule();
        }
      };
      ws.onclose = () => {
        setConnected(false);
        setSend(null);
        if (!closed) retry = window.setTimeout(connect, 1500);
      };
      ws.onerror = () => ws?.close();
    };

    connect();
    return () => {
      closed = true;
      if (retry) window.clearTimeout(retry);
      channel.port1.close();
      ws?.close();
    };
  }, []);
}
