export type Clase = 'sana' | 'oidio' | 'alternaria' | 'heliothis' | 'desconocida'

export interface Incidencia {
  id: string
  ts: number
  dia: number | null
  hora: string | null
  ubicacion: string
  nave: number
  cama: number
  planta: number | null
  deteccion: string
  clase: Clase
  temperatura_c: number | null
  humedad_pct: number | null
  estado: 'Saludable' | 'Alerta'
  fuente: 'simulacion' | 'camara_d1'
  confianza: number | null
  frame?: string | null
}

export interface Resumen {
  sesion: number | null
  bloque?: number
  bloque_naves?: number[]
  conectado: boolean
  total: number
  dia?: number
  hora?: string
  temperatura_promedio?: number
  temperatura_actual?: number
  humedad_actual?: number
  humedad_promedio?: number
  plantas_saludables_pct?: number
  incidencias_activas?: number
  alertas_total?: number
  por_clase?: Record<string, number>
}

export type Modo = 'conectando' | 'vivo' | 'ejemplo'

export type EstadoFoco = 'nuevo' | 'asignado' | 'verificado' | 'tratado' | 'cerrado'
export type Semaforo3 = 'verde' | 'ambar' | 'rojo'

export interface Foco {
  id: string
  nave: number
  cama: number
  ubicacion: string
  deteccion: string
  clase: Clase
  familia: string
  plantas: number
  detecciones: number
  incidencias: string[]
  fuentes: string[]
  frame: string | null
  foto?: string | null
  riesgo_cama: number
  puntaje: number
  nivel: 'alta' | 'media' | 'baja'
  horas_sin_atender: number
  semaforo: Semaforo3
  tendencia: 'crece' | 'estable' | 'baja'
  serie: number[]
  por_que: string[]
  estado: EstadoFoco
  resultado: 'confirmado' | 'falsa_alarma' | null
  responsable: string | null
  tratamiento: string | null
  abierto: boolean
  aviso: string
}

export interface FocosKpis {
  focos_abiertos: number
  detecciones: number
  sin_atender_rojo: number
  por_estado: Record<EstadoFoco, number>
  etiquetas: { total: number; confirmadas: number; falsas_alarma: number; pct_falsas: number | null }
}

export interface AccionHist { id: number; accion: string; estado: string; resultado: string | null; responsable: string | null; detalle: string | null; nota: string | null; ts: number }

export type NivelRiesgo = 'bajo' | 'medio' | 'alto'
export interface VentanaRiesgo { horas: string; riesgo: number; nivel: NivelRiesgo; enfermedad_nombre: string; horas_mojadas: number; horas_hr_alta: number; temp_mojada_c: number }
export interface CamaRiesgo { nave: number; cama: number; nivel: NivelRiesgo; max_riesgo: number; ahora: { riesgo: number; nivel: NivelRiesgo }; ventanas: VentanaRiesgo[] }
export interface Aviso { id: string; nivel: NivelRiesgo; texto: string; nota: string; ventana: string }
export interface Riesgo { umbrales?: Record<string, [number, number]>; estimado: boolean; nota: string; camas: CamaRiesgo[]; avisos: Aviso[]; clima?: { horas_mojadas_hoy: number } }
export interface CamaCobertura { nave: number; cama: number; ultima_dia: number | null; ultima_hora: string | null; horas_sin_revisar: number | null; ciego: boolean }
export interface Cobertura { ciego_h: number; camas: CamaCobertura[]; puntos_ciegos: CamaCobertura[]; nota?: string }
export interface Prevencion { focos: Foco[]; kpis: FocosKpis; riesgo: Riesgo | null; cobertura: Cobertura | null }

export interface Rejilla { nx: number; ny: number; celda: number; x0: number; y0: number; valores: number[]; medido: number[]; min: number | null; max: number | null; n_lecturas: number }
export interface GeoCama { bed: number; nave: number; cama: number; x: number; ancho: number; y0: number; y1: number }
export interface Geometria {
  bounds: { x0: number; x1: number; y0: number; y1: number }
  naves: { nave: number; x0: number; x1: number }[]
  camas: GeoCama[]
  plantas: { n: number; espaciado: number; y_primera: number }
  pasillos: { x: number; nave: number; y0: number; y1: number }[]
  camino_central: { x0: number; x1: number; y0: number; y1: number } | null // entre el Bloque 1 y el 2 (con camino_cabecera)
  camino_cabecera?: { x0: number; x1: number; y0: number; y1: number } // cabecera sur, de lado a lado
  cabecera_norte: { y0: number; y1: number }
  bloques?: { id: number; naves: number[]; x0: number; x1: number; inicio: [number, number, number]; inicio_txt: string }[]
  bloque_activo?: number
  base: { x: number; y: number }
}
export interface Deteccion {
  id: string; ts: number; dia: number | null; hora: string | null; t_h: number; ubicacion: string; nave: number; cama: number; planta: number | null
  deteccion: string; clase: Clase; temperatura_c: number | null; humedad_pct: number | null; estado: 'Saludable' | 'Alerta'
  fuente: 'simulacion' | 'camara_d1'; confianza: number | null; x: number; y: number
  foco_id: string | null; foco_estado: EstadoFoco | null; foco_abierto: boolean; foco_semaforo: Semaforo3 | null
}
export interface RiesgoCamaMapa { nave: number; cama: number; ahora: number; nivel_ahora: NivelRiesgo; max: number; nivel: NivelRiesgo }
export interface Mapa {
  sesion: number | null
  ahora_h: number
  horas_ventana?: number
  geometria: Geometria
  temperatura: Rejilla
  humedad: Rejilla
  lecturas: { n: number; por_tipo: Record<string, number>; puntos?: [number, number, number, number, string][] }
  detecciones: Deteccion[]
  riesgo: RiesgoCamaMapa[]
  robot: { x: number; y: number; heading: number; estado: string; rastro: { x: number; y: number }[] }
  nota: string
}
