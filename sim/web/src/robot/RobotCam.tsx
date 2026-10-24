import { useEffect, useState } from 'react';
import { useStore } from '../state/store';

/** Base URL of the camera panel (panel_demo.py). Set VITE_PANEL_URL when the panel runs on another host. */
const PANEL_URL = (import.meta.env.VITE_PANEL_URL ?? 'http://localhost:8092').replace(/\/$/, '');

const CLASS_ES: Record<string, string> = { sana: 'sana', oidio: 'oídio', alternaria: 'alternaria', heliothis: 'Heliothis', sin_hoja: 'sin hoja' };
const RETRY_MS = 3000;

/**
 * Thumbnail of the D1's camera floating above the robot (positioned each frame by RobotTagAnchor, like the tag).
 * Plain DOM outside the canvas. If the panel does not answer it says "sin video" and never blocks anything.
 */
export function RobotCam() {
  const robot = useStore((s) => s.state?.robot);
  const mode = useStore((s) => s.mode);
  const recordMode = useStore((s) => s.recordMode);
  const panel = useStore((s) => s.realRobot?.safety?.panel ?? null);
  const [big, setBig] = useState(false);
  const [failed, setFailed] = useState(false);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (!failed) return;
    const id = window.setTimeout(() => {
      setFailed(false);
      setNonce((n) => n + 1);
    }, RETRY_MS);
    return () => window.clearTimeout(id);
  }, [failed]);

  // An MJPEG <img> never fires onError when the server dies mid-stream (it freezes on the last frame):
  // probe the panel every 2 s (no-cors: the answer is opaque, but a dead server rejects).
  useEffect(() => {
    const probe = () => {
      fetch(`${PANEL_URL}/api/estado`, { mode: 'no-cors', cache: 'no-store' }).catch(() => setFailed(true));
    };
    const id = window.setInterval(probe, 2000);
    return () => window.clearInterval(id);
  }, []);

  if (!robot?.active || mode === 'compare' || recordMode) return null;

  const videoOk = !failed && (panel ? panel.fresh && panel.cam_ok : true);
  const clase = panel?.clase ?? null;
  const noLeaf = clase === 'sin_hoja';
  const alert = videoOk && !!panel?.sospecha;
  let tone = 'is-ok';
  let text = clase ? (CLASS_ES[clase] ?? clase) : 'cámara D1';
  if (!videoOk) {
    tone = 'is-off';
    text = 'sin video';
  } else if (alert) {
    tone = 'is-alert';
    text = `${CLASS_ES[clase ?? ''] ?? clase ?? 'alerta'} · alerta`;
  } else if (noLeaf) {
    tone = 'is-off';
  }
  const conf = videoOk && panel?.confianza != null && !noLeaf ? ` ${Math.round(panel.confianza * 100)} %` : '';

  return (
    <div id="robot-cam" className={`robot-cam ${tone} ${big ? 'is-big' : ''}`}>
      <button
        type="button"
        className="robot-cam-btn"
        onClick={() => setBig((b) => !b)}
        aria-label={big ? 'Achicar la cámara del D1' : 'Agrandar la cámara del D1'}
        title={big ? 'Clic: achicar' : 'Clic: agrandar'}
      >
        {!failed ? (
          <img
            key={nonce}
            src={`${PANEL_URL}/stream.mjpg?n=${nonce}`}
            alt=""
            draggable={false}
            onError={() => setFailed(true)}
            style={{ visibility: videoOk ? 'visible' : 'hidden' }}
          />
        ) : null}
        {!videoOk && <span className="robot-cam-off">sin video</span>}
        <span className="robot-cam-label">
          {text}
          {conf}
        </span>
      </button>
    </div>
  );
}
