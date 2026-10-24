import { CLASES } from '../lib/catalogo'
import { hace, hora, zona } from '../lib/format'
import type { Clase, Incidencia, Modo, Resumen } from '../types'
import { Big, Tag } from './Card'
import { BloqueRobot } from './BloqueRobot'

interface Props {
  items: Incidencia[]
  resumen: Resumen
  modo: Modo
  ahora: number
  onZona: (q: string) => void
  onVer: () => void
  focosAbiertos?: number
  detecciones?: number
  sinAtender?: number
}

/** Tarjeta ancha destacada: responde en 5 s "¿hay alertas?, ¿dónde?, ¿qué enfermedad?". */
export function StatusBanner({ items, resumen, modo, ahora, onZona, onVer, focosAbiertos, detecciones, sinAtender }: Props) {
  // En vivo se espera a los focos: así el número grande no salta de "alertas" a "focos" al cargar.
  if (modo === 'conectando' || (modo === 'vivo' && focosAbiertos === undefined)) {
    return <section className="card p-6" aria-label="Estado general" aria-busy="true"><Tag>Estado del bloque</Tag><div className="skeleton mt-4 h-12 w-56" /><div className="skeleton mt-3 h-5 w-96 max-w-full" /></section>
  }
  const alertas = items.filter((i) => i.estado === 'Alerta')
  const activas = focosAbiertos ?? resumen.incidencias_activas ?? alertas.length
  const dets = detecciones ?? resumen.incidencias_activas ?? alertas.length
  const porFocos = focosAbiertos != null
  const hay = activas > 0

  const porClase = resumen.por_clase ?? alertas.reduce<Record<string, number>>((a, i) => ({ ...a, [i.clase]: (a[i.clase] ?? 0) + 1 }), {})
  const enf = Object.entries(porClase).filter(([c, n]) => c !== 'sana' && n > 0).sort((a, b) => b[1] - a[1])
  const totalEnf = enf.reduce((s, [, n]) => s + n, 0)
  const [topClase, topN] = enf[0] ?? []

  const zonas = new Map<string, { nave: number; cama: number; n: number }>()
  alertas.forEach((i) => { const k = `${i.nave}-${i.cama}`; const z = zonas.get(k) ?? { nave: i.nave, cama: i.cama, n: 0 }; z.n++; zonas.set(k, z) })
  const top = [...zonas.values()].sort((a, b) => b.n - a.n).slice(0, 3)
  const ultima = alertas[0]

  return (
    <section aria-label="Estado general" className={`card relative overflow-hidden p-5 md:p-6 ${hay ? '' : 'bg-[rgb(var(--c-mint))]'}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <Tag>Estado del bloque</Tag>
        <BloqueRobot actual={resumen.bloque} modo={modo} />
      </div>
      <div className="mt-3 flex flex-col gap-6 lg:flex-row lg:items-center lg:gap-10">
        <div className="flex items-center gap-4 lg:min-w-[20rem]">
          <span aria-hidden className={`grid h-14 w-14 shrink-0 place-items-center rounded-full text-2xl ${hay ? 'bg-danger/10 text-danger-300' : 'bg-white/70 text-[rgb(var(--c-mint-fg))]'}`}>{hay ? '▲' : '✓'}</span>
          <div>
            {hay ? <Big valor={String(activas)} size="text-[3.5rem]" /> : <p className="text-title font-semibold text-[rgb(var(--c-mint-fg))]">Sin alertas activas</p>}
            <p className="mt-1 text-body font-medium text-fg">{hay ? (porFocos ? (activas === 1 ? 'foco abierto' : 'focos abiertos') : (activas === 1 ? 'alerta activa' : 'alertas activas')) : 'El cultivo se ve estable en la última inspección.'}</p>
            {hay && porFocos && sinAtender ? <p className="text-label font-medium text-danger-300">{sinAtender} llevan más de 24 h sin atender</p> : null}
            {hay && <p className="text-label text-fg-muted">{porFocos ? `${dets} detecciones · ` : ''}{ultima ? <>última {modo === 'vivo' ? hace(ultima.ts * 1000, ahora) : hora(ultima)}</> : 'revisar la tabla de incidencias'}</p>}
          </div>
        </div>
        {hay && (
          <dl className="grid flex-1 grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2">
            <div>
              <dt className="tag">Enfermedad principal</dt>
              <dd className="mt-1 text-title font-semibold text-fg">
                {topClase ? <><span aria-hidden className="mr-1.5 text-danger-300">{CLASES[topClase as Clase]?.glifo}</span>{CLASES[topClase as Clase]?.nombre ?? topClase} <span className="text-body font-normal text-fg-muted">· {Math.round((100 * topN) / Math.max(1, totalEnf))} % de las detecciones</span></> : '—'}
              </dd>
            </div>
            <div>
              <dt className="tag">Camas con más detecciones</dt>
              <dd className="mt-1 flex flex-wrap gap-2">
                {top.map((z) => (
                  <button key={`${z.nave}-${z.cama}`} type="button" className="btn !min-h-[44px] !px-3 md:!min-h-[36px]" onClick={() => onZona(`N${z.nave} C${z.cama}`)} title="Filtrar la tabla por esta cama">
                    {zona(z.nave, z.cama)} <span className="rounded-full bg-danger/10 px-2 text-label tabular-nums text-danger-300">{z.n}</span>
                  </button>
                ))}
              </dd>
            </div>
          </dl>
        )}
        {hay && <button type="button" onClick={onVer} className="btn btn-primary lg:ml-auto">Ver qué atender ↓</button>}
      </div>
    </section>
  )
}
