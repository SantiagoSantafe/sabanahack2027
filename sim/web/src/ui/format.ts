const cache = new Map<number, Intl.NumberFormat>();

/** Spanish (Colombia) number formatting: decimal comma, thin grouping. */
export function fmt(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '–';
  let f = cache.get(digits);
  if (!f) {
    f = new Intl.NumberFormat('es-CO', { minimumFractionDigits: digits, maximumFractionDigits: digits });
    cache.set(digits, f);
  }
  return f.format(v);
}

export type Level = { label: string; tone: 'ok' | 'warn' | 'danger' };

export type RiskLevels = { medium: number; high: number };
export const DEFAULT_LEVELS: RiskLevels = { medium: 0.05, high: 0.15 };

/** Daily infection index → plain-language level (thresholds come from weather.yaml risk_levels). */
export function riskLevel(r: number, lv: RiskLevels = DEFAULT_LEVELS): Level {
  if (r >= lv.high) return { label: 'Alto', tone: 'danger' };
  if (r >= lv.medium) return { label: 'Medio', tone: 'warn' };
  return { label: 'Bajo', tone: 'ok' };
}

export function pct(v: number): string {
  return `${fmt(v * 100, 0)} %`;
}
