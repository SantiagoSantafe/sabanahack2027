import type { Clase, Incidencia } from '../types'

export type Nivel = 'alta' | 'media' | 'normal' | 'desconocida'

export interface InfoClase {
  nombre: string
  nivel: Nivel
  glifo: string // forma distinta por clase: no depender solo del color
  color: string // para gráficos (variables CSS)
  queEs: string
  queHacer: string[]
}

const v = (n: string) => `rgb(var(--c-${n}))`

export const CLASES: Record<Clase, InfoClase> = {
  sana: {
    nombre: 'Hoja sana', nivel: 'normal', glifo: '✓', color: v('pos'),
    queEs: 'La hoja no muestra signos de enfermedad ni plaga.',
    queHacer: ['No requiere acción.'],
  },
  oidio: {
    nombre: 'Oídio', nivel: 'alta', glifo: '●', color: v('cl-oidio'),
    queEs: 'Hongo que forma un polvillo blanco en hojas y frutos. Se favorece con humedad alta y poca ventilación.',
    queHacer: ['Inspeccionar las plantas vecinas de la misma cama.', 'Ventilar la nave para bajar la humedad relativa.', 'Retirar hojas afectadas y consultar al agrónomo el fungicida.'],
  },
  alternaria: {
    nombre: 'Alternaria', nivel: 'alta', glifo: '■', color: v('cl-alternaria'),
    queEs: 'Hongo que causa manchas oscuras con anillos en hojas y frutos. Prospera con follaje húmedo.',
    queHacer: ['Retirar hojas con manchas y sacarlas de la nave.', 'Evitar mojar el follaje y ventilar.', 'Confirmar con el agrónomo y definir tratamiento.'],
  },
  heliothis: {
    nombre: 'Heliothis', nivel: 'media', glifo: '▲', color: v('cl-heliothis'),
    queEs: 'Plaga: oruga que perfora frutos y brotes.',
    queHacer: ['Revisar el envés de las hojas y los frutos cercanos.', 'Buscar orugas o excremento y reforzar el monitoreo con trampas.', 'Consultar al agrónomo el control (p. ej. biológico).'],
  },
  desconocida: {
    nombre: 'Sin clasificar', nivel: 'desconocida', glifo: '?', color: 'rgb(139 144 160)',
    queEs: 'El robot detectó algo que no pudo clasificar.',
    queHacer: ['Revisar la planta en sitio.'],
  },
}

export const NIVEL_TXT: Record<Nivel, string> = { alta: 'Alta', media: 'Media', normal: 'Normal', desconocida: 'Revisar' }
const NIVEL_ORDEN: Record<Nivel, number> = { alta: 0, media: 1, desconocida: 2, normal: 3 }

export const nivelDe = (i: Pick<Incidencia, 'clase' | 'estado'>): Nivel =>
  i.estado === 'Saludable' ? 'normal' : (CLASES[i.clase] ?? CLASES.desconocida).nivel

/** Menor = más urgente: alertas primero, luego gravedad. */
export const urgencia = (i: Incidencia) => NIVEL_ORDEN[nivelDe(i)]

export const FUENTE: Record<Incidencia['fuente'], string> = { simulacion: 'Simulación', camara_d1: 'Cámara D1' }
