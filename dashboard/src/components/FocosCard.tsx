import { useMemo, useState } from 'react'
import { ESTADO_TXT, horasTxt, SEMAFORO, siguienteAccion, TEND } from '../lib/foco'
import type { EstadoFoco, Foco, FocosKpis } from '../types'
import { ClaseBadge } from './Badge'
import { Card } from './Card'

// Tres grupos en lugar de seis estados: lo que falta atender, lo que está en curso y lo cerrado.
type Grupo = 'por_atender' | 'en_curso' | 'cerrados'
const GRUPOS: { k: Grupo; t: string; estados: EstadoFoco[] }[] = [
  { k: 'por_atender', t: 'Por atender', estados: ['nuevo'] },
  { k: 'en_curso', t: 'En curso', estados: ['asignado', 'verificado', 'tratado'] },
  { k: 'cerrados', t: 'Cerrados', estados: ['cerrado'] },
]
const NIVEL: Record<Foco['nivel'], string> = {
  alta: 'bg-danger/10 text-danger-300 border-danger/40', media: 'bg-warn/15 text-warn-300 border-warn/40', baja: 'bg-ink-900 text-fg-muted border-ink-700',
}
const PASO = 5

export function FocosCard({ focos, kpis, onOpen, cargando }: { focos: Foco[]; kpis: FocosKpis; onOpen: (f: Foco, accion?: string) => void; cargando: boolean }) {
  const [grupo, setGrupo] = useState<Grupo>('por_atender')
  const [n, setN] = useState(PASO)
  const g = GRUPOS.find((x) => x.k === grupo)!
  const lista = useMemo(() => focos.filter((f) => g.estados.includes(f.estado)).sort((a, b) => b.puntaje - a.puntaje), [focos, g])
  const cuenta = (x: (typeof GRUPOS)[number]) => x.estados.reduce((s, e) => s + (kpis.por_estado[e] ?? 0), 0)
  const vista = lista.slice(0, n)
  const et = kpis.etiquetas
  const elegir = (k: Grupo) => { setGrupo(k); setN(PASO) }

  return (
    <Card tag="Qué atender hoy" id="atender" className="scroll-mt-32" label="Focos priorizados: qué atender hoy"
      title="Los focos más urgentes primero" sub="El robot sugiere; el supervisor envía a un operario a confirmar en campo. Un foco agrupa detecciones de la misma cama.">
      <div role="group" aria-label="Filtrar focos" className="flex flex-wrap gap-2">
        {GRUPOS.map((x) => (
          <button key={x.k} type="button" className="pill !min-h-[44px] md:!min-h-[36px]" aria-current={grupo === x.k ? 'true' : undefined} onClick={() => elegir(x.k)}
            title={x.estados.map((e) => `${ESTADO_TXT[e]}: ${kpis.por_estado[e] ?? 0}`).join(' · ')}>
            {x.t} <span className="ml-1.5 tabular-nums opacity-80">{cuenta(x)}</span>
          </button>
        ))}
      </div>

      {cargando ? <div className="skeleton mt-4 h-32 w-full" aria-busy="true" /> : vista.length === 0 ? (
        <p className="mt-4 rounded-2xl bg-ink-900 p-4 text-body text-fg-muted">{grupo === 'por_atender' ? 'Nada pendiente: todos los focos están asignados o cerrados.' : `No hay focos ${g.t.toLowerCase()}.`}</p>
      ) : (
        <ol className="mt-4 divide-y divide-ink-700 overflow-hidden rounded-2xl border border-ink-700">
          {vista.map((f, i) => {
            const sig = siguienteAccion(f)
            const s = SEMAFORO[f.semaforo]
            return (
              <li key={f.id} className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3 hover:bg-ink-900/60">
                <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-full border text-label font-bold tabular-nums ${NIVEL[f.nivel]}`}
                  title={`Prioridad ${f.nivel} · puntaje ${Math.round(f.puntaje)}/100. ${f.por_que.join(' · ')}`}>{i + 1}</span>
                <button type="button" onClick={() => onOpen(f)} className="min-w-0 flex-1 basis-[11rem] text-left" aria-label={`Ver detalle del foco en nave ${f.nave} cama ${f.cama}`}>
                  <span className="flex flex-wrap items-center gap-2">
                    <b className="text-body text-fg">Nave {f.nave} · Cama {f.cama}</b>
                    <ClaseBadge clase={f.clase} />
                    {f.fuentes.includes('camara_d1') && <span className="rounded-full border border-brand/40 px-2 py-0.5 text-label text-brand-300">Cámara D1</span>}
                  </span>
                  <span className="mt-0.5 block text-label text-fg-muted">
                    <b className="tabular-nums text-fg">{f.plantas}</b> {f.plantas === 1 ? 'planta' : 'plantas'} · {TEND[f.tendencia]}{f.responsable ? ` · ${f.responsable}` : ''}
                  </span>
                </button>
                <span className="ml-auto flex items-center gap-2">
                <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-label font-medium ${s.chip}`} title="Horas del escenario desde la primera detección. Rojo desde 24 h.">
                  <span aria-hidden>{s.glifo}</span>{f.estado === 'nuevo' ? horasTxt(f.horas_sin_atender) : ESTADO_TXT[f.estado]}
                </span>
                {sig ? <button type="button" className="btn btn-primary !min-h-[40px] md:!min-h-[36px]" onClick={() => onOpen(f, sig.accion)}>{sig.texto}</button>
                  : <button type="button" className="btn !min-h-[40px] md:!min-h-[36px]" onClick={() => onOpen(f)}>Ver</button>}
                </span>
              </li>
            )
          })}
        </ol>
      )}

      {!cargando && lista.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-label text-fg-muted">
          <span>Mostrando {vista.length} de {lista.length}</span>
          {lista.length > n && <button type="button" className="btn !min-h-[36px]" onClick={() => setN(n + 10)}>Ver {Math.min(10, lista.length - n)} más</button>}
          {n > PASO && <button type="button" className="btn !min-h-[36px]" onClick={() => setN(PASO)}>Ver menos</button>}
          {et.total > 0 && <span className="ml-auto" title="Cada verificación en campo es una etiqueta para reentrenar el modelo">{et.total} verificaciones guardadas para reentrenar{et.pct_falsas != null ? ` · ${String(et.pct_falsas).replace('.', ',')} % falsas alarmas` : ''}</span>}
        </div>
      )}
      <details className="mt-3 text-label text-fg-subtle">
        <summary className="cursor-pointer select-none hover:text-fg-muted">¿Cómo se ordena?</summary>
        <p className="mt-1">Prioridad = gravedad de la enfermedad × plantas afectadas × riesgo ambiental de la cama × horas sin atender. El número a la izquierda es el orden; su color indica prioridad alta, media o baja. Un foco agrupa detecciones cercanas de la misma cama.</p>
      </details>
    </Card>
  )
}
