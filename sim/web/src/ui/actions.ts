import { API_URL } from '../net/ws';
import { requestInicio, requestRecenter } from '../robot/twin';
import { useStore, type CameraMode } from '../state/store';
import { useRutaParams } from './ruta';

const send = (msg: Record<string, unknown>) => useStore.getState().send?.(msg);

export const ALTERNATIVES = [
  { code: 'F', name: 'Red fija + D1', note: 'Propuesta: el riesgo decide qué pasillo revisar primero' },
  { code: 'A', name: 'D1 Ultra con mástil', note: 'Ve todo el arbusto, pero el mástil roza el follaje' },
  { code: 'B', name: 'Red fija de sensores', note: 'Sin robot: el riesgo activa una revisión humana' },
  { code: 'C', name: 'Cámara en la aspersora', note: 'Solo los días de aspersión' },
  { code: 'D', name: 'Humanoide', note: 'Más alto y lento, puede caerse' },
  { code: 'E', name: 'Ruedas y torso alto', note: 'Rígido: no cabe donde el follaje se desborda' },
  { code: 'REF', name: 'Solo monitoreo humano', note: 'Operario de 6 a 14 h, registro a mano' },
];

export const SPEEDS = [1, 10, 50];

/** Ask before anything that throws away the current run. */
function guarded(title: string, body: string, ok: string, run: () => void) {
  const s = useStore.getState().state;
  const progressed = !!s && (s.day > 0 || s.robot.patrol_active || (s.kpis?.captures ?? 0) > 0);
  if (!progressed) {
    run();
    return;
  }
  useStore.setState({ confirm: { title, body, ok, run } });
}

const resetNote = (seed?: number) =>
  `Se pierde el avance de esta corrida. La semilla ${seed ?? ''} se mantiene, así que el brote será el mismo.`;

export const actions = {
  togglePlay() {
    const playing = !useStore.getState().playing;
    useStore.setState({ playing });
    send({ cmd: playing ? 'play' : 'pause' });
  },
  setSpeed(v: number) {
    useStore.setState({ speed: v });
    send({ cmd: 'speed', value: v });
  },
  skip() {
    send({ cmd: 'skip' });
  },
  setAlternative(code: string) {
    const seed = useStore.getState().state?.seed;
    const name = ALTERNATIVES.find((a) => a.code === code)?.name ?? code;
    guarded(`Cambiar a ${name}`, resetNote(seed), 'Cambiar y reiniciar', () => {
      useStore.setState({ manual: false });
      send({ cmd: 'alternative', value: code });
    });
  },
  setSeed(v: number) {
    guarded(
      `Usar la semilla ${v}`,
      'Una semilla distinta genera otro brote y otro follaje. Se pierde el avance de esta corrida.',
      'Cambiar semilla',
      () => send({ cmd: 'seed', value: v }),
    );
  },
  reset() {
    const seed = useStore.getState().state?.seed;
    guarded('Reiniciar la corrida', resetNote(seed), 'Reiniciar', () => send({ cmd: 'reset' }));
  },
  setMast(v: boolean) {
    const seed = useStore.getState().state?.seed;
    guarded(
      v ? 'Montar el mástil de producción' : 'Quitar el mástil',
      `${v ? 'La cámara sube a 1,35 m y ve todo el arbusto, pero el mástil roza el follaje desbordado.' : 'La cámara vuelve a 0,3 m.'} ${resetNote(seed)}`,
      v ? 'Montar y reiniciar' : 'Quitar y reiniciar',
      () => send({ cmd: 'mast', value: v }),
    );
  },
  toggleManual() {
    const s = useStore.getState();
    if (s.mode === 'compare' || !s.state?.robot.active) return;
    const manual = !s.manual;
    useStore.setState({ manual, cameraMode: manual ? 'follow' : s.cameraMode, robotTab: 'sensores', robotOpen: true });
    send({ cmd: 'manual', value: manual });
  },
  inspect() {
    send({ cmd: 'inspect' });
  },
  exportCsv() {
    send({ cmd: 'export' });
  },
  cycleCamera() {
    const order: CameraMode[] = ['orbit', 'follow', 'side', 'cinematic'];
    const cur = useStore.getState().cameraMode;
    useStore.setState({ cameraMode: order[(order.indexOf(cur) + 1) % order.length] });
  },
  compare(on: boolean) {
    guarded(
      on ? 'Comparar 4 alternativas' : 'Salir de la comparación',
      on
        ? 'Corre F, A, C y la referencia con la misma semilla, en paralelo. Se pierde el avance de esta corrida.'
        : 'Vuelve a una sola alternativa desde el día 0.',
      on ? 'Comparar' : 'Salir',
      () => {
        useStore.setState({ manual: false });
        send({ cmd: 'compare', value: on, alternatives: ['F', 'A', 'C', 'REF'] });
      },
    );
  },
  /** Buttons of the real D1: stand, lie, estop, resume (relayed by the server to the bridge). */
  robotAction(name: 'stand' | 'lie' | 'estop' | 'resume') {
    send({ cmd: 'robot_action', name });
    // The stop must not depend on the browser's WebSocket (closed, half-open, mid-reconnect): also HTTP.
    if (name === 'estop' || !useStore.getState().send) {
      fetch(`${API_URL}/api/robot/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
        keepalive: true,
      }).catch(() => undefined);
    }
  },
  /** Ruta real: draws the scaled Auto route in the scene without moving the robot. */
  rutaDryrun() {
    const { escala, largo, deriva, escaneos } = useRutaParams.getState();
    send({ cmd: 'ruta', op: 'dryrun', escala, largo_max_m: largo, deriva_max_m: deriva, escaneos });
  },
  /** Ruta real: the D1 follows the Auto route from where it stands now (enters Manual if needed). */
  rutaStart() {
    const s = useStore.getState();
    if (!s.manual) actions.toggleManual();
    const { escala, largo, deriva, escaneos } = useRutaParams.getState();
    send({ cmd: 'ruta', op: 'start', escala, largo_max_m: largo, deriva_max_m: deriva, escaneos });
  },
  rutaCancel() {
    send({ cmd: 'ruta', op: 'cancel' });
  },
  recenterTwin() {
    requestRecenter();
  },
  /** Bloque que recorre el robot (1 = naves 1–2, 2 = naves 3–4): la patrulla y la Ruta real usan solo ese bloque. */
  setBloque(b: number) {
    send({ cmd: 'bloque', value: b });
    useStore.setState({ bloque: b });
  },
  /** Vuelve el robot de la escena al inicio del bloque elegido (y re-ancla el gemelo del D1 ahí). */
  volverInicio() {
    const s = useStore.getState();
    const b = s.state?.layout?.blocks?.find((x) => x.id === s.bloque);
    if (!b) return;
    const [x, z, heading] = b.start;
    requestInicio({ x, z, heading });
    send({ cmd: 'inicio' });
  },
  record(on: boolean) {
    useStore.setState({ recordMode: on, cameraMode: on ? 'cinematic' : 'orbit' });
    if (on) actions.setSpeed(10);
  },
};

let hotkeysInstalled = false;
export function installHotkeys() {
  if (hotkeysInstalled) return;
  hotkeysInstalled = true;
  window.addEventListener('keydown', (e) => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const s = useStore.getState();
    // Stopping the real D1 beats everything else, dialogs and focused fields included: after clicking a
    // layer checkbox the focus stays on the <input> and X used to do nothing. The only text-like field
    // is the numeric seed, where an "x" means nothing anyway.
    if (e.key.toLowerCase() === 'x' && (s.realRobot?.connected || !s.connected)) {
      e.preventDefault();
      actions.robotAction('estop');
      return;
    }
    const t = e.target as HTMLElement | null;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'SELECT' || t.tagName === 'TEXTAREA')) return;
    if (s.confirm) {
      if (e.key === 'Escape') s.set({ confirm: null });
      return;
    }
    switch (e.key.toLowerCase()) {
      case ' ':
      case 'p':
        e.preventDefault();
        actions.togglePlay();
        break;
      case 'e':
        if (s.manual) actions.inspect();
        break;
      case 'm':
        actions.toggleManual();
        break;
      case 'c':
        actions.cycleCamera();
        break;
      case 'g':
        s.set({ godMode: !s.godMode });
        break;
      case 'h':
        s.set({ showHeatmap: !s.showHeatmap });
        break;
      case 'v':
        s.set({ showSensors: !s.showSensors });
        break;
      case '?':
        s.set({ helpOpen: !s.helpOpen });
        break;
      case 'escape':
        if (s.helpOpen) s.set({ helpOpen: false });
        else if (s.recordMode) actions.record(false);
        break;
    }
  });
}
