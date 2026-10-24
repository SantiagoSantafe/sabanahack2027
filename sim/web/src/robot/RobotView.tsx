import { useFrame } from '@react-three/fiber';
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { manualPose, robotRenderPose, useStore } from '../state/store';
import { palette } from '../theme/palette';
import { blocked, type FieldGeom } from '../scene/geometry';
import { D1Model } from './D1Model';
import { D1 } from './gait';
import { axis, installKeyboard } from './keyboard';
import { cameraSpec } from './labels';
import { RobotTagAnchor } from './RobotTag';
import { HumanoidModel, SprayerModel, WheeledModel } from './Platforms';
import { CameraFrustum, PlcLink, ProductionSensors, RealDetectionTag, SensorOverlays } from './SensorViz';
import { anchorTwin, odomOf, recenterPose, twin, twinPose, wrapAngle } from './twin';

const MAN_SPEED = 0.5;
const MAN_FAST = 1.5;
const TURN_RATE = 1.8;
const SEND_EVERY = 0.1;
/** Smoothing of the 10 Hz odometry (1/s). */
const TWIN_SMOOTH = 12;
const TWIN_SMOOTH_RUTA = 3.5; // posición del gemelo en Ruta real
const TWIN_TURN_RUTA = 5; // rumbo: un poco más vivo para que se note cuando mira a los lados
/** Bridge states in which the real D1 does not walk: the dead-reckoned twin stands still too. */
const STILL_STATES = new Set(['estop', 'detection_hold', 'lying', 'passive', 'sdk_error']);

type Props = { g: FieldGeom; heights: number[] | null; compact?: boolean; robotOverride?: import('../state/store').RobotSnap };

export function RobotView({ g, heights, compact = false, robotOverride }: Props) {
  const storeRobot = useStore((s) => s.state?.robot);
  const robot = robotOverride ?? storeRobot;
  const manual = useStore((s) => s.manual) && !compact;
  const showSensors = useStore((s) => s.showSensors);
  const showProd = useStore((s) => s.showProdSensors) && !compact;
  const group = useRef<THREE.Group>(null);
  const speedRef = useRef(0);
  const inspectRef = useRef(0);
  const sendT = useRef(0);
  const init = useRef(false);

  useEffect(() => {
    installKeyboard();
  }, []);

  useEffect(() => {
    if (manual && robot) {
      manualPose.x = robot.x;
      manualPose.z = robot.z;
      manualPose.heading = robot.heading;
      manualPose.active = true;
    } else {
      manualPose.active = false;
    }
    twin.anchored = false;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [manual]);

  useFrame((_, dtRaw) => {
    const grp = group.current;
    if (!grp || !robot) return;
    const dt = Math.min(dtRaw, 0.05);
    let x: number;
    let z: number;
    let heading: number;
    let speed: number;

    if (manual) {
      const rr = useStore.getState().realRobot;
      const real = rr?.connected ? rr : null;
      const odom = real && !real.telemetry_stale ? odomOf(real.telemetry) : null;
      if (twin.inicio) {
        Object.assign(manualPose, twin.inicio);
        twin.inicio = null;
        twin.anchored = false; // el siguiente cuadro ancla la odometría aquí
      }
      if (twin.recenter) {
        twin.recenter = false;
        Object.assign(manualPose, recenterPose(g, manualPose));
        twin.anchored = false;
      }
      const enRuta = real?.ruta && (real.ruta.estado === 'en_marcha' || real.ruta.estado === 'pausa') && real.ruta.gemelo;
      if (real && odom) {
        // Twin: replay the real D1's odometry from the anchor. No collisions here: the real robot is the truth.
        // En Ruta real (ruta reducida en una sala) el servidor da la pose a tamaño de campo; al terminar se re-ancla.
        if (enRuta) twin.anchored = false;
        else if (!twin.anchored || twin.linkId !== real.link_id) anchorTwin(manualPose, odom, real.link_id);
        const g = enRuta ? real.ruta!.gemelo! : null;
        const p = g ? { x: g[0], z: g[1], heading: g[2] } : twinPose(odom);
        // En Ruta real la pose viene a tamaño de campo (1 cm real = 2 m en la escena): se suaviza más para que no salte.
        const k = 1 - Math.exp(-(g ? TWIN_SMOOTH_RUTA : TWIN_SMOOTH) * dt);
        manualPose.x += (p.x - manualPose.x) * k;
        manualPose.z += (p.z - manualPose.z) * k;
        const kh = g ? 1 - Math.exp(-TWIN_TURN_RUTA * dt) : k;
        manualPose.heading += wrapAngle(p.heading - manualPose.heading) * kh;
        const t = real.telemetry;
        manualPose.speed = Math.hypot(t?.vx ?? 0, t?.vy ?? 0) + Math.abs(t?.wz ?? 0) * 0.2;
      } else {
        twin.anchored = false;
        const { fwd, turn, fast } = axis();
        // Real D1 linked without odometry: dead-reckon at the bridge's limits and stand still when it does.
        const frozen = !!real && (real.estop || real.hold_s_left > 0 || STILL_STATES.has(real.state ?? ''));
        const vSlow = real ? (real.limits?.vx_max ?? 0.4) : MAN_SPEED;
        const vFast = real ? vSlow * 2 : MAN_FAST;
        const wMax = real ? (real.limits?.wz_max ?? 0.6) : TURN_RATE;
        const gain = frozen ? 0 : 1;
        manualPose.heading += turn * wMax * dt * gain;
        const v = fwd * (fast ? vFast : vSlow) * gain;
        const nx = manualPose.x + Math.sin(manualPose.heading) * v * dt;
        const nz = manualPose.z + Math.cos(manualPose.heading) * v * dt;
        const radius = (robot.width_m ?? 0.36) / 2 + 0.05;
        const ok = (px: number, pz: number) => !blocked(g, px, pz, radius);
        if (ok(nx, nz)) {
          manualPose.x = nx;
          manualPose.z = nz;
        } else if (ok(nx, manualPose.z)) {
          manualPose.x = nx;
        } else if (ok(manualPose.x, nz)) {
          manualPose.z = nz;
        }
        manualPose.speed = Math.abs(v);
      }
      x = manualPose.x;
      z = manualPose.z;
      heading = manualPose.heading;
      speed = manualPose.speed;
      sendT.current += dt;
      if (sendT.current >= SEND_EVERY) {
        sendT.current = 0;
        useStore.getState().send?.({ cmd: 'pose', x, z, heading, speed });
      }
      grp.position.set(x, 0, z);
      grp.rotation.y = heading;
    } else {
      x = robot.x;
      z = robot.z;
      heading = robot.heading;
      speed = robot.speed;
      const far = Math.hypot(grp.position.x - x, grp.position.z - z) > 4;
      if (!init.current || far) {
        grp.position.set(x, 0, z);
        grp.rotation.y = heading;
        init.current = true;
      } else {
        grp.position.x = THREE.MathUtils.damp(grp.position.x, x, 10, dt);
        grp.position.z = THREE.MathUtils.damp(grp.position.z, z, 10, dt);
        let d = heading - grp.rotation.y;
        while (d > Math.PI) d -= Math.PI * 2;
        while (d < -Math.PI) d += Math.PI * 2;
        grp.rotation.y += d * Math.min(1, dt * 8);
      }
    }
    speedRef.current = THREE.MathUtils.damp(speedRef.current, speed, 6, dt);
    inspectRef.current = robot.state === 'inspecting' || robot.state === 'docked' || robot.state === 'charging' ? 1 : 0;
    if (!compact) {
      robotRenderPose.x = grp.position.x;
      robotRenderPose.z = grp.position.z;
      robotRenderPose.heading = grp.rotation.y;
      robotRenderPose.valid = true;
    }
  });

  if (!robot || !robot.active) return null;
  const cam = cameraSpec(robot.platform, robot.mast);
  const warn = robot.state === 'failed' || robot.state === 'stuck';
  const busy = ['walking', 'inspecting', 'manual'].includes(robot.state);

  return (
    <>
      <group ref={group}>
        {robot.platform === 'quadruped' && <D1Model speedRef={speedRef} inspectRef={inspectRef} procedural={compact} />}
        {robot.platform === 'humanoid' && <HumanoidModel speedRef={speedRef} />}
        {robot.platform === 'human' && <HumanoidModel speedRef={speedRef} human />}
        {robot.platform === 'wheeled' && <WheeledModel speedRef={speedRef} />}
        {robot.platform === 'sprayer' && <SprayerModel speedRef={speedRef} />}
        {robot.platform === 'quadruped' && robot.mast && (
          <group position={[0, 0, -0.05]}>
            <mesh position={[0, (D1.mastHeight + D1.bodyHeight) / 2 + 0.03, 0]} castShadow>
              <cylinderGeometry args={[0.014, 0.02, D1.mastHeight - D1.bodyHeight, 10]} />
              <meshStandardMaterial color="#C8CDD8" metalness={0.6} roughness={0.3} />
            </mesh>
            <mesh position={[0, D1.mastHeight, 0.06]} castShadow>
              <boxGeometry args={[0.09, 0.06, 0.1]} />
              <meshStandardMaterial color={palette.robotBody} />
            </mesh>
          </group>
        )}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
          <ringGeometry args={[0.5, 0.58, 40]} />
          <meshBasicMaterial color={warn ? palette.danger : palette.robotAccent} transparent opacity={0.85} toneMapped={false} />
        </mesh>
        {showSensors && busy && <CameraFrustum cameraH={cam.h} forward={cam.fwd} active={robot.state === 'inspecting'} />}
        {showProd && robot.platform === 'quadruped' && <ProductionSensors />}
        {!compact && <RobotTagAnchor height={Math.max(cam.h, 0.6) + 0.6} />}
      </group>
      {!compact && <SensorOverlays g={g} heights={heights} cameraH={cam.h} forward={cam.fwd} />}
      {!compact && <RealDetectionTag g={g} heights={heights} />}
      {showProd && robot.platform === 'quadruped' && <PlcLink g={g} />}
    </>
  );
}
