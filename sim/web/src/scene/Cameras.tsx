import { OrbitControls, PerspectiveCamera } from '@react-three/drei';
import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import type { OrbitControls as OrbitImpl } from 'three-stdlib';
import { robotRenderPose, useStore } from '../state/store';
import type { FieldGeom } from './geometry';

const _target = new THREE.Vector3();
const _pos = new THREE.Vector3();

function overview(g: FieldGeom): { pos: [number, number, number]; target: [number, number, number] } {
  const w = g.x1 - g.x0;
  return {
    pos: [g.x1 + w * 0.55, w * 0.95, g.bed_z0 - w * 0.75],
    target: [(g.x0 + g.x1) / 2, 0.5, g.bed_z0 + (g.bed_z1 - g.bed_z0) * 0.3],
  };
}

export function Cameras({ g }: { g: FieldGeom }) {
  const mode = useStore((s) => s.cameraMode);
  const camRef = useRef<THREE.PerspectiveCamera>(null);
  const orbit = useRef<OrbitImpl>(null);
  const t = useRef(0);
  const { size } = useThree();
  const view = overview(g);

  const curve = useMemo(() => {
    const w = (g.x1 - g.x0) / 2;
    const cx = (g.x0 + g.x1) / 2;
    return new THREE.CatmullRomCurve3(
      [
        new THREE.Vector3(cx - w * 0.3, 5, g.bed_z0 - 12),
        new THREE.Vector3(cx + w * 1.4, 7, g.bed_z0 - 2),
        new THREE.Vector3(cx + w * 1.3, 5, g.bed_z0 + 25),
        new THREE.Vector3(cx + w * 0.2, 2.6, g.bed_z0 + 12),
        new THREE.Vector3(cx - w * 1.3, 6, g.bed_z0 + 4),
        new THREE.Vector3(cx - w * 0.9, 10, g.bed_z0 - 8),
      ],
      true,
      'centripetal',
    );
  }, [g.x0, g.x1, g.bed_z0]);

  useEffect(() => {
    if (mode !== 'orbit' || !camRef.current) return;
    camRef.current.position.set(...view.pos);
    orbit.current?.target.set(...view.target);
    orbit.current?.update();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, g.x0, g.x1, g.bed_z0]);

  useFrame((_, dt) => {
    const cam = camRef.current;
    if (!cam) return;
    if ((mode === 'follow' || mode === 'side') && robotRenderPose.valid) {
      const p = robotRenderPose;
      const sx = Math.sin(p.heading);
      const cz = Math.cos(p.heading);
      if (mode === 'follow') {
        _target.set(p.x + sx * 1.4, 0.7, p.z + cz * 1.4);
        _pos.set(p.x - sx * 3.0, 2.0, p.z - cz * 3.0);
      } else {
        _target.set(p.x + sx * 0.3, 0.35, p.z + cz * 0.3);
        _pos.set(p.x + cz * 0.45 + sx * 1.7, 0.8, p.z - sx * 0.45 + cz * 1.7);
      }
      cam.position.x = THREE.MathUtils.damp(cam.position.x, _pos.x, 4, dt);
      cam.position.y = THREE.MathUtils.damp(cam.position.y, _pos.y, 4, dt);
      cam.position.z = THREE.MathUtils.damp(cam.position.z, _pos.z, 4, dt);
      cam.lookAt(_target);
    } else if (mode === 'cinematic') {
      t.current = (t.current + dt * 0.015) % 1;
      cam.position.copy(curve.getPointAt(t.current));
      if (robotRenderPose.valid) _target.set(robotRenderPose.x, 0.5, robotRenderPose.z);
      else _target.set((g.x0 + g.x1) / 2, 0.5, g.bed_z0 + 10);
      cam.lookAt(_target);
    }
  });

  return (
    <>
      <PerspectiveCamera ref={camRef} makeDefault fov={size.width < 700 ? 60 : 42} near={0.1} far={500} position={view.pos} />
      {mode === 'orbit' && (
        <OrbitControls ref={orbit} makeDefault target={view.target} maxPolarAngle={Math.PI / 2.15} minDistance={2} maxDistance={140} enableDamping />
      )}
    </>
  );
}
