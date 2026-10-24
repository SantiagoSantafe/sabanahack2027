import { Html } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { robotRenderPose, useStore, type Capture } from '../state/store';
import { palette } from '../theme/palette';
import { fmt } from '../ui/format';
import { plantWorldPos, type FieldGeom } from '../scene/geometry';

const H_FOV = THREE.MathUtils.degToRad(111);
const V_FOV = THREE.MathUtils.degToRad(70);
const RANGE = 2.4;
const TAG_LIFE = 2.4;

/** Camera frustum in robot-local frame (forward = +Z), pyramid with apex at the lens. */
export function CameraFrustum({ cameraH, forward, active }: { cameraH: number; forward: number; active: boolean }) {
  const geo = useMemo(() => {
    const hw = Math.tan(H_FOV / 2) * RANGE;
    const hh = Math.tan(V_FOV / 2) * RANGE;
    const c = [
      [-hw, -hh, RANGE],
      [hw, -hh, RANGE],
      [hw, hh, RANGE],
      [-hw, hh, RANGE],
    ];
    const pos: number[] = [];
    for (let i = 0; i < 4; i++) pos.push(0, 0, 0, ...c[i], ...c[(i + 1) % 4]);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    return g;
  }, []);
  const edges = useMemo(() => new THREE.EdgesGeometry(geo), [geo]);
  const mat = useRef<THREE.MeshBasicMaterial>(null);
  useFrame(({ clock }) => {
    if (mat.current) mat.current.opacity = active ? 0.09 + 0.04 * Math.sin(clock.elapsedTime * 5) : 0.04;
  });
  return (
    <group position={[0, cameraH, forward]}>
      <mesh geometry={geo} raycast={() => null}>
        <meshBasicMaterial ref={mat} color={palette.sensorBeam} transparent opacity={0.1} side={THREE.DoubleSide} depthWrite={false} toneMapped={false} />
      </mesh>
      <lineSegments geometry={edges}>
        <lineBasicMaterial color={palette.sensorBeam} transparent opacity={0.4} toneMapped={false} />
      </lineSegments>
    </group>
  );
}

function makeLine(color: string): THREE.Line {
  const g = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]);
  const l = new THREE.Line(g, new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.6, toneMapped: false }));
  l.frustumCulled = false;
  return l;
}

const _cam = new THREE.Vector3();
const _tgt = new THREE.Vector3();

function setLine(line: THREE.Line, a: THREE.Vector3, b: THREE.Vector3, opacity: number) {
  const pos = line.geometry.getAttribute('position') as THREE.BufferAttribute;
  pos.setXYZ(0, a.x, a.y, a.z);
  pos.setXYZ(1, b.x, b.y, b.z);
  pos.needsUpdate = true;
  (line.material as THREE.LineBasicMaterial).opacity = opacity;
}

/** World-space overlays: scan beams to both rows, visible band on each bush, classification tags, ArUco reads. */
export function SensorOverlays({ g, heights, cameraH, forward }: { g: FieldGeom; heights: number[] | null; cameraH: number; forward: number }) {
  const target = useStore((s) => s.state?.robot.target ?? null);
  const captures = useStore((s) => s.state?.robot.sensors?.recent_captures ?? null);
  const aruco = useStore((s) => s.state?.robot.sensors?.last_aruco ?? null);
  const robotState = useStore((s) => s.state?.robot.state);
  const showSensors = useStore((s) => s.showSensors);

  const beams = useMemo(() => [makeLine(palette.sensorBeam), makeLine(palette.sensorBeam)], []);
  const arRays = useMemo(() => [makeLine('#FFFFFF'), makeLine('#FFFFFF')], []);
  const flash = useRef(0);
  const [tags, setTags] = useState<{ c: Capture; t: number }[]>([]);
  const [arShown, setArShown] = useState<{ beds: number[]; t: number } | null>(null);
  const [, tick] = useState(0);

  const lastSeq = captures?.length ? captures[captures.length - 1].seq : -1;
  useEffect(() => {
    if (!captures?.length) return;
    flash.current = 1;
    const now = performance.now();
    setTags(captures.map((c) => ({ c, t: now })));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastSeq]);

  const arSeq = aruco?.seq ?? -1;
  useEffect(() => {
    if (aruco) setArShown({ beds: aruco.beds, t: performance.now() });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [arSeq]);

  useEffect(() => {
    const id = window.setInterval(() => tick((v) => v + 1), 300);
    return () => window.clearInterval(id);
  }, []);

  const targets = useMemo(() => {
    if (!target) return [];
    const a = g.aisles[target[0]];
    if (!a) return [];
    return [a.left, a.right].map((bed) => {
      const [x, , z] = plantWorldPos(g, bed, target[1]);
      const h = heights?.[bed * g.nPlants + target[1]] ?? 1.5;
      return { x, z, h, frac: Math.max(0.35, Math.min(1, cameraH / h)) };
    });
  }, [target, g, heights, cameraH]);

  const walking = robotState === 'walking' || robotState === 'inspecting' || robotState === 'manual';

  useFrame((_, dt) => {
    flash.current = Math.max(0, flash.current - dt * 2.5);
    const p = robotRenderPose;
    _cam.set(p.x + Math.sin(p.heading) * forward, cameraH, p.z + Math.cos(p.heading) * forward);
    targets.forEach((tg, k) => {
      _tgt.set(tg.x, g.bedH + tg.h * tg.frac * 0.5, tg.z);
      setLine(beams[k], _cam, _tgt, 0.3 + flash.current * 0.7);
    });
    if (arShown) {
      const age = (performance.now() - arShown.t) / 1000;
      arShown.beds.forEach((bed, k) => {
        _tgt.set(g.bed_x[bed] ?? 0, 0.92, g.bed_z0 - 0.24);
        if (arRays[k]) setLine(arRays[k], _cam, _tgt, Math.max(0, 1 - age / 2.2));
      });
    }
  });

  if (!showSensors) return null;
  const now = performance.now();
  const arAge = arShown ? (now - arShown.t) / 1000 : 99;

  return (
    <group>
      {walking &&
        targets.map((tg, k) => (
          <group key={k}>
            <primitive object={beams[k]} />
            <mesh position={[tg.x, g.bedH + (tg.h * tg.frac) / 2, tg.z]} raycast={() => null}>
              <cylinderGeometry args={[0.5, 0.5, tg.h * tg.frac, 24, 1, true]} />
              <meshBasicMaterial color={palette.sensorBeam} transparent opacity={0.12} side={THREE.DoubleSide} depthWrite={false} toneMapped={false} />
            </mesh>
            <mesh position={[tg.x, g.bedH + tg.h * tg.frac, tg.z]} rotation={[-Math.PI / 2, 0, 0]}>
              <ringGeometry args={[0.47, 0.52, 32]} />
              <meshBasicMaterial color={palette.sensorBeam} side={THREE.DoubleSide} toneMapped={false} />
            </mesh>
          </group>
        ))}
      {arShown && arAge < 2.2 && arShown.beds.map((_, k) => arRays[k] && <primitive key={k} object={arRays[k]} />)}
      {arShown && arAge < 2.2 && (
        <Html position={[((g.bed_x[arShown.beds[0]] ?? 0) + (g.bed_x[arShown.beds[1]] ?? 0)) / 2, 1.35, g.bed_z0 - 0.24]} center zIndexRange={[12, 0]}>
          <div className="aruco-tag">ArUco {arShown.beds.map((b) => b + 1).join(' y ')} leídos</div>
        </Html>
      )}
      {tags.map(({ c, t }) => {
        const age = (now - t) / 1000;
        if (age > TAG_LIFE) return null;
        const [x, , z] = plantWorldPos(g, c.bed, c.plant);
        const h = heights?.[c.bed * g.nPlants + c.plant] ?? 1.5;
        return (
          <Html key={c.seq} position={[x, g.bedH + h + 0.3, z]} center zIndexRange={[12, 0]}>
            <div className={`capture-tag ${c.alert ? 'is-alert' : ''}`} style={{ opacity: Math.max(0, 1 - age / TAG_LIFE) }}>
              <span className="capture-label">
                {c.label}
                {c.score !== null && <em>{fmt(c.score * 100, 0)} %</em>}
              </span>
              {c.alert && <span className="capture-alert">Alerta registrada</span>}
            </div>
          </Html>
        );
      })}
    </group>
  );
}

const REAL_TAG_LIFE = 9;
/** Detection already shown (survives remounts, so switching views does not replay it). */
const realTagSeen = { key: '' };

/** Tag and ring on the plant where the real D1's camera flagged something (latest `real_detection`). */
export function RealDetectionTag({ g, heights }: { g: FieldGeom; heights: number[] | null }) {
  const ev = useStore((s) => s.log.findLast((e) => e.type === 'real_detection'));
  const group = useRef<THREE.Group>(null);
  const ring = useRef<THREE.Mesh>(null);
  const tag = useRef<HTMLDivElement>(null);
  const born = useRef({ key: '', t: -1e9 });
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    if (ev) {
      const key = `${ev.id}:${ev.text}`;
      if (key !== born.current.key) {
        born.current = { key, t: key === realTagSeen.key ? -1e9 : t };
        realTagSeen.key = key;
      }
    }
    const age = t - born.current.t;
    const on = !!ev && age < REAL_TAG_LIFE;
    if (group.current) group.current.visible = on;
    if (ring.current) ring.current.scale.setScalar(1 + 0.12 * Math.sin(t * 6));
    if (tag.current) {
      tag.current.style.display = on ? '' : 'none';
      tag.current.style.opacity = String(Math.min(1, (REAL_TAG_LIFE - age) / 1.5));
    }
  });
  if (!ev || ev.bed === undefined || ev.plant === undefined) return null;
  const [x, , z] = plantWorldPos(g, ev.bed, ev.plant);
  const h = heights?.[ev.bed * g.nPlants + ev.plant] ?? 1.5;
  return (
    <group ref={group}>
      <mesh ref={ring} position={[x, g.bedH + 0.04, z]} rotation={[-Math.PI / 2, 0, 0]} raycast={() => null}>
        <ringGeometry args={[0.5, 0.6, 32]} />
        <meshBasicMaterial color={palette.alertRing} side={THREE.DoubleSide} toneMapped={false} />
      </mesh>
      <Html position={[x, g.bedH + h + 0.45, z]} center zIndexRange={[13, 0]}>
        <div ref={tag} className="capture-tag is-alert is-real" style={{ display: 'none' }}>
          <span className="capture-label">{ev.text.split(' · ')[0]}</span>
          <span className="capture-alert">Incidencia registrada · °C y HR simulados</span>
        </div>
      </Html>
    </group>
  );
}

/** Legend colors of the production sensors (also used for the dots in the label). */
const PROD = {
  probe: '#8BD346',
  thermal: '#FF8A3D',
  up: '#B78CFF',
  radio: '#FFD34D',
};
const PROD_ITEMS: [string, string][] = [
  [PROD.probe, 'Sonda de T y HR en el follaje'],
  [PROD.thermal, 'Cámara térmica: hoja mojada sin contacto'],
  [PROD.up, 'Cámara hacia arriba: envés de la hoja'],
  [PROD.radio, 'LoRaWAN/Modbus al PLC del bloque'],
];
/** Antenna tip in robot-local coordinates (forward = +Z). */
const ANTENNA = new THREE.Vector3(-0.1, 0.66, -0.18);

/**
 * Production kit drawn on the D1 as an example only: none of it is mounted for the demo.
 * Robot-local frame (forward = +Z, left = +X); static meshes, no per-frame work.
 */
export function ProductionSensors() {
  return (
    <group>
      {/* T/HR probe on an arm reaching into the foliage (AGRAR: T and HR at the exact point of each detection) */}
      <group position={[0.1, 0.37, 0.05]} rotation={[0, 0, -0.9]}>
        <mesh position={[0, 0.2, 0]}>
          <cylinderGeometry args={[0.008, 0.01, 0.4, 6]} />
          <meshStandardMaterial color={palette.steel} metalness={0.5} roughness={0.4} />
        </mesh>
        {[0, 1, 2].map((k) => (
          <mesh key={k} position={[0, 0.42 + k * 0.018, 0]}>
            <cylinderGeometry args={[0.03 - k * 0.004, 0.03 - k * 0.004, 0.01, 12]} />
            <meshStandardMaterial color="#F7F8FC" />
          </mesh>
        ))}
        <mesh position={[0, 0.405, 0]}>
          <sphereGeometry args={[0.012, 8, 6]} />
          <meshBasicMaterial color={PROD.probe} toneMapped={false} />
        </mesh>
      </group>
      {/* Thermal camera next to the stock one, with its narrow field of view */}
      <group position={[-0.08, 0.37, 0.27]}>
        <mesh>
          <boxGeometry args={[0.06, 0.045, 0.05]} />
          <meshStandardMaterial color={palette.robotBody} />
        </mesh>
        <mesh position={[0, 0, 0.027]} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.014, 0.014, 0.006, 12]} />
          <meshBasicMaterial color={PROD.thermal} toneMapped={false} />
        </mesh>
        <mesh position={[0, 0, 0.47]} rotation={[-Math.PI / 2, 0, 0]} raycast={() => null}>
          <coneGeometry args={[0.32, 0.9, 16, 1, true]} />
          <meshBasicMaterial color={PROD.thermal} transparent opacity={0.08} side={THREE.DoubleSide} depthWrite={false} toneMapped={false} />
        </mesh>
      </group>
      {/* Upward camera for the underside of the leaves */}
      <group position={[0.04, 0.39, 0.12]} rotation={[0.4, 0, 0]}>
        <mesh>
          <cylinderGeometry args={[0.022, 0.026, 0.03, 12]} />
          <meshStandardMaterial color={palette.robotBody} />
        </mesh>
        <mesh position={[0, 0.017, 0]}>
          <cylinderGeometry args={[0.014, 0.014, 0.004, 12]} />
          <meshBasicMaterial color={PROD.up} toneMapped={false} />
        </mesh>
        <mesh position={[0, 0.47, 0]} rotation={[Math.PI, 0, 0]} raycast={() => null}>
          <coneGeometry args={[0.42, 0.9, 16, 1, true]} />
          <meshBasicMaterial color={PROD.up} transparent opacity={0.07} side={THREE.DoubleSide} depthWrite={false} toneMapped={false} />
        </mesh>
      </group>
      {/* LoRaWAN antenna */}
      <mesh position={[ANTENNA.x, (0.37 + ANTENNA.y) / 2, ANTENNA.z]}>
        <cylinderGeometry args={[0.005, 0.007, ANTENNA.y - 0.37, 6]} />
        <meshStandardMaterial color="#2B2F3A" />
      </mesh>
      <mesh position={ANTENNA}>
        <sphereGeometry args={[0.014, 8, 6]} />
        <meshBasicMaterial color={PROD.radio} toneMapped={false} />
      </mesh>
      <Html position={[-0.8, 0.55, 0]} center zIndexRange={[11, 0]}>
        <div className="prod-tag">
          <b>Ejemplo · no montado en la demo</b>
          {PROD_ITEMS.map(([c, t]) => (
            <span key={t}>
              <i style={{ background: c }} />
              {t}
            </span>
          ))}
        </div>
      </Html>
    </group>
  );
}

const LINK_RANGE_M = 16;
const _ant = new THREE.Vector3();

function showLink(line: THREE.Line, a: THREE.Vector3, b: THREE.Vector3, opacity: number, on: boolean) {
  line.visible = on;
  if (!on) return;
  setLine(line, a, b, opacity);
  line.computeLineDistances();
}

/**
 * Example PLC cabinet at the head of the block and the store-and-forward radio link: there is no
 * network inside the block, so the robot keeps its records and hands them over when in range.
 */
export function PlcLink({ g }: { g: FieldGeom }) {
  const pos = useMemo(() => new THREE.Vector3(g.base[0] + 2.6, 0, g.base[1] - 0.9), [g.base]);
  const tip = useMemo(() => new THREE.Vector3(pos.x, 1.95, pos.z), [pos]);
  const line = useMemo(() => {
    const geo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]);
    const l = new THREE.Line(geo, new THREE.LineDashedMaterial({ color: PROD.radio, dashSize: 0.35, gapSize: 0.2, transparent: true, opacity: 0.8, toneMapped: false }));
    l.frustumCulled = false;
    return l;
  }, []);
  const led = useRef<THREE.MeshBasicMaterial>(null);
  useFrame(({ clock }) => {
    const p = robotRenderPose;
    const c = Math.cos(p.heading);
    const s = Math.sin(p.heading);
    _ant.set(p.x + ANTENNA.x * c + ANTENNA.z * s, ANTENNA.y, p.z - ANTENNA.x * s + ANTENNA.z * c);
    const inRange = p.valid && _ant.distanceTo(tip) < LINK_RANGE_M;
    showLink(line, _ant, tip, 0.45 + 0.35 * Math.sin(clock.elapsedTime * 4), inRange);
    if (led.current) led.current.color.set(inRange ? PROD.radio : '#5A5F70');
  });
  return (
    <group>
      <primitive object={line} />
      <group position={pos}>
        <mesh position={[0, 0.6, 0]} castShadow>
          <cylinderGeometry args={[0.04, 0.05, 1.2, 8]} />
          <meshStandardMaterial color={palette.steel} metalness={0.5} roughness={0.35} />
        </mesh>
        <mesh position={[0, 1.35, 0]} castShadow>
          <boxGeometry args={[0.5, 0.6, 0.22]} />
          <meshStandardMaterial color="#C9CED8" roughness={0.5} />
        </mesh>
        <mesh position={[0.17, 1.55, 0.115]}>
          <sphereGeometry args={[0.02, 8, 6]} />
          <meshBasicMaterial ref={led} color="#5A5F70" toneMapped={false} />
        </mesh>
        <mesh position={[0, 1.8, 0]}>
          <cylinderGeometry args={[0.008, 0.01, 0.3, 6]} />
          <meshStandardMaterial color="#2B2F3A" />
        </mesh>
        <Html position={[0, 2.35, 0]} center zIndexRange={[11, 0]}>
          <div className="prod-tag">
            <b>Ejemplo · no montado en la demo</b>
            <span>
              <i style={{ background: PROD.radio }} />
              Gabinete PLC del bloque (LoRaWAN/Modbus)
            </span>
            <small>Sin red en el bloque: el robot guarda y reenvía al pasar cerca</small>
          </div>
        </Html>
      </group>
    </group>
  );
}
