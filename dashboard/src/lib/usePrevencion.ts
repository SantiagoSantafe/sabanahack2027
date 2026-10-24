import { useCallback, useEffect, useRef, useState } from 'react'
import mock from '../data/mock_prevencion.json'
import type { AccionHist, Cobertura, Foco, FocosKpis, Modo, Prevencion, Riesgo } from '../types'
import { API_URL } from './useIncidents'

const VACIO: Prevencion = { focos: [], kpis: { focos_abiertos: 0, detecciones: 0, sin_atender_rojo: 0, por_estado: { nuevo: 0, asignado: 0, verificado: 0, tratado: 0, cerrado: 0 }, etiquetas: { total: 0, confirmadas: 0, falsas_alarma: 0, pct_falsas: null } }, riesgo: null, cobertura: null }
const POLL_MS = 4000

async function getJson<T>(path: string): Promise<T> {
  const r = await fetch(`${API_URL}${path}`, { signal: AbortSignal.timeout(4000) })
  if (!r.ok) throw new Error(String(r.status))
  return (await r.json()) as T
}

export interface AccionIn { accion: 'asignar' | 'verificar' | 'tratar' | 'cerrar' | 'nota'; responsable?: string; resultado?: 'confirmado' | 'falsa_alarma'; detalle?: string; nota?: string }

/** Focos, riesgo próximo y cobertura. En modo ejemplo usa datos locales y las acciones quedan desactivadas. */
export function usePrevencion(modo: Modo) {
  const [data, setData] = useState<Prevencion>(modo === 'ejemplo' ? (mock as unknown as Prevencion) : VACIO)
  const [cargado, setCargado] = useState(modo === 'ejemplo')
  const vivo = useRef(false)
  vivo.current = modo === 'vivo'

  const cargar = useCallback(async () => {
    try {
      const [f, r, c] = await Promise.all([
        getJson<{ items: Foco[]; kpis: FocosKpis }>('/api/dashboard/focos?limit=200'),
        getJson<Riesgo>('/api/dashboard/riesgo'),
        getJson<Cobertura>('/api/dashboard/cobertura'),
      ])
      if (vivo.current) { setCargado(true); setData({ focos: f.items, kpis: f.kpis, riesgo: r.camas?.length ? r : null, cobertura: c.camas?.length ? c : null }) }
    } catch { /* el próximo ciclo reintenta; la conexión general ya avisa */ }
  }, [])

  useEffect(() => {
    if (modo === 'ejemplo') { setData(mock as unknown as Prevencion); setCargado(true); return }
    if (modo !== 'vivo') return
    cargar()
    const id = setInterval(cargar, POLL_MS)
    return () => clearInterval(id)
  }, [modo, cargar])

  const accion = useCallback(async (focoId: string, body: AccionIn): Promise<string | null> => {
    try {
      const r = await fetch(`${API_URL}/api/dashboard/focos/${encodeURIComponent(focoId)}/accion`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) })
      if (!r.ok) { const e = await r.json().catch(() => ({})); return typeof e.detail === 'string' ? e.detail : 'No se pudo registrar la acción' }
      await cargar()
      return null
    } catch { return 'Sin conexión con el simulador' }
  }, [cargar])

  const historial = useCallback(async (focoId: string): Promise<AccionHist[]> => {
    try { return (await getJson<{ historial: AccionHist[] }>(`/api/dashboard/focos/${encodeURIComponent(focoId)}/historial`)).historial } catch { return [] }
  }, [])

  return { ...data, cargado, accion, historial, puedeActuar: modo === 'vivo' }
}
