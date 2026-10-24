import { useState } from 'react'
import type { Cobertura, NivelRiesgo, Riesgo } from '../types'
import { Card } from './Card'

const TONO: Record<NivelRiesgo, { c: string; g: string; t: string }> = {
  bajo: { c: 'bg-[rgb(var(--c-mint))] text-[rgb(var(--c-mint-fg))]', g: '✓', t: 'Bajo' },
  medio: { c: 'bg-warn/20 text-warn-300 border-warn/50', g: '◆', t: 'Medio' },
  alto: { c: 'bg-danger/20 text-danger-300 border-danger/50', g: '▲', t: 'Alto' },
}
const VENT = ['Ahora', '0-24 h', '24-48 h', '48-72 h']

export function RiesgoCard({ riesgo, className, cargando }: { riesgo: Riesgo | null; className?: string; cargando: boolean }) {
  const [v, setV] = useState('0-24 h')
  if (!riesgo) {
    return <Card n="10" tag="Riesgo próximo" id="riesgo" className={`scroll-mt-32 ${className ?? ''}`} label="Riesgo próximo 24 a 72 horas" title="Riesgo próximo (24–72 h)">
      {cargando ? <div className="skeleton h-40 w-full" /> : <p className="text-body text-fg-muted">Sin datos de riesgo: el simulador aún no tiene una sesión activa.</p>}
    </Card>
  }
  const naves = Math.max(...riesgo.camas.map((c) => c.nave)), camas = Math.max(...riesgo.camas.map((c) => c.cama))
  const dato = (n: number, c: number) => {
    const cm = riesgo.camas.find((x) => x.nave === n && x.cama === c)
    if (!cm) return null
    if (v === 'Ahora') return { nivel: cm.ahora.nivel, riesgo: cm.ahora.riesgo, extra: '' }
    const w = cm.ventanas.find((x) => x.horas === v)
    return w ? { nivel: w.nivel, riesgo: w.riesgo, extra: `${w.horas_mojadas} h de hoja mojada, ${w.horas_hr_alta} h de HR alta, ${w.enfermedad_nombre}` } : null
  }
  const altas = riesgo.camas.filter((c) => c.nivel === 'alto').length
  const medias = riesgo.camas.filter((c) => c.nivel === 'medio').length
  const mojada = riesgo.clima?.horas_mojadas_hoy ?? 0
  const titulo = altas ? `${altas} ${altas === 1 ? 'cama' : 'camas'} con riesgo alto en las próximas 72 h` : medias ? `${medias} ${medias === 1 ? 'cama' : 'camas'} con riesgo medio; ninguna alta` : 'Riesgo bajo en todas las camas'
  return (
    <Card n="10" tag="Riesgo próximo" id="riesgo" className={`scroll-mt-32 ${className ?? ''}`} label="Riesgo próximo 24 a 72 horas" title={titulo}
      sub="Estimado con el clima · orientativo">
      {!altas && !medias && mojada > 0 && <p className="mb-3 rounded-2xl bg-ink-900 px-3 py-2 text-label text-fg-muted">Hoy hubo {mojada} h de hoja mojada, pero con el frío actual los modelos de Botrytis, antracnosis y roya no llegan a «medio». Que el agrónomo lo valide en campo.</p>}
      <div role="group" aria-label="Ventana de tiempo" className="mb-3 flex flex-wrap gap-2">
        {VENT.map((x) => <button key={x} type="button" className="pill !min-h-[44px] md:!min-h-[36px]" aria-current={v === x ? 'true' : undefined} onClick={() => setV(x)}>{x}</button>)}
      </div>
      <div className="grid gap-1.5" style={{ gridTemplateColumns: `auto repeat(${camas}, minmax(0, 1fr))` }} role="table" aria-label={`Riesgo por nave y cama, ventana ${v}`}>
        <div role="row" className="contents">
          <span role="columnheader" className="pb-1 text-label text-fg-subtle">Nave</span>
          {Array.from({ length: camas }, (_, c) => <span role="columnheader" key={c} className="pb-1 text-center text-label text-fg-subtle">Cama {c + 1}</span>)}
        </div>
        {Array.from({ length: naves }, (_, n) => (
          <div role="row" className="contents" key={n}>
            <span role="rowheader" className="pr-2 text-label leading-[3rem] text-fg-muted">Nave {n + 1}</span>
            {Array.from({ length: camas }, (_, c) => {
              const d = dato(n + 1, c + 1)
              if (!d) return <div role="cell" key={c} className="h-12 rounded-2xl border border-ink-700" />
              const t = TONO[d.nivel]
              return <div role="cell" key={c} title={`Nave ${n + 1} · Cama ${c + 1}: riesgo ${t.t.toLowerCase()} (${Math.round(d.riesgo * 100)} %). ${d.extra}`}
                className={`flex h-12 items-center justify-center gap-1 rounded-2xl border border-transparent text-label font-semibold tabular-nums ${t.c}`}>
                <span aria-hidden>{t.g}</span><span>{t.t}<span className="sr-only"> riesgo en nave {n + 1} cama {c + 1}</span></span>
              </div>
            })}
          </div>
        ))}
      </div>
      {(() => {
        const top = [...riesgo.camas].sort((a, b) => b.max_riesgo - a.max_riesgo)[0]
        const u = riesgo.umbrales
        return top ? <details className="mt-3 text-label text-fg-subtle"><summary className="cursor-pointer select-none hover:text-fg-muted">Detalle del cálculo</summary><p className="mt-1">Mayor índice estimado: Nave {top.nave} · Cama {top.cama}, {Math.round(top.max_riesgo * 100)} %{riesgo.clima ? ` · ${riesgo.clima.horas_mojadas_hoy} h de hoja mojada hoy` : ''}.
          {u ? ` Pasa a «medio» desde ${Math.round(u.botrytis[0] * 100)} % (Botrytis), ${Math.round(u.anthracnose[0] * 100)} % (antracnosis) o ${Math.round(u.rust[0] * 100)} % (roya).` : ''}</p></details> : null
      })()}
      <h3 className="mt-5 text-body font-semibold text-fg">Avisos preventivos</h3>
      {riesgo.avisos.length === 0 ? <p className="mt-1 text-body text-fg-muted">Sin avisos en las próximas 72 h.</p> : (
        <ul className="mt-2 space-y-2">
          {riesgo.avisos.map((a) => (
            <li key={a.id} className="rounded-2xl border border-ink-700 bg-ink-900/60 p-3 text-body text-fg">
              <span className={`mr-2 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-label font-medium ${a.nivel === 'alto' ? TONO.alto.c : TONO.medio.c}`}><span aria-hidden>{TONO[a.nivel].g}</span>{TONO[a.nivel].t}</span>
              {a.texto}
              <span className="mt-1 block text-label text-fg-subtle">{a.nota}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

export function CoberturaCard({ cobertura, className }: { cobertura: Cobertura | null; className?: string }) {
  if (!cobertura) return <Card n="11" tag="Cobertura" className={className} label="Cobertura del robot" title="Cobertura del robot"><p className="text-body text-fg-muted">Sin datos de cobertura todavía.</p></Card>
  const naves = Math.max(...cobertura.camas.map((c) => c.nave)), camas = Math.max(...cobertura.camas.map((c) => c.cama))
  const ciegos = cobertura.puntos_ciegos
  const nunca = cobertura.camas.filter((c) => c.horas_sin_revisar == null).length
  return (
    <Card n="11" tag="Cobertura" className={className} label="Cobertura del robot por cama"
      title={ciegos.length ? `${ciegos.length} ${ciegos.length === 1 ? 'cama' : 'camas'} sin revisar en más de ${cobertura.ciego_h} h` : `Todas las camas revisadas en las últimas ${cobertura.ciego_h} h`}
      sub={`Última inspección del robot por cama${nunca ? ` · ${nunca} aún sin primera visita` : ''} (horas del escenario)`}>
      <div className="grid gap-1.5" style={{ gridTemplateColumns: `auto repeat(${camas}, minmax(0, 1fr))` }} role="table" aria-label="Última inspección por nave y cama">
        <div role="row" className="contents">
          <span role="columnheader" className="pb-1 text-label text-fg-subtle">Nave</span>
          {Array.from({ length: camas }, (_, c) => <span role="columnheader" key={c} className="pb-1 text-center text-label text-fg-subtle">C{c + 1}</span>)}
        </div>
        {Array.from({ length: naves }, (_, n) => (
          <div role="row" className="contents" key={n}>
            <span role="rowheader" className="pr-2 text-label leading-[3rem] text-fg-muted">N{n + 1}</span>
            {Array.from({ length: camas }, (_, c) => {
              const x = cobertura.camas.find((k) => k.nave === n + 1 && k.cama === c + 1)
              if (!x) return <div role="cell" key={c} />
              const txt = x.horas_sin_revisar == null ? 'Sin visita' : x.horas_sin_revisar < 1 ? 'Ahora' : `${Math.round(x.horas_sin_revisar)} h`
              return <div role="cell" key={c} title={`Nave ${n + 1} · Cama ${c + 1}: ${x.ultima_hora ? `última visita día ${x.ultima_dia} ${x.ultima_hora}` : 'sin visita del robot'}`}
                className={`flex h-12 items-center justify-center gap-1 rounded-2xl border text-label font-semibold tabular-nums ${x.ciego ? 'border-warn/50 bg-warn/20 text-warn-300' : 'border-transparent bg-[rgb(var(--c-mint))] text-[rgb(var(--c-mint-fg))]'}`}>
                <span aria-hidden>{x.ciego ? '◆' : '✓'}</span>{txt}{x.ciego && <span className="sr-only"> punto ciego</span>}
              </div>
            })}
          </div>
        ))}
      </div>
      {ciegos.length > 0 && <p className="mt-3 text-body text-fg-muted"><b className="text-fg">Sin revisar:</b> {ciegos.map((c) => `N${c.nave} C${c.cama}`).join(', ')}.</p>}
    </Card>
  )
}
