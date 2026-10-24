import { useEffect, useState } from 'react'
import mock from '../data/mock_mapa.json'
import type { Mapa, Modo } from '../types'
import { API_URL } from './useIncidents'

/** Planta del bloque: en vivo consulta /api/dashboard/mapa cada 3 s; en modo ejemplo usa datos locales. */
export function useMapa(modo: Modo): Mapa | null {
  const [m, setM] = useState<Mapa | null>(modo === 'ejemplo' ? (mock as unknown as Mapa) : null)
  useEffect(() => {
    if (modo === 'ejemplo') { setM(mock as unknown as Mapa); return }
    if (modo !== 'vivo') return
    let vivo = true
    const cargar = async () => {
      try {
        const r = await fetch(`${API_URL}/api/dashboard/mapa?horas=24`, { signal: AbortSignal.timeout(6000) })
        if (!r.ok) return
        const d = (await r.json()) as Mapa
        if (vivo && d.geometria) setM(d)
      } catch { /* reintenta en el próximo ciclo */ }
    }
    cargar()
    const id = setInterval(cargar, 3000)
    return () => { vivo = false; clearInterval(id) }
  }, [modo])
  return m
}
