import { useEffect, useRef } from 'react';
import { useStore } from '../state/store';
import { STATE_COLORS, STATE_NAMES } from '../theme/palette';

export function ConfirmDialog() {
  const confirm = useStore((s) => s.confirm);
  const set = useStore((s) => s.set);
  const okRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (confirm) okRef.current?.focus();
  }, [confirm]);
  if (!confirm) return null;
  return (
    <div className="scrim" role="presentation" onMouseDown={() => set({ confirm: null })}>
      <div className="dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" onMouseDown={(e) => e.stopPropagation()}>
        <h2 id="confirm-title">{confirm.title}</h2>
        <p>{confirm.body}</p>
        <div className="dialog-actions">
          <button type="button" className="btn-secondary" onClick={() => set({ confirm: null })}>
            Cancelar
          </button>
          <button
            ref={okRef}
            type="button"
            className="btn-primary"
            onClick={() => {
              confirm.run();
              set({ confirm: null });
            }}
          >
            {confirm.ok}
          </button>
        </div>
      </div>
    </div>
  );
}

const HELP_KEY = 'berrysim.help.v2';

export function HelpOverlay() {
  const open = useStore((s) => s.helpOpen);
  const set = useStore((s) => s.set);
  useEffect(() => {
    if (!localStorage.getItem(HELP_KEY)) set({ helpOpen: true });
  }, [set]);
  if (!open) return null;
  const close = () => {
    localStorage.setItem(HELP_KEY, '1');
    set({ helpOpen: false });
  };
  return (
    <div className="scrim" role="presentation" onMouseDown={close}>
      <div className="dialog help" role="dialog" aria-modal="true" aria-labelledby="help-title" onMouseDown={(e) => e.stopPropagation()}>
        <h2 id="help-title">Cómo leer la simulación</h2>
        <div className="help-grid">
          <section>
            <h3>Qué estás viendo</h3>
            <p>
              Un bloque de arándano en maceta bajo macrotúnel: naves de 6,8 m con 3 camas y 80 m de largo. Un robot recorre los pasillos, mira las
              plantas de ambos lados, mide temperatura y humedad, y guarda cada hallazgo para el agrónomo.
            </p>
            <p>
              Con el robot en el campo el reloj va en tiempo real. Cuando está en la base, los días pasan rápido hasta el próximo recorrido; usa{' '}
              <b>Ir al recorrido</b> para no esperar.
            </p>
          </section>
          <section>
            <h3>Colores de las plantas</h3>
            <ul className="legend">
              {[0, 1, 3, 4, 6, 7, 2].map((s) => (
                <li key={s}>
                  <i style={{ background: STATE_COLORS[s] }} />
                  <span>
                    {STATE_NAMES[s]}
                    {s === 2 ? ' (solo en modo dios)' : ''}
                  </span>
                </li>
              ))}
            </ul>
            <p className="note">El cono y los haces cian son la cámara; la banda cian sobre el arbusto es la parte que alcanza a ver.</p>
          </section>
          <section>
            <h3>Controles</h3>
            <dl className="keys">
              <dt>Espacio</dt>
              <dd>Pausar o reanudar</dd>
              <dt>M</dt>
              <dd>Cambiar entre automático y manual</dd>
              <dt>W A S D</dt>
              <dd>Conducir en manual (Shift más rápido)</dd>
              <dt>E</dt>
              <dd>Inspeccionar en manual</dd>
              <dt>C</dt>
              <dd>Cambiar cámara</dd>
              <dt>V, H, G</dt>
              <dd>Sensores, mapa de riesgo, modo dios</dd>
              <dt>X</dt>
              <dd>Parar el D1 real (parada de emergencia)</dd>
              <dt>?</dt>
              <dd>Abrir esta ayuda</dd>
            </dl>
          </section>
          <section>
            <h3>Robot real (D1 EDU)</h3>
            <p>
              Con el puente conectado aparece la barra <b>D1 real</b> abajo. En Manual, <kbd>W</kbd>
              <kbd>A</kbd>
              <kbd>S</kbd>
              <kbd>D</kbd> mueven también el robot real: recibe 20 órdenes por segundo y se queda quieto si dejan de llegar. <kbd>X</kbd> o{' '}
              <b>Parar D1</b> lo detienen hasta <b>Reanudar</b>. El robot de la escena sigue la odometría del D1.
            </p>
            <p className="note">
              La temperatura y la humedad de las detecciones del D1 son simuladas (en producción: sensor a bordo). La capa Sensores de
              producción es un ejemplo: no está montada en la demo.
            </p>
          </section>
          <section>
            <h3>De dónde salen los datos</h3>
            <p>
              Clima horario de Open-Meteo (Chía, 2025). Medidas del bloque, horario del operario y falta de WiFi: entrevista con la empresa. Riesgo:
              antracnosis con Wilson 1990 y Gillett y Schilder 2009, Botrytis con Bulger 1987 y roya con Magarey 2005. El detector usa lo medido
              en el test de DrBerry (80 % de enfermas detectadas, 36 % de falsas alarmas); las enfermedades simuladas son clases que el
              clasificador todavía no conoce. Los valores sin fuente están marcados como supuestos en la configuración y el README.
            </p>
          </section>
        </div>
        <div className="dialog-actions">
          <button type="button" className="btn-primary" onClick={close} autoFocus>
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
}
