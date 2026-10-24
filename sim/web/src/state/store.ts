import { create } from 'zustand';

export type Capture = {
  seq: number;
  bed: number;
  plant: number;
  label: string;
  score: number | null;
  alert: boolean;
  state: number;
};

export type Layout = {
  naves: number;
  beds_per_nave: number;
  nave_width: number;
  nave_x0: number[];
  bed_x: number[];
  bed_w: number;
  aisles: { x: number; left: number; right: number; nave: number }[];
  n_plants: number;
  spacing: number;
  z0: number;
  bed_z0: number;
  bed_z1: number;
  head_s: number;
  head_n: number;
  main_path_w: number;
  north_w: number;
  base: [number, number];
  area_ha: number;
  central?: [number, number] | null; // camino central entre bloques (x0, x1)
  blocks?: { id: number; naves: number[]; x0: number; x1: number; aisles: number[]; start: [number, number, number]; start_label: string }[];
};

export type RobotSnap = {
  x: number;
  z: number;
  heading: number;
  speed: number;
  state: string;
  mode: 'auto' | 'manual';
  battery: number;
  bed_label: string;
  mast: boolean;
  current_aisle: number;
  platform: string;
  active: boolean;
  odometry_m: number;
  busy_s: number;
  target: [number, number] | null;
  patrol_active: boolean;
  aisles_done: number;
  aisles_total: number;
  base: [number, number];
  width_m: number;
  height_m: number;
  rigid: boolean;
  contacts: number;
  careful_passes: number;
  plants_skipped: number;
  patrol_plants: number;
  patrol_alerts: number;
  sensors: {
    frames: number;
    last_capture: Capture | null;
    recent_captures: Capture[];
    last_aruco: { seq: number; aisle: number; beds: number[]; marker_ids: number[] } | null;
    probe: { temp_c: number; rh_pct: number; bed: number; kind: string } | null;
  };
};

export type SimEvent = {
  id: number;
  type: string;
  level: 'info' | 'ok' | 'warn' | 'danger';
  text: string;
  day: number;
  clock: string;
  summary?: PatrolSummary;
  bed?: number;
  plant?: number;
};

export type PatrolSummary = {
  day: number;
  clock: string;
  aisles: number;
  beds: number;
  plants: number;
  alerts: number;
  minutes: number;
  distance_m: number;
  battery_used: number;
  alert_beds: string[];
  contacts: number;
  careful: number;
  skipped: number;
  human_minutes: number;
};

export type Incident = {
  id: number;
  day: number;
  clock: string;
  nave: number;
  cama: number;
  planta: number | null;
  temp_c: number;
  rh_pct: number;
  clase?: string;
  confianza?: number;
  fuente?: string;
  th_fuente?: string;
  synced: boolean;
};

export type Climate = {
  T: number;
  RH: number;
  precip: number;
  precip_day: number;
  T_in: number;
  RH_in: number;
  RH_bed: number[];
  wet_h: number;
  wet_now: boolean;
  vent_on: boolean;
  vent_forgotten: boolean;
  alero_open: boolean;
  tunnel: boolean;
};

export type Kpis = {
  distance_km: number;
  field_hours: number;
  captures: number;
  captures_per_hour: number;
  patrols: number;
  avg_patrol_min: number | null;
  human_minutes_per_block: number;
  block_area_ha: number;
  records: number;
  unsynced: number;
  unsynced_incidents: number;
  contacts: number;
  careful_passes: number;
  plants_skipped: number;
  overflowing_plants: number;
};

export type SimState = {
  run_id: number;
  day: number;
  max_days: number;
  clock: string;
  sim_time_days: number;
  realtime: boolean;
  done: boolean;
  next_patrol: { day: number; clock: string } | null;
  seed: number;
  alternative: string;
  alternative_title: string;
  alternative_name: string;
  sensor_network: boolean;
  decision_threshold: number;
  risk_levels?: { medium: number; high: number };
  weather: Climate;
  weather_source: string;
  risk: { per_disease: Record<string, number>; combined: number; per_bed: number[] };
  plants: string;
  n_beds: number;
  n_plants: number;
  layout: Layout;
  robot: RobotSnap;
  events: SimEvent[];
  last_patrol: PatrolSummary | null;
  last_sync: { day: number; clock: string; records: number; incidents: number } | null;
  connectivity: string;
  incidents: Incident[];
  kpis: Kpis;
  metrics: Record<string, number | null>;
  field: {
    plant_spacing_m: number;
    bed_height_m: number;
    bed_width_m: number;
    pot_diameter_m: number;
    cultivation_mode: string;
    arch_height_m: number;
  };
};

/** Telemetry of the real D1 as relayed by the bridge (contract v1). Odometry is null when the SDK gives none. */
export type Telemetry = {
  t: number | null;
  x: number | null;
  y: number | null;
  yaw: number | null;
  vx: number | null;
  vy: number | null;
  wz: number | null;
  state: string | null;
  sdk_ok: boolean | null;
  battery: number | null;
  last_cmd_age_ms: number | null;
};

export type TruthCounts = {
  hits: number;
  false_alarms: number;
  misses: number;
  true_negatives: number;
  class_match: number;
  leaves: number;
  frames: number;
  current: { truth: string; suspected: boolean } | null;
};

export type RealDetection = {
  t: number;
  label: string;
  label_es: string;
  conf: number;
  p_enfermedad: number | null;
  sospecha: boolean;
  cama: number | null;
  truth_label: string | null;
  incident_no: number | null;
  duplicate: boolean;
  forwarded: boolean;
  where: { nave: number; cama: number; planta: number | null; temp_c: number; rh_pct: number } | null;
};

/** Camera panel heartbeat relayed by sim-core (panel_demo.py --sim-url) and the safety barriers' state. */
export type PanelBeat = {
  cam_ok: boolean;
  clase: string | null;
  confianza: number | null;
  sospecha: boolean | null;
  estable: boolean | null;
  p_hoja: number | null;
  age_s: number | null;
  fresh: boolean;
};

export type SafetyState = {
  config: {
    speed_cap_mps: number;
    geofence: boolean;
    bed_margin_m: number;
    battery_stand_min: number;
    battery_lie_below: number;
    video_guard: string;
    video_loss_s: number;
  };
  geofence_violation: string | null;
  battery_low: boolean;
  battery_critical: boolean;
  link_stale: boolean;
  video_guard_active: boolean;
  video_ok: boolean;
  video_lost_s: number;
  video_block: boolean;
  blocked: string | null;
  trips: Record<string, number>;
  panel: PanelBeat | null;
};

/** Ruta real: the real D1 follows the Auto route (scaled) while the twin follows the D1. */
export type RutaReal = {
  estado: 'inactiva' | 'simulacion' | 'en_marcha' | 'pausa' | 'terminada' | 'cancelada';
  motivo: string;
  tramo: number;
  tramos: number;
  restante_m: number;
  total_m: number;
  deriva_m: number;
  escala: number;
  largo_max_m: number;
  deriva_max_m: number;
  puntos: [number, number][];
  gemelo?: [number, number, number] | null; // pose del gemelo en la escena (x, z, rumbo) mientras la ruta corre
  mirando?: 'izquierda' | 'derecha' | null;
  escaneos_pendientes?: number;
};

/** `real_robot` block of every state message: link with the AgiBot D1 through the bridge. */
export type RealRobot = {
  connected: boolean;
  link_id: number;
  ever_connected: boolean;
  hello: boolean;
  robot: string | null;
  mock: boolean | null;
  limits: { vx_max?: number | null; vy_max?: number | null; wz_max?: number | null } | null;
  since_disconnect_s: number | null;
  telemetry: Telemetry | null;
  telemetry_age_ms: number | null;
  telemetry_stale: boolean;
  latency_ms: number | null;
  clock_offset_suspect: boolean;
  state: string | null;
  estop: boolean;
  hold_s: number;
  hold_s_left: number;
  teleop_active: boolean;
  detections: number;
  incidents: number;
  last_detection: RealDetection | null;
  truth: TruthCounts | null;
  th_note: string;
  safety?: SafetyState;
  ruta?: RutaReal;
};

export type Toast = SimEvent & { born: number; big?: boolean; count: number };
export type CameraMode = 'orbit' | 'follow' | 'side' | 'cinematic';
export type Confirm = { title: string; body: string; ok: string; run: () => void } | null;

/** Pose of the robot as rendered this frame (shared with cameras, avoids React re-renders). */
export const robotRenderPose = { x: 0, z: 0, heading: 0, valid: false };

/** Locally driven pose in manual mode (client-authoritative, synced to the server). */
export const manualPose = { x: 0, z: 0, heading: 0, speed: 0, active: false };

type Statics = { heights: number[] | null; spreadL: number[] | null; spreadR: number[] | null };

type AppStore = Statics & {
  connected: boolean;
  realRobot: RealRobot | null;
  mode: 'single' | 'compare';
  state: SimState | null;
  compareStates: SimState[];
  plantBytes: Uint8Array | null;
  comparePlantBytes: Uint8Array[];
  playing: boolean;
  speed: number;
  manual: boolean;
  bloque: number;
  mastOverride: boolean | null;
  godMode: boolean;
  cameraMode: CameraMode;
  recordMode: boolean;
  showHeatmap: boolean;
  showTunnel: boolean;
  showSensors: boolean;
  showStations: boolean;
  showProdSensors: boolean;
  statsOpen: boolean;
  robotOpen: boolean;
  statsTab: 'resumen' | 'clima' | 'plantas';
  robotTab: 'sensores' | 'registro' | 'datos';
  helpOpen: boolean;
  confirm: Confirm;
  log: SimEvent[];
  toasts: Toast[];
  lastEventId: number;
  runId: number;
  send: ((msg: Record<string, unknown>) => void) | null;
  setSend: (fn: ((msg: Record<string, unknown>) => void) | null) => void;
  applyMessage: (msg: Record<string, unknown>) => void;
  setConnected: (v: boolean) => void;
  dismissToast: (id: number) => void;
  set: (p: Partial<AppStore>) => void;
};

function decodePlants(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function download(filename: string, text: string) {
  const blob = new Blob([text], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Only events that change what the user should do become toasts; the rest go to the log. */
const TOAST_TYPES = new Set([
  'aisle_complete',
  'patrol_complete',
  'alert',
  'failed',
  'stuck',
  'blocked',
  'battery_low',
  'human_review',
  'ventilation',
  'alero',
  'sync',
  'real_link',
  'real_alert',
  'real_detection',
]);
const GROUPED = new Set(['alert', 'aisle_complete']);

export const useStore = create<AppStore>((set, get) => ({
  connected: false,
  realRobot: null,
  mode: 'single',
  state: null,
  compareStates: [],
  heights: null,
  spreadL: null,
  spreadR: null,
  plantBytes: null,
  comparePlantBytes: [],
  playing: true,
  speed: 1,
  manual: false,
  bloque: 1,
  mastOverride: null,
  godMode: false,
  cameraMode: 'orbit',
  recordMode: false,
  showHeatmap: true,
  showTunnel: true,
  showSensors: true,
  showStations: false,
  showProdSensors: false,
  statsOpen: true,
  robotOpen: true,
  statsTab: 'resumen',
  robotTab: 'sensores',
  helpOpen: false,
  confirm: null,
  log: [],
  toasts: [],
  lastEventId: 0,
  runId: 0,
  send: null,
  setSend: (fn) => set({ send: fn }),
  setConnected: (v) => set(v ? { connected: true } : { connected: false, realRobot: null }),
  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
  set: (p) => set(p),
  applyMessage: (msg) => {
    if (msg.mode === 'export') {
      download(String(msg.filename ?? 'registros.csv'), String(msg.csv ?? ''));
      return;
    }
    const prev = get();
    const common = {
      playing: (msg.playing as boolean) ?? prev.playing,
      speed: (msg.speed as number) ?? prev.speed,
      manual: (msg.manual as boolean) ?? prev.manual,
      bloque: (msg.bloque as number) ?? prev.bloque,
      mastOverride: (msg.mast_override as boolean | null) ?? null,
      realRobot: (msg.real_robot as RealRobot | undefined) ?? prev.realRobot,
    };
    const statics: Partial<Statics> = Array.isArray(msg.heights)
      ? {
          heights: msg.heights as number[],
          spreadL: (msg.spread_l as number[]) ?? null,
          spreadR: (msg.spread_r as number[]) ?? null,
        }
      : {};

    if (msg.mode === 'compare' && Array.isArray(msg.states)) {
      const states = msg.states as SimState[];
      set({
        ...common,
        ...statics,
        mode: 'compare',
        compareStates: states,
        comparePlantBytes: states.map((s) => decodePlants(s.plants)),
        state: states[0] ?? null,
        plantBytes: states[0] ? decodePlants(states[0].plants) : null,
      });
      return;
    }
    const s = msg as unknown as SimState;
    if (!s.plants) return;

    let { lastEventId, log, toasts } = prev;
    if (s.run_id !== prev.runId) {
      lastEventId = 0;
      log = [];
      toasts = [];
    }
    const fresh = (s.events ?? []).filter((e) => e.id > lastEventId);
    if (fresh.length) {
      lastEventId = fresh[fresh.length - 1].id;
      log = [...log, ...fresh].slice(-150);
      const now = performance.now();
      const next = [...toasts];
      for (const e of fresh) {
        if (!TOAST_TYPES.has(e.type)) continue;
        const same = GROUPED.has(e.type) ? next.find((t) => t.type === e.type) : undefined;
        if (same) {
          Object.assign(same, { ...e, id: same.id, born: now, count: same.count + 1 });
        } else {
          next.push({ ...e, born: now, big: e.type === 'patrol_complete', count: 1 });
        }
      }
      toasts = next.slice(-4);
    }
    const samePlants = prev.mode === 'single' && prev.state?.plants === s.plants && prev.plantBytes;
    set({
      ...common,
      ...statics,
      mode: 'single',
      state: s,
      plantBytes: samePlants ? prev.plantBytes : decodePlants(s.plants),
      lastEventId,
      log,
      toasts,
      runId: s.run_id,
    });
  },
}));
