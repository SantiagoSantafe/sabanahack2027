import { useState } from 'react';
import { useStore, type SimEvent } from '../state/store';
import { PLATFORM_NAME, STATE_LABEL } from '../robot/labels';
import { bedLabel, fieldGeom } from '../scene/geometry';
import { actions } from './actions';
import { fmt } from './format';
import { IconChevron } from './icons';
import { RealRobotSection } from './RealRobot';
import { Tabs } from './Tabs';

function batteryColor(b: number) {
  return b < 0.2 ? 'var(--danger)' : b < 0.45 ? 'var(--warn)' : 'var(--leaf)';
}

const STATE_HINT: Record<string, string> = {
  failed: 'Un operario lo lleva a la base en 2 h simuladas, o tómalo en Manual.',
  stuck: 'Suele liberarse solo en unos minutos.',
  docked: 'Espera el próximo recorrido programado.',
  charging: 'Retoma el recorrido al cargar.',
};

function Sensores() {
  const state = useStore((s) => s.state)!;
  const manual = useStore((s) => s.manual);
  const r = state.robot;
  const g = fieldGeom(state);
  const cap = r.sensors?.last_capture;
  const ar = r.sensors?.last_aruco;
  const probe = r.sensors?.probe;
  const thr = state.decision_threshold ?? 0.35;
  const progress = r.aisles_total ? r.aisles_done / r.aisles_total : 0;
  const live = ['walking', 'inspecting', 'manual'].includes(r.state);
  return (
    <>
      <RealRobotSection />
      <section className="sensor">
        <header>
          <span className={`led ${live ? 'is-live' : ''}`} />
          <h4>Cámara RGB</h4>
          <small>{fmt(r.sensors?.frames ?? 0)} capturas</small>
        </header>
        {cap ? (
          <>
            <p className="sensor-line">
              {bedLabel(g, cap.bed)}, planta {cap.plant + 1}: <b className={cap.alert ? 'is-danger' : ''}>{cap.label}</b>
            </p>
            {cap.score !== null && (
              <div className="score" aria-label={`Confianza ${fmt(cap.score * 100)} %, umbral ${fmt(thr * 100)} %`}>
                <i style={{ width: `${cap.score * 100}%` }} className={cap.alert ? 'is-alert' : ''} />
                <span className="score-thr" style={{ left: `${thr * 100}%` }} />
                <em>{fmt(cap.score * 100)} %</em>
              </div>
            )}
            <p className="note">Por encima de la línea blanca ({fmt(thr * 100)} %) se genera una alerta.</p>
          </>
        ) : (
          <p className="sensor-line muted">Sin capturas todavía</p>
        )}
      </section>

      <section className="sensor">
        <header>
          <span className={`led ${probe && live ? 'is-live' : probe ? 'is-on' : ''}`} />
          <h4>Sonda de temperatura y humedad</h4>
        </header>
        {probe ? (
          <p className="sensor-line">
            <b>{fmt(probe.temp_c, 1)} °C</b> y <b>{fmt(probe.rh_pct, 0)} % HR</b> en {bedLabel(g, probe.bed)}
          </p>
        ) : (
          <p className="sensor-line muted">Mide cada 5 m y en cada incidencia</p>
        )}
      </section>

      <section className="sensor">
        <header>
          <span className={`led ${ar ? 'is-on' : ''}`} />
          <h4>Marcadores ArUco</h4>
        </header>
        <p className="sensor-line">{ar ? <>Leídos {ar.marker_ids.join(' y ')}: <b>{r.bed_label || '–'}</b></> : 'Sin lecturas'}</p>
      </section>

      <section className="sensor">
        <header>
          <span className={`led ${r.patrol_active ? 'is-live' : ''}`} />
          <h4>Recorrido</h4>
          <small>
            {r.aisles_done}/{r.aisles_total || g.aisles.length} pasillos
          </small>
        </header>
        <div className="beds-progress">
          <i style={{ width: `${progress * 100}%` }} />
        </div>
        <div className="kv tight">
          <span>Capturas en este recorrido</span>
          <b>{fmt(r.patrol_plants)}</b>
          <span>Alertas en este recorrido</span>
          <b className={r.patrol_alerts ? 'is-warn' : ''}>{fmt(r.patrol_alerts)}</b>
          <span>Velocidad</span>
          <b>{fmt(r.speed, 2)} m/s</b>
          <span>Ancho y alto</span>
          <b>
            {fmt(r.width_m, 2)} × {fmt(r.height_m, 2)} m{r.rigid ? ', rígido' : ''}
          </b>
        </div>
      </section>

      {manual && (
        <p className="note">
          Conduce con <kbd>W</kbd>
          <kbd>A</kbd>
          <kbd>S</kbd>
          <kbd>D</kbd>, <kbd>Shift</kbd> para ir rápido y <kbd>E</kbd> para inspeccionar las plantas de enfrente.
        </p>
      )}
    </>
  );
}

function Registro() {
  const log = useStore((s) => s.log);
  const [only, setOnly] = useState<'all' | 'alerts'>('all');
  const items = log
    .filter((e) => e.type !== 'aruco')
    .filter((e) => only === 'all' || e.level === 'warn' || e.level === 'danger')
    .slice(-40)
    .reverse();
  return (
    <section className="log">
      <div className="seg-small" role="radiogroup" aria-label="Filtrar registro">
        <button type="button" role="radio" aria-checked={only === 'all'} className={only === 'all' ? 'is-on' : ''} onClick={() => setOnly('all')}>
          Todo
        </button>
        <button type="button" role="radio" aria-checked={only === 'alerts'} className={only === 'alerts' ? 'is-on' : ''} onClick={() => setOnly('alerts')}>
          Alertas y fallas
        </button>
      </div>
      {items.length === 0 && <p className="muted">Sin eventos todavía.</p>}
      <ol>
        {items.map((e: SimEvent) => (
          <li key={e.id} className={`lvl-${e.level}`}>
            <time>
              D{e.day} {e.clock}
            </time>
            <span>{e.text}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Datos() {
  const state = useStore((s) => s.state)!;
  const k = state.kpis;
  const ls = state.last_sync;
  const store = state.connectivity === 'store_and_forward';
  const fromD1 = state.incidents.some((r) => r.fuente === 'camara_d1');
  return (
    <>
      <section className="sensor">
        <header>
          <span className={`led ${k.unsynced ? 'is-warn' : 'is-on'}`} />
          <h4>Base de datos</h4>
        </header>
        <p className="sensor-line">
          {k.unsynced ? (
            <>
              <b>{fmt(k.unsynced)}</b> registros guardados en el robot, se envían al llegar a la base.
            </>
          ) : (
            'Todo sincronizado.'
          )}
        </p>
        <p className="note">
          {store
            ? 'El bloque no tiene WiFi: el robot guarda cada lectura y la envía desde la base, donde hay conexión con la oficina.'
            : 'Envío en vivo.'}
          {ls && ` Última sincronización: día ${ls.day}, ${ls.clock} (${fmt(ls.records)} registros).`}
        </p>
      </section>
      <section>
        <h4>Últimas incidencias</h4>
        {state.incidents.length === 0 ? (
          <p className="muted">Sin incidencias registradas.</p>
        ) : (
          <table className="mini-table">
            <thead>
              <tr>
                <th scope="col">Dónde</th>
                <th scope="col">Qué</th>
                <th scope="col">°C</th>
                <th scope="col">HR</th>
              </tr>
            </thead>
            <tbody>
              {[...state.incidents].reverse().map((r) => (
                <tr key={r.id} className={r.synced ? '' : 'is-pending'} title={`Día ${r.day}, ${r.clock}${r.synced ? '' : ', pendiente de envío'}`}>
                  <td>
                    N{r.nave} C{r.cama} P{r.planta}
                  </td>
                  <td>
                    {r.clase}
                    {r.fuente === 'camara_d1' && <abbr title={`Cámara del D1 real. °C y HR: ${r.th_fuente ?? 'simulado'}`}> (D1*)</abbr>}
                  </td>
                  <td>{fmt(r.temp_c, 1)}</td>
                  <td>{fmt(r.rh_pct, 0)} %</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {fromD1 && <p className="note">* Detectada por la cámara del D1 real. Temperatura y humedad simuladas (en producción: sensor a bordo).</p>}
        <button type="button" className="btn-secondary" onClick={actions.exportCsv}>
          Exportar {fmt(k.records)} registros (CSV)
        </button>
      </section>
    </>
  );
}

export function RobotPanel() {
  const state = useStore((s) => s.state);
  const open = useStore((s) => s.robotOpen);
  const tab = useStore((s) => s.robotTab);
  const set = useStore((s) => s.set);
  if (!state) return null;
  const r = state.robot;
  const warn = r.state === 'failed' || r.state === 'stuck';
  const unsynced = state.kpis?.unsynced_incidents ?? 0;

  return (
    <aside className={`panel robot ${open ? '' : 'is-closed'}`} aria-label="Robot y sensores">
      <button type="button" className="panel-head" onClick={() => set({ robotOpen: !open })} aria-expanded={open}>
        <span>
          <strong>{r.active ? PLATFORM_NAME[r.platform] ?? r.platform : 'Sin robot'}</strong>
          <small className={warn ? 'is-danger' : ''}>{r.active ? STATE_LABEL[r.state] ?? r.state : state.alternative_name}</small>
        </span>
        {r.active && (
          <span className="batt" title={`Batería ${fmt(r.battery * 100)} %`}>
            <i style={{ width: `${Math.round(r.battery * 100)}%`, background: batteryColor(r.battery) }} />
            <em>{fmt(r.battery * 100)} %</em>
          </span>
        )}
        <IconChevron open={open} />
      </button>
      {open && (
        <>
          {r.active && STATE_HINT[r.state] && <p className="state-hint">{STATE_HINT[r.state]}</p>}
          <Tabs
            label="Secciones del robot"
            value={r.active ? tab : 'registro'}
            onChange={(v) => set({ robotTab: v })}
            tabs={
              r.active
                ? [
                    { id: 'sensores', label: 'Sensores' },
                    { id: 'registro', label: 'Registro' },
                    {
                      id: 'datos',
                      label: 'Datos',
                      badge: unsynced ? (
                        <i className="tab-badge" title={`${unsynced} incidencias esperan llegar a la base`}>
                          {unsynced > 99 ? '99+' : unsynced}
                        </i>
                      ) : undefined,
                    },
                  ]
                : [{ id: 'registro', label: 'Registro' }]
            }
          />
          <div className="panel-body" role="tabpanel">
            {!r.active && <p className="note">La red fija mide el riesgo por cama y, cuando sube, una persona revisa el bloque.</p>}
            {r.active && tab === 'sensores' && <Sensores />}
            {(tab === 'registro' || !r.active) && <Registro />}
            {r.active && tab === 'datos' && <Datos />}
          </div>
        </>
      )}
    </aside>
  );
}
