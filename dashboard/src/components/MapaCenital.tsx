import { useEffect, useMemo, useRef, useState } from 'react'
import type { Clase, Deteccion, Mapa, NivelRiesgo, Rejilla } from '../types'
import { Card } from './Card'

type Capa = 'temp' | 'hr' | 'riesgo' | 'ninguna'
type Rango = '24' | '168' | 'todo'
type Vista = 'focos' | 'detecciones' | 'nada'
interface Grupo { id: string; x: number; y: number; n: number; clase: Clase; abierto: boolean; estado: string | null; ubicacion: string; conf: number }

// Escalas continuas, no arcoíris. Temperatura: azul -> amarillo -> rojo. HR: blanco -> azul. Riesgo: verde menta -> ámbar -> rojo.
const ESC_T: [number, number, number][] = [[44, 90, 160], [150, 190, 220], [242, 226, 122], [232, 140, 60], [192, 57, 43]]
const ESC_H: [number, number, number][] = [[250, 251, 253], [180, 200, 235], [90, 120, 200], [31, 58, 147]]
const ESC_R: [number, number, number][] = [[205, 239, 227], [245, 200, 120], [220, 90, 70]]

function color(stops: [number, number, number][], t: number): [number, number, number] {
  const u = Math.max(0, Math.min(1, t)) * (stops.length - 1)
  const i = Math.min(stops.length - 2, Math.floor(u)), f = u - i
  return [0, 1, 2].map((k) => Math.round(stops[i][k] + (stops[i + 1][k] - stops[i][k]) * f)) as [number, number, number]
}
const css = (c: [number, number, number]) => `rgb(${c[0]} ${c[1]} ${c[2]})`
const gradiente = (stops: [number, number, number][]) => `linear-gradient(90deg, ${stops.map((s, i) => `${css(s)} ${Math.round((100 * i) / (stops.length - 1))}%`).join(', ')})`
const NIVEL_R: Record<NivelRiesgo, number> = { bajo: 0.1, medio: 0.55, alto: 0.95 }
const rad = (c: number | null) => 4 + Math.max(0, Math.min(1, ((c ?? 0.5) - 0.5) / 0.45)) * 10 // 50 % -> 4 px, 95 % -> 14 px
const radG = (n: number) => Math.min(20, 6 + 2.2 * Math.sqrt(n)) // foco: crece con la raíz del nº de detecciones
const nf = (v: number | null | undefined, d = 1) => (v == null ? '—' : v.toFixed(d).replace('.', ','))

function imagenCampo(g: Rejilla, rot: 0 | 90, esc: [number, number, number][], lo: number, hi: number): string {
  const w = rot === 0 ? g.nx : g.ny, h = rot === 0 ? g.ny : g.nx
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h
  const ctx = cv.getContext('2d')!
  const img = ctx.createImageData(w, h)
  const span = Math.max(1e-6, hi - lo)
  for (let j = 0; j < g.ny; j++) for (let i = 0; i < g.nx; i++) {
    const c = color(esc, (g.valores[j * g.nx + i] - lo) / span)
    const px = rot === 0 ? i : j, py = rot === 0 ? g.ny - 1 - j : i
    const o = (py * w + px) * 4
    img.data[o] = c[0]; img.data[o + 1] = c[1]; img.data[o + 2] = c[2]; img.data[o + 3] = 255
  }
  ctx.putImageData(img, 0, 0)
  return cv.toDataURL()
}

export function MapaCenital({ mapa, onSelect, onFoco, cargando, className }: { mapa: Mapa | null; onSelect: (d: Deteccion) => void; onFoco?: (id: string) => void; cargando: boolean; className?: string }) {
  const [capa, setCapa] = useState<Capa>('temp')
  const [vista, setVista] = useState<Vista>('focos')
  const verDet = vista !== 'nada'
  const [verSanas, setVerSanas] = useState(false)
  const [rango, setRango] = useState<Rango>('24')
  const [clase, setClase] = useState<'todas' | Clase>('todas')
  const [fuente, setFuente] = useState<'todas' | 'simulacion' | 'camara_d1'>('todas')
  const [rotUser, setRotUser] = useState<0 | 90 | null>(null)
  const [zoom, setZoom] = useState({ k: 1, cx: 0, cy: 0 })
  const [hover, setHover] = useState<{ d: Deteccion; x: number; y: number } | null>(null)
  const caja = useRef<HTMLDivElement>(null)
  const envoltorio = useRef<HTMLDivElement>(null)
  const [anchoCard, setAnchoCard] = useState(1000)
  const [tam, setTam] = useState({ w: 800, h: 480 })
  const punteros = useRef(new Map<number, { x: number; y: number }>())
  const ultimo = useRef<{ x: number; y: number } | null>(null)
  const pinch = useRef<number | null>(null)

  useEffect(() => {
    const el = envoltorio.current; if (!el) return
    const ro = new ResizeObserver(() => setAnchoCard(el.clientWidth))
    ro.observe(el); setAnchoCard(el.clientWidth)
    return () => ro.disconnect()
  }, [!!mapa])

  useEffect(() => {
    const el = caja.current; if (!el) return
    const ro = new ResizeObserver(() => setTam({ w: el.clientWidth, h: el.clientHeight }))
    ro.observe(el); setTam({ w: el.clientWidth, h: el.clientHeight })
    return () => ro.disconnect()
  }, [!!mapa])

  const rot: 0 | 90 = rotUser ?? (anchoCard >= 640 ? 90 : 0) // por defecto el eje largo del bloque va a lo largo de la pantalla
  const geo = mapa?.geometria
  const gT = mapa?.temperatura
  const B = useMemo(() => {
    if (!gT || !geo) return null
    return { x0: gT.x0, y0: gT.y0, x1: gT.x0 + gT.nx * gT.celda, y1: gT.y0 + gT.ny * gT.celda }
  }, [gT, geo])

  const campo = capa === 'temp' ? mapa?.temperatura : capa === 'hr' ? mapa?.humedad : null
  const dom = useMemo(() => {
    if (!campo || campo.min == null || campo.max == null) return null
    const minSpan = capa === 'temp' ? 2 : 6
    const c = (campo.min + campo.max) / 2, span = Math.max(minSpan, campo.max - campo.min)
    const hi = capa === 'hr' ? Math.min(100, c + span / 2) : c + span / 2
    return { lo: hi - span, hi }
  }, [campo, capa])
  const imagen = useMemo(() => (campo && dom && campo.valores.length ? imagenCampo(campo, rot, capa === 'temp' ? ESC_T : ESC_H, dom.lo, dom.hi) : null), [campo, dom, rot, capa])

  if (!mapa || !geo || !B) {
    return <Card n="12" tag="Vista cenital" className={className} label="Vista cenital del bloque" title="Vista cenital del bloque">{cargando ? <div className="skeleton h-72 w-full" /> : <p className="text-body text-fg-muted">Sin datos del bloque: el simulador aún no tiene una sesión activa.</p>}</Card>
  }

  // Caminos: cabecera sur de lado a lado y camino central entre bloques (datos viejos: solo camino_central = cabecera)
  const cab = geo.camino_cabecera ?? geo.camino_central!
  const central = geo.camino_cabecera ? geo.camino_central : null
  // Proyección (metros) -> pantalla; norte arriba (0°) o a la derecha (90°)
  const W = rot === 0 ? B.x1 - B.x0 : B.y1 - B.y0, H = rot === 0 ? B.y1 - B.y0 : B.x1 - B.x0
  const P = (x: number, y: number): [number, number] => (rot === 0 ? [x - B.x0, B.y1 - y] : [y - B.y0, x - B.x0])
  const pad = 2
  const altoCaja = rot === 90 ? Math.round(Math.min(720, Math.max(300, anchoCard * (H + 2 * pad) / (W + 2 * pad)))) : Math.round(Math.min(640, Math.max(360, anchoCard * 1.9)))
  const s0 = Math.min(tam.w / (W + 2 * pad), tam.h / (H + 2 * pad))
  const pxm = s0 * zoom.k
  const vw = tam.w / pxm, vh = tam.h / pxm
  const cx = W / 2 + zoom.cx, cy = H / 2 + zoom.cy
  const vb = `${cx - vw / 2} ${cy - vh / 2} ${vw} ${vh}`
  const ajustar = (k: number) => setZoom((z) => ({ ...z, k: Math.max(1, Math.min(14, k)) }))

  const onDown = (e: React.PointerEvent) => { (e.currentTarget as Element).setPointerCapture?.(e.pointerId); punteros.current.set(e.pointerId, { x: e.clientX, y: e.clientY }); ultimo.current = { x: e.clientX, y: e.clientY } }
  const onMove = (e: React.PointerEvent) => {
    const mp = punteros.current
    if (!mp.has(e.pointerId)) return
    mp.set(e.pointerId, { x: e.clientX, y: e.clientY })
    if (mp.size === 2) {
      const [a, b] = [...mp.values()]
      const d = Math.hypot(a.x - b.x, a.y - b.y)
      if (pinch.current) ajustar(zoom.k * (d / pinch.current))
      pinch.current = d
    } else if (ultimo.current) {
      const dx = (e.clientX - ultimo.current.x) / pxm, dy = (e.clientY - ultimo.current.y) / pxm
      ultimo.current = { x: e.clientX, y: e.clientY }
      setZoom((z) => ({ ...z, cx: z.cx - dx, cy: z.cy - dy }))
    }
  }
  const onUp = (e: React.PointerEvent) => { punteros.current.delete(e.pointerId); pinch.current = null; ultimo.current = punteros.current.size === 1 ? [...punteros.current.values()][0] : null }

  // Detecciones filtradas
  const lim = rango === 'todo' ? -Infinity : mapa.ahora_h - Number(rango)
  const dets = mapa.detecciones.filter((d) => d.t_h >= lim && (verSanas || d.clase !== 'sana') && (clase === 'todas' || d.clase === clase) && (fuente === 'todas' || d.fuente === fuente))
    .sort((a, b) => (a.clase === 'sana' ? -1 : 0) - (b.clase === 'sana' ? -1 : 0))
  // Vista por focos: una marca por foco (centro de sus detecciones) en lugar de cientos de círculos encimados.
  const sueltas: Deteccion[] = []
  const gm = new Map<string, { xs: number; ys: number; n: number; cl: Map<Clase, number>; d: Deteccion; conf: number }>()
  if (vista === 'focos') dets.forEach((d) => {
    if (!d.foco_id || d.clase === 'sana') { sueltas.push(d); return }
    const g = gm.get(d.foco_id) ?? { xs: 0, ys: 0, n: 0, cl: new Map(), d, conf: 0 }
    g.xs += d.x; g.ys += d.y; g.n++; g.cl.set(d.clase, (g.cl.get(d.clase) ?? 0) + 1); g.conf = Math.max(g.conf, d.confianza ?? 0); gm.set(d.foco_id, g)
  })
  const grupos: Grupo[] = [...gm.entries()].map(([id, g]) => ({ id, x: g.xs / g.n, y: g.ys / g.n, n: g.n, clase: [...g.cl.entries()].sort((a, b) => b[1] - a[1])[0][0], abierto: g.d.foco_abierto, estado: g.d.foco_estado, ubicacion: `Nave ${g.d.nave} · Cama ${g.d.cama}`, conf: g.conf }))
    .sort((a, b) => b.n - a.n)
  const individuales = vista === 'detecciones' ? dets : sueltas
  const marcas = individuales.length + grupos.length
  const interactivas = marcas <= 120

  const colorDet = (c: Clase) => (c === 'sana' ? 'rgb(var(--c-pos))' : c === 'heliothis' ? 'rgb(var(--c-warn))' : 'rgb(var(--c-danger))')
  const riesgoDe = (n: number, c: number) => mapa.riesgo.find((r) => r.nave === n && r.cama === c)
  const barraM = [5, 10, 20, 50].find((m) => m * pxm >= 70) ?? 50
  const t = mapa.lecturas.por_tipo
  const rotuloInterp = `Temperatura y HR interpoladas a partir de ${mapa.lecturas.n} lecturas (${t.sensor_bloque ?? 0} sensores del bloque, ${t.sonda_robot ?? 0} sondas del robot, ${t.incidencia ?? 0} en incidencias; últimas ${mapa.horas_ventana ?? 24} h del escenario). Datos simulados.`
  const [nx0, ny0] = P(B.x0, B.y0)
  const [nx1, ny1] = P(B.x1, B.y1)
  const imgX = Math.min(nx0, nx1), imgY = Math.min(ny0, ny1)
  const sel = 'ctl !min-h-[40px] text-label md:!min-h-[34px]'
  function seg<T extends string>(nombre: string, v: T, set: (x: T) => void, ops: [T, string][]) {
    return <div role="group" aria-label={nombre} className="inline-flex flex-wrap gap-1">
      {ops.map(([k, t]) => <button key={k} type="button" aria-pressed={v === k} onClick={() => set(k)} className={`min-h-[40px] rounded-full px-3 text-label md:min-h-[34px] ${v === k ? 'bg-brand font-semibold text-white' : 'text-fg-muted hover:bg-ink-800'}`}>{t}</button>)}
    </div>
  }
  const resumenAria = `Vista cenital del bloque: ${geo.naves.length} naves y ${geo.camas.length} camas. ${dets.length} detecciones visibles. Capa: ${capa === 'ninguna' ? 'ninguna' : capa === 'temp' ? 'temperatura' : capa === 'hr' ? 'humedad relativa' : 'riesgo'}.`

  return (
    <Card tag="Mapa del bloque" className={className} label="Vista cenital del bloque" title={vista === 'focos' ? `Dónde está pasando: ${grupos.length} focos` : `Dónde está pasando: ${dets.filter((d) => d.estado === 'Alerta').length} detecciones`}
      sub="Vista desde arriba, a escala. Toca un círculo para ver el detalle.">
      <div ref={envoltorio}>
      {/* Barra de controles: qué color, qué marcas y filtros a la izquierda; zoom a la derecha */}
      <div className="flex flex-wrap items-center gap-2 rounded-[22px] border border-ink-700 bg-ink-900 p-1.5">
        {seg('Color', capa, setCapa, [['temp', 'Temperatura'], ['hr', 'Humedad'], ['riesgo', 'Riesgo'], ['ninguna', 'Sin color']])}
        <span className="hidden h-6 w-px bg-ink-700 md:block" aria-hidden />
        {seg('Marcas', vista, setVista, [['focos', 'Focos'], ['detecciones', 'Detecciones'], ['nada', 'Ocultar']])}
        <span className="ml-auto flex gap-1" role="group" aria-label="Zoom del mapa">
          <button type="button" className="icon-btn !h-9 !w-9" onClick={() => ajustar(zoom.k * 1.5)} aria-label="Acercar" title="Acercar">+</button>
          <button type="button" className="icon-btn !h-9 !w-9" onClick={() => ajustar(zoom.k / 1.5)} aria-label="Alejar" title="Alejar">−</button>
          <button type="button" className="icon-btn !h-9 !w-9" onClick={() => setZoom({ k: 1, cx: 0, cy: 0 })} aria-label="Restablecer zoom" title="Restablecer zoom">⤢</button>
          <button type="button" className="icon-btn !h-9 !w-9" onClick={() => setRotUser(rot === 0 ? 90 : 0)} aria-pressed={rot === 90} aria-label="Girar 90°" title="Girar 90°">⟳</button>
        </span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <label className="sr-only" htmlFor="m-rango">Rango de tiempo</label>
        <select id="m-rango" className={sel} value={rango} data-activo={rango !== '24' ? '1' : undefined} onChange={(e) => setRango(e.target.value as Rango)}><option value="24">Últimas 24 h</option><option value="168">Últimos 7 días</option><option value="todo">Todo</option></select>
        <label className="sr-only" htmlFor="m-clase">Tipo</label>
        <select id="m-clase" className={sel} value={clase} data-activo={clase !== 'todas' ? '1' : undefined} onChange={(e) => setClase(e.target.value as 'todas' | Clase)}><option value="todas">Todos los tipos</option><option value="oidio">Oídio</option><option value="alternaria">Alternaria</option><option value="heliothis">Heliothis</option><option value="sana">Hoja sana</option></select>
        <label className="sr-only" htmlFor="m-fuente">Fuente</label>
        <select id="m-fuente" className={sel} value={fuente} data-activo={fuente !== 'todas' ? '1' : undefined} onChange={(e) => setFuente(e.target.value as typeof fuente)}><option value="todas">Simulación y robot</option><option value="simulacion">Solo simulación</option><option value="camara_d1">Solo robot real</option></select>
        <label className="ml-1 flex min-h-[40px] items-center gap-2 text-label text-fg-muted"><input type="checkbox" className="h-4 w-4 accent-[rgb(var(--c-brand))]" checked={verSanas} onChange={(e) => setVerSanas(e.target.checked)} />Mostrar hojas sanas</label>
      </div>

      <div ref={caja} className="relative mt-3 overflow-hidden rounded-2xl border border-ink-700 bg-ink-900" style={{ touchAction: 'none', height: altoCaja }}
        onWheel={(e) => { ajustar(zoom.k * (e.deltaY < 0 ? 1.15 : 1 / 1.15)) }}
        onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}>
        <svg width="100%" height="100%" viewBox={vb} role="img" aria-label={resumenAria} className="block select-none">
          {imagen && <image href={imagen} x={imgX} y={imgY} width={rot === 0 ? W : W} height={H} preserveAspectRatio="none" opacity=".88" />}
          {/* camino central, cabecera y naves */}
          {[cab, central].map((c, i) => { if (!c) return null; const [a, b] = P(c.x0, c.y0), [d, e] = P(c.x1, c.y1); return <rect key={i} x={Math.min(a, d)} y={Math.min(b, e)} width={Math.abs(d - a)} height={Math.abs(e - b)} fill="rgb(var(--c-ink-700))" opacity={imagen ? 0.35 : 0.7} /> })}
          {geo.naves.map((n) => { const [a, b] = P(n.x0, B.y0 + (cab.y1 - cab.y0)), [d, e] = P(n.x1, geo.cabecera_norte.y1); return (
            <g key={n.nave}><rect x={Math.min(a, d)} y={Math.min(b, e)} width={Math.abs(d - a)} height={Math.abs(e - b)} fill="none" stroke="rgb(var(--c-fg-subtle))" strokeWidth={1.5 / pxm} strokeDasharray={`${6 / pxm} ${4 / pxm}`} />
              </g>) })}
          {(() => { const c = central ?? cab; const [a2, b2] = central ? P((c.x0 + c.x1) / 2, (c.y0 + c.y1) / 2) : P((c.x0 + c.x1) / 2, c.y0 + 1.3); const vertical = central ? rot === 0 : rot === 90; return <text x={a2} y={b2} textAnchor="middle" dominantBaseline="middle" fontSize={12 / pxm} fill="rgb(var(--c-fg-muted))" stroke="rgb(var(--c-ink-800))" strokeWidth={3 / pxm} paintOrder="stroke" transform={vertical ? `rotate(-90 ${a2} ${b2})` : undefined}>Camino central</text> })()}
          {/* bloque activo: el otro queda atenuado; rótulo de cada bloque en la cabecera */}
          {geo.bloques?.map((bq) => { const [a, b] = P(bq.x0, cab.y1), [d, e] = P(bq.x1, geo.cabecera_norte.y1); const [lx, ly] = P((bq.x0 + bq.x1) / 2, cab.y1 + (rot === 90 ? 1.5 : -1.2)); const act = bq.id === (geo.bloque_activo ?? 1); return (
            <g key={`b${bq.id}`}>
              {!act && <rect x={Math.min(a, d)} y={Math.min(b, e)} width={Math.abs(d - a)} height={Math.abs(e - b)} fill="rgb(var(--c-ink-800))" opacity=".55" pointerEvents="none" />}
              <text x={lx} y={ly} textAnchor={rot === 90 ? 'start' : 'middle'} dominantBaseline="middle" fontSize={12 / pxm} fontWeight={700} fill={act ? 'rgb(var(--c-brand))' : 'rgb(var(--c-fg-subtle))'} stroke="rgb(var(--c-ink-800))" strokeWidth={3 / pxm} paintOrder="stroke">{act ? `Bloque ${bq.id} · en recorrido` : `Bloque ${bq.id}`}</text>
            </g>) })}
          {geo.pasillos.map((p, i) => { const [a, b] = P(p.x, p.y0), [d, e] = P(p.x, p.y1); return <line key={i} x1={a} y1={b} x2={d} y2={e} stroke="rgb(var(--c-ink-600))" strokeWidth={1 / pxm} strokeDasharray={`${3 / pxm} ${5 / pxm}`} opacity=".7" /> })}
          
          {geo.camas.map((c) => {
            const r = riesgoDe(c.nave, c.cama)
            const [a, b] = P(c.x - c.ancho / 2, c.y0), [d, e] = P(c.x + c.ancho / 2, c.y1)
            const x = Math.min(a, d), y = Math.min(b, e), w = Math.abs(d - a), h = Math.abs(e - b)
            const rc = r ? css(color(ESC_R, NIVEL_R[r.nivel])) : 'transparent'
            const gr = 1.5
            return <g key={c.bed}>
              {capa === 'riesgo' && r && <rect x={rot === 0 ? x - gr / 2 + w / 2 : x} y={rot === 0 ? y : y - gr / 2 + h / 2} width={rot === 0 ? gr : w} height={rot === 0 ? h : gr} rx={0.4} fill={rc} opacity=".9"><title>{`Nave ${c.nave} · Cama ${c.cama}: riesgo ${r.nivel}`}</title></rect>}
              <rect x={x} y={y} width={w} height={h} fill="rgb(var(--c-ink-800))" stroke="rgb(var(--c-fg-muted))" strokeWidth={1 / pxm} opacity=".92" />
              {capa === 'riesgo' && r && <text x={rot === 0 ? x + w / 2 : x + 2} y={rot === 0 ? y - 0.6 : y - 0.8} textAnchor="middle" fontSize={11 / pxm} fontWeight={700} fill="rgb(var(--c-fg))" stroke="rgb(var(--c-ink-800))" strokeWidth={3 / pxm} paintOrder="stroke">{r.nivel === 'alto' ? '▲' : r.nivel === 'medio' ? '◆' : '✓'}</text>}
            </g>
          })}
          {geo.naves.map((n) => { const [lx, ly] = P((n.x0 + n.x1) / 2, cab.y1 - 1.5); return <text key={`l${n.nave}`} x={lx} y={ly} textAnchor="middle" dominantBaseline="middle" fontSize={12 / pxm} fontWeight={700} fill="rgb(var(--c-fg))" stroke="rgb(var(--c-ink-800))" strokeWidth={3 / pxm} paintOrder="stroke"><title>{`Nave ${n.nave}`}</title>{rot === 90 || (n.x1 - n.x0) * pxm < 60 ? `N${n.nave}` : `Nave ${n.nave}`}</text> })}
          {pxm > 5 && geo.camas.map((c) => Array.from({ length: geo.plantas.n }, (_, k) => { const [a, b] = P(c.x, geo.plantas.y_primera + k * geo.plantas.espaciado); return <circle key={`${c.bed}-${k}`} cx={a} cy={b} r={0.13} fill="rgb(var(--c-pos))" opacity=".35" /> }))}
          {/* lecturas puntuales (solo con capa de campo) */}
          {campo && mapa.lecturas.puntos?.map((p, i) => { const [a, b] = P(p[0], p[1]); const q = 2.5 / pxm; return <rect key={i} x={a - q} y={b - q} width={2 * q} height={2 * q} transform={`rotate(45 ${a} ${b})`} fill="rgb(255 255 255)" stroke="rgb(var(--c-fg-muted))" strokeWidth={0.8 / pxm} opacity=".45" /> })}
          {/* rastro y robot */}
          {/* solo el tramo reciente: el rastro completo de 24 h tapaba las camas */}
          {mapa.robot.rastro.length > 1 && <polyline points={mapa.robot.rastro.slice(-60).map((p) => P(p.x, p.y).join(',')).join(' ')} fill="none" stroke="rgb(var(--c-brand))" strokeWidth={1.8 / pxm} strokeDasharray={`${5 / pxm} ${4 / pxm}`} strokeLinecap="round" opacity=".55" />}
          {(() => { const [a, b] = P(mapa.robot.x, mapa.robot.y); const u = 11 / pxm; return (
            <g transform={`translate(${a} ${b}) rotate(${(rot === 0 ? -mapa.robot.heading * 180 / Math.PI : 90 - mapa.robot.heading * 180 / Math.PI) + 0})`}>
              <title>{`Robot (${mapa.robot.estado})`}</title>
              <path d={`M0 ${-u} L${u * 0.8} ${u * 0.8} L0 ${u * 0.4} L${-u * 0.8} ${u * 0.8} Z`} fill="rgb(var(--c-brand))" stroke="white" strokeWidth={1.8 / pxm} strokeLinejoin="round" />
            </g>) })()}
          {/* detecciones */}
          {vista === 'focos' && grupos.map((g) => {
            const [a, b] = P(g.x, g.y), r = radG(g.n) / pxm
            const abrir = () => onFoco?.(g.id)
            return <g key={g.id} style={{ cursor: 'pointer' }} onClick={(e) => { e.stopPropagation(); abrir() }}
              {...(interactivas ? { tabIndex: 0, role: 'button', 'aria-label': `Foco de ${g.clase} en ${g.ubicacion}: ${g.n} detecciones. Abrir` } : { 'aria-hidden': true })}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); abrir() } }}>
              <title>{`${g.ubicacion} · ${g.n} detecciones · confianza máx. ${Math.round(g.conf * 100)} %${g.estado ? ` · ${g.estado}` : ''}`}</title>
              <circle cx={a} cy={b} r={r} fill={colorDet(g.clase)} fillOpacity={0.78} stroke={g.abierto ? 'rgb(var(--c-fg))' : 'white'} strokeWidth={(g.abierto ? 2.4 : 1.2) / pxm} />
              {g.n > 1 && <text x={a} y={b} textAnchor="middle" dominantBaseline="central" fontSize={10 / pxm} fontWeight={700} fill="white" pointerEvents="none">{g.n}</text>}
            </g>
          })}
          {verDet && individuales.map((d) => {
            const [a, b] = P(d.x, d.y), r = rad(d.confianza) / pxm
            const grueso = d.foco_abierto && d.clase !== 'sana'
            const accion = () => onSelect(d)
            return <circle key={d.id} cx={a} cy={b} r={r} fill={colorDet(d.clase)} fillOpacity={d.clase === 'sana' ? 0.6 : 0.72}
              stroke={grueso ? 'rgb(var(--c-fg))' : 'white'} strokeWidth={(grueso ? 3.2 : 1.2) / pxm} style={{ cursor: 'pointer' }}
              {...(interactivas ? { tabIndex: 0, role: 'button', 'aria-label': `${d.deteccion} en ${d.ubicacion}, confianza ${d.confianza != null ? Math.round(d.confianza * 100) + ' %' : 'sin dato'}. Abrir detalle` } : { 'aria-hidden': true })}
              onClick={(e) => { e.stopPropagation(); accion() }} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); accion() } }}
              onPointerEnter={(e) => { const bb = caja.current!.getBoundingClientRect(); setHover({ d, x: e.clientX - bb.left, y: e.clientY - bb.top }) }}
              onPointerMove={(e) => { const bb = caja.current!.getBoundingClientRect(); setHover({ d, x: e.clientX - bb.left, y: e.clientY - bb.top }) }}
              onPointerLeave={() => setHover(null)} onFocus={() => setHover({ d, x: tam.w / 2, y: 20 })} onBlur={() => setHover(null)} />
          })}
        </svg>
        {/* brújula y escala */}
        <div className="pointer-events-none absolute left-3 top-3 flex flex-col items-center rounded-xl bg-ink-800/90 px-2 py-1 text-label font-semibold text-fg shadow-card" aria-hidden>
          <svg width="22" height="26" viewBox="0 0 22 26" style={{ transform: `rotate(${rot}deg)` }}><path d="M11 2 L17 20 L11 16 L5 20 Z" fill="rgb(var(--c-fg))" /></svg>N
        </div>
        <div className="pointer-events-none absolute bottom-3 left-3 rounded-xl bg-ink-800/90 px-2.5 py-1.5 text-label text-fg shadow-card" aria-hidden>
          <div style={{ width: barraM * pxm }} className="h-1.5 border-x-2 border-b-2 border-fg" />{barraM} m
        </div>
        {hover && (
          <div role="tooltip" className="pointer-events-none absolute z-10 max-w-[16rem] rounded-xl border border-ink-700 bg-ink-800 p-2.5 text-label text-fg shadow-pop" style={{ left: Math.min(Math.max(8, hover.x + 14), tam.w - 260), top: Math.min(hover.y + 14, tam.h - 130) }}>
            <b className="text-body">{hover.d.deteccion}</b> · {hover.d.ubicacion}<br />
            Confianza {hover.d.confianza != null ? `${Math.round(hover.d.confianza * 100)} %` : '—'} · {hover.d.fuente === 'camara_d1' ? 'Cámara D1' : 'Simulación'}<br />
            {nf(hover.d.temperatura_c)} °C · {nf(hover.d.humedad_pct, 0)} % HR · Día {hover.d.dia} {hover.d.hora}
            {hover.d.foco_estado && <><br />Foco: {hover.d.foco_estado}</>}
          </div>
        )}
      </div>

      {/* Leyenda en dos bloques: el color del fondo y lo que significan las marcas */}
      <div className="mt-3 grid gap-x-8 gap-y-3 rounded-2xl border border-ink-700 p-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
        <div className="min-w-0">
          <p className="tag">{campo ? (capa === 'temp' ? 'Temperatura (°C)' : 'Humedad relativa (%)') : capa === 'riesgo' ? 'Riesgo por cama' : 'Sin color de fondo'}</p>
          {campo && dom ? (<>
            <div className="mt-1.5 h-2.5 rounded-full" style={{ background: gradiente(capa === 'temp' ? ESC_T : ESC_H) }} aria-hidden />
            <div className="mt-1 flex justify-between text-label tabular-nums text-fg-muted"><span>{nf(dom.lo, capa === 'temp' ? 1 : 0)}</span><span>{nf((dom.lo + dom.hi) / 2, capa === 'temp' ? 1 : 0)}</span><span>{nf(dom.hi, capa === 'temp' ? 1 : 0)}</span></div>
          </>) : capa === 'riesgo' ? (<>
            <div className="mt-1.5 h-2.5 rounded-full" style={{ background: gradiente(ESC_R) }} aria-hidden />
            <div className="mt-1 flex justify-between text-label text-fg-muted"><span>✓ Bajo</span><span>◆ Medio</span><span>▲ Alto</span></div>
          </>) : null}
        </div>
        <div className="min-w-0">
          <p className="tag">Marcas</p>
          <div className="legend mt-1.5">
            <span className="legend-item"><i className="h-2.5 w-2.5 rounded-full bg-danger" aria-hidden />Hongo</span>
            <span className="legend-item"><i className="h-2.5 w-2.5 rounded-full bg-warn" aria-hidden />Plaga</span>
            {verSanas && <span className="legend-item"><i className="h-2.5 w-2.5 rounded-full bg-pos" aria-hidden />Sana</span>}
            <span className="legend-item"><i className="h-2.5 w-2.5 rounded-full border-2 border-fg" aria-hidden />Sin cerrar</span>
            <span className="legend-item"><span className="text-brand-300" aria-hidden>▲</span>Robot</span>
            <span className="legend-item text-fg-subtle">{vista === 'focos' ? 'Tamaño = nº de detecciones' : vista === 'detecciones' ? 'Tamaño = confianza' : ''}</span>
          </div>
        </div>
        <details className="text-label text-fg-subtle md:col-span-2">
          <summary className="cursor-pointer select-none hover:text-fg-muted">{vista === 'focos' ? `${grupos.length} focos · ${dets.length} detecciones` : `${dets.length} detecciones`} · datos simulados · cómo se calcula</summary>
          <p className="mt-1">◇ = lectura de sensor; el resto del color se interpola. {rotuloInterp} {interactivas ? 'Toca un círculo para ver el detalle.' : 'Hay muchas marcas: filtra o acerca el mapa; la tabla tiene todas.'}</p>
        </details>
      </div>
      </div>
    </Card>
  )
}
