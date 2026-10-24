import { useEffect, useRef, useState } from 'react'
import { CLASES } from '../lib/catalogo'
import { ESTADO_TXT, PASOS, horasTxt, siguienteAccion } from '../lib/foco'
import { API_URL } from '../lib/useIncidents'
import type { AccionIn } from '../lib/usePrevencion'
import type { AccionHist, Foco } from '../types'
import { ClaseBadge } from './Badge'
import { CopiarAviso, Reloj, Tendencia } from './FocoBits'

export function Foto({ frame, fuente }: { frame: string | null | undefined; fuente: string }) {
  const [falla, setFalla] = useState(false)
  if (fuente === 'camara_d1' && frame && !falla) {
    return <img src={`${API_URL}/api/dashboard/captura?f=${encodeURIComponent(frame)}`} alt={`Foto de la cámara del D1 (${frame})`} onError={() => setFalla(true)} className="aspect-video w-full rounded-2xl border border-ink-700 object-cover" />
  }
  return (
    <div className="grid aspect-video w-full place-items-center rounded-2xl border border-dashed border-ink-600 bg-ink-900 p-3 text-center text-label text-fg-muted">
      {fuente === 'camara_d1' ? 'Sin foto disponible para esta detección' : 'Sin foto (simulación)'}
    </div>
  )
}

const fecha = (ts: number) => new Date(ts * 1000).toLocaleString('es-CO', { hour12: false, dateStyle: 'short', timeStyle: 'short' })
const TXT_ACC: Record<string, string> = { asignar: 'Supervisor envió operario', verificar: 'Operario confirmó en campo', tratar: 'Tratado', cerrar: 'Cerrado', nota: 'Nota' }

export function FocoPanel({ foco, accionInicial, puedeActuar, onClose, onAccion, historial }: {
  foco: Foco; accionInicial?: string; puedeActuar: boolean; onClose: () => void
  onAccion: (id: string, b: AccionIn) => Promise<string | null>; historial: (id: string) => Promise<AccionHist[]>
}) {
  const ref = useRef<HTMLButtonElement>(null)
  const [hist, setHist] = useState<AccionHist[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)
  const [responsable, setResponsable] = useState('')
  const [resultado, setResultado] = useState<'confirmado' | 'falsa_alarma'>('confirmado')
  const [detalle, setDetalle] = useState('')
  const [nota, setNota] = useState('')
  const closeRef = useRef(onClose)
  closeRef.current = onClose
  const sig = siguienteAccion(foco)
  const info = CLASES[foco.clase] ?? CLASES.desconocida

  useEffect(() => { historial(foco.id).then(setHist) }, [foco.id, foco.estado, historial])
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null
    ref.current?.focus()
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeRef.current()
      if (e.key === 'Tab') {
        const f = document.querySelectorAll<HTMLElement>('[data-panel] button:not([disabled]), [data-panel] a, [data-panel] input, [data-panel] select, [data-panel] textarea')
        if (!f.length) return
        const first = f[0], last = f[f.length - 1]
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
      }
    }
    document.addEventListener('keydown', key)
    return () => { document.removeEventListener('keydown', key); prev?.focus?.() }
  }, [])

  const enviar = async (b: AccionIn) => {
    setEnviando(true); setErr(null)
    const e = await onAccion(foco.id, b)
    setEnviando(false)
    if (e) setErr(e); else { setNota(''); setDetalle('') }
  }
  const campo = 'w-full rounded-2xl border border-ink-600 bg-ink-800 px-3 py-2 text-body text-fg min-h-[44px]'

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-[rgb(17_24_39/.35)] backdrop-blur-[2px]" onClick={onClose}>
      <aside data-panel role="dialog" aria-modal="true" aria-labelledby="foco-t" onClick={(e) => e.stopPropagation()}
        className="slide-in glass flex h-full w-full max-w-lg flex-col overflow-y-auto rounded-l-[28px] border-l border-ink-700 p-6 shadow-pop">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="tag">Foco · ciclo de acción</p>
            <h2 id="foco-t" className="mt-1 text-xl font-semibold leading-tight text-fg">Nave {foco.nave} · Cama {foco.cama} · {foco.ubicacion.split(' ').pop()}</h2>
            <p className="mt-1 flex flex-wrap items-center gap-2 text-body text-fg-muted"><ClaseBadge clase={foco.clase} />{foco.plantas} plantas · {foco.detecciones} detecciones</p>
          </div>
          <button ref={ref} type="button" onClick={onClose} className="btn" aria-label="Cerrar detalle del foco">Cerrar ✕</button>
        </div>

        <p className="mt-3 rounded-2xl bg-ink-900 px-3 py-2 text-label text-fg-muted"><b className="text-fg">Quién actúa:</b> el robot sugiere → el <b className="text-fg">supervisor</b> lo ve aquí y envía a un <b className="text-fg">operario</b> → el operario confirma en campo si es enfermedad o falsa alarma → se registra el tratamiento y se cierra.</p>
        <ol className="mt-3 flex flex-wrap gap-1.5" aria-label="Estado del foco">
          {PASOS.map((p) => {
            const i = PASOS.indexOf(p), a = PASOS.indexOf(foco.estado)
            return <li key={p} aria-current={p === foco.estado ? 'step' : undefined} className={`rounded-full border px-3 py-1 text-label font-medium ${p === foco.estado ? 'border-brand bg-brand text-white' : i < a ? 'border-transparent bg-[rgb(var(--c-mint))] text-[rgb(var(--c-mint-fg))]' : 'border-ink-700 text-fg-subtle'}`}>{i < a ? '✓ ' : ''}{ESTADO_TXT[p]}</li>
          })}
        </ol>
        {foco.resultado && <p className="mt-2 text-body text-fg-muted">Verificación: <b className="text-fg">{foco.resultado === 'confirmado' ? 'Confirmado' : 'Falsa alarma'}</b>{foco.responsable ? ` · ${foco.responsable}` : ''}{foco.tratamiento ? ` · Tratamiento: ${foco.tratamiento}` : ''}</p>}

        <div className="mt-4 flex flex-wrap items-center gap-3"><Reloj f={foco} /><Tendencia f={foco} /></div>
        <p className="mt-3 text-body text-fg-muted"><b className="text-fg">Por qué es prioritario:</b> {foco.por_que.join(' · ')}. Puntaje {Math.round(foco.puntaje)}/100.</p>

        <h3 className="mt-5 text-title font-semibold text-fg">Foto</h3>
        <div className="mt-2"><Foto frame={foco.frame} fuente={foco.fuentes.includes('camara_d1') ? 'camara_d1' : 'simulacion'} /></div>

        <h3 className="mt-5 text-title font-semibold text-fg">Qué hacer</h3>
        <ol className="mt-1 list-decimal space-y-1 pl-5 text-body text-fg-muted">{info.queHacer.map((a) => <li key={a}>{a}</li>)}</ol>
        <p className="mt-1 text-label text-fg-subtle">Recomendación orientativa; confirmar con el agrónomo.</p>

        <h3 className="mt-5 text-title font-semibold text-fg">Registrar acción</h3>
        {!puedeActuar && <p className="mt-1 rounded-2xl bg-ink-900 p-3 text-body text-fg-muted">Con datos de ejemplo no se guardan acciones. Conecta el simulador para usar el ciclo.</p>}
        {puedeActuar && sig && (
          <form className="mt-2 space-y-3" onSubmit={(e) => { e.preventDefault(); const b: AccionIn = { accion: sig.accion }
            if (sig.accion === 'asignar') b.responsable = responsable
            if (sig.accion === 'verificar') { b.resultado = resultado; if (nota.trim()) b.nota = nota }
            if (sig.accion === 'tratar') b.detalle = detalle
            enviar(b) }}>
            {sig.accion === 'asignar' && <label className="block text-label text-fg-muted">¿Qué operario va a confirmar en campo?<input className={`${campo} mt-1`} value={responsable} onChange={(e) => setResponsable(e.target.value)} placeholder="Nombre del operario" autoFocus={accionInicial === 'asignar'} required /></label>}
            {sig.accion === 'verificar' && (
              <fieldset className="space-y-2"><legend className="text-label text-fg-muted">¿Qué encontró el operario en campo?</legend>
                {(['confirmado', 'falsa_alarma'] as const).map((r) => <label key={r} className="flex min-h-[44px] items-center gap-2 text-body text-fg"><input type="radio" name="res" checked={resultado === r} onChange={() => setResultado(r)} className="h-5 w-5 accent-[rgb(var(--c-brand))]" />{r === 'confirmado' ? 'Confirmado: hay enfermedad o plaga' : 'Falsa alarma: la planta está sana'}</label>)}
              </fieldset>
            )}
            {sig.accion === 'tratar' && <label className="block text-label text-fg-muted">¿Qué se hizo?<textarea className={`${campo} mt-1`} rows={2} value={detalle} onChange={(e) => setDetalle(e.target.value)} placeholder="Ej.: poda de hojas afectadas y aplicación indicada por el agrónomo" required /></label>}
            <button type="submit" className="btn btn-primary" disabled={enviando}>{sig.texto}</button>
          </form>
        )}
        {puedeActuar && !sig && <p className="mt-1 text-body text-fg-muted">Foco cerrado.</p>}
        {err && <p role="alert" className="mt-2 rounded-2xl border border-danger/40 bg-danger/10 px-3 py-2 text-body text-danger-300">{err}</p>}

        {puedeActuar && foco.estado !== 'cerrado' && (
          <form className="mt-4 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (nota.trim()) enviar({ accion: 'nota', nota }) }}>
            <label className="sr-only" htmlFor="nota-foco">Añadir una nota</label>
            <input id="nota-foco" className={campo} value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Añadir una nota…" />
            <button type="submit" className="btn" disabled={enviando || !nota.trim()}>Añadir</button>
          </form>
        )}

        <h3 className="mt-5 text-title font-semibold text-fg">Historial</h3>
        {hist.length === 0 ? <p className="text-body text-fg-muted">Sin acciones todavía: el foco está en «Nuevo».</p> : (
          <ol className="mt-1 space-y-2">
            {hist.map((h) => (
              <li key={h.id} className="rounded-2xl border border-ink-700 bg-ink-900/60 px-3 py-2 text-body">
                <b className="text-fg">{TXT_ACC[h.accion] ?? h.accion}</b> <span className="text-label text-fg-subtle">· {fecha(h.ts)}</span>
                <p className="text-fg-muted">{[h.responsable, h.resultado && (h.resultado === 'confirmado' ? 'Confirmado' : 'Falsa alarma'), h.detalle, h.nota].filter(Boolean).join(' · ')}</p>
              </li>
            ))}
          </ol>
        )}
        <div className="mt-5 flex flex-wrap items-center gap-2"><CopiarAviso texto={foco.aviso} /><span className="text-label text-fg-subtle">Antigüedad en horas del escenario simulado ({horasTxt(foco.horas_sin_atender)}).</span></div>
      </aside>
    </div>
  )
}
