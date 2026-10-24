import { useEffect } from 'react';
import { useTeleop } from './net/teleop';
import { useSimSocket } from './net/ws';
import { RobotCam } from './robot/RobotCam';
import { RobotTag } from './robot/RobotTag';
import { FieldCanvas } from './scene/Field';
import { useStore } from './state/store';
import { actions, installHotkeys } from './ui/actions';
import { CompareGrid } from './ui/CompareGrid';
import { ConfirmDialog, HelpOverlay } from './ui/Dialogs';
import { RealRobotBar, StopFab } from './ui/RealRobot';
import { RobotPanel } from './ui/RobotPanel';
import { SimLabel } from './ui/SimLabel';
import { StatsPanel } from './ui/StatsPanel';
import { Toasts } from './ui/Toasts';
import { TopBar } from './ui/TopBar';
import './App.css';

function ManualHint() {
  const manual = useStore((s) => s.manual);
  const recordMode = useStore((s) => s.recordMode);
  const real = useStore((s) => !!s.realRobot?.connected);
  const realShown = useStore((s) => !!s.realRobot?.ever_connected);
  if (!manual || recordMode) return null;
  return (
    <div className={`manual-hint ${realShown ? 'above-real' : ''}`} role="note">
      <kbd>W</kbd>
      <kbd>A</kbd>
      <kbd>S</kbd>
      <kbd>D</kbd> conducir
      <span className="sep" />
      <kbd>Shift</kbd> rápido
      <span className="sep" />
      <kbd>E</kbd> inspeccionar
      <span className="sep" />
      <kbd>M</kbd> volver a automático
      {real && (
        <>
          <span className="sep" />
          <kbd>X</kbd> parar D1
        </>
      )}
    </div>
  );
}

function Offline() {
  const connected = useStore((s) => s.connected);
  const state = useStore((s) => s.state);
  if (connected && state) return null;
  return (
    <div className="offline" role="alert">
      <h2>{state ? 'Se perdió la conexión con el motor' : 'Conectando con el motor de simulación'}</h2>
      <p>
        Reintentando cada 1,5 s. Si no arranca, inicia el servidor: <code>cd sim-core && uvicorn server:app --reload</code>
      </p>
    </div>
  );
}

export default function App() {
  useSimSocket();
  useTeleop();
  const mode = useStore((s) => s.mode);
  const recordMode = useStore((s) => s.recordMode);
  const realShown = useStore((s) => !!s.realRobot?.ever_connected);

  useEffect(() => {
    installHotkeys();
    const params = new URLSearchParams(window.location.search);
    if (params.get('record') === '1') actions.record(true);
    if (params.get('compare') !== '1') return;
    const t = window.setInterval(() => {
      if (useStore.getState().send) {
        useStore.getState().send?.({ cmd: 'compare', value: true, alternatives: ['F', 'A', 'C', 'REF'] });
        window.clearInterval(t);
      }
    }, 200);
    return () => window.clearInterval(t);
  }, []);

  return (
    <div className={`app ${recordMode ? 'is-record' : ''} ${realShown ? 'has-real' : ''}`}>
      {mode === 'compare' ? <CompareGrid /> : <FieldCanvas />}
      <RobotTag />
      <RobotCam />
      {!recordMode && (
        <>
          <TopBar />
          {mode !== 'compare' && <StatsPanel />}
          {mode !== 'compare' && <RobotPanel />}
          <Toasts />
          <ManualHint />
          <HelpOverlay />
        </>
      )}
      <RealRobotBar />
      <StopFab />
      <ConfirmDialog />
      <SimLabel />
      <Offline />
    </div>
  );
}
