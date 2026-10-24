import { forwardRef, useEffect, useMemo, useState } from 'react'
import { FUENTE, CLASES, urgencia } from '../lib/catalogo'
import { hora, num } from '../lib/format'
import { Tag } from './Card'
import { ClaseBadge, NivelBadge } from './Badge'
import type { Incidencia } from '../types'

export interface Filtros { q: string; estado: 'todos' | 'Alerta' | 'Saludable'; clase: string }
export const FILTROS_INICIALES: Filtros = { q: '', estado: 'todos', clase: 'todas' }

type Col = 'prioridad' | 'ts' | 'ubicacion' | 'deteccion' | 'temperatura_c' | 'humedad_pct' | 'confianza' | 'fuente'
const COLS: { k: Col; t: string; num?: boolean; tip?: string }[] = [
  { k: 'ts', t: 'Hora', tip: 'Día de la simulación y hora' },
  { k: 'ubicacion', t: 'Ubicación', tip: 'N = nave · C = cama · P = planta' },
  { k: 'deteccion', t: 'Detección' },
  { k: 'prioridad', t: 'Urgencia', tip: 'Alta: hongos (oídio, alternaria) · Media: plaga (heliothis)' },
  { k: 'temperatura_c', t: 'Temp.', num: true, tip: 'Temperatura en °C' },
  { k: 'humedad_pct', t: 'HR', num: true, tip: 'Humedad relativa en %' },
  { k: 'confianza', t: 'Confianza', num: true, tip: 'Seguridad del modelo en la detección' },
  { k: 'fuente', t: 'Fuente' },
]
const PAGE = 10

function cmp(a: Incidencia, b: Incidencia, k: Col): number {
  switch (k) {
    case 'prioridad': return urgencia(a) - urgencia(b)
    case 'ubicacion': return a.nave - b.nave || a.cama - b.cama || (a.planta ?? 0) - (b.planta ?? 0)
    case 'deteccion': return (CLASES[a.clase]?.nombre ?? '').localeCompare(CLASES[b.clase]?.nombre ?? '', 'es')
    case 'fuente': return a.fuente.localeCompare(b.fuente)
    default: {
      const x = a[k], y = b[k]
      if (x == null) return y == null ? 0 : -1 // vacíos siempre al final en asc
      if (y == null) return 1
      return (x as number) - (y as number)
    }
  }
}

interface Props {
  items: Incidencia[]
  nuevos: Set<string>
  cargando: boolean
  filtros: Filtros
  setFiltros: (f: Filtros) => void
  onSelect: (i: Incidencia) => void
}

export const IncidentTable = forwardRef<HTMLElement, Props>(function IncidentTable({ items, nuevos, cargando, filtros, setFiltros, onSelect }, ref) {
  const [sort, setSort] = useState<{ k: Col; dir: 1 | -1 }>({ k: 'prioridad', dir: 1 })
  const [page, setPage] = useState(0)
  const { q, estado, clase } = filtros
  const set = (p: Partial<Filtros>) => { setFiltros({ ...filtros, ...p }); setPage(0) }

  const rows = useMemo(() => {
    const s = q.trim().toLowerCase()
    const f = items.filter((i) =>
      (estado === 'todos' || i.estado === estado) && (clase === 'todas' || i.clase === clase) &&
      (!s || `${i.ubicacion} ${i.deteccion} ${i.estado} ${FUENTE[i.fuente]}`.toLowerCase().includes(s)))
    // Prioridad: alertas primero, luego gravedad, luego lo más reciente; el resto de columnas desempata por recencia.
    return f.sort((a, b) => sort.dir * cmp(a, b, sort.k) || b.ts - a.ts)
  }, [items, q, estado, clase, sort])

  const pages = Math.max(1, Math.ceil(rows.length / PAGE))
  useEffect(() => { if (page >= pages) setPage(pages - 1) }, [page, pages])
  const view = rows.slice(page * PAGE, page * PAGE + PAGE)
  const hayFiltro = q !== '' || estado !== 'todos' || clase !== 'todas'
  const cuenta = (e: Filtros['estado']) => (e === 'todos' ? items.length : items.filter((i) => i.estado === e).length)
  const porColumna = (k: Col) => setSort((s) => (s.k === k ? { k, dir: (-s.dir) as 1 | -1 } : { k, dir: k === 'ts' || k === 'confianza' ? -1 : 1 }))
  const orden = sort.k === 'prioridad' && sort.dir === 1 ? 'prioridad' : sort.k === 'ts' && sort.dir === -1 ? 'recientes' : 'otro'

  const seg = (v: Filtros['estado'], t: string) => (
    <button key={v} type="button" aria-pressed={estado === v} onClick={() => set({ estado: v })} disabled={v !== 'todos' && cuenta(v) === 0 && estado !== v}
      className={`min-h-[40px] whitespace-nowrap rounded-full px-3 text-body disabled:opacity-40 md:min-h-[34px] ${estado === v ? 'bg-brand font-semibold text-white' : 'text-fg-muted hover:bg-ink-800 disabled:hover:bg-transparent'}`}>
      {t} <span className={`tabular-nums ${estado === v ? "text-white/80" : "text-fg-subtle"}`}>{cuenta(v)}</span>
    </button>
  )
  return (
    <section ref={ref} className="card scroll-mt-32 overflow-hidden" aria-label="Incidencias" id="incidencias">
      <div className="space-y-3 p-5 pb-4 md:p-6 md:pb-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <Tag>Registro</Tag>
            <h2 className="mt-1 text-title font-semibold text-fg">Todas las detecciones <span className="text-body font-normal tabular-nums text-fg-muted">· {hayFiltro ? `${rows.length} de ${items.length}` : rows.length}</span></h2>
          </div>
          <label className="sr-only" htmlFor="ord">Ordenar por</label>
          <select id="ord" value={orden} className="ctl" onChange={(e) => { setSort(e.target.value === 'recientes' ? { k: 'ts', dir: -1 } : { k: 'prioridad', dir: 1 }); setPage(0) }}>
            <option value="prioridad">Más urgentes primero</option>
            <option value="recientes">Más recientes primero</option>
            {orden === 'otro' && <option value="otro">Ordenado por columna</option>}
          </select>
        </div>
        {/* Una sola barra de filtros: estado, tipo y búsqueda; "Limpiar" solo aparece si hay algo filtrado */}
        <div className="flex flex-wrap items-center gap-2 rounded-[22px] border border-ink-700 bg-ink-900 p-1.5" role="search" aria-label="Filtros de la tabla">
          <div className="inline-flex gap-1" role="group" aria-label="Filtrar por estado">
            {seg('todos', 'Todas')}{seg('Alerta', 'Alertas')}{seg('Saludable', 'Sanas')}
          </div>
          <span className="hidden h-6 w-px bg-ink-700 sm:block" aria-hidden />
          <label className="sr-only" htmlFor="fc">Tipo de detección</label>
          <select id="fc" value={clase} data-activo={clase !== 'todas' ? '1' : undefined} onChange={(e) => set({ clase: e.target.value })} className="ctl !min-h-[40px] md:!min-h-[34px]">
            <option value="todas">Todos los tipos</option>
            {(['oidio', 'alternaria', 'heliothis', 'sana'] as const).map((c) => <option key={c} value={c}>{CLASES[c].nombre}</option>)}
          </select>
          <label className="sr-only" htmlFor="q">Buscar por ubicación o detección</label>
          <div className="relative min-w-[12rem] flex-1">
            <svg aria-hidden width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-fg-subtle"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
            <input id="q" type="search" placeholder="Buscar cama o enfermedad (N2 C3, oídio…)" value={q} onChange={(e) => set({ q: e.target.value })} className="ctl !min-h-[40px] w-full !pl-10 md:!min-h-[34px]" />
          </div>
          {hayFiltro && <button type="button" className="btn !min-h-[40px] md:!min-h-[34px]" onClick={() => { setFiltros(FILTROS_INICIALES); setPage(0) }}>Limpiar</button>}
        </div>
      </div>

      {/* Escritorio: tabla */}
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-body">
          <caption className="sr-only">Incidencias detectadas. Seleccione una fila para ver el detalle y qué hacer.</caption>
          <thead className="border-y border-ink-700 bg-ink-900 text-left font-mono text-[.6875rem] uppercase tracking-[.1em] text-fg-muted">
            <tr>
              {COLS.map((c) => (
                <th key={c.k} scope="col" title={c.tip} aria-sort={sort.k === c.k ? (sort.dir === 1 ? 'ascending' : 'descending') : 'none'} className={`px-3 py-2 ${c.num ? 'text-right' : ''}`}>
                  <button type="button" className="inline-flex min-h-[32px] items-center gap-1 font-semibold uppercase hover:text-gold-300" onClick={() => { porColumna(c.k); setPage(0) }}>
                    {c.t}<span aria-hidden className="w-3 text-brand-300">{sort.k === c.k ? (sort.dir === 1 ? '▲' : '▼') : ''}</span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cargando && Array.from({ length: 6 }, (_, k) => <tr key={k} className="border-t border-ink-700"><td colSpan={COLS.length} className="px-3 py-3"><div className="skeleton h-5 w-full" /></td></tr>)}
            {!cargando && view.length === 0 && <tr><td colSpan={COLS.length} className="px-3 py-10 text-center text-fg-muted"><Vacio hayFiltro={hayFiltro} onLimpiar={() => { setFiltros(FILTROS_INICIALES); setPage(0) }} /></td></tr>}
            {view.map((i) => (
              <tr key={i.id} onClick={() => onSelect(i)} className={`cursor-pointer border-t border-ink-700/70 hover:bg-ink-900 ${nuevos.has(i.id) ? 'row-new' : ''}`}>
                <td className="whitespace-nowrap px-3 py-2.5 tabular-nums text-fg-muted">{hora(i)}</td>
                <td className="whitespace-nowrap px-3 py-2 font-medium tabular-nums text-fg">
                  <button type="button" className="rounded underline decoration-ink-600 decoration-dotted underline-offset-4 hover:decoration-gold" onClick={(e) => { e.stopPropagation(); onSelect(i) }} aria-label={`Ver detalle de ${i.ubicacion}`}>
                    N{i.nave} · C{i.cama}{i.planta != null ? ` · P${i.planta}` : ''}
                  </button>
                </td>
                <td className="px-3 py-2"><ClaseBadge clase={i.clase} estado={i.estado} /></td>
                <td className="px-3 py-2"><NivelBadge item={i} /></td>
                <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">{num(i.temperatura_c)} °C</td>
                <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">{num(i.humedad_pct, 0)} %</td>
                <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">{i.confianza != null ? `${Math.round(i.confianza * 100)} %` : '—'}</td>
                <td className="px-3 py-2 text-fg-muted">{FUENTE[i.fuente]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Móvil: tarjetas */}
      <ul className="divide-y divide-ink-700 md:hidden">
        {cargando && <li className="p-3"><div className="skeleton h-16 w-full" /></li>}
        {!cargando && view.length === 0 && <li className="px-3 py-8 text-center text-fg-muted"><Vacio hayFiltro={hayFiltro} onLimpiar={() => { setFiltros(FILTROS_INICIALES); setPage(0) }} /></li>}
        {view.map((i) => (
          <li key={i.id} className={nuevos.has(i.id) ? 'row-new' : ''}>
            <button type="button" onClick={() => onSelect(i)} className="block w-full p-3 text-left hover:bg-ink-700/60">
              <span className="flex items-center justify-between gap-2"><span className="font-semibold tabular-nums text-fg">N{i.nave} · C{i.cama}{i.planta != null ? ` · P${i.planta}` : ''}</span><span className="text-label text-fg-muted">{hora(i)}</span></span>
              <span className="mt-1.5 flex flex-wrap items-center gap-2"><ClaseBadge clase={i.clase} estado={i.estado} /><NivelBadge item={i} /></span>
              <span className="mt-1.5 block text-label tabular-nums text-fg-muted">{num(i.temperatura_c)} °C · HR {num(i.humedad_pct, 0)} % · {FUENTE[i.fuente]}</span>
            </button>
          </li>
        ))}
      </ul>

      <nav className="flex flex-wrap items-center justify-between gap-2 border-t border-ink-700 p-4 text-body text-fg-muted" aria-label="Paginación">
        <span>{rows.length ? `${page * PAGE + 1}–${Math.min(rows.length, page * PAGE + PAGE)} de ${rows.length}` : '0 resultados'} · Página {page + 1} de {pages}</span>
        <span className="flex gap-2">
          <button type="button" disabled={page === 0} onClick={() => setPage(page - 1)} className="btn">← Anterior</button>
          <button type="button" disabled={page >= pages - 1} onClick={() => setPage(page + 1)} className="btn">Siguiente →</button>
        </span>
      </nav>
    </section>
  )
})

function Vacio({ hayFiltro, onLimpiar }: { hayFiltro: boolean; onLimpiar: () => void }) {
  return hayFiltro
    ? <div className="space-y-3"><p>Ninguna incidencia coincide con los filtros.</p><button type="button" className="btn" onClick={onLimpiar}>Limpiar filtros</button></div>
    : <p>Aún no hay incidencias. Aparecerán aquí cuando el robot detecte algo.</p>
}
