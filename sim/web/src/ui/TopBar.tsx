import { useState } from 'react';
import { useStore, type CameraMode } from '../state/store';
import { actions, ALTERNATIVES, SPEEDS } from './actions';
import { IconChevron, IconGrid, IconJoystick, IconLayers, IconPause, IconPlay, IconRecord, IconReset, IconRobot, IconSkip } from './icons';
import { Popover, Toggle } from './Popover';

const CAMERAS: { id: CameraMode; label: string; hint: string }[] = [
  { id: 'orbit', label: 'Vista del bloque', hint: 'Arrastra para girar, rueda para acercar' },
  { id: 'follow', label: 'Detrás del robot', hint: 'Sigue al robot por el pasillo' },
  { id: 'side', label: 'Junto al robot', hint: 'Primer plano de la marcha' },
  { id: 'cinematic', label: 'Recorrido de cámara', hint: 'Movimiento suave para grabar' },
];

function StatusPill() {
  const state = useStore((s) => s.state);
  const connected = useStore((s) => s.connected);
  const playing = useStore((s) => s.playing);
  const manual = useStore((s) => s.manual);
  const realDriving = useStore((s) => !!s.realRobot?.teleop_active);
  if (!connected) return <span className="status is-danger">Sin conexión con el motor</span>;
  if (!state) return <span className="status">Cargando…</span>;
  if (state.done) return <span className="status">Simulación terminada ({state.max_days} días)</span>;
  if (!playing) return <span className="status is-paused">En pausa</span>;
  if (manual) return <span className="status is-live">{realDriving ? 'Conduciendo el D1 real' : 'Control manual'}, tiempo real</span>;
  if (state.realtime) return <span className="status is-live">{state.robot.active ? 'Robot en campo' : 'Revisión en curso'}, tiempo real</span>;
  const np = state.next_patrol;
  return (
    <span className="status">
      {np ? (
        <>
          Próximo recorrido: día {np.day}, {np.clock}
          <button type="button" className="status-action" onClick={actions.skip} title="Avanzar hasta que empiece el recorrido">
            <IconSkip /> Ir al recorrido
          </button>
        </>
      ) : (
        'Sin más recorridos programados'
      )}
    </span>
  );
}

export function TopBar() {
  const state = useStore((s) => s.state);
  const playing = useStore((s) => s.playing);
  const speed = useStore((s) => s.speed);
  const manual = useStore((s) => s.manual);
  const mode = useStore((s) => s.mode);
  const cameraMode = useStore((s) => s.cameraMode);
  const godMode = useStore((s) => s.godMode);
  const showHeatmap = useStore((s) => s.showHeatmap);
  const showTunnel = useStore((s) => s.showTunnel);
  const showSensors = useStore((s) => s.showSensors);
  const showStations = useStore((s) => s.showStations);
  const showProdSensors = useStore((s) => s.showProdSensors);
  const mastOverride = useStore((s) => s.mastOverride);
  const set = useStore((s) => s.set);
  const [seed, setSeed] = useState('');

  const alt = ALTERNATIVES.find((a) => a.code === state?.alternative) ?? ALTERNATIVES[0];
  const robotActive = state?.robot.active ?? false;
  const isQuad = state?.robot.platform === 'quadruped';
  const mastOn = mastOverride ?? state?.robot.mast ?? false;
  const manualDisabled = !robotActive || mode === 'compare';

  return (
    <header className="topbar">
      <div className="tb-group">
        <span className="sim-badge">SIMULACIÓN</span>
        <Popover
          title="Elegir la alternativa a simular"
          className="alt-pop"
          label={
            <span className="alt-chip">
              <b>{mode === 'compare' ? '2×2' : alt.code}</b>
              <span>{mode === 'compare' ? 'Comparación' : alt.name}</span>
              <IconChevron />
            </span>
          }
        >
          {(close) => (
            <ul className="alt-list" role="menu">
              {ALTERNATIVES.map((a) => (
                <li key={a.code}>
                  <button
                    type="button"
                    role="menuitemradio"
                    aria-checked={a.code === state?.alternative && mode !== 'compare'}
                    className={a.code === state?.alternative && mode !== 'compare' ? 'is-current' : ''}
                    onClick={() => {
                      close();
                      if (a.code !== state?.alternative || mode === 'compare') actions.setAlternative(a.code);
                    }}
                  >
                    <b>{a.code}</b>
                    <span>
                      {a.name}
                      <small>{a.note}</small>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Popover>
      </div>

      <div className="tb-group tb-time">
        <button type="button" className="tb-btn tb-play" onClick={actions.togglePlay} title={playing ? 'Pausar (Espacio)' : 'Reanudar (Espacio)'} aria-label={playing ? 'Pausar' : 'Reanudar'}>
          {playing ? <IconPause /> : <IconPlay />}
        </button>
        <div className="speed-seg" role="radiogroup" aria-label="Velocidad">
          {SPEEDS.map((v) => (
            <button key={v} type="button" role="radio" aria-checked={speed === v} className={speed === v ? 'is-on' : ''} onClick={() => actions.setSpeed(v)}>
              {v}×
            </button>
          ))}
        </div>
        <div className="clock" aria-label="Fecha simulada">
          <span className="clock-day">Día {state?.day ?? 0}</span>
          <span className="clock-time">{state?.clock ?? '--:--'}</span>
        </div>
        <StatusPill />
      </div>

      <div className="tb-group">
        <div className="mode-seg" role="radiogroup" aria-label="Control del robot" title={manualDisabled ? 'Esta alternativa no tiene robot que conducir' : 'Cambiar con M'}>
          <button type="button" role="radio" aria-checked={!manual} className={!manual ? 'is-on' : ''} onClick={() => manual && actions.toggleManual()} disabled={manualDisabled}>
            <IconRobot /> Auto
          </button>
          <button type="button" role="radio" aria-checked={manual} className={manual ? 'is-on' : ''} onClick={() => !manual && actions.toggleManual()} disabled={manualDisabled}>
            <IconJoystick /> Manual
          </button>
        </div>
        <BloqueSeg />

        <Popover title="Qué se ve en la escena" align="right" label={<><IconLayers /> Vista</>}>
          <div className="menu">
            <p className="menu-title">Cámara (C)</p>
            {CAMERAS.map((c) => (
              <button key={c.id} type="button" role="menuitemradio" aria-checked={cameraMode === c.id} className={`menu-item ${cameraMode === c.id ? 'is-current' : ''}`} onClick={() => set({ cameraMode: c.id })}>
                {c.label}
                <small>{c.hint}</small>
              </button>
            ))}
            <p className="menu-title">Capas</p>
            <Toggle label="Sensores del robot" hint="Cono, haz y lecturas (V)" on={showSensors} onChange={(v) => set({ showSensors: v })} />
            <Toggle label="Mapa de riesgo" hint="Color en el suelo de cada cama (H)" on={showHeatmap} onChange={(v) => set({ showHeatmap: v })} />
            <Toggle label="Dataloggers" hint="Temperatura y humedad por nave" on={showStations} onChange={(v) => set({ showStations: v })} />
            <Toggle
              label="Sensores de producción"
              hint="Ejemplo · no montado en la demo: sonda, térmica, envés, PLC"
              on={showProdSensors}
              onChange={(v) => set({ showProdSensors: v })}
            />
            <Toggle label="Plástico del macrotúnel" on={showTunnel} onChange={(v) => set({ showTunnel: v })} />
            <Toggle label="Modo dios" hint="Revela infectadas sin síntomas (G)" on={godMode} onChange={(v) => set({ godMode: v })} />
          </div>
        </Popover>

        <Popover title="Configurar la corrida" align="right" label={<><IconReset /> Corrida</>}>
          {(close) => (
            <div className="menu">
              <p className="menu-title">Escenario</p>
              <form
                className="seed-row"
                onSubmit={(e) => {
                  e.preventDefault();
                  const v = Number(seed);
                  close();
                  if (seed !== '' && Number.isFinite(v)) actions.setSeed(v);
                }}
              >
                <label htmlFor="seed">Semilla</label>
                <input id="seed" type="number" placeholder={String(state?.seed ?? 42)} value={seed} onChange={(e) => setSeed(e.target.value)} />
                <button type="submit">Aplicar</button>
              </form>
              {isQuad && (
                <Toggle
                  label="Mástil de producción"
                  hint="Cámara a 1,35 m. Reinicia la corrida"
                  on={mastOn}
                  onChange={(v) => {
                    close();
                    actions.setMast(v);
                  }}
                />
              )}
              <button type="button" className="menu-item" onClick={() => { close(); actions.reset(); }}>
                <IconReset /> Reiniciar corrida
              </button>
              <p className="menu-title">Evidencia</p>
              <button type="button" className="menu-item" onClick={() => { close(); actions.exportCsv(); }} disabled={mode === 'compare'}>
                Exportar registros (CSV)
                <small>Temperatura, humedad e incidencias por nave, cama y planta</small>
              </button>
              <button type="button" className="menu-item" onClick={() => { close(); actions.compare(mode !== 'compare'); }}>
                <IconGrid /> {mode === 'compare' ? 'Salir de la comparación' : 'Comparar 2×2'}
                <small>{mode === 'compare' ? 'Vuelve a una alternativa' : 'F, A, C y referencia con la misma semilla'}</small>
              </button>
              <button type="button" className="menu-item" onClick={() => { close(); actions.record(true); }}>
                <IconRecord /> Modo grabación
                <small>Pantalla limpia a 1920×1080. Esc para salir</small>
              </button>
            </div>
          )}
        </Popover>

        <button type="button" className="tb-btn tb-help" onClick={() => set({ helpOpen: true })} title="Ayuda (?)" aria-label="Ayuda">
          ?
        </button>
      </div>
    </header>
  );
}


/** Bloque que recorre el robot (predefinido para el operario) y vuelta al inicio de ese bloque. */
function BloqueSeg() {
  const bloque = useStore((s) => s.bloque);
  const blocks = useStore((s) => s.state?.layout?.blocks);
  if (!blocks || blocks.length < 2) return null;
  const actual = blocks.find((b) => b.id === bloque);
  return (
    <div className="mode-seg" role="group" aria-label="Bloque a recorrer" title={actual ? `Inicio: ${actual.start_label}, entrada sur, mirando al fondo` : undefined}>
      {/* El bloque lo elige el supervisor desde el dashboard (POST /api/dashboard/bloque); aquí solo se muestra */}
      <span className="is-on" role="status" style={{ padding: '0 12px', display: 'inline-flex', alignItems: 'center', borderRadius: 999 }}
        title={`Bloque ${bloque}${actual ? `: naves ${actual.naves.join(' y ')}` : ''} · lo elige el supervisor en el panel de incidencias`}>
        Bloque {bloque}
      </span>
      <button type="button" onClick={actions.volverInicio} title="Volver el robot de la escena al inicio del bloque (en Manual re-ancla el gemelo del D1)">
        ⟲ Inicio
      </button>
    </div>
  );
}
