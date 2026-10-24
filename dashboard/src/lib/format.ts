import type { Incidencia } from '../types'

export const num = (v: number | null | undefined, d = 1) => (v == null || Number.isNaN(v) ? '—' : v.toFixed(d).replace('.', ','))

export const hora = (i: Pick<Incidencia, 'dia' | 'hora'>) => (i.dia != null ? `Día ${i.dia} · ${i.hora ?? ''}` : (i.hora ?? '—'))

/** "N1 C2 P50" -> "Nave 1 · Cama 2 · Planta 50" */
export const ubicLarga = (i: Pick<Incidencia, 'nave' | 'cama' | 'planta'>) =>
  `Nave ${i.nave} · Cama ${i.cama}${i.planta != null ? ` · Planta ${i.planta}` : ''}`
export const zona = (nave: number, cama: number) => `Nave ${nave} · Cama ${cama}`

export function hace(ms: number | null, ahora: number): string {
  if (ms == null) return '—'
  const s = Math.max(0, Math.round((ahora - ms) / 1000))
  if (s < 2) return 'ahora'
  if (s < 60) return `hace ${s} s`
  if (s < 3600) return `hace ${Math.floor(s / 60)} min`
  return `hace ${Math.floor(s / 3600)} h`
}
