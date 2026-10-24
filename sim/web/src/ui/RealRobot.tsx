import { odomOf } from '../robot/twin';
import { useStore, type RealRobot } from '../state/store';
import { actions } from './actions';
import { useRutaParams } from './ruta';
import { fmt } from './format';

/** Bridge states (contract v1) in the farm's words. */
const REAL_STATE: Record<string, string> = {
  standing: 'De pie',
  moving: 'En marcha',
  lying: 'Acostado',
  passive: 'Motores sueltos',
  estop: 'Parada de emergencia',
  detection_hold: 'Quieto por detección',
  sdk_error: 'Error del SDK',
};

type Tone = 'ok' | 'warn' | 'danger' | 'off';

function latencyText(rr: RealRobot): string {
  if (rr.latency_ms !== null) return `${fmt(rr.latency_ms, 0)} ms`;
  return rr.clock_offset_suspect ? 'latencia n/d (relojes desfasados)' : 'latencia n/d';
}

/** "D1 real: conectado (mock) · 23 ms" / "D1 real: sin conexión". */
function realLinkLabel(rr: RealRobot | null): { text: string; tone: Tone } {
  if (!rr?.connected) return { text: 'D1 real: sin conexión', tone: rr?.ever_connected ? 'danger' : 'off' };
  const kind = rr.hello ? (rr.mock ? 'mock' : 'real') : 'esperando saludo';
  const stale = rr.telemetry_stale ? ' · sin telemetría' : '';
  return { text: `D1 real: conectado (${kind}) · ${latencyText(rr)}${stale}`, tone: rr.estop ? 'danger' : rr.telemetry_stale ? 'warn' : 'ok' };
}

/** "38 ms" while driving, "7,5 s" / "446 s" once the robot has been idle for a while. */
function ageText(ms: number): string {
  if (ms < 1000) return `${fmt(ms, 0)} ms`;
  return `${fmt(ms / 1000, ms < 10000 ? 1 : 0)} s`;
}

function stateText(rr: RealRobot): string {
  if (rr.estop) return REAL_STATE.estop;
  return rr.state ? (REAL_STATE[rr.state] ?? rr.state) : 'Sin estado';
}

/** Lying or with loose motors: the SDK refuses move() until standUp, so the bridge ignores WASD. */
const NEEDS_STAND = new Set(['lying', 'passive']);

/**
 * What the operator has to do before WASD can move the real D1, or null. The robot never stands up
 * on its own: a person presses Pararse (and, after Pararse or Reanudar, lets go of the keys first).
 */
const BARRIER_TEXT: Record<string, string> = {
  geocerca: 'Geocerca: el gemelo salió del pasillo. Re-centra el gemelo y pulsa Reanudar',
  'sin video': 'Sin video: robot detenido hasta que vuelva la cámara',
  'telemetría vieja': 'Sin telemetría del D1: el simulador dejó de mandar órdenes',
  batería: 'Batería crítica: el D1 se acuesta',
};

function driveBlocker(rr: RealRobot | null): string | null {
  if (!rr?.connected) return null;
  const barrier = rr.safety?.blocked;
  if (barrier) return BARRIER_TEXT[barrier] ?? `Bloqueado por seguridad (${barrier})`;
  if (rr.estop) return 'Pulsa Reanudar para volver a conducirlo';
  if (rr.state && NEEDS_STAND.has(rr.state)) return 'Pulsa Pararse primero: acostado no acepta WASD';
  return null;
}

/**
 * Always-visible controls while a real D1 is (or was) linked: the stop must never hide behind a
 * collapsed panel. Bottom center, right under the scene's focus.
 */
export function RealRobotBar() {
  const rr = useStore((s) => s.realRobot);
  const manual = useStore((s) => s.manual);
  const recordMode = useStore((s) => s.recordMode);
  if (!rr?.ever_connected || (recordMode && !rr.connected)) return null;
  const on = rr.connected;
  const link = realLinkLabel(rr);
  const t = rr.telemetry;
  const blocker = driveBlocker(rr);
  const needsStand = !!rr.state && NEEDS_STAND.has(rr.state) && !rr.estop;
  const ruta = rr.ruta;
  const rutaOn = ruta?.estado === 'en_marcha' || ruta?.estado === 'pausa';
  const parts = on
    ? [
        stateText(rr),
        t?.battery != null ? `batería ${fmt(t.battery, 0)} %${rr.safety?.battery_low ? ' (baja: no puede pararse)' : ''}` : null,
        rr.safety && rr.safety.config.speed_cap_mps > 0 ? `tope ${fmt(rr.safety.config.speed_cap_mps, 1)} m/s` : null,
        rr.hold_s_left > 0 ? `quieto ${fmt(rr.hold_s_left, 0)} s por detección` : null,
        rutaOn && ruta
          ? `Ruta real${ruta.estado === 'pausa' ? ' en pausa' : ''}: tramo ${ruta.tramo}/${ruta.tramos} · quedan ${fmt(ruta.restante_m, 1)} m`
          : blocker
            ? null
            : rr.teleop_active
              ? 'recibe WASD'
              : manual
                ? null
                : 'pasa a Manual (M) para conducirlo',
      ]
    : ['El puente lo deja quieto y reintenta solo', rr.since_disconnect_s !== null ? `hace ${fmt(rr.since_disconnect_s, 0)} s` : null];
  return (
    <div className={`real-bar ${rr.estop ? 'is-estop' : ''}`} role="region" aria-label="Robot real D1">
      <div className="real-status" aria-live="polite">
        <span className={`led tone-${link.tone} ${rr.teleop_active ? 'is-live' : ''}`} />
        <span>
          <b>{link.text}</b>
          <small>{parts.filter(Boolean).join(' · ')}</small>
          {blocker && manual && <small className="is-warn">{blocker}</small>}
        </span>
      </div>
      <div className="real-actions">
        <button
          type="button"
          className="btn-estop"
          disabled={!on}
          aria-pressed={rr.estop}
          aria-keyshortcuts="X"
          onClick={() => actions.robotAction('estop')}
          title="Parada de emergencia: velocidad cero hasta Reanudar (X)"
        >
          {rr.estop ? 'D1 parado' : 'Parar D1'} <kbd>X</kbd>
        </button>
        <button
          type="button"
          className={rr.estop ? 'btn-primary' : 'btn-secondary'}
          disabled={!on}
          onClick={() => actions.robotAction('resume')}
          title="Quita la parada de emergencia"
        >
          Reanudar
        </button>
      </div>
      <div className="real-actions real-posture" role="group" aria-label="Ruta real">
        <button
          type="button"
          className={rutaOn ? 'btn-secondary' : 'btn-primary'}
          disabled={!on}
          onClick={rutaOn ? actions.rutaCancel : actions.rutaStart}
          title="El D1 recorre solo la ruta del modo Auto desde donde está (escala en el panel D1 real). PARADA/X la cancela."
        >
          {rutaOn ? 'Cancelar ruta' : 'Ruta real'}
        </button>
      </div>
      <div className="real-actions real-posture" role="group" aria-label="Postura del D1">
        <button
          type="button"
          className={needsStand ? 'btn-primary' : 'btn-secondary'}
          disabled={!on}
          onClick={() => actions.robotAction('stand')}
          title="Ponerse de pie (hace falta antes de conducirlo)"
        >
          Pararse
        </button>
        <button type="button" className="btn-secondary" disabled={!on} onClick={() => actions.robotAction('lie')} title="Echarse en el suelo">
          Acostarse
        </button>
      </div>
    </div>
  );
}

/** Ruta real parameters and the dry-run (draws the scaled route in the scene before starting). */
function RutaControls({ rr }: { rr: RealRobot }) {
  const { escala, largo, deriva, escaneos, set } = useRutaParams();
  const ruta = rr.ruta;
  const num = (v: string, d: number) => (Number.isFinite(parseFloat(v.replace(',', '.'))) ? parseFloat(v.replace(',', '.')) : d);
  const live = ruta?.estado === 'en_marcha' || ruta?.estado === 'pausa';
  return (
    <div className="ruta-box">
      <h4>Ruta real (recorrido Auto en el D1)</h4>
      <div className="kv tight">
        <span>Escala de la ruta</span>
        <input aria-label="Escala de la ruta" type="number" min={0.002} max={1} step={0.001} value={escala} disabled={live} onChange={(e) => set({ escala: num(e.target.value, escala) })} />
        <span>Largo máx. (m, 0 = todo)</span>
        <input aria-label="Largo máximo en metros" type="number" min={0} step={1} value={largo} disabled={live} onChange={(e) => set({ largo: num(e.target.value, largo) })} />
        <span>Deriva máx. (m)</span>
        <input aria-label="Deriva máxima en metros" type="number" min={0.1} step={0.05} value={deriva} disabled={live} onChange={(e) => set({ deriva: num(e.target.value, deriva) })} />
        <span>Paradas para mirar por pasillo</span>
        <input aria-label="Paradas por pasillo para mirar a izquierda y derecha" type="number" min={0} max={6} step={1} value={escaneos} disabled={live} onChange={(e) => set({ escaneos: Math.round(num(e.target.value, escaneos)) })} />
      </div>
      <button type="button" className="btn-secondary" disabled={live} onClick={actions.rutaDryrun} title="Solo dibuja la ruta escalada en la escena (ámbar), sin mover el robot">
        Ver ruta (simulación)
      </button>
      {ruta && ruta.estado !== 'inactiva' && (
        <p className={`note ${ruta.estado === 'cancelada' ? 'is-warn' : ''}`}>
          {ruta.estado === 'simulacion' && `Simulación: ${fmt(ruta.tramos)} tramos, ${fmt(ruta.total_m, 1)} m (escala ${fmt(ruta.escala, 3)}): en la sala el D1 recorre ${fmt(ruta.total_m, 1)} m; en el campo, la ruta dibujada.`}
          {live && `Tramo ${ruta.tramo}/${ruta.tramos} · quedan ${fmt(ruta.restante_m, 1)} de ${fmt(ruta.total_m, 1)} m · desvío ${fmt(ruta.deriva_m, 2)} m${ruta.estado === 'pausa' ? ' · en pausa (detección)' : ''}${ruta.mirando ? ` · mirando a la ${ruta.mirando}` : ''}`}
          {ruta.estado === 'terminada' && 'Ruta completada.'}
          {ruta.estado === 'cancelada' && `Ruta detenida: ${ruta.motivo}`}
        </p>
      )}
    </div>
  );
}

/**
 * Big always-visible stop in the 3D view, even with no bridge linked (then it only warns). It goes over
 * HTTP too, so it works with the browser's WebSocket down; sim-core also zeroes the D1 when it drops.
 */
export function StopFab() {
  const rr = useStore((s) => s.realRobot);
  const connected = useStore((s) => s.connected);
  const recordMode = useStore((s) => s.recordMode);
  if (recordMode && !rr?.connected) return null;
  const on = !!rr?.connected;
  const stopped = !!rr?.estop;
  return (
    <button
      type="button"
      className={`stop-fab ${stopped ? 'is-stopped' : ''} ${on ? '' : 'is-idle'}`}
      aria-pressed={stopped}
      aria-keyshortcuts="X"
      onClick={() => actions.robotAction('estop')}
      title={on ? 'Parada de emergencia del D1 (X): velocidad cero hasta Reanudar' : connected ? 'No hay D1 conectado: no hay nada que parar' : 'Sin servidor: intenta parar por HTTP'}
    >
      <span className="stop-fab-big">{stopped ? 'PARADO' : 'PARADA'}</span>
      <kbd>X</kbd>
    </button>
  );
}

/** "D1 real" block at the top of the robot panel: link, telemetry, twin, last camera detection, ground truth. */
export function RealRobotSection() {
  const rr = useStore((s) => s.realRobot);
  const manual = useStore((s) => s.manual);
  const link = realLinkLabel(rr);
  if (!rr?.connected) {
    return (
      <section className="sensor real-sec">
        <header>
          <span className={`led tone-${link.tone}`} />
          <h4>D1 real</h4>
          <small>sin conexión</small>
        </header>
        <p className="note">
          {rr?.ever_connected
            ? 'Se perdió el enlace: el puente deja el robot quieto y reintenta solo.'
            : 'Para conectar el robot, arranca el puente en la VM (docs/ROBOT_REAL.md).'}
        </p>
      </section>
    );
  }
  const t = rr.telemetry;
  const odom = odomOf(t);
  const d = rr.last_detection;
  const tr = rr.truth;
  return (
    <section className="sensor real-sec">
      <header>
        <span className={`led tone-${link.tone} ${rr.teleop_active ? 'is-live' : ''}`} />
        <h4>D1 real</h4>
        <small>
          {rr.hello ? (rr.mock ? 'mock' : 'real') : 'esperando saludo'} · {latencyText(rr)}
        </small>
      </header>
      <div className="kv tight">
        <span>Estado</span>
        <b className={rr.estop ? 'is-danger' : ''}>{stateText(rr)}</b>
        <span>Batería</span>
        <b>{t?.battery != null ? `${fmt(t.battery, 0)} %` : '–'}</b>
        <span>Odometría</span>
        <b>{odom ? `${fmt(odom.x, 2)}; ${fmt(odom.y, 2)} m · ${fmt((odom.yaw * 180) / Math.PI, 0)}°` : 'no disponible'}</b>
        <span>Última orden en el robot</span>
        <b>{t?.last_cmd_age_ms != null ? `hace ${ageText(t.last_cmd_age_ms)}` : '–'}</b>
      </div>
      <p className="note">
        {odom ? 'El robot de la escena sigue la odometría del D1. ' : 'Sin odometría: el robot de la escena avanza con el teclado. '}
        {manual ? 'WASD mueve el D1 real.' : 'Pasa a Manual (M) para conducirlo con WASD.'}
      </p>
      {driveBlocker(rr) && <p className="note is-warn">{driveBlocker(rr)}.</p>}
      <InicioBloque />
      <button
        type="button"
        className="btn-secondary"
        disabled={!manual}
        onClick={actions.recenterTwin}
        title="Alinea el robot de la escena con el centro del pasillo más cercano y ancla ahí la odometría del D1"
      >
        Re-centrar el gemelo
      </button>

      <RutaControls rr={rr} />

      {d && (
        <div className="real-det">
          <p className="sensor-line">
            Cámara del D1: <b className={d.sospecha ? 'is-danger' : ''}>{d.label_es}</b> {fmt(d.conf * 100, 0)} %
            {d.sospecha ? ' · sospecha' : ' · sin sospecha'}
          </p>
          {d.where && d.sospecha && (
            <p className="note">
              Incidencia en Nave {d.where.nave} · Cama {d.where.cama}
              {d.where.planta ? `, planta ${d.where.planta}` : ''}: {fmt(d.where.temp_c, 1)} °C y {fmt(d.where.rh_pct, 0)} % HR,{' '}
              {rr.th_note}.
            </p>
          )}
        </div>
      )}

      {tr && (
        <div className="real-truth">
          <h4>
            Verdad de terreno · {fmt(tr.leaves)} {tr.leaves === 1 ? 'hoja' : 'hojas'}
          </h4>
          <div className="patrol-grid">
            <div className={tr.hits ? 'is-ok' : ''}>
              <b>{fmt(tr.hits)}</b>
              <span>aciertos</span>
            </div>
            <div className={tr.false_alarms ? 'is-warn' : ''}>
              <b>{fmt(tr.false_alarms)}</b>
              <span>falsas alarmas</span>
            </div>
            <div className={tr.misses ? 'is-danger' : ''}>
              <b>{fmt(tr.misses)}</b>
              <span>no detectadas</span>
            </div>
            <div>
              <b>{fmt(tr.true_negatives)}</b>
              <span>sanas bien descartadas</span>
            </div>
          </div>
          <p className="note">
            {fmt(tr.class_match)} de {fmt(tr.hits)} {tr.hits === 1 ? 'acierto' : 'aciertos'} con la enfermedad correcta. Cada hoja agrupa
            los cuadros seguidos con la misma etiqueta del visor ({fmt(tr.frames)} {tr.frames === 1 ? 'cuadro' : 'cuadros'}).
          </p>
        </div>
      )}
    </section>
  );
}


/** Instrucción fija para el operario: dónde poner el D1 antes de pulsar Ruta real, y vuelta al inicio. */
function InicioBloque() {
  const bloque = useStore((s) => s.bloque);
  const b = useStore((s) => s.state?.layout?.blocks?.find((x) => x.id === s.bloque));
  if (!b) return null;
  return (
    <div className="ruta-box">
      <h4>Bloque {bloque} · inicio <small style={{ fontWeight: 400, opacity: 0.7 }}>(lo elige el supervisor)</small></h4>
      <p className="note">
        Pon el D1 en la entrada del pasillo <b>{b.start_label}</b>, en la cabecera sur, mirando hacia el fondo. Pulsa
        <b> Volver al inicio</b>, luego <b>Pararse</b> y <b>Ruta real</b>.
      </p>
      <button type="button" className="btn-secondary" onClick={actions.volverInicio} title="El robot de la escena vuelve al inicio del bloque y el gemelo se ancla ahí">
        Volver al inicio
      </button>
    </div>
  );
}
