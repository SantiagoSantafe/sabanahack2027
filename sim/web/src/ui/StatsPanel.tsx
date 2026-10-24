import { useMemo } from 'react';
import { useStore } from '../state/store';
import { STATE_COLORS, STATE_NAMES } from '../theme/palette';
import { fmt, riskLevel } from './format';
import { IconChevron } from './icons';
import { LevelChip, Tabs } from './Tabs';


function Kpi({ value, label, tone }: { value: string; label: string; tone?: 'warn' | 'danger' | 'ok' }) {
  return (
    <div className={`kpi ${tone ? `is-${tone}` : ''}`}>
      <b>{value}</b>
      <span>{label}</span>
    </div>
  );
}

function Resumen() {
  const state = useStore((s) => s.state)!;
  const m = state.metrics;
  const lp = state.last_patrol;
  const k = state.kpis;
  const det = m.first_detection_day as number | null;
  const deliv = m.first_alert_delivered_day as number | null;
  return (
    <>
      <div className="kpi-grid">
        <Kpi value={fmt(m.infected ?? 0)} label="infectadas" tone={(m.infected ?? 0) > 0 ? 'warn' : undefined} />
        <Kpi value={fmt(m.detected ?? 0)} label="detectadas y tratadas" tone="ok" />
        <Kpi value={fmt(m.pending ?? 0)} label="por confirmar" />
        <Kpi value={fmt(m.missed ?? 0)} label="sin detectar" tone={(m.missed ?? 0) > 0 ? 'danger' : undefined} />
      </div>
      <p className="lead">
        {det != null ? (
          <>
            Primera detección el <b>día {fmt(det, 1)}</b>
            {m.beds_infected_at_detection != null && <>, con {m.beds_infected_at_detection} camas ya infectadas</>}.
            {deliv != null && deliv - det > 0.001 && <> Llegó al agrónomo el día {fmt(deliv, 1)}.</>}
          </>
        ) : (
          'Todavía no hay una detección correcta.'
        )}{' '}
        Falsas alarmas: {fmt(m.false_alarms ?? 0)}.
      </p>

      {lp ? (
        <section className="patrol-card">
          <h3>Último recorrido</h3>
          <p className="patrol-when">
            Día {lp.day}, {lp.clock}
          </p>
          <div className="patrol-grid">
            <div>
              <b>{fmt(lp.minutes, 0)}</b>
              <span>min (operario: {fmt(lp.human_minutes, 0)})</span>
            </div>
            <div>
              <b>{fmt(lp.plants)}</b>
              <span>capturas</span>
            </div>
            <div className={lp.alerts ? 'is-warn' : ''}>
              <b>{fmt(lp.alerts)}</b>
              <span>alertas</span>
            </div>
            <div>
              <b>{fmt(lp.distance_m, 0)}</b>
              <span>metros</span>
            </div>
          </div>
          <p className="patrol-note">
            Pasó con cuidado {fmt(lp.careful)} veces por follaje desbordado
            {lp.contacts ? `, rozó hojas ${fmt(lp.contacts)} veces` : ''}
            {lp.skipped ? ` y dejó ${fmt(lp.skipped)} plantas sin revisar porque no cabía` : ''}.
          </p>
        </section>
      ) : (
        <p className="note">El resumen aparece al terminar el primer recorrido.</p>
      )}

      <section>
        <h3>Cobertura acumulada</h3>
        <div className="kv">
          <span>Recorridos</span>
          <b>{fmt(k.patrols)}</b>
          <span>Distancia</span>
          <b>{fmt(k.distance_km, 2)} km</b>
          <span>Horas en campo</span>
          <b>{fmt(k.field_hours, 1)} h</b>
          <span>Capturas por hora</span>
          <b>{fmt(k.captures_per_hour)}</b>
          <span>Área del bloque simulado</span>
          <b>{fmt(k.block_area_ha, 2)} ha</b>
        </div>
      </section>
    </>
  );
}

function Clima() {
  const state = useStore((s) => s.state)!;
  const w = state.weather;
  const r = state.risk.per_disease;
  const per = state.risk.per_bed;
  const bpn = state.layout.beds_per_nave;
  const naves = state.layout.naves;
  return (
    <>
      <section>
        <h3>Ahora</h3>
        <div className="climate-cols">
          <div>
            <small>Afuera</small>
            <b>{fmt(w.T, 1)} °C</b>
            <span>{fmt(w.RH, 0)} % HR</span>
          </div>
          <div className="is-in">
            <small>{w.tunnel ? 'Dentro del macrotúnel' : 'En el bloque'}</small>
            <b>{fmt(w.T_in, 1)} °C</b>
            <span>{fmt(w.RH_in, 0)} % HR</span>
          </div>
        </div>
        <div className="kv">
          <span>Ventilación</span>
          <b className={w.vent_forgotten ? 'is-danger' : ''}>{w.vent_forgotten ? 'Apagada por olvido' : w.vent_on ? 'Encendida' : 'En reposo'}</b>
          <span>Alero</span>
          <b className={w.alero_open ? 'is-danger' : ''}>{w.alero_open ? 'Abierto con lluvia' : 'Cerrado'}</b>
          <span>Hoja mojada hoy (cama más húmeda)</span>
          <b>{fmt(w.wet_h, 0)} h</b>
          <span>Lluvia afuera hoy</span>
          <b>{fmt(w.precip_day, 1)} mm</b>
        </div>
        {state.weather_source === 'synthetic' && <p className="note">Clima sintético: no había red ni caché.</p>}
      </section>
      <section>
        <h3>Riesgo del día</h3>
        <ul className="risk-list">
          {(
            [
              ['Antracnosis', r.anthracnose ?? 0],
              ['Botrytis', r.botrytis ?? 0],
              ['Roya', r.rust ?? 0],
            ] as const
          ).map(([name, v]) => {
            const lvl = riskLevel(v, state.risk_levels);
            return (
              <li key={name}>
                <span>{name}</span>
                <LevelChip {...lvl} />
                <em>{fmt(v, 2)}</em>
              </li>
            );
          })}
        </ul>
        <div className="nave-grid" style={{ gridTemplateColumns: `repeat(${naves}, 1fr)` }} aria-label="Riesgo por cama">
          {Array.from({ length: naves }, (_, k) => (
            <div key={k} className="nave-col">
              <small>Nave {k + 1}</small>
              <div className="nave-beds">
                {Array.from({ length: bpn }, (_, j) => {
                  const b = k * bpn + j;
                  const v = per[b] ?? 0;
                  const lvl = riskLevel(v, state.risk_levels);
                  return (
                    <span key={j} className={`bed-cell tone-${lvl.tone}`} title={`Nave ${k + 1} · Cama ${j + 1}: riesgo ${lvl.label.toLowerCase()} (${fmt(v, 2)}), ${fmt(w.RH_bed[b], 0)} % HR`}>
                      {j + 1}
                    </span>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
        <p className="note">El mismo color se ve en el suelo de cada cama con la capa Mapa de riesgo.</p>
      </section>
    </>
  );
}

function Plantas() {
  const plantBytes = useStore((s) => s.plantBytes);
  const godMode = useStore((s) => s.godMode);
  const k = useStore((s) => s.state?.kpis);
  const counts = useMemo(() => {
    const c = new Array(8).fill(0);
    if (plantBytes) for (const v of plantBytes) c[v] = (c[v] ?? 0) + 1;
    return c;
  }, [plantBytes]);
  const visible = [0, 1, 2, 3, 4, 6, 7].filter((s) => s !== 2 || godMode);
  return (
    <>
      <ul className="legend">
        {visible.map((s) => (
          <li key={s}>
            <i style={{ background: STATE_COLORS[s] }} />
            <span>{STATE_NAMES[s]}</span>
            <b>{fmt(counts[s] + (s === 0 && !godMode ? counts[2] : 0))}</b>
          </li>
        ))}
      </ul>
      {!godMode && <p className="note">Las infectadas sin síntomas se ven sanas. Actívalas con Modo dios (G).</p>}
      {k && (
        <section>
          <h3>Follaje</h3>
          <div className="kv">
            <span>Plantas desbordadas al pasillo</span>
            <b>{fmt(k.overflowing_plants)}</b>
            <span>Pasos con cuidado</span>
            <b>{fmt(k.careful_passes)}</b>
            <span>Roces con hojas</span>
            <b>{fmt(k.contacts)}</b>
            <span>Plantas sin revisar por falta de espacio</span>
            <b className={k.plants_skipped ? 'is-danger' : ''}>{fmt(k.plants_skipped)}</b>
          </div>
        </section>
      )}
    </>
  );
}

export function StatsPanel() {
  const state = useStore((s) => s.state);
  const bloque = useStore((s) => s.bloque);
  const open = useStore((s) => s.statsOpen);
  const tab = useStore((s) => s.statsTab);
  const set = useStore((s) => s.set);
  if (!state) return null;
  const overall = riskLevel(state.risk.combined, state.risk_levels);
  const blk = state.layout.blocks?.find((b) => b.id === bloque);
  return (
    <aside className={`panel stats ${open ? '' : 'is-closed'}`} aria-label="Estado del bloque">
      <button type="button" className="panel-head" onClick={() => set({ statsOpen: !open })} aria-expanded={open}>
        <span>
          <strong>Bloque {bloque}</strong>
          <small>
            {blk ? `naves ${blk.naves.join(' y ')} · ${blk.naves.length * state.layout.beds_per_nave} camas` : `${state.layout.naves} naves, ${state.n_beds} camas, ${fmt(state.n_beds * state.n_plants)} plantas`}
          </small>
        </span>
        <LevelChip label={`Riesgo ${overall.label.toLowerCase()}`} tone={overall.tone} />
        <IconChevron open={open} />
      </button>
      {open && (
        <>
          <Tabs
            label="Secciones del bloque"
            value={tab}
            onChange={(v) => set({ statsTab: v })}
            tabs={[
              { id: 'resumen', label: 'Resumen' },
              { id: 'clima', label: 'Clima' },
              { id: 'plantas', label: 'Plantas' },
            ]}
          />
          <div className="panel-body" role="tabpanel">
            {tab === 'resumen' && <Resumen />}
            {tab === 'clima' && <Clima />}
            {tab === 'plantas' && <Plantas />}
          </div>
        </>
      )}
    </aside>
  );
}
