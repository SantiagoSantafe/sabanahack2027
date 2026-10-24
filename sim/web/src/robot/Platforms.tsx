import { RoundedBox } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import * as THREE from 'three';
import { palette } from '../theme/palette';

type Anim = { speedRef: React.MutableRefObject<number> };

/** Two-legged walker (alternative D). Forward = +Z. */
export function HumanoidModel({ speedRef, human = false }: Anim & { human?: boolean }) {
  const l = useRef<THREE.Group>(null);
  const r = useRef<THREE.Group>(null);
  const al = useRef<THREE.Group>(null);
  const ar = useRef<THREE.Group>(null);
  const ph = useRef(0);
  useFrame((_, dt) => {
    const v = speedRef.current;
    ph.current += dt * (v > 0.02 ? 1.8 + v * 2 : 0) * Math.PI * 2;
    const a = Math.min(1, v / 0.4) * 0.45 * Math.sin(ph.current);
    if (l.current) l.current.rotation.x = a;
    if (r.current) r.current.rotation.x = -a;
    if (al.current) al.current.rotation.x = -a * 0.8;
    if (ar.current) ar.current.rotation.x = a * 0.8;
  });
  const body = human ? '#3D6FB5' : palette.robotShell;
  const limb = human ? '#3B3B48' : palette.robotBody;
  const H = human ? 1.7 : 1.32;
  const legLen = H * 0.47;
  return (
    <group>
      {[
        [l, 0.09],
        [r, -0.09],
      ].map(([ref, x], k) => (
        <group key={k} ref={ref as React.RefObject<THREE.Group>} position={[x as number, legLen, 0]}>
          <mesh position={[0, -legLen / 2, 0]} castShadow>
            <capsuleGeometry args={[0.055, legLen - 0.1, 4, 10]} />
            <meshStandardMaterial color={limb} />
          </mesh>
        </group>
      ))}
      <RoundedBox args={[0.34, H * 0.3, 0.2]} radius={0.06} position={[0, legLen + H * 0.15, 0]} castShadow>
        <meshStandardMaterial color={body} roughness={0.5} />
      </RoundedBox>
      {[
        [al, 0.22],
        [ar, -0.22],
      ].map(([ref, x], k) => (
        <group key={k} ref={ref as React.RefObject<THREE.Group>} position={[x as number, legLen + H * 0.28, 0]}>
          <mesh position={[0, -H * 0.14, 0]} castShadow>
            <capsuleGeometry args={[0.04, H * 0.22, 4, 8]} />
            <meshStandardMaterial color={limb} />
          </mesh>
        </group>
      ))}
      <mesh position={[0, legLen + H * 0.38, 0]} castShadow>
        <sphereGeometry args={[0.11, 16, 12]} />
        <meshStandardMaterial color={human ? '#C98E62' : palette.robotShell} />
      </mesh>
      {human ? (
        <mesh position={[0, legLen + H * 0.45, 0]}>
          <cylinderGeometry args={[0.2, 0.2, 0.03, 20]} />
          <meshStandardMaterial color="#E9D8A6" />
        </mesh>
      ) : (
        <mesh position={[0, legLen + H * 0.39, 0.09]}>
          <boxGeometry args={[0.16, 0.05, 0.03]} />
          <meshBasicMaterial color={palette.sensorBeam} toneMapped={false} />
        </mesh>
      )}
    </group>
  );
}

/** Wheeled base with tall torso and camera head (alternative E). */
export function WheeledModel({ speedRef }: Anim) {
  const wheels = useRef<THREE.Group>(null);
  useFrame((_, dt) => {
    wheels.current?.children.forEach((w) => (w.rotation.x += (speedRef.current / 0.16) * dt));
  });
  return (
    <group>
      <RoundedBox args={[0.6, 0.22, 0.95]} radius={0.05} position={[0, 0.27, 0]} castShadow>
        <meshStandardMaterial color="#F2B630" roughness={0.45} />
      </RoundedBox>
      <group ref={wheels}>
        {[
          [0.34, 0.33],
          [-0.34, 0.33],
          [0.34, -0.33],
          [-0.34, -0.33],
        ].map(([x, z], k) => (
          <mesh key={k} position={[x, 0.16, z]} rotation={[0, 0, Math.PI / 2]} castShadow>
            <cylinderGeometry args={[0.16, 0.16, 0.1, 18]} />
            <meshStandardMaterial color="#202228" roughness={0.9} />
          </mesh>
        ))}
      </group>
      <mesh position={[0, 0.9, -0.15]} castShadow>
        <cylinderGeometry args={[0.03, 0.04, 1.1, 10]} />
        <meshStandardMaterial color="#C8CDD8" metalness={0.5} />
      </mesh>
      <RoundedBox args={[0.2, 0.12, 0.16]} radius={0.03} position={[0, 1.45, -0.1]} castShadow>
        <meshStandardMaterial color={palette.robotBody} />
      </RoundedBox>
    </group>
  );
}

/** Compact sprayer with camera kit on the boom (alternative C). */
export function SprayerModel({ speedRef }: Anim) {
  const mist = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!mist.current) return;
    const m = mist.current.material as THREE.MeshBasicMaterial;
    m.opacity = speedRef.current > 0.05 ? 0.18 + 0.08 * Math.sin(clock.elapsedTime * 8) : 0;
  });
  return (
    <group>
      <RoundedBox args={[0.9, 0.5, 1.4]} radius={0.08} position={[0, 0.55, 0]} castShadow>
        <meshStandardMaterial color="#D63C2F" roughness={0.45} />
      </RoundedBox>
      <mesh position={[0, 0.95, -0.25]} rotation={[Math.PI / 2, 0, 0]} castShadow>
        <cylinderGeometry args={[0.32, 0.32, 0.7, 20]} />
        <meshStandardMaterial color="#F3F5FF" roughness={0.3} />
      </mesh>
      {[0.42, -0.42].map((x) =>
        [0.5, -0.5].map((z) => (
          <mesh key={`${x}${z}`} position={[x, 0.3, z]} rotation={[0, 0, Math.PI / 2]} castShadow>
            <cylinderGeometry args={[0.3, 0.3, 0.16, 18]} />
            <meshStandardMaterial color="#202228" />
          </mesh>
        )),
      )}
      <mesh position={[-0.9, 1.0, 0.6]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.02, 0.02, 1.4, 6]} />
        <meshStandardMaterial color="#555" />
      </mesh>
      <mesh ref={mist} position={[-1.2, 0.9, 0.6]}>
        <sphereGeometry args={[0.6, 12, 10]} />
        <meshBasicMaterial color="#E8F4FF" transparent opacity={0} depthWrite={false} />
      </mesh>
    </group>
  );
}
