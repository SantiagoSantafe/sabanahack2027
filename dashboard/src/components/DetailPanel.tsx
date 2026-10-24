import { useEffect, useRef } from 'react'
import { CLASES, FUENTE } from '../lib/catalogo'
import { hora, num, ubicLarga } from '../lib/format'
import { evalHr, evalTemp } from '../lib/umbrales'
import { ESTADO_TXT } from '../lib/foco'
import { ClaseBadge, NivelBadge } from './Badge'
import { Foto } from './FocoPanel'
import type { Foco, Incidencia } from '../types'

export function DetailPanel({ item, onClose, foco, onFoco }: { item: Incidencia; onClose: () => void; foco?: Foco | null; onFoco?: (f: Foco) => void }) {
  const ref = useRef<HTMLButtonElement>(null)
  const info = CLASES[item.clase] ?? CLASES.desconocida
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null
    ref.current?.focus()
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'Tab') { // atrapa el foco dentro del panel
        const f = document.querySelectorAll<HTMLElement>('[data-panel] button, [data-panel] a')
        if (!f.length) return
        const first = f[0], last = f[f.length - 1]
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
      }
    }
    document.addEventListener('keydown', key)
    return () => { document.removeEventListener('keydown', key); prev?.focus?.() }
  }, [onClose])
  const t = evalTemp(item.temperatura_c ?? undefined)
  const h = evalHr(item.humedad_pct ?? undefined)
  const conf = item.confianza != null ? Math.round(item.confianza * 100) : null
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-[rgb(17_24_39/.35)] backdrop-blur-[2px]" onClick={onClose}>
      <aside data-panel role="dialog" aria-modal="true" aria-labelledby="det-t" onClick={(e) => e.stopPropagation()}
        className="slide-in glass flex h-full w-full max-w-md flex-col overflow-y-auto rounded-l-[28px] border-l border-ink-700 p-6 shadow-pop">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="tag">Detalle de la incidencia</p>
            <h2 id="det-t" className="mt-1 text-xl font-semibold leading-tight text-fg">{ubicLarga(item)}</h2>
            <p className="mt-1 text-body text-fg-muted">{hora(item)}</p>
          </div>
          <button ref={ref} type="button" onClick={onClose} className="btn" aria-label="Cerrar detalle">Cerrar ✕</button>
        </div>
        <div className="mt-4 flex flex-wrap gap-2"><ClaseBadge clase={item.clase} estado={item.estado} /><NivelBadge item={item} /></div>

        {foco && (
          <div className="mt-4 rounded-2xl border border-ink-700 bg-ink-900/70 p-3">
            <p className="tag">Foco al que pertenece</p>
            <p className="mt-1 text-body text-fg">{foco.ubicacion} · {foco.plantas} plantas · estado <b>{ESTADO_TXT[foco.estado]}</b></p>
            {onFoco && <button type="button" className="btn btn-primary mt-2" onClick={() => onFoco(foco)}>Gestionar foco</button>}
          </div>
        )}
        <div className="mt-4"><Foto frame={item.frame} fuente={item.fuente} /></div>

        <h3 className="mt-5 text-title font-semibold text-fg">Qué es</h3>
        <p className="text-body text-fg-muted">{info.queEs}</p>
        <h3 className="mt-4 text-title font-semibold text-fg">Qué hacer</h3>
        <ol className="mt-1 list-decimal space-y-1 pl-5 text-body text-fg-muted">{info.queHacer.map((a) => <li key={a}>{a}</li>)}</ol>
        <p className="mt-2 text-label text-fg-subtle">Recomendación orientativa; confirmar con el agrónomo.</p>

        <h3 className="mt-5 text-title font-semibold text-fg">Condiciones al momento</h3>
        <dl className="mt-1 grid grid-cols-2 gap-3 text-body">
          <div className="rounded-2xl border border-ink-700 bg-ink-900/70 p-3"><dt className="text-label text-fg-subtle">Temperatura</dt><dd className="text-title font-semibold tabular-nums">{num(item.temperatura_c)} °C</dd><dd className="text-label text-fg-muted">{t.texto}</dd></div>
          <div className="rounded-2xl border border-ink-700 bg-ink-900/70 p-3"><dt className="text-label text-fg-subtle">Humedad relativa</dt><dd className="text-title font-semibold tabular-nums">{num(item.humedad_pct, 0)} %</dd><dd className="text-label text-fg-muted">{h.texto}</dd></div>
          <div className="rounded-2xl border border-ink-700 bg-ink-900/70 p-3"><dt className="text-label text-fg-subtle">Confianza del modelo</dt><dd className="text-title font-semibold tabular-nums">{conf != null ? `${conf} %` : 'No disponible'}</dd></div>
          <div className="rounded-2xl border border-ink-700 bg-ink-900/70 p-3"><dt className="text-label text-fg-subtle">Fuente</dt><dd className="text-title font-semibold">{FUENTE[item.fuente] ?? item.fuente}</dd>{item.fuente === 'camara_d1' && <dd className="text-label text-fg-muted">T y HR simuladas</dd>}</div>
        </dl>
        <p className="mt-4 text-label text-fg-subtle">N = nave · C = cama · P = planta (posición en la cama).</p>
      </aside>
    </div>
  )
}
