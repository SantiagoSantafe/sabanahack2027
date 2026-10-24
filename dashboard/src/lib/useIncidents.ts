import { useEffect, useRef, useState } from 'react'
import mock from '../data/mock.json'
import type { Incidencia, Modo, Resumen } from '../types'

export const FORCE_MOCK_ON = import.meta.env.VITE_FORCE_MOCK === 'true'
export const API_URL: string = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8010'
const FORCE_MOCK = import.meta.env.VITE_FORCE_MOCK === 'true'
const MAX_ITEMS = 1000
const HISTORY = 60

export interface Muestra { t: number; temp: number; hum: number; sana: number; activas: number }

export interface Estado {
  modo: Modo
  items: Incidencia[] // más recientes primero
  resumen: Resumen
  historia: Muestra[]
  nuevos: Set<string>
  actualizado: number | null // ms del último dato recibido en vivo
}

const MOCK = mock as Incidencia[]

function resumenDeItems(items: Incidencia[]): Resumen {
  const t = items.filter((i) => i.temperatura_c != null)
  const h = items.filter((i) => i.humedad_pct != null)
  const alertas = items.filter((i) => i.estado === 'Alerta').length
  const avg = (a: number[]) => (a.length ? Math.round((a.reduce((x, y) => x + y, 0) / a.length) * 10) / 10 : undefined)
  return {
    sesion: null, conectado: false, total: items.length,
    temperatura_promedio: avg(t.map((i) => i.temperatura_c as number)),
    humedad_promedio: avg(h.map((i) => i.humedad_pct as number)),
    plantas_saludables_pct: items.length ? Math.round((1000 * (items.length - alertas)) / items.length) / 10 : 100,
    incidencias_activas: alertas, alertas_total: alertas,
  }
}

function historiaMock(): Muestra[] {
  const asc = [...MOCK].sort((a, b) => a.ts - b.ts)
  return asc.map((_, k) => {
    const r = resumenDeItems(asc.slice(0, k + 1))
    return { t: asc[k].ts * 1000, temp: r.temperatura_promedio ?? 0, hum: r.humedad_promedio ?? 0, sana: r.plantas_saludables_pct ?? 0, activas: r.incidencias_activas ?? 0 }
  })
}

async function getJson<T>(path: string, ms = 2500): Promise<T> {
  const ctl = new AbortController()
  const timer = setTimeout(() => ctl.abort(), ms)
  try {
    const r = await fetch(`${API_URL}${path}`, { signal: ctl.signal })
    if (!r.ok) throw new Error(String(r.status))
    return (await r.json()) as T
  } finally {
    clearTimeout(timer)
  }
}

export function useIncidents(): Estado {
  const [state, setState] = useState<Estado>({
    modo: 'conectando', items: [], resumen: { sesion: null, conectado: false, total: 0 }, historia: [], nuevos: new Set(), actualizado: null,
  })
  const itemsRef = useRef<Incidencia[]>([])

  useEffect(() => {
    let es: EventSource | null = null
    let retry: ReturnType<typeof setTimeout> | undefined
    let cancelled = false
    let clearNew: ReturnType<typeof setTimeout> | undefined
    let historia: Muestra[] = []

    const useMock = () => {
      itemsRef.current = [...MOCK].sort((a, b) => b.ts - a.ts)
      historia = historiaMock()
      setState({ modo: 'ejemplo', items: itemsRef.current, resumen: resumenDeItems(itemsRef.current), historia, nuevos: new Set(), actualizado: null })
    }

    const connect = async () => {
      if (FORCE_MOCK) return useMock()
      try {
        const [res, inc] = await Promise.all([
          getJson<Resumen>('/api/dashboard/resumen'),
          getJson<{ items: Incidencia[] }>('/api/dashboard/incidencias?limit=500'),
        ])
        if (cancelled) return
        itemsRef.current = inc.items
        historia = []
        setState({ modo: 'vivo', items: inc.items, resumen: res, historia, nuevos: new Set(), actualizado: Date.now() })
        es = new EventSource(`${API_URL}/api/dashboard/stream`)
        es.addEventListener('update', (ev) => {
          const d = JSON.parse((ev as MessageEvent).data) as { reset: boolean; nuevas: Incidencia[]; resumen: Resumen }
          const base = d.reset ? [] : itemsRef.current
          const known = new Set(base.map((i) => i.id))
          const fresh = d.nuevas.filter((i) => !known.has(i.id))
          itemsRef.current = [...fresh.reverse(), ...base].slice(0, MAX_ITEMS)
          const r = d.resumen
          historia = [...(d.reset ? [] : historia), {
            t: Date.now(), temp: r.temperatura_promedio ?? 0, hum: r.humedad_promedio ?? 0,
            sana: r.plantas_saludables_pct ?? 0, activas: r.incidencias_activas ?? 0,
          }].slice(-HISTORY)
          const nuevos = d.reset ? new Set<string>() : new Set(fresh.map((i) => i.id))
          setState({ modo: 'vivo', items: itemsRef.current, resumen: r, historia, nuevos, actualizado: Date.now() })
          if (nuevos.size) {
            clearTimeout(clearNew)
            clearNew = setTimeout(() => setState((s) => ({ ...s, nuevos: new Set() })), 3500)
          }
        })
        es.onerror = () => {
          es?.close()
          es = null
          if (!cancelled) { useMock(); retry = setTimeout(connect, 5000) }
        }
      } catch {
        if (cancelled) return
        useMock()
        retry = setTimeout(connect, 8000)
      }
    }
    connect()
    return () => { cancelled = true; es?.close(); clearTimeout(retry); clearTimeout(clearNew) }
  }, [])

  return state
}
