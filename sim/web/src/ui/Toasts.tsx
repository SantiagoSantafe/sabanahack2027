import { useEffect } from 'react';
import { useStore, type Toast } from '../state/store';
import { fmt } from './format';
import { IconClose } from './icons';

const LIFE_MS: Record<string, number> = { aisle_complete: 3500, sync: 4000, patrol_complete: 12000, real_detection: 9000 };
const DEFAULT_LIFE = 6000;

const GROUP_TEXT: Record<string, (n: number) => string> = {
  alert: (n) => `${n} alertas nuevas en este recorrido`,
  aisle_complete: (n) => `${n} pasillos completos`,
};

function ToastItem({ t }: { t: Toast }) {
  const dismiss = useStore((s) => s.dismissToast);
  const set = useStore((s) => s.set);
  useEffect(() => {
    const id = window.setTimeout(() => dismiss(t.id), LIFE_MS[t.type] ?? DEFAULT_LIFE);
    return () => window.clearTimeout(id);
  }, [t.id, t.born, t.type, dismiss]);

  if (t.big && t.summary) {
    const s = t.summary;
    return (
      <div className="toast toast-big" role="status">
        <button type="button" className="toast-x" onClick={() => dismiss(t.id)} aria-label="Cerrar resumen">
          <IconClose />
        </button>
        <h3>Recorrido completo</h3>
        <p className="toast-sub">
          Bloque {useStore.getState().bloque}, día {s.day} a las {s.clock}
        </p>
        <div className="toast-grid">
          <div>
            <b>{fmt(s.minutes, 0)}</b>
            <span>min (operario: {fmt(s.human_minutes, 0)})</span>
          </div>
          <div>
            <b>{fmt(s.plants)}</b>
            <span>capturas</span>
          </div>
          <div className={s.alerts ? 'is-warn' : ''}>
            <b>{fmt(s.alerts)}</b>
            <span>alertas</span>
          </div>
          <div>
            <b>{fmt(s.distance_m, 0)}</b>
            <span>metros</span>
          </div>
          <div>
            <b>{fmt(s.careful)}</b>
            <span>pasos con cuidado</span>
          </div>
          <div className={s.skipped ? 'is-warn' : ''}>
            <b>{fmt(s.skipped)}</b>
            <span>sin revisar</span>
          </div>
        </div>
        <p className="toast-foot">
          {s.alert_beds.length
            ? `Revisar ${s.alert_beds.slice(0, 4).join(', ')}${s.alert_beds.length > 4 ? ` y ${s.alert_beds.length - 4} más` : ''}. Los datos se enviaron al llegar a la base.`
            : 'Ninguna planta sospechosa en este recorrido.'}
        </p>
        <button
          type="button"
          className="btn-secondary"
          onClick={() => {
            set({ statsOpen: true, statsTab: 'resumen' });
            dismiss(t.id);
          }}
        >
          Ver en el panel del bloque
        </button>
      </div>
    );
  }

  const text = t.count > 1 && GROUP_TEXT[t.type] ? GROUP_TEXT[t.type](t.count) : t.text;
  return (
    <div className={`toast lvl-${t.level}`} role="status">
      <time>{t.clock}</time>
      <span>
        {text}
        {t.count > 1 && GROUP_TEXT[t.type] && <small>Último: {t.text}</small>}
      </span>
      <button type="button" className="toast-x-inline" onClick={() => dismiss(t.id)} aria-label="Cerrar aviso">
        <IconClose size={12} />
      </button>
    </div>
  );
}

export function Toasts() {
  const toasts = useStore((s) => s.toasts);
  const recordMode = useStore((s) => s.recordMode);
  if (recordMode) return null;
  return (
    <div className="toasts" aria-live="polite">
      {toasts.map((t) => (
        <ToastItem key={t.id} t={t} />
      ))}
    </div>
  );
}
