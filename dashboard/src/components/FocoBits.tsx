import { useState } from 'react'
import { copiar, horasTxt, SEMAFORO, TEND } from '../lib/foco'
import type { Foco } from '../types'

export function Spark({ serie, label }: { serie: number[]; label: string }) {
  if (serie.length < 2) return null
  const max = Math.max(...serie), min = Math.min(...serie), span = Math.max(1, max - min)
  const pts = serie.map((v, i) => `${(i / (serie.length - 1)) * 60},${18 - ((v - min) / span) * 16}`).join(' ')
  return (
    <svg width="64" height="20" viewBox="0 0 60 20" role="img" aria-label={label} className="shrink-0 text-brand-300">
      <polyline points={pts} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function Reloj({ f }: { f: Foco }) {
  const s = SEMAFORO[f.semaforo]
  const atendido = f.estado === 'verificado' || f.estado === 'tratado' || f.estado === 'cerrado'
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-label font-medium ${s.chip}`}
      title="Horas del escenario simulado desde la primera detección hasta la verificación en campo. Rojo desde 24 h.">
      <span aria-hidden>{s.glifo}</span>{atendido ? `Atendido en ${horasTxt(f.horas_sin_atender)}` : `Sin atender ${horasTxt(f.horas_sin_atender)}`}
    </span>
  )
}

export function Tendencia({ f }: { f: Foco }) {
  return <span className="inline-flex items-center gap-1.5 text-label text-fg-muted" title="Plantas afectadas a lo largo del tiempo"><Spark serie={f.serie} label={`Plantas afectadas: de ${f.serie[0]} a ${f.serie[f.serie.length - 1]}`} />{TEND[f.tendencia]}</span>
}

export function CopiarAviso({ texto }: { texto: string }) {
  const [ok, setOk] = useState<boolean | null>(null)
  const click = async () => { setOk(await copiar(texto)); setTimeout(() => setOk(null), 2200) }
  return (
    <button type="button" className="btn" onClick={click}>
      Copiar aviso<span className="sr-only" role="status">{ok === true ? 'Aviso copiado' : ok === false ? 'No se pudo copiar' : ''}</span>
      {ok != null && <span aria-hidden className="text-label text-fg-subtle">{ok ? '✓ copiado' : '✕'}</span>}
    </button>
  )
}
