import { useStore } from '../state/store';
import { actions } from './actions';

/** Fixed label shown only in recording mode (the top bar carries it otherwise). */
export function SimLabel() {
  const state = useStore((s) => s.state);
  const mode = useStore((s) => s.mode);
  const recordMode = useStore((s) => s.recordMode);
  if (!recordMode) return null;
  return (
    <div className="rec-label">
      <span className="sim-badge">SIMULACIÓN</span>
      {mode !== 'compare' && state && (
        <span className="rec-title">
          <b>{state.alternative}</b> {state.alternative_name}
        </span>
      )}
      {state && (
        <span className="rec-clock">
          Día {state.day}, {state.clock}
        </span>
      )}
      <button type="button" className="rec-exit" onClick={() => actions.record(false)}>
        Salir (Esc)
      </button>
    </div>
  );
}
