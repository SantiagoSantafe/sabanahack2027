/** Color tokens — single source of truth for scene and UI. */
export const palette = {
  // foliage
  leafHealthy: ['#5DBB3F', '#6FCB45', '#4EA83A', '#7FD34E', '#3F9A34'],
  leafNewGrowth: '#B6D94C',
  leafAtRisk: '#E8E23A',
  leafAsympGod: '#FF9A1F',
  leafSymptomatic: '#E8392B',
  leafConfirmed: '#8E1B1B',
  leafTreated: '#3E8EF0',
  stem: '#8A4B2E',

  // berries
  berryRipe: ['#3A55D6', '#2F45B8', '#4A62E8', '#5A4BC9'],
  berryUnripe: ['#A9D44A', '#D9729A'],
  berrySick: '#7A4E2B',
  berryCrown: '#26305E',

  // terrain
  bedSoil: '#D2733D',
  bedTop: '#B95E2E',
  pot: '#22252C',
  groundCover: '#34373F',
  tunnelFloor: '#C88A55',
  plastic: '#F2F8FF',
  steel: '#D5DAE3',
  grass: '#79C44A',
  grassDark: '#5FAE3A',
  path: '#C9A06A',
  drip: '#1E1E24',
  wood: '#9A6337',
  woodDark: '#6B4024',

  // scene accents
  sky: '#9ED3F5',
  fog: '#DDEBF2',
  robotBody: '#30364A',
  robotShell: '#E9EDF5',
  robotAccent: '#8BD346',
  sensorBeam: '#59E0FF',
  alertRing: '#FF5A4E',
  falseAlarmRing: '#A7AFBF',
  treatedRing: '#3E8EF0',

  // UI
  ink: '#1B1F4B',
  inkSoft: '#2A3070',
  paper: '#F3F5FF',
  leafUi: '#8BD346',
  berryUi: '#6F8BFF',
  warn: '#FFB830',
  danger: '#FF5A4E',
} as const;

/** Leaf tint for a plant state; returns null when the base green should be kept. */
export function stateTint(state: number, godMode: boolean): { color: string; mix: number } | null {
  switch (state) {
    case 1:
      return { color: palette.leafAtRisk, mix: 0.4 };
    case 2:
      return godMode ? { color: palette.leafAsympGod, mix: 0.75 } : null;
    case 3:
    case 4:
      return { color: palette.leafSymptomatic, mix: 0.78 };
    case 5:
      return { color: palette.leafConfirmed, mix: 0.85 };
    case 6:
      return { color: palette.leafTreated, mix: 0.55 };
    default:
      return null;
  }
}

/** Ring marker drawn at the plant base. */
export function stateRing(state: number): string | null {
  if (state === 4) return palette.alertRing;
  if (state === 5) return palette.leafConfirmed;
  if (state === 6) return palette.treatedRing;
  if (state === 7) return palette.falseAlarmRing;
  return null;
}

export function isSick(state: number): boolean {
  return state === 3 || state === 4 || state === 5;
}

export const STATE_NAMES: Record<number, string> = {
  0: 'Sana',
  1: 'En riesgo',
  2: 'Infectada sin síntomas',
  3: 'Con síntomas',
  4: 'Alerta pendiente',
  5: 'Confirmada',
  6: 'Tratada',
  7: 'Falsa alarma',
};

export const STATE_COLORS: Record<number, string> = {
  0: palette.leafHealthy[0],
  1: palette.leafAtRisk,
  2: palette.leafAsympGod,
  3: palette.leafSymptomatic,
  4: palette.alertRing,
  5: palette.leafConfirmed,
  6: palette.leafTreated,
  7: palette.falseAlarmRing,
};

