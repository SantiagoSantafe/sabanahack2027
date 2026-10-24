import { aisleAt, type FieldGeom } from '../scene/geometry';
import type { Telemetry } from '../state/store';

/**
 * Digital twin of the real D1 in Manual. The bridge's odometry lives in the robot's own frame
 * (x forward, y left, yaw counter-clockwise). It is anchored to the twin's pose when the link comes
 * up, when Manual starts or on "Re-centrar"; from then on the twin replays the displacement.
 * Scene frame: forward = (sin h, cos h) on (x, z) and the heading grows when turning left.
 */
export const twin = { anchored: false, linkId: -1, x0: 0, z0: 0, h0: 0, ox: 0, oy: 0, oyaw: 0, recenter: false,
  inicio: null as { x: number; z: number; heading: number } | null };

/** "Volver al inicio": pone el gemelo en el inicio del bloque y ancla ahí la odometría actual del D1. */
export function requestInicio(p: { x: number; z: number; heading: number }) {
  twin.inicio = p;
}

type Pose = { x: number; z: number; heading: number };
export type Odom = { x: number; y: number; yaw: number };

export function odomOf(t: Telemetry | null | undefined): Odom | null {
  if (!t || t.x == null || t.y == null || t.yaw == null) return null;
  return { x: t.x, y: t.y, yaw: t.yaw };
}

export function anchorTwin(p: Pose, o: Odom, linkId: number) {
  Object.assign(twin, { anchored: true, linkId, x0: p.x, z0: p.z, h0: p.heading, ox: o.x, oy: o.y, oyaw: o.yaw });
}

export function twinPose(o: Odom): Pose {
  const dx = o.x - twin.ox;
  const dy = o.y - twin.oy;
  const c = Math.cos(twin.oyaw);
  const s = Math.sin(twin.oyaw);
  const fwd = c * dx + s * dy; // displacement in the robot frame at the anchor
  const left = -s * dx + c * dy;
  const sh = Math.sin(twin.h0);
  const ch = Math.cos(twin.h0);
  return { x: twin.x0 + fwd * sh + left * ch, z: twin.z0 + fwd * ch - left * sh, heading: twin.h0 + wrapAngle(o.yaw - twin.oyaw) };
}

/** "Re-centrar": inside the rows, put the twin on the nearest aisle's center line, facing along it. */
export function recenterPose(g: FieldGeom, p: Pose): Pose {
  if (!g.aisles.length || p.z < g.bed_z0 || p.z > g.bed_z1) return p;
  return { x: aisleAt(g, p.x).x, z: p.z, heading: Math.cos(p.heading) >= 0 ? 0 : Math.PI };
}

export function requestRecenter() {
  twin.recenter = true;
}

export function wrapAngle(a: number): number {
  return Math.atan2(Math.sin(a), Math.cos(a));
}
