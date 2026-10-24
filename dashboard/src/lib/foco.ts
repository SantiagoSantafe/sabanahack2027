import type { EstadoFoco, Foco, Semaforo3 } from '../types'

export const ESTADO_TXT: Record<EstadoFoco, string> = { nuevo: 'Nuevo', asignado: 'Asignado', verificado: 'Verificado', tratado: 'Tratado', cerrado: 'Cerrado' }
export const PASOS: EstadoFoco[] = ['nuevo', 'asignado', 'verificado', 'tratado', 'cerrado']

export const SEMAFORO: Record<Semaforo3, { glifo: string; chip: string }> = {
  rojo: { glifo: '▲', chip: 'bg-danger/10 text-danger-300 border-danger/40' },
  ambar: { glifo: '◆', chip: 'bg-warn/15 text-warn-300 border-warn/40' },
  verde: { glifo: '✓', chip: 'bg-[rgb(var(--c-mint))] text-[rgb(var(--c-mint-fg))] border-transparent' },
}
export const TEND: Record<Foco['tendencia'], string> = { crece: '↗ Crece', estable: '→ Estable', baja: '↘ Baja' }

export function horasTxt(h: number): string {
  if (h < 1) return 'menos de 1 h'
  if (h < 48) return `${Math.round(h)} h`
  return `${Math.floor(h / 24)} d ${Math.round(h % 24)} h`
}

/** Siguiente acción del ciclo para el botón principal del foco. */
export function siguienteAccion(f: Foco): { accion: 'asignar' | 'verificar' | 'tratar' | 'cerrar'; texto: string } | null {
  switch (f.estado) {
    case 'nuevo': return { accion: 'asignar', texto: 'Enviar operario' }
    case 'asignado': return { accion: 'verificar', texto: 'Registrar confirmación' }
    case 'verificado': return f.resultado === 'confirmado' ? { accion: 'tratar', texto: 'Registrar tratamiento' } : { accion: 'cerrar', texto: 'Cerrar' }
    case 'tratado': return { accion: 'cerrar', texto: 'Cerrar' }
    default: return null
  }
}

export async function copiar(texto: string): Promise<boolean> {
  try { await navigator.clipboard.writeText(texto); return true } catch {
    try {
      const t = document.createElement('textarea'); t.value = texto; t.style.position = 'fixed'; t.style.opacity = '0'
      document.body.appendChild(t); t.select(); const ok = document.execCommand('copy'); t.remove(); return ok
    } catch { return false }
  }
}
