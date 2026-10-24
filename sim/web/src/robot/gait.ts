/** Procedural trot for the D1 (URDF joint conventions: thigh +θ swings the foot backward). */

export type JointAngles = Record<string, number>;

export const LEGS = ['FL', 'FR', 'RL', 'RR'] as const;

/** Dimensions from the official D1 URDF (used by the procedural fallback). */
export const D1 = {
  hipX: 0.17449,
  hipY: 0.062,
  abadOffset: 0.0974,
  thigh: 0.2,
  calf: 0.21366,
  standThigh: 0.8,
  standKnee: -1.6,
  bodyHeight: 0.31,
  cameraHeight: 0.3,
  cameraForward: 0.3,
  mastHeight: 1.35,
};

/**
 * Diagonal pairs (FL+RR, FR+RL) in phase; amplitude and cadence follow speed.
 * `phase` accumulates in radians; `inspect` blends into the lean-forward pose.
 */
export function trotGait(speed: number, phase: number, inspect: number, out: JointAngles): JointAngles {
  const k = Math.min(1, speed / 0.5);
  for (const leg of LEGS) {
    const front = leg[0] === 'F';
    const ph = phase + (leg === 'FL' || leg === 'RR' ? 0 : Math.PI);
    const swing = Math.sin(ph);
    const lift = Math.max(0, -Math.cos(ph));
    let thigh = D1.standThigh + 0.3 * k * swing;
    let knee = D1.standKnee - 0.55 * k * lift;
    const lean = front ? 0.32 : -0.12;
    thigh += inspect * lean;
    knee += inspect * (front ? -0.35 : 0.1);
    out[`${leg}_ABAD_JOINT`] = (leg[1] === 'L' ? 1 : -1) * 0.04 * k * Math.sin(ph);
    out[`${leg}_HIP_JOINT`] = thigh;
    out[`${leg}_KNEE_JOINT`] = knee;
  }
  return out;
}

/** Cadence in Hz for a stride of ~0.25 m. */
export function cadence(speed: number): number {
  return Math.max(1.6, speed / 0.25);
}
