import { useFrame } from '@react-three/fiber';
import { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useStore } from '../state/store';
import { palette } from '../theme/palette';
import { fieldGeom, mulberry32 } from './geometry';

/** Fog thickens only with high relative humidity, so clear days keep full color. */
export function FogController() {
  useFrame(({ scene }, dt) => {
    const rh = useStore.getState().state?.weather.RH ?? 60;
    const k = THREE.MathUtils.clamp((rh - 78) / 22, 0, 1);
    const near = 70 - 52 * k;
    const far = 260 - 200 * k;
    if (!(scene.fog instanceof THREE.Fog)) scene.fog = new THREE.Fog(palette.fog, near, far);
    const f = scene.fog as THREE.Fog;
    f.near = THREE.MathUtils.damp(f.near, near, 1.5, dt);
    f.far = THREE.MathUtils.damp(f.far, far, 1.5, dt);
  });
  return null;
}

export function Rain() {
  const state = useStore((s) => s.state);
  const g = fieldGeom(state);
  const ref = useRef<THREE.LineSegments>(null);
  const precip = state?.weather.precip ?? 0;
  const count = 1400;

  const positions = useMemo(() => {
    const rand = mulberry32(99);
    const arr = new Float32Array(count * 6);
    for (let i = 0; i < count; i++) {
      const x = (rand() - 0.5) * (g.groundW + 10);
      const y = rand() * 10;
      const z = (rand() - 0.5) * (g.groundD + 10);
      arr.set([x, y, z, x + 0.02, y + 0.35, z], i * 6);
    }
    return arr;
  }, [g.groundD, g.groundW]);

  useFrame((_, dt) => {
    const seg = ref.current;
    if (!seg || precip <= 0) return;
    const pos = seg.geometry.attributes.position as THREE.BufferAttribute;
    const arr = pos.array as Float32Array;
    const v = (9 + precip * 3) * dt;
    for (let i = 0; i < count; i++) {
      const o = i * 6;
      arr[o + 1] -= v;
      arr[o + 4] -= v;
      if (arr[o + 1] < 0) {
        arr[o + 1] += 10;
        arr[o + 4] += 10;
      }
    }
    pos.needsUpdate = true;
  });

  if (precip <= 0.05) return null;
  return (
    <lineSegments ref={ref} frustumCulled={false}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <lineBasicMaterial color="#CFE3F2" transparent opacity={Math.min(0.75, 0.3 + precip * 0.15)} />
    </lineSegments>
  );
}
