import type { Layout, SimState } from '../state/store';

export type FieldGeom = Layout & {
  nBeds: number;
  nPlants: number;
  bedH: number;
  potD: number;
  bedLen: number;
  x0: number;
  x1: number;
  archH: number;
  groundW: number;
  groundD: number;
};

const FALLBACK: Layout = {
  naves: 4,
  beds_per_nave: 3,
  nave_width: 6.8,
  nave_x0: [-13.6, -6.8, 0, 6.8],
  bed_x: Array.from({ length: 12 }, (_, b) => -13.6 + Math.floor(b / 3) * 6.8 + ((b % 3) + 0.5) * (6.8 / 3)),
  bed_w: 0.6,
  aisles: [],
  n_plants: 107,
  spacing: 0.75,
  z0: -39.75,
  bed_z0: -40.05,
  bed_z1: 40.05,
  head_s: -41.35,
  head_n: 40.8,
  main_path_w: 5,
  north_w: 1.5,
  base: [-12.4, -43.65],
  area_ha: 0.22,
};

/** Geometry comes from the server (`layout`) so client and engine never disagree. */
export function fieldGeom(state: SimState | null): FieldGeom {
  const l = state?.layout ?? FALLBACK;
  const nBeds = l.bed_x.length;
  const x0 = l.nave_x0[0];
  const x1 = l.nave_x0[l.naves - 1] + l.nave_width; // incluye el camino central entre bloques
  const bedLen = (l.n_plants - 1) * l.spacing;
  return {
    ...l,
    nBeds,
    nPlants: l.n_plants,
    bedH: state?.field.bed_height_m ?? 0.35,
    potD: state?.field.pot_diameter_m ?? 0.42,
    bedLen,
    x0,
    x1,
    archH: state?.field.arch_height_m ?? 4.2,
    groundW: x1 - x0 + 24,
    groundD: l.bed_z1 - l.bed_z0 + l.main_path_w + 30,
  };
}

export function plantWorldPos(g: FieldGeom, bed: number, plant: number): [number, number, number] {
  return [g.bed_x[bed] ?? 0, g.bedH, g.z0 + plant * g.spacing];
}

/** Obstacles for manual driving: pot rows, nave walls inside the tunnel and the block edges. */
export function blocked(g: FieldGeom, x: number, z: number, r: number): boolean {
  const inTunnel = z > g.bed_z0 - 0.4 && z < g.bed_z1 + g.north_w;
  if (z > g.bed_z1 + g.north_w - r || z < g.bed_z0 - g.main_path_w + r) return true;
  if (x < g.x0 - 4 || x > g.x1 + 4) return true;
  if (inTunnel && (x < g.x0 + r || x > g.x1 - r)) return true;
  if (z >= g.bed_z0 - r && z <= g.bed_z1 + r) {
    for (const cx of g.bed_x) if (Math.abs(x - cx) <= g.bed_w / 2 + r) return true;
    for (let k = 1; k < g.naves; k++) if (Math.abs(x - (g.x0 + k * g.nave_width)) < 0.06 + r) return true;
  }
  return false;
}

export function aisleAt(g: FieldGeom, x: number) {
  let best = g.aisles[0];
  for (const a of g.aisles) if (Math.abs(a.x - x) < Math.abs(best.x - x)) best = a;
  return best;
}

/** Deterministic PRNG so every plant keeps the same shape across reloads. */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function bedLabel(g: FieldGeom, bed: number): string {
  return `Nave ${Math.floor(bed / g.beds_per_nave) + 1} · Cama ${(bed % g.beds_per_nave) + 1}`;
}
