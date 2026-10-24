import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CLASES } from '../lib/catalogo'
import { Card } from './Card'
import { num, zona } from '../lib/format'
import type { Clase, Incidencia, Resumen } from '../types'

const GRID = 'rgb(var(--c-ink-700))'
const TIP = { background: 'rgb(var(--c-ink-900))', border: '1px solid rgb(var(--c-gold))', borderRadius: 8, color: 'rgb(var(--c-fg))', fontSize: 13 }
const AXIS = { fill: 'rgb(var(--c-fg-muted))', fontSize: 12 }

function Tarjeta({ n, tag, titulo, sub, children, label, className, onOpen, openLabel }: { n: string; tag: string; titulo: string; sub?: string; children: React.ReactNode; label: string; className?: string; onOpen?: () => void; openLabel?: string }) {
  return <Card n={n} tag={tag} title={titulo} sub={sub} label={label} className={className} onOpen={onOpen} openLabel={openLabel}>{children}</Card>
}

export function Distribucion({ items, resumen, className, onOpen }: { items: Incidencia[]; resumen: Resumen; className?: string; onOpen?: () => void }) {
  const orden: Clase[] = ['oidio', 'alternaria', 'heliothis', 'sana']
  const pc = resumen.por_clase
  const data = orden.map((c) => ({ clase: c, nombre: CLASES[c].nombre, total: pc ? (pc[c] ?? 0) : items.filter((i) => i.clase === c).length })).filter((d) => d.clase !== 'sana' || d.total > 0)
  const enf = data.filter((d) => d.clase !== 'sana').sort((a, b) => b.total - a.total)
  const tot = enf.reduce((s, d) => s + d.total, 0)
  const pct = (d: (typeof data)[number]) => Math.round((100 * d.total) / Math.max(1, tot))
  // "Domina" solo si le saca más de 5 puntos a la segunda; si no, se dice que están parejas.
  const titulo = !tot ? 'Sin enfermedades detectadas' : enf.length > 1 && pct(enf[0]) - pct(enf[1]) <= 5 ? `Parejas: ${enf.map((d) => `${d.nombre.toLowerCase()} ${pct(d)} %`).join(', ')}` : `${enf[0].nombre} domina: ${pct(enf[0])} % de las alertas`
  return (
    <Tarjeta n="07" tag="Distribución" className={className} onOpen={onOpen} openLabel="Ver alertas en la tabla" label="Distribución de detecciones" titulo={titulo} sub="Detecciones acumuladas por tipo">
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 32 }}>
            <CartesianGrid stroke={GRID} horizontal={false} />
            <XAxis type="number" allowDecimals={false} tick={AXIS} stroke={GRID} />
            <YAxis type="category" dataKey="nombre" width={84} tick={AXIS} stroke={GRID} />
            <Tooltip contentStyle={TIP} cursor={{ fill: 'rgb(var(--c-brand) / .08)' }} formatter={(v) => [`${v} detecciones`, '']} separator="" />
            <Bar dataKey="total" name="Detecciones" radius={[0, 4, 4, 0]} isAnimationActive={false} label={{ position: 'right', fill: 'rgb(var(--c-bar-label))', fontSize: 12 }}>
              {data.map((d) => <Cell key={d.clase} fill={CLASES[d.clase].color} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Tarjeta>
  )
}

export function Heatmap({ items, onZona, className, onOpen }: { items: Incidencia[]; onZona: (q: string) => void; className?: string; onOpen?: () => void }) {
  const alertas = items.filter((i) => i.estado === 'Alerta')
  const naves = Math.max(1, ...items.map((i) => i.nave))
  const camas = Math.max(1, ...items.map((i) => i.cama))
  const cnt = new Map<string, number>()
  alertas.forEach((i) => cnt.set(`${i.nave}-${i.cama}`, (cnt.get(`${i.nave}-${i.cama}`) ?? 0) + 1))
  const max = Math.max(1, ...cnt.values())
  const [topK] = [...cnt.entries()].sort((a, b) => b[1] - a[1])[0] ?? []
  const [tn, tc] = topK ? topK.split('-').map(Number) : [0, 0]
  const titulo = topK ? `${zona(tn, tc)} concentra más alertas (${cnt.get(topK)})` : 'Sin alertas por cama'
  return (
    <Tarjeta n="06" tag="Alertas por cama" className={className} onOpen={onOpen} openLabel="Ver alertas en la tabla" label="Mapa de alertas por nave y cama" titulo={titulo} sub="Toca una cama para filtrar la tabla">
      <div className="grid gap-1.5" style={{ gridTemplateColumns: `auto repeat(${camas}, minmax(0, 1fr))` }} role="table" aria-label="Conteo de alertas por nave y cama">
        <div role="row" className="contents">
          <span role="columnheader" className="pb-1 text-label text-fg-subtle">Nave</span>
          {Array.from({ length: camas }, (_, c) => <span role="columnheader" key={c} className="pb-1 text-center text-label text-fg-subtle">Cama {c + 1}</span>)}
        </div>
        {Array.from({ length: naves }, (_, n) => (
          <div role="row" className="contents" key={n}>
            <span role="rowheader" className="pr-2 text-label leading-[3rem] text-fg-muted">Nave {n + 1}</span>
            {Array.from({ length: camas }, (_, c) => {
              const v = cnt.get(`${n + 1}-${c + 1}`) ?? 0
              const a = v / max
              const es = topK === `${n + 1}-${c + 1}`
              return (
                <div role="cell" key={c}>
                  <button type="button" onClick={() => onZona(`N${n + 1} C${c + 1}`)} disabled={!v}
                    aria-label={`${zona(n + 1, c + 1)}: ${v} alertas`} title={`${zona(n + 1, c + 1)}: ${v} alertas`}
                    className={`flex h-12 w-full items-center justify-center rounded-2xl border text-body font-semibold tabular-nums text-fg ${es ? 'border-brand ring-2 ring-brand' : 'border-ink-700'} ${v ? 'hover:brightness-125' : 'text-fg-subtle'}`}
                    style={{ background: v ? `rgb(var(--c-danger) / ${0.1 + 0.42 * a})` : 'rgb(var(--c-ink-900))' }}>
                    {v}
                  </button>
                </div>
              )
            })}
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-2 text-label text-fg-muted" aria-hidden>
        <span>0</span>
        <span className="h-2 flex-1 rounded-full" style={{ background: 'linear-gradient(90deg, rgb(var(--c-ink-900)), rgb(var(--c-danger) / .52))' }} />
        <span>{max}</span>
        <span className="ml-2 inline-flex items-center gap-1"><span className="h-3 w-3 rounded-sm border-2 border-brand" />Mayor</span>
      </div>
    </Tarjeta>
  )
}

export function TH({ items, resumen, className }: { items: Incidencia[]; resumen: Resumen; className?: string }) {
  const data = [...items].reverse().filter((i) => i.temperatura_c != null).slice(-80)
    .map((i) => ({ x: `${i.dia != null ? `Día ${i.dia} ` : ''}${i.hora ?? ''}`, temp: i.temperatura_c, hum: i.humedad_pct }))
  const t = resumen.temperatura_actual ?? resumen.temperatura_promedio
  const h = resumen.humedad_actual ?? resumen.humedad_promedio
  // Solo describe el clima; el nivel de riesgo lo da la tarjeta «Riesgo próximo» (un solo lugar decide, sin mensajes contradictorios).
  const titulo = h != null && h > 92 ? `Ahora ${num(t)} °C y ${num(h, 0)} % de humedad: hoja probablemente mojada` : h != null && h > 85 ? `Ahora ${num(t)} °C y humedad alta (${num(h, 0)} %)` : `Ahora ${num(t)} °C y ${num(h, 0)} % de humedad`
  return (
    <Tarjeta n="08" tag="Clima" className={className} label="Temperatura y humedad en el tiempo" titulo={titulo} sub="Temperatura (°C, izquierda) y humedad (%, derecha) en cada detección">
      <div className="h-64 lg:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ left: -8, right: 4, top: 4 }}>
            <CartesianGrid stroke={GRID} />
            <XAxis dataKey="x" tick={AXIS} stroke={GRID} minTickGap={40} />
            <YAxis yAxisId="t" tick={{ ...AXIS, fill: 'rgb(var(--c-line-t))' }} stroke={GRID} unit="°" domain={[(d: number) => Math.floor(d - 1), (d: number) => Math.ceil(d + 1)]} />
            <YAxis yAxisId="h" orientation="right" tick={AXIS} stroke={GRID} unit="%" domain={[(d: number) => Math.max(0, Math.floor(d - 5)), 100]} />
            <Tooltip contentStyle={TIP} formatter={(v, n) => [n === 'Temperatura' ? `${num(Number(v))} °C` : `${num(Number(v), 0)} %`, n]} />
            <Legend wrapperStyle={{ fontSize: 13 }} />
            <Line yAxisId="t" type="monotone" dataKey="temp" name="Temperatura" stroke="rgb(var(--c-line-t))" strokeWidth={2.5} dot={false} isAnimationActive={false} />
            <Line yAxisId="h" type="monotone" dataKey="hum" name="Humedad (HR)" stroke="rgb(var(--c-line-h))" strokeDasharray="6 4" strokeWidth={2.5} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Tarjeta>
  )
}
