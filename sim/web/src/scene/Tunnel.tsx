import { useLayoutEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useStore } from '../state/store';
import { palette } from '../theme/palette';
import type { FieldGeom } from './geometry';

const GUTTER_H = 3.0;
const BAY = 4.0;

/** Macrotunnel: one arched plastic roof per nave, posts and gutters on the nave walls, side curtains (aleros). */
export function Tunnel({ g }: { g: FieldGeom }) {
  const show = useStore((s) => s.showTunnel);
  const aleroOpen = useStore((s) => s.state?.weather.alero_open ?? false);
  const enabled = useStore((s) => s.state?.weather.tunnel ?? true);
  const posts = useRef<THREE.InstancedMesh>(null);
  const hoops = useRef<THREE.InstancedMesh>(null);

  const z0 = g.bed_z0 - 0.3;
  const z1 = g.bed_z1 + g.north_w;
  const len = z1 - z0;
  const r = g.nave_width / 2;
  const rise = Math.max(0.4, g.archH - GUTTER_H);
  const bays = Math.max(1, Math.round(len / BAY));
  const walls = g.naves + 1;

  const roofGeo = useMemo(() => {
    const geo = new THREE.CylinderGeometry(r, r, len, 28, 1, true, Math.PI / 2, Math.PI);
    geo.rotateX(Math.PI / 2);
    geo.scale(1, rise / r, 1);
    return geo;
  }, [r, len, rise]);
  const hoopGeo = useMemo(() => {
    const geo = new THREE.TorusGeometry(r, 0.025, 5, 28, Math.PI);
    geo.scale(1, rise / r, 1);
    return geo;
  }, [r, rise]);

  useLayoutEffect(() => {
    const m = new THREE.Matrix4();
    if (posts.current) {
      let i = 0;
      for (let w = 0; w < walls; w++) {
        for (let b = 0; b <= bays; b++) {
          m.makeTranslation(g.x0 + w * g.nave_width, GUTTER_H / 2, z0 + (b * len) / bays);
          posts.current.setMatrixAt(i++, m);
        }
      }
      posts.current.instanceMatrix.needsUpdate = true;
    }
    if (hoops.current) {
      let i = 0;
      for (let k = 0; k < g.naves; k++) {
        for (let b = 0; b <= bays; b++) {
          m.makeTranslation(g.x0 + (k + 0.5) * g.nave_width, GUTTER_H, z0 + (b * len) / bays);
          hoops.current.setMatrixAt(i++, m);
        }
      }
      hoops.current.instanceMatrix.needsUpdate = true;
    }
  }, [g.x0, g.nave_width, g.naves, walls, bays, len, z0]);

  if (!enabled) return null;
  const curtainH = aleroOpen ? GUTTER_H * 0.35 : GUTTER_H;
  const curtainY = aleroOpen ? GUTTER_H - curtainH / 2 : curtainH / 2;

  return (
    <group>
      <instancedMesh ref={posts} args={[undefined, undefined, walls * (bays + 1)]} castShadow>
        <boxGeometry args={[0.07, GUTTER_H, 0.07]} />
        <meshStandardMaterial color={palette.steel} metalness={0.6} roughness={0.3} />
      </instancedMesh>
      <instancedMesh ref={hoops} args={[hoopGeo, undefined, g.naves * (bays + 1)]}>
        <meshStandardMaterial color={palette.steel} metalness={0.6} roughness={0.3} />
      </instancedMesh>
      {Array.from({ length: walls }, (_, w) => (
        <mesh key={`gutter${w}`} position={[g.x0 + w * g.nave_width, GUTTER_H + 0.04, z0 + len / 2]}>
          <boxGeometry args={[0.16, 0.1, len]} />
          <meshStandardMaterial color={palette.steel} metalness={0.5} roughness={0.35} />
        </mesh>
      ))}
      {show &&
        Array.from({ length: g.naves }, (_, k) => (
          <mesh key={`roof${k}`} geometry={roofGeo} position={[g.x0 + (k + 0.5) * g.nave_width, GUTTER_H, z0 + len / 2]} raycast={() => null}>
            <meshStandardMaterial color={palette.plastic} transparent opacity={0.17} roughness={0.15} side={THREE.DoubleSide} depthWrite={false} />
          </mesh>
        ))}
      {show &&
        [g.x0, g.x1].map((x) => (
          <mesh key={`curtain${x}`} position={[x, curtainY, z0 + len / 2]} rotation={[0, Math.PI / 2, 0]} raycast={() => null}>
            <planeGeometry args={[len, curtainH]} />
            <meshStandardMaterial color={palette.plastic} transparent opacity={0.2} side={THREE.DoubleSide} depthWrite={false} />
          </mesh>
        ))}
    </group>
  );
}
