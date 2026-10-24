import { useCallback, useEffect, useRef, useState } from 'react'
import { Distribucion, Heatmap, TH } from './components/Charts'
import { DetailPanel } from './components/DetailPanel'
import { FocoPanel } from './components/FocoPanel'
import { FocosCard } from './components/FocosCard'
import { CoberturaCard, RiesgoCard } from './components/Riesgo'
import { MapaCenital } from './components/MapaCenital'
import { useMapa } from './lib/useMapa'
import { FILTROS_INICIALES, IncidentTable, type Filtros } from './components/IncidentTable'
import { Anillo, Kpi } from './components/Kpi'
import { StatusBanner } from './components/StatusBanner'
import { hace, num } from './lib/format'
import { evalAlertas, evalHr, evalSanas, evalTemp, UMBRALES } from './lib/umbrales'
import { API_URL, FORCE_MOCK_ON, useIncidents } from './lib/useIncidents'
import { usePrevencion } from './lib/usePrevencion'
import type { Foco, Incidencia } from './types'

const ico = (d: string) => <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={d} /></svg>
const I = {
  leaf: ico('M5 19c0-9 5-14 15-14 0 10-5 15-14 15M5 19l8-8'),
}
const STALE_MS = 6000

function useAhora() {
  const [t, setT] = useState(Date.now())
  useEffect(() => { const id = setInterval(() => setT(Date.now()), 1000); return () => clearInterval(id) }, [])
  return t
}

function usePresentacion() {
  const [on, setOn] = useState(() => { try { return localStorage.getItem('pres') === '1' } catch { return false } })
  useEffect(() => {
    document.documentElement.dataset.pres = on ? '1' : '0'
    try { localStorage.setItem('pres', on ? '1' : '0') } catch { /* sin almacenamiento */ }
  }, [on])
  return [on, setOn] as const
}

function useTema() {
  const [oscuro, setOscuro] = useState(() => document.documentElement.dataset.theme === 'dark')
  useEffect(() => {
    document.documentElement.dataset.theme = oscuro ? 'dark' : 'light'
    try { localStorage.setItem('tema', oscuro ? 'dark' : 'light') } catch { /* sin almacenamiento */ }
  }, [oscuro])
  return [oscuro, setOscuro] as const
}

export default function App() {
  const { modo, items, resumen, historia, nuevos, actualizado } = useIncidents()
  const ahora = useAhora()
  const prev = usePrevencion(modo)
  const mapa = useMapa(modo)
  const [focoSel, setFocoSel] = useState<{ id: string; accion?: string } | null>(null)
  const focoActual = focoSel ? prev.focos.find((f) => f.id === focoSel.id) ?? null : null
  const [oscuro, setOscuro] = useTema()
  const [pres, setPres] = usePresentacion()
  const [filtros, setFiltros] = useState<Filtros>(FILTROS_INICIALES)
  const [sel, setSel] = useState<Incidencia | null>(null)
  const tablaRef = useRef<HTMLElement>(null)
  const cerrar = useCallback(() => setSel(null), [])

  const serie = (f: (m: (typeof historia)[number]) => number) => historia.map(f)
  const cargando = modo === 'conectando'
  const sinSenal = modo === 'vivo' && actualizado != null && ahora - actualizado > STALE_MS
  const estadoConexion = cargando ? 'Conectando…' : modo === 'ejemplo' ? 'Datos de ejemplo' : sinSenal ? 'Sin señal' : 'En vivo'
  const tono = cargando ? 'border-ink-700 text-fg-muted' : modo === 'ejemplo' ? 'border-gold/60 text-gold-300' : sinSenal ? 'border-warn/50 text-warn-300' : 'border-transparent bg-[rgb(var(--c-mint))] text-[rgb(var(--c-mint-fg))]'
  const alertas = prev.cargado ? prev.kpis.focos_abiertos : 0

  const irATabla = () => { tablaRef.current?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' }) }
  const filtrarZona = (q: string) => { setFiltros({ ...FILTROS_INICIALES, q, estado: 'Alerta' }); setTimeout(irATabla, 0) }

  const tAct = resumen.temperatura_actual, hAct = resumen.humedad_actual
  const irAClima = () => document.getElementById('clima')?.scrollIntoView({ block: 'start' })
  const ventana = historia.length > 1 && modo === 'vivo' ? `últimos ${historia.length} s` : ''

  const nav = [['resumen', 'Resumen'], ['atender', 'Atender'], ['incidencias', 'Incidencias'], ['mapa', 'Mapa'], ['riesgo', 'Riesgo'], ['clima', 'Clima']] as const
  const [activa, setActiva] = useState<string>('resumen')
  useEffect(() => {
    const els = nav.map(([id]) => document.getElementById(id)).filter(Boolean) as HTMLElement[]
    const io = new IntersectionObserver((es) => { es.forEach((e) => { if (e.isIntersecting) setActiva(e.target.id) }) }, { rootMargin: '-25% 0px -60% 0px' })
    els.forEach((e) => io.observe(e))
    return () => io.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cargando])
  const irAAtender = () => document.getElementById('atender')?.scrollIntoView({ block: 'start' })
  const verAlertas = () => { setFiltros({ ...FILTROS_INICIALES, estado: 'Alerta' }); setTimeout(irATabla, 0) }
  const svg = (d: string) => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d={d} /></svg>

  return (
    <div className="min-h-screen">
      <a href="#incidencias" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-full focus:bg-brand focus:px-4 focus:py-2 focus:text-white">Saltar a la tabla de incidencias</a>
      <div className="mx-auto max-w-[1600px] px-gutter pt-gap lg:sticky lg:top-0 lg:z-40">
        <header className="glass rounded-[28px] border border-ink-700/60 px-4 py-3 shadow-card md:px-5">
          {/* Una fila en pantallas anchas (logo · pestañas centradas · iconos); en angostas: logo + iconos arriba y pestañas en su propia fila */}
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-3 xl:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
            <div className="flex min-w-0 items-center gap-3">
              <span className="relative hidden h-11 w-11 shrink-0 place-items-center rounded-full bg-brand text-white sm:grid" aria-hidden>
                {I.leaf}<span className="absolute right-0.5 top-0.5 h-2 w-2 rounded-full bg-gold" />
              </span>
              <div className="min-w-0">
                <h1 className="truncate text-xl font-bold leading-tight tracking-tight text-fg sm:text-2xl"><span aria-hidden>Hola, AGRAR</span><span className="sr-only">Panel de incidencias en tiempo real · AGRAR</span></h1>
                <p className="truncate text-label text-fg-muted">Finca demo · Bloque {resumen.bloque ?? 1}{resumen.bloque_naves?.length ? ` (naves ${resumen.bloque_naves.join(' y ')})` : ''}{resumen.hora ? ` · simulación día ${resumen.dia} ${resumen.hora}` : ''}</p>
              </div>
            </div>
            <nav aria-label="Secciones" className="order-last col-span-2 -mx-1 flex gap-2 overflow-x-auto px-1 no-scrollbar xl:order-none xl:col-span-1 xl:mx-0">
              {nav.map(([id, t]) => <a key={id} href={`#${id}`} className="pill shrink-0" aria-current={activa === id ? 'true' : undefined}>{t}</a>)}
            </nav>
            <div className="flex items-center justify-end gap-2">
              <div title={estadoConexion} className={`inline-flex min-h-[40px] items-center gap-2 rounded-full border bg-ink-800 px-3 text-body font-medium sm:px-3.5 ${tono}`}>
                <span role="status" aria-live="polite" className="inline-flex items-center gap-2">
                  <span aria-hidden className={`h-2.5 w-2.5 rounded-full bg-current ${modo === 'vivo' && !sinSenal ? 'pulse-dot' : ''} ${cargando ? 'opacity-50' : ''}`} />
                  <span className="sr-only sm:not-sr-only">{estadoConexion}</span>
                </span>
                {modo === 'vivo' && actualizado && <span className="hidden text-label font-normal text-fg-subtle tabular-nums sm:inline">· {hace(actualizado, ahora)}</span>}
              </div>
              <button type="button" className="icon-btn" onClick={irAAtender} aria-label={`Ver focos abiertos${alertas ? `: ${alertas}` : ''}`} title="Ver qué atender hoy">
                {svg('M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.94 1.94 0 0 0 3.4 0')}
                {alertas > 0 && <span className="absolute -right-1 -top-1 min-w-[20px] rounded-full bg-danger px-1 text-center text-[11px] font-bold leading-5 text-white tabular-nums">{alertas > 99 ? '99+' : alertas}</span>}
              </button>
              <button type="button" className="icon-btn" aria-pressed={oscuro} onClick={() => setOscuro(!oscuro)} aria-label={oscuro ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'} title={oscuro ? 'Tema claro' : 'Tema oscuro'}>
                {oscuro ? svg('M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z') : svg('M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8ZM12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4')}
              </button>
              <button type="button" className="icon-btn !hidden sm:!grid" aria-pressed={pres} onClick={() => setPres(!pres)} aria-label={pres ? 'Desactivar modo presentación' : 'Activar modo presentación'} title="Modo presentación (letra grande)">
                {svg('M3 4h18v12H3zM8 20h8M12 16v4')}
              </button>
            </div>
          </div>
        </header>
      </div>

      <main className="mx-auto max-w-[1600px] px-gutter pb-gap pt-gap">
        <div className="space-y-gap">
          {modo === 'ejemplo' && (
            <p role="alert" className="flex flex-wrap items-center gap-2 rounded-2xl border border-gold/50 bg-gold/10 px-4 py-2.5 text-body text-fg">
              <span aria-hidden className="text-gold-300">◆</span>
              {FORCE_MOCK_ON ? 'Modo de datos de ejemplo activado manualmente.' : <>No hay conexión con el simulador (<code className="text-gold-300">{API_URL}</code>). Se muestran datos de ejemplo, no reales; se reintenta solo.</>}
            </p>
          )}
          {sinSenal && <p role="alert" className="rounded-2xl border border-warn/40 bg-warn/10 px-4 py-2.5 text-body text-fg"><span aria-hidden className="text-warn-300">◆ </span>Sin datos nuevos desde {hace(actualizado, ahora)}: lo que ves puede estar desactualizado.</p>}

          <section id="resumen" className="scroll-mt-32 space-y-gap" aria-label="Resumen">
            <StatusBanner items={items} resumen={resumen} modo={modo} ahora={ahora} onZona={filtrarZona} onVer={irAAtender} focosAbiertos={prev.cargado ? prev.kpis.focos_abiertos : undefined} detecciones={prev.kpis.detecciones || undefined} sinAtender={prev.kpis.sin_atender_rojo} />
            <FocosCard focos={prev.focos} kpis={prev.kpis} cargando={cargando || !prev.cargado} onOpen={(f: Foco, accion) => setFocoSel({ id: f.id, accion })} />
            <div className="grid grid-cols-1 gap-gap md:grid-cols-2 xl:grid-cols-12">
              <Kpi n="02" tag="Temperatura" className="xl:col-span-4" titulo="Temperatura promedio" valor={num(resumen.temperatura_promedio)} unidad="°C" serie={serie((m) => m.temp)} eval={evalTemp(resumen.temperatura_promedio)} referencia={`Ideal: ${UMBRALES.temp.min}–${UMBRALES.temp.max} °C`} nota={tAct != null ? `Ahora: ${num(tAct)} °C` : (ventana ? `Tendencia ${ventana}` : 'Promedio de lecturas')} cargando={cargando} onOpen={irAClima} openLabel="Ver gráfico de clima" />
              <Kpi n="03" tag="Humedad" className="xl:col-span-4" titulo="Humedad relativa (HR) promedio" valor={num(resumen.humedad_promedio, 0)} unidad="%" serie={serie((m) => m.hum)} eval={evalHr(resumen.humedad_promedio)} referencia={`Ideal: ${UMBRALES.hr.min}–${UMBRALES.hr.max} %`} nota={hAct != null ? `Ahora: ${num(hAct, 0)} %` : 'Promedio de lecturas'} cargando={cargando} onOpen={irAClima} openLabel="Ver gráfico de clima" />
              <Kpi n="04" tag="Plantas sanas" className="md:col-span-2 xl:col-span-4" titulo="Plantas saludables" valor={num(resumen.plantas_saludables_pct)} unidad="%" serie={serie((m) => m.sana)} eval={evalSanas(resumen.plantas_saludables_pct)} referencia={`Meta: ${UMBRALES.sanas.ok} % o más`} nota={`${resumen.total} detecciones`} cargando={cargando}
                extra={resumen.plantas_saludables_pct != null ? <Anillo pct={resumen.plantas_saludables_pct} tono={evalSanas(resumen.plantas_saludables_pct).nivel} /> : undefined} />
            </div>
          </section>

          <IncidentTable ref={tablaRef} items={items} nuevos={nuevos} cargando={cargando} filtros={filtros} setFiltros={setFiltros} onSelect={setSel} />

          <section id="mapa" className="scroll-mt-32 grid grid-cols-1 gap-gap lg:grid-cols-12" aria-label="Mapa de alertas">
            <MapaCenital className="lg:col-span-12" mapa={mapa} cargando={cargando} onFoco={(id) => setFocoSel({ id })} onSelect={(d) => { const i = items.find((x) => x.id === d.id); if (i) setSel(i); else if (d.foco_id) setFocoSel({ id: d.foco_id }) }} />
            <Heatmap className="lg:col-span-7" items={items} onZona={filtrarZona} onOpen={verAlertas} />
            <Distribucion className="lg:col-span-5" items={items} resumen={resumen} onOpen={verAlertas} />
          </section>

          <section id="riesgo" className="scroll-mt-32 grid grid-cols-1 gap-gap lg:grid-cols-12" aria-label="Prevención">
            <RiesgoCard className="lg:col-span-7" riesgo={prev.riesgo} cargando={cargando} />
            <CoberturaCard className="lg:col-span-5" cobertura={prev.cobertura} />
          </section>

          <section id="clima" className="scroll-mt-32" aria-label="Clima"><TH items={items} resumen={resumen} /></section>
        </div>

        <footer className="py-6 text-center text-label text-fg-subtle" title="Las lecturas de T y HR del robot son simuladas; en producción vienen del sensor a bordo. Umbrales en lib/umbrales.ts.">Datos de temperatura y humedad simulados.</footer>
      </main>
      {sel && <DetailPanel item={sel} onClose={cerrar} foco={prev.focos.find((f) => f.incidencias.includes(sel.id)) ?? null} onFoco={(f) => { setSel(null); setFocoSel({ id: f.id }) }} />}
      {focoActual && <FocoPanel foco={focoActual} accionInicial={focoSel?.accion} puedeActuar={prev.puedeActuar} onClose={() => setFocoSel(null)} onAccion={prev.accion} historial={prev.historial} />}
    </div>
  )
}
