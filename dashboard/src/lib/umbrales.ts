// Umbrales de referencia (orientativos, ajustables; validar con el agrónomo de AGRAR).
export const UMBRALES = {
  temp: { min: 12, max: 26 },        // °C ideal en invernadero
  hr: { min: 60, max: 85, critica: 92 }, // % HR; >85 favorece hongos, >92 riesgo alto
  sanas: { ok: 95, atencion: 85 },   // % plantas saludables
}

export type Semaforo = 'ok' | 'atencion' | 'critico' | 'nd'
export interface Evaluacion { nivel: Semaforo; texto: string }

export function evalTemp(v?: number): Evaluacion {
  const { min, max } = UMBRALES.temp
  if (v == null) return { nivel: 'nd', texto: 'Sin dato' }
  if (v < min) return { nivel: 'atencion', texto: 'Por debajo del rango' }
  if (v > max) return { nivel: 'atencion', texto: 'Por encima del rango' }
  return { nivel: 'ok', texto: 'En rango' }
}
export function evalHr(v?: number): Evaluacion {
  const { max, critica, min } = UMBRALES.hr
  if (v == null) return { nivel: 'nd', texto: 'Sin dato' }
  if (v > critica) return { nivel: 'critico', texto: 'Muy alta: riesgo de hongos' }
  if (v > max) return { nivel: 'atencion', texto: 'Alta: vigilar hongos' }
  if (v < min) return { nivel: 'atencion', texto: 'Baja' }
  return { nivel: 'ok', texto: 'En rango' }
}
export function evalSanas(v?: number): Evaluacion {
  if (v == null) return { nivel: 'nd', texto: 'Sin dato' }
  if (v >= UMBRALES.sanas.ok) return { nivel: 'ok', texto: 'Cultivo sano' }
  if (v >= UMBRALES.sanas.atencion) return { nivel: 'atencion', texto: 'Por debajo de la meta' }
  return { nivel: 'critico', texto: 'Muy por debajo de la meta' }
}
export function evalAlertas(n?: number): Evaluacion {
  if (n == null) return { nivel: 'nd', texto: 'Sin dato' }
  return n === 0 ? { nivel: 'ok', texto: 'Sin alertas' } : { nivel: n >= 50 ? 'critico' : 'atencion', texto: n === 1 ? 'Requiere revisión' : 'Requieren revisión' }
}
