import { useEffect, useState } from 'react'
import { API_URL } from '../lib/useIncidents'
import type { Modo } from '../types'

const BLOQUES = [
  { id: 1, naves: '1 y 2' },
  { id: 2, naves: '3 y 4' },
]

/** El supervisor decide qué bloque recorre el robot esta noche; el simulador y la ruta real lo siguen. */
export function BloqueRobot({ actual, modo }: { actual?: number; modo: Modo }) {
  const [pedido, setPedido] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const vivo = modo === 'vivo'
  const activo = pedido ?? actual ?? 1
  useEffect(() => { if (pedido != null && actual === pedido) setPedido(null) }, [actual, pedido])

  const elegir = async (b: number) => {
    if (!vivo || b === activo) return
    setPedido(b); setError(null)
    try {
      const r = await fetch(`${API_URL}/api/dashboard/bloque`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ bloque: b }), signal: AbortSignal.timeout(4000) })
      if (!r.ok) throw new Error(r.status === 409 ? 'El simulador no tiene una sesión abierta' : `Error ${r.status}`)
    } catch (e) {
      setPedido(null)
      setError(e instanceof Error ? e.message : 'No se pudo cambiar el bloque')
    }
  }

  return (
    <div className="flex flex-col items-start gap-1 lg:items-end">
      <span className="tag">Robot asignado a</span>
      <div role="radiogroup" aria-label="Bloque que recorre el robot" className="inline-flex gap-1 rounded-full border border-ink-700 bg-ink-900 p-1">
        {BLOQUES.map((b) => (
          <button key={b.id} type="button" role="radio" aria-checked={activo === b.id} disabled={!vivo} onClick={() => elegir(b.id)}
            title={`Bloque ${b.id}: naves ${b.naves}`}
            className={`min-h-[40px] whitespace-nowrap rounded-full px-3.5 text-body disabled:opacity-50 md:min-h-[34px] ${activo === b.id ? 'bg-brand font-semibold text-white' : 'text-fg-muted hover:bg-ink-800'}`}>
            Bloque {b.id}
          </button>
        ))}
      </div>
      {error ? <span role="alert" className="text-label text-danger-300">{error}</span>
        : <span className="text-label text-fg-subtle">{pedido != null ? 'Enviando al robot…' : vivo ? 'El robot y la simulación siguen este bloque' : 'Solo con el simulador conectado'}</span>}
    </div>
  )
}
