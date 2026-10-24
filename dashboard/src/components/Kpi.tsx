import { Area, AreaChart, ResponsiveContainer, YAxis } from 'recharts'
import type { ReactNode } from 'react'
import type { Evaluacion, Semaforo } from '../lib/umbrales'
import { Big, Card } from './Card'

interface Props {
  n: string
  tag: string
  titulo: string
  valor: string
  unidad?: string
  serie: number[]
  eval: Evaluacion
  referencia: string
  nota?: string
  decimales?: number
  cargando?: boolean
  onOpen?: () => void
  openLabel?: string
  className?: string
  extra?: ReactNode // p. ej. anillo de progreso
}

const TONO: Record<Semaforo, { chip: string; glifo: string; color: string }> = {
  ok: { chip: 'bg-[rgb(var(--c-mint))] text-[rgb(var(--c-mint-fg))] border-transparent', glifo: '✓', color: 'rgb(var(--c-pos))' },
  atencion: { chip: 'bg-warn/15 text-warn-300 border-warn/40', glifo: '◆', color: 'rgb(var(--c-warn))' },
  critico: { chip: 'bg-danger/10 text-danger-300 border-danger/40', glifo: '▲', color: 'rgb(var(--c-danger))' },
  nd: { chip: 'bg-ink-900 text-fg-muted border-ink-700', glifo: '–', color: 'rgb(var(--c-brand-300))' },
}

export function Kpi({ n, tag, titulo, valor, unidad, serie, eval: ev, referencia, nota, decimales = 1, cargando, onOpen, openLabel, className, extra }: Props) {
  const t = TONO[ev.nivel]
  const data = serie.map((v, i) => ({ i, v }))
  const delta = serie.length > 1 ? serie[serie.length - 1] - serie[0] : 0
  const quieto = Math.abs(delta) < 0.05
  return (
    <Card n={n} tag={tag} label={titulo} onOpen={onOpen} openLabel={openLabel} className={`flex flex-col ${className ?? ''}`}>
      <h2 className="sr-only">{titulo}</h2>
      <div className="mt-3 flex items-end justify-between gap-3">
        {cargando ? <div className="skeleton h-12 w-32" aria-label="Cargando" /> : <Big valor={valor} unidad={unidad} />}
        {extra}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-label font-medium ${t.chip}`}><span aria-hidden>{t.glifo}</span>{ev.texto}</span>
        {serie.length > 1 && (
          <span className="inline-flex items-center rounded-full bg-ink-900 px-2.5 py-0.5 text-label tabular-nums text-fg-muted" title="Variación en la ventana mostrada">
            {quieto ? '= Estable' : `${delta > 0 ? '▲' : '▼'} ${Math.abs(delta).toFixed(decimales).replace('.', ',')}`}
          </span>
        )}
      </div>
      <p className="mt-3 text-label text-fg-muted">{referencia}{nota ? <span className="text-fg-subtle"> · {nota}</span> : null}</p>
      <div className="mt-3 h-12" aria-hidden>
        {data.length > 1 && (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
              <YAxis hide domain={['dataMin', 'dataMax']} />
              <Area type="monotone" dataKey="v" stroke={t.color} strokeWidth={2} fill={t.color} fillOpacity={0.1} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  )
}

/** Anillo punteado de porcentaje (estilo panel técnico). */
export function Anillo({ pct, tono }: { pct: number; tono: Semaforo }) {
  const r = 30, c = 2 * Math.PI * r
  const color = TONO[tono].color
  const lleno = Math.max(0, Math.min(100, pct))
  return (
    <svg width="76" height="76" viewBox="0 0 76 76" aria-hidden className="shrink-0">
      <circle cx="38" cy="38" r={r} fill="none" stroke="rgb(var(--c-ink-700))" strokeWidth="6" strokeDasharray="1.5 4.5" strokeLinecap="round" />
      <circle cx="38" cy="38" r={r} fill="none" stroke={color} strokeWidth="6" strokeDasharray={`${(c * lleno) / 100} ${c}`} strokeLinecap="round" transform="rotate(-90 38 38)" opacity=".9" />
    </svg>
  )
}
