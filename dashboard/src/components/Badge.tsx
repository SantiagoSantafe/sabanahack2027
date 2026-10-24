import { CLASES, NIVEL_TXT, nivelDe, type Nivel } from '../lib/catalogo'
import type { Clase, Incidencia } from '../types'

const TONO: Record<Nivel, string> = {
  normal: 'bg-[rgb(var(--c-mint))] text-[rgb(var(--c-mint-fg))] border-transparent',
  alta: 'bg-danger/10 text-danger-300 border-danger/40',
  media: 'bg-warn/15 text-warn-300 border-warn/40',
  desconocida: 'bg-ink-600/40 text-fg-muted border-ink-600',
}
const GLIFO_NIVEL: Record<Nivel, string> = { alta: '▲', media: '◆', normal: '✓', desconocida: '?' }

/** Detección: forma + texto + color (no depende solo del color). */
export function ClaseBadge({ clase, estado }: { clase: Clase; estado?: Incidencia['estado'] }) {
  const info = CLASES[clase] ?? CLASES.desconocida
  const n = nivelDe({ clase, estado: estado ?? (clase === 'sana' ? 'Saludable' : 'Alerta') })
  return <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-label font-medium ${TONO[n]}`}>
    <span aria-hidden>{info.glifo}</span>{info.nombre}
  </span>
}

/** Nivel de urgencia: Alta / Media / Normal. */
export function NivelBadge({ item }: { item: Pick<Incidencia, 'clase' | 'estado'> }) {
  const n = nivelDe(item)
  return <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-label font-medium ${TONO[n]}`}>
    <span aria-hidden>{GLIFO_NIVEL[n]}</span>{NIVEL_TXT[n]}
  </span>
}
