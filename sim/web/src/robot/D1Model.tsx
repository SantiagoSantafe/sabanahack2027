import { useFrame } from '@react-three/fiber';
import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import URDFLoader from 'urdf-loader';
import { palette } from '../theme/palette';
import { cadence, D1, LEGS, trotGait, type JointAngles } from './gait';

type URDFRobot = THREE.Object3D & { setJointValue: (name: string, ...v: number[]) => boolean };

let urdfPromise: Promise<URDFRobot> | null = null;

/** Load the official URDF once per page; reused across remounts. */
function loadUrdf(): Promise<URDFRobot> {
  if (urdfPromise) return urdfPromise;
  urdfPromise = new Promise<URDFRobot>((resolve, reject) => {
    const manager = new THREE.LoadingManager();
    const loader = new URDFLoader(manager);
    const shell = new THREE.MeshStandardMaterial({ color: palette.robotShell, metalness: 0.25, roughness: 0.4 });
    const dark = new THREE.MeshStandardMaterial({ color: palette.robotBody, metalness: 0.45, roughness: 0.35 });
    const foot = new THREE.MeshStandardMaterial({ color: '#15171F', roughness: 0.7 });
    let robotObj: URDFRobot | null = null;
    let failed = false;
    const timer = window.setTimeout(() => reject(new Error('URDF load timeout')), 20000);
    manager.onError = () => {
      failed = true;
    };
    manager.onLoad = () => {
      window.clearTimeout(timer);
      if (robotObj && !failed) resolve(robotObj);
      else reject(new Error('URDF meshes failed'));
    };
    loader.loadMeshCb = (path, mgr, _urdfMaterial, done) => {
      const file = path.split('/').pop() ?? path;
      const name = file.toUpperCase();
      new STLLoader(mgr).load(
        `/d1/meshes/${file}`,
        (geom) => {
          geom.computeVertexNormals();
          const mat = name.includes('FOOT') ? foot : name.includes('KNEE') ? dark : shell;
          const mesh = new THREE.Mesh(geom, mat);
          mesh.castShadow = true;
          done(mesh);
        },
        undefined,
        () => {
          failed = true;
          done(new THREE.Object3D());
        },
      );
    };
    loader.load(
      '/d1/urdf/ultra.urdf',
      (robot) => {
        robotObj = robot as unknown as URDFRobot;
      },
      undefined,
      (err) => {
        window.clearTimeout(timer);
        reject(err);
      },
    );
  });
  urdfPromise.catch(() => {
    urdfPromise = null;
  });
  return urdfPromise;
}

type Props = {
  speedRef: React.MutableRefObject<number>;
  inspectRef: React.MutableRefObject<number>;
  /** The URDF object can live in one scene only; compare views use the procedural twin. */
  procedural?: boolean;
};

/** Procedural D1 in URDF frame (Z-up, X forward), same joint names as the official model. */
function ProceduralD1({ joints }: { joints: React.MutableRefObject<Record<string, THREE.Object3D>> }) {
  const legs = useMemo(
    () =>
      LEGS.map((leg) => ({
        leg,
        x: leg[0] === 'F' ? D1.hipX : -D1.hipX,
        y: leg[1] === 'L' ? D1.hipY : -D1.hipY,
        side: leg[1] === 'L' ? 1 : -1,
      })),
    [],
  );
  return (
    <group>
      <mesh castShadow>
        <boxGeometry args={[0.46, 0.2, 0.12]} />
        <meshStandardMaterial color={palette.robotShell} metalness={0.25} roughness={0.4} />
      </mesh>
      <mesh position={[0.27, 0, 0.01]} castShadow>
        <boxGeometry args={[0.08, 0.17, 0.09]} />
        <meshStandardMaterial color={palette.robotBody} metalness={0.4} roughness={0.35} />
      </mesh>
      <mesh position={[0, 0, 0.065]}>
        <boxGeometry args={[0.3, 0.12, 0.01]} />
        <meshStandardMaterial color={palette.robotAccent} />
      </mesh>
      {legs.map((l) => (
        <group key={l.leg} position={[l.x, l.y, 0]} ref={(o) => o && (joints.current[`${l.leg}_ABAD_JOINT`] = o)}>
          <mesh rotation={[0, Math.PI / 2, 0]}>
            <cylinderGeometry args={[0.045, 0.045, 0.08, 14]} />
            <meshStandardMaterial color={palette.robotBody} />
          </mesh>
          <group position={[0, l.side * D1.abadOffset, 0]} ref={(o) => o && (joints.current[`${l.leg}_HIP_JOINT`] = o)}>
            <mesh position={[0, 0, -D1.thigh / 2]} castShadow>
              <boxGeometry args={[0.05, 0.035, D1.thigh]} />
              <meshStandardMaterial color={palette.robotShell} />
            </mesh>
            <group position={[0, 0, -D1.thigh]} ref={(o) => o && (joints.current[`${l.leg}_KNEE_JOINT`] = o)}>
              <mesh position={[0, 0, -D1.calf / 2]} castShadow>
                <boxGeometry args={[0.03, 0.025, D1.calf]} />
                <meshStandardMaterial color={palette.robotBody} />
              </mesh>
              <mesh position={[0, 0, -D1.calf]}>
                <sphereGeometry args={[0.022, 10, 8]} />
                <meshStandardMaterial color="#15171F" />
              </mesh>
            </group>
          </group>
        </group>
      ))}
    </group>
  );
}

/**
 * D1 quadruped in world frame: forward = +Z of the parent group, feet on y = 0.
 * Uses the official URDF when available, otherwise the procedural twin.
 */
export function D1Model({ speedRef, inspectRef, procedural = false }: Props) {
  const holder = useRef<THREE.Group>(null);
  const [robot, setRobot] = useState<URDFRobot | null>(null);
  const [fallback, setFallback] = useState(procedural);
  const joints = useRef<Record<string, THREE.Object3D>>({});
  const phase = useRef(0);
  const angles = useRef<JointAngles>({});
  const smoothInspect = useRef(0);

  useEffect(() => {
    if (procedural) return;
    let alive = true;
    loadUrdf()
      .then((r) => alive && setRobot(r))
      .catch(() => alive && setFallback(true));
    return () => {
      alive = false;
    };
  }, [procedural]);

  useEffect(() => {
    const h = holder.current;
    if (!h || !robot) return;
    h.add(robot);
    return () => {
      h.remove(robot);
    };
  }, [robot]);

  useFrame((_, dt) => {
    const speed = speedRef.current;
    phase.current += dt * cadence(speed) * Math.PI * 2 * (speed > 0.02 ? 1 : 0);
    smoothInspect.current = THREE.MathUtils.damp(smoothInspect.current, inspectRef.current, 4, dt);
    trotGait(speed, phase.current, smoothInspect.current, angles.current);
    if (robot) {
      for (const [k, v] of Object.entries(angles.current)) robot.setJointValue(k, v);
    } else {
      for (const [k, v] of Object.entries(angles.current)) {
        const o = joints.current[k];
        if (!o) continue;
        if (k.includes('ABAD')) o.rotation.x = v;
        else o.rotation.y = v;
      }
    }
  });

  return (
    <group rotation={[0, -Math.PI / 2, 0]}>
      <group rotation={[-Math.PI / 2, 0, 0]} position={[0, D1.bodyHeight, 0]}>
        <group ref={holder} />
        {(fallback || !robot) && <ProceduralD1 joints={joints} />}
      </group>
    </group>
  );
}
